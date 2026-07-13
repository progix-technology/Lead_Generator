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
is_batch_running: bool = False
last_log_date = None

def is_directory_url(url: str) -> bool:
    """Helper to detect if a URL is a directory listing profile (like Yelp) rather than a custom business website."""
    if not url:
        return False
    url_lower = url.lower()
    directories = [
        'yelp.com', 'facebook.com', 'instagram.com', 'apple.com/place', 'maps.apple.com',
        'yellowpages.com', 'yp.com', 'foursquare.com', 'bbb.org', 'manta.com',
        'tripadvisor.com', 'angi.com', 'houzz.com', 'chamberofcommerce.com', 'local.yahoo.com'
    ]
    return any(domain in url_lower for domain in directories)

def log_progress(msg: str):
    global automation_progress, last_log_date
    logger.info(msg)
    from zoneinfo import ZoneInfo
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_date = ist_now.strftime("%Y-%m-%d")
    
    # Auto-clear logs when the day changes to keep only the current day's data
    if last_log_date is not None and last_log_date != current_date:
        automation_progress.clear()
        
    last_log_date = current_date
    timestamp = ist_now.strftime("%H:%M:%S")
    automation_progress.append(f"[{timestamp}] {msg}")

CATEGORIES = [
    "Carpenters", "Locksmiths", "Paving Contractors", "Painting Contractors",
    "Window Cleaning", "Carpet Cleaning", "House Cleaning", "Tree Services",
    "Drywall Contractors", "Concrete Contractors", "Fence Contractors", "Moving Companies",
    "Towing Services", "Appliance Repair", "Junk Removal", "Physiotherapists",
    "Chiropractors", "Veterinarians", "Acupuncture Clinics", "Optometrists",
    "Yoga Studios", "Dance Schools", "Daycare Centers", "Driving Schools", "Tailor Shops",
    "Roofing Contractors", "HVAC Services", "Plumbers", "Electricians", "Dentists",
    "Catering Services", "Auto Repair",
    "Cosmetic Dentists", "Orthodontists", "IVF Clinics", "Medical Spas", "Corporate Lawyers", "Accountants",
    "Solar Panel Installers", "Swimming Pool Builders", "Custom Home Builders", "Commercial HVAC", "Commercial Roofing", "Interior Designers",
    "Logistics Companies", "Consulting Agencies", "Corporate Event Planners"
]
LOCATIONS = [
    "Sunnyvale, CA", "Santa Clara, CA", "Mountain View, CA", "Palo Alto, CA",
    "San Mateo, CA", "Redwood City, CA", "Fremont, CA", "Pleasanton, CA",
    "San Ramon, CA", "Walnut Creek, CA", "Concord, CA", "Bakersfield, CA",
    "Modesto, CA", "Stockton, CA", "Sacramento, CA", "Elk Grove, CA",
    "Rancho Cordova, CA", "Davis, CA", "Woodland, CA", "Napa, CA",
    "San Rafael, CA", "Novato, CA", "Petaluma, CA", "Santa Rosa, CA", "Berkeley, CA"
]

async def run_automation_cycle(db, batch_targets: list = None) -> Dict[str, Any]:
    """
    Runs a single autopilot lead generation & outreach cycle.
    Queries Google Places, filters for website-less leads, crawls emails,
    checks for Facebook source, SMTP verifies them, and auto-sends pitches.
    """
    global automation_progress
    
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
    # Prioritize manual search terms if configured by the user, bypassing AI lookup to ensure manual targets are respected
    categories_list = current_settings.get("categories")
    use_ai_targets = False if categories_list else current_settings.get("use_ai_targets", True)
    openrouter_key = current_settings.get("openrouter_api_key")
    
    category = None
    location = None
    
    if use_ai_targets and openrouter_key:
        try:
            log_progress("Autopilot: Invoking AI to recommend a high-converting search target...")
            cursor = db["automation_records"].find({}).sort("created_at", -1).limit(15)
            recent_records = [doc async for doc in cursor]
            recent_targets = [f"{r.get('category')} | {r.get('location')}" for r in recent_records if r.get('category')]
            if batch_targets:
                recent_targets.extend(batch_targets)
            
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

    if batch_targets is not None:
        batch_targets.append(f"{category} | {location}")

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
        # Yelp, Apple Maps, or other directory profiles do not count as custom websites.
        if website_url and not is_directory_url(website_url):
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
            email, discovered_web, email_source = await find_email_for_company(name, location, company.get("phone_number", ""))
            
            if discovered_web:
                log_progress(f"Autopilot: Lead '{name}' has a discovered website: '{discovered_web}' (skipped)")
                continue

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
    return {"status": "completed", "sent_count": sent_count, "scanned_count": scanned_count}

async def run_automation_batch(db, batch_target: int = 5) -> Dict[str, Any]:
    """
    Runs automated cycles in a loop until batch_target emails are sent.
    Shared by scheduler and manual trigger.
    """
    global automation_progress, is_batch_running
    
    if is_batch_running:
        logger.warning("Autopilot: A batch is already actively running. Skipping duplicate trigger.")
        return {"status": "skipped", "reason": "already_running"}
        
    try:
        is_batch_running = True
        automation_progress.clear()
        
        repo = AutomationRepository(db)
        config = await repo.get_settings()
        daily_limit = config.get("daily_email_limit", 20)
        
        batch_sent = 0
        attempts = 0
        batch_targets = []
        
        log_progress(f"Autopilot: Starting automated batch run (Target: {batch_target} emails)...")
        
        while batch_sent < batch_target:
            current_sent_today = await repo.count_records_today()
            if current_sent_today >= daily_limit:
                log_progress("Autopilot: Daily email limit reached mid-batch. Halting batch run.")
                break
                
            log_progress(f"Autopilot: Batch run attempt {attempts + 1} (Sent in this batch: {batch_sent}/{batch_target})")
            cycle_result = await run_automation_cycle(db, batch_targets=batch_targets)
            
            cycle_sent = cycle_result.get("sent_count", 0)
            batch_sent += cycle_sent
            attempts += 1
            
            if batch_sent >= batch_target:
                log_progress(f"Autopilot: Batch target of {batch_target} emails reached. Ending batch run.")
                break
                
            if cycle_sent == 0:
                log_progress("Autopilot: Cycle sent 0 emails. Sleeping 60 seconds to let server cool down, then switching to next niche...")
                await asyncio.sleep(60) # Wait 60s to release browser memory and avoid spamming APIs
                
        log_progress(f"Autopilot: Batch run completed. Total sent in this run: {batch_sent} over {attempts} attempts.")
        return {"status": "completed", "sent_count": batch_sent, "attempts": attempts}
    finally:
        is_batch_running = False

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
                
                if sent_today < daily_limit:
                    batch_target = config.get("batch_email_limit", 5)
                    await run_automation_batch(db, batch_target=batch_target)
                    log_progress("Autopilot: Scheduler sleeping for 30 minutes. Next run will start soon...")
                else:
                    logger.info(f"Autopilot: Daily email limit reached ({sent_today}/{daily_limit}). Skipping.")
            else:
                logger.info("Autopilot: Autopilot is disabled. Sleeping...")
        except Exception as e:
            logger.error(f"Autopilot: Scheduler loop error: {e}")
            
        # Check every 30 minutes
        await asyncio.sleep(1800)
