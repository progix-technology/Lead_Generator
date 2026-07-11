import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List

from app.config.settings import settings
from app.repositories.automation import AutomationRepository
from app.repositories.company import CompanyRepository
from app.services.company import CompanyService
from app.services.places import search_companies_google_places
from app.services.email_scraper import find_email_for_company
from app.services.email_verifier import verify_email_existence
from app.services.email_sender import send_smtp_email
from app.services.llm_service import clean_first_name_with_ai

logger = logging.getLogger(__name__)

# Global list to track live progress of the automation cycle for frontend display
automation_progress: List[str] = []

def log_progress(msg: str):
    global automation_progress
    logger.info(msg)
    timestamp = datetime.now().strftime("%H:%M:%S")
    automation_progress.append(f"[{timestamp}] {msg}")

CATEGORIES = [
    "Carpenters", "Locksmiths", "Paving Contractors", "Painting Contractors",
    "Window Cleaning", "Carpet Cleaning", "House Cleaning", "Tree Services",
    "Drywall Contractors", "Concrete Contractors", "Fence Contractors", "Moving Companies",
    "Towing Services", "Appliance Repair", "Junk Removal", "Physiotherapists",
    "Chiropractors", "Veterinarians", "Acupuncture Clinics", "Optometrists",
    "Yoga Studios", "Dance Schools", "Daycare Centers", "Driving Schools", "Tailor Shops",
    "Roofing Contractors", "HVAC Services", "Plumbers", "Electricians", "Dentists",
    "Catering Services", "Auto Repair"
]
LOCATIONS = [
    "Sunnyvale, CA", "Santa Clara, CA", "Mountain View, CA", "Palo Alto, CA",
    "San Mateo, CA", "Redwood City, CA", "Fremont, CA", "Pleasanton, CA",
    "San Ramon, CA", "Walnut Creek, CA", "Concord, CA", "Bakersfield, CA",
    "Modesto, CA", "Stockton, CA", "Sacramento, CA", "Elk Grove, CA",
    "Rancho Cordova, CA", "Davis, CA", "Woodland, CA", "Napa, CA",
    "San Rafael, CA", "Novato, CA", "Petaluma, CA", "Santa Rosa, CA", "Berkeley, CA"
]

async def run_automation_cycle(db) -> Dict[str, Any]:
    """
    Runs a single autopilot lead generation & outreach cycle.
    Queries Google Places, filters for website-less leads, crawls emails,
    checks for Facebook source, SMTP verifies them, and auto-sends pitches.
    """
    global automation_progress
    automation_progress.clear()
    
    log_progress("Autopilot: Initializing automated outreach cycle...")
    
    repo = AutomationRepository(db)
    co_repo = CompanyRepository(db)
    co_service = CompanyService(co_repo)

    current_settings = await repo.get_settings()
    daily_limit = current_settings.get("daily_email_limit", 20)
    
    # 1. Check daily limit
    sent_today = await repo.count_records_today()
    log_progress(f"Autopilot: Daily limit check. Emails sent today: {sent_today}/{daily_limit}")
    if sent_today >= daily_limit:
        log_progress(f"Autopilot: Daily limit of {daily_limit} emails already reached for today. Cycle stopped.")
        return {"status": "skipped", "reason": "daily_limit_reached"}

    limit_to_send = daily_limit - sent_today
    log_progress(f"Autopilot: Autopilot will target sending up to {limit_to_send} emails in this run.")

    # 2. Get search terms (AI recommended or rotation fallback)
    use_ai_targets = current_settings.get("use_ai_targets", True)
    openrouter_key = current_settings.get("openrouter_api_key")
    
    category = None
    location = None
    
    if use_ai_targets and openrouter_key:
        try:
            log_progress("Autopilot: Invoking AI to recommend a high-converting search target...")
            cursor = db["automation_records"].find({}).sort("created_at", -1).limit(15)
            recent_records = [doc async for doc in cursor]
            recent_targets = [f"{r.get('category')} | {r.get('location')}" for r in recent_records if r.get('category')]
            
            from app.services.llm_service import generate_ai_search_query
            category, location = await generate_ai_search_query(recent_targets, openrouter_key)
            log_progress(f"Autopilot: AI Recommended target ➔ Category: '{category}' | Location: '{location}'!")
        except Exception as e:
            log_progress(f"Autopilot: Warning: AI target recommendation failed: {e}. Falling back to rotation index.")
            
    if not category or not location:
        search_index = current_settings.get("search_index", 0)
        categories = current_settings.get("categories") or CATEGORIES
        locations = current_settings.get("locations") or LOCATIONS
        category = categories[search_index % len(categories)]
        location = locations[(search_index // len(categories)) % len(locations)]
        log_progress(f"Autopilot: Selected target category: '{category}' | location: '{location}' (Index: {search_index})")
        # Increment search index
        await repo.update_settings({"search_index": search_index + 1})

    # 3. Search Google Places fallback scraper
    log_progress(f"Autopilot: Fetching local businesses from Google Maps...")
    results, _ = await search_companies_google_places(category, location)
    if not results:
        log_progress("Autopilot: No local businesses found for this category and location.")
        return {"status": "completed", "sent_count": 0, "scanned_count": 0}

    log_progress(f"Autopilot: Found {len(results)} local businesses. Starting website filters...")
    scanned_count = 0
    sent_count = 0

    # 5. Process results
    for company in results:
        if sent_count >= limit_to_send:
            log_progress("Autopilot: Daily campaign outreach target of 10 reached. Halting cycle.")
            break

        scanned_count += 1
        name = company.get("name")
        address = company.get("address", "")
        website_url = company.get("website_url")

        # ONLY target leads without a website!
        if website_url:
            log_progress(f"Autopilot: Lead '{name}' has website: {website_url} (skipped)")
            continue

        # Prevent duplicate outreach: check if already exists in DB
        existing = await co_repo.collection.find_one({"name": name})
        if existing:
            log_progress(f"Autopilot: Lead '{name}' is already saved in database (skipped)")
            continue

        log_progress(f"Autopilot: Target match! Processing '{name}'...")

        # Deep crawl emails
        try:
            log_progress(f"Autopilot: Crawling social profiles and searching contact info for '{name}'...")
            email, discovered_web, email_source = await find_email_for_company(name, location)
            
            facebook_only = current_settings.get("facebook_only", False)
            if not email:
                log_progress(f"Autopilot: No contact emails discovered for '{name}'.")
                continue
                
            allowed_sources = ["Facebook"] if facebook_only else ["Facebook", "Instagram", "LinkedIn"]
            if email_source not in allowed_sources:
                log_progress(f"Autopilot: Email '{email}' found for '{name}' via '{email_source}' (skipped - source must be in {allowed_sources})")
                continue

            log_progress(f"Autopilot: Verified email '{email}' found via {email_source}! Performing SMTP mailbox validation...")

            # SMTP Verification Check
            is_valid, _ = await verify_email_existence(email)
            if not is_valid:
                log_progress(f"Autopilot: Email '{email}' failed active mailbox validation checks (skipped).")
                continue

            log_progress(f"Autopilot: Email '{email}' validated successfully. Running AI greeting name extraction...")

            # Resolve Smart Greeting Name via AI
            greeting_name = await clean_first_name_with_ai(email, name, custom_api_key=current_settings.get("openrouter_api_key"))
            if not greeting_name:
                greeting_name = name.split()[0] if name else "Team"
            
            log_progress(f"Autopilot: AI extracted greeting name: '{greeting_name}'")

            # Parse template placeholders
            subject_tmpl = current_settings.get("subject_template", "")
            body_tmpl = current_settings.get("body_template", "")

            # Personalize placeholders
            co_website = "your business"
            co_industry = category
            co_location = location or "your area"
            current_platform = "Facebook"
            service_type = "custom website design"

            subject = subject_tmpl.replace("{{company}}", name)\
                                  .replace("{{first_name}}", greeting_name)\
                                  .replace("{{website}}", co_website)\
                                  .replace("{{industry}}", co_industry)\
                                  .replace("{{location}}", co_location)\
                                  .replace("{{current_platform}}", current_platform)\
                                  .replace("{{service_type}}", service_type)

            body = body_tmpl.replace("{{company}}", name)\
                            .replace("{{first_name}}", greeting_name)\
                            .replace("{{website}}", co_website)\
                            .replace("{{industry}}", co_industry)\
                            .replace("{{location}}", co_location)\
                            .replace("{{current_platform}}", current_platform)\
                            .replace("{{service_type}}", service_type)

            html_body = f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"

            log_progress(f"Autopilot: Dispatching outreach email to '{email}'...")
            # Send the email!
            success = await send_smtp_email(email, subject, html_body, smtp_config=current_settings)

            # Save lead to companies collection (to prevent double emails in future)
            await co_repo.create({
                "name": name,
                "industry": category,
                "location": location or address,
                "website": None,
                "phone": company.get("phone_number"),
                "email": email,
                "email_source": "Facebook",
                "status": "Emailed" # Marked as emailed immediately
            })

            if success:
                # Log success to automation_records
                await repo.create_record({
                    "company_name": name,
                    "email": email,
                    "category": category,
                    "location": location,
                    "subject": subject,
                    "body": body,
                    "status": "Sent",
                    "error_message": None
                })
                sent_count += 1
                log_progress(f"Autopilot: ✓ Outreach email successfully delivered to '{name}' at '{email}'!")
            else:
                # Log failure
                await repo.create_record({
                    "company_name": name,
                    "email": email,
                    "category": category,
                    "location": location,
                    "subject": subject,
                    "body": body,
                    "status": "Failed",
                    "error_message": "SMTP send failed"
                })
                log_progress(f"Autopilot: ✕ Failed to send SMTP email to '{name}' at '{email}'")

        except Exception as err:
            log_progress(f"Autopilot: Error processing lead '{name}': {err}")

    log_progress(f"Autopilot: Cycle complete. Scanned: {scanned_count} leads, Sent: {sent_count} emails.")
    log_progress("Autopilot: Scheduler sleeping for 30 minutes. Next run will start soon...")
    return {"status": "completed", "sent_count": sent_count, "scanned_count": scanned_count}

async def run_automation_scheduler():
    """
    Autopilot worker loop. Runs natively in the FastAPI event loop.
    Checks status every 30 minutes.
    """
    logger.info("Autopilot: Background scheduler loop started.")
    await asyncio.sleep(15) # Let application startup fully
    
    from app.database.connection import get_database
    db = get_database()
    
    while True:
        try:
            repo = AutomationRepository(db)
            config = await repo.get_settings()
            if config.get("enabled", False):
                sent_today = await repo.count_records_today()
                daily_limit = config.get("daily_email_limit", 20)
                
                now = datetime.now()
                current_hour = now.hour
                
                is_active_window = 10 <= current_hour < 12
                # If we haven't reached our daily email limit, keep running catch-up cycles until 10:00 PM (22:00)!
                is_catchup_window = (12 <= current_hour < 22) and (sent_today < daily_limit)
                
                if is_active_window or is_catchup_window:
                    logger.info(f"Autopilot: Starting automated batch run (Hour: {current_hour}, Sent today: {sent_today}/{daily_limit})...")
                    
                    batch_sent = 0
                    batch_target = 5  # Target sending at least 5 emails in this scheduler wake-up run
                    max_attempts = 5  # Maximum different target query attempts to prevent API/loop exhaustion
                    attempts = 0
                    
                    while batch_sent < batch_target and attempts < max_attempts:
                        # Re-read daily limits status mid-batch
                        current_sent_today = await repo.count_records_today()
                        if current_sent_today >= daily_limit:
                            logger.info("Autopilot: Daily email limit reached mid-batch. Halting batch run.")
                            break
                            
                        logger.info(f"Autopilot: Batch run attempt {attempts + 1}/{max_attempts} (Sent in this batch: {batch_sent}/{batch_target})")
                        cycle_result = await run_automation_cycle(db)
                        
                        cycle_sent = cycle_result.get("sent_count", 0)
                        batch_sent += cycle_sent
                        attempts += 1
                        
                        if batch_sent >= batch_target:
                            logger.info(f"Autopilot: Batch target of {batch_target} emails reached. Ending batch run.")
                            break
                            
                        if cycle_sent == 0:
                            log_progress(f"Autopilot: Cycle sent 0 emails. Auto-switching to next target niche...")
                            await asyncio.sleep(2) # Small safety gap
                            
                    logger.info(f"Autopilot: Batch run completed. Total sent in this run: {batch_sent} over {attempts} attempts.")
                else:
                    logger.info(f"Autopilot: Outside active/catch-up window (Hour: {current_hour}, Sent: {sent_today}/{daily_limit}). Skipping.")
            else:
                logger.info("Autopilot: Autopilot is disabled. Sleeping...")
        except Exception as e:
            logger.error(f"Autopilot: Scheduler loop error: {e}")
            
        # Check every 30 minutes
        await asyncio.sleep(1800)
