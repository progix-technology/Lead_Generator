import logging
import asyncio
import re
import traceback
import html
from datetime import datetime
from typing import Dict, Any, List

from app.config.settings import settings
from app.repositories.automation import AutomationRepository
from app.repositories.company import CompanyRepository
from app.services.company import CompanyService
from app.services.places import search_companies_google_places
from app.services.email_scraper import find_email_for_company, find_email_from_company_website
from app.services.email_verifier import verify_email_existence
from app.services.email_sender import send_smtp_email
from app.services.llm_service import clean_first_name_with_ai
from bson import ObjectId

logger = logging.getLogger(__name__)

# Global list to track live progress of the automation cycle for frontend display
automation_progress: List[str] = []
is_batch_running: bool = False
cancel_requested: bool = False
last_log_date = None

def request_cancellation():
    global cancel_requested
    cancel_requested = True
    log_progress("Autopilot: Cancellation requested by user. Halting execution...")

def is_directory_url(url: str) -> bool:
    """Helper to detect if a URL is a directory listing profile (like Yelp, RestaurantGuru, Placewing) rather than a custom business website."""
    if not url:
        return False
    url_lower = url.lower()
    directories = [
        'yelp.com', 'facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com',
        'apple.com', 'maps.apple.com', 'yellowpages.com', 'yp.com', 'foursquare.com', 'bbb.org',
        'manta.com', 'tripadvisor.com', 'angi.com', 'houzz.com', 'chamberofcommerce.com',
        'local.yahoo.com', 'mapquest.com', 'greatschools.org', 'privateschoolreview.com',
        'childcarecenter.us', 'allbiz.com', 'schoolandcollegelistings.com', 'restaurantguru.com',
        'placewing.com', 'mymenuweb.com', 'cloveronline.com', 'seamless.com', 'grubhub.com',
        'doordash.com', 'ubereats.com', 'postmates.com', 'menupix.com', 'singleplatform.com',
        'chownow.com', 'toasttab.com', 'zmenu.com', 'allmenus.com', 'sirved.com',
        'loc8nearme.com', 'findglocal.com', 'top-rated.online', 'us-businesses.com',
        'companycheck.com', 'dnb.com', 'bizzlist.com', 'youtube.com', 'youtubekids.com',
        'wikipedia.org', 'wikihow.com', 'softonic.com', 'overleaf.com', 'cermati.com',
        'merriam-webster.com', 'uidai.gov.in', 'dailymotion.com', 'konglongdao.com',
        'glassdoor.com', 'indeed.com', 'duckduckgo.com', 'google.com', 'yahoo.com',
        'bing.com', 'microsoft.com', 'heavenlydelightsbakery.com', 'localoria.com',
        'findcoffeeshop.com', 'atly.com', 'roadtrippers.com', 'checkle.com', 'alltopplaces.com'
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
    formatted = f"[{timestamp}] {msg}"
    automation_progress.append(formatted)
    
    if len(automation_progress) > 200:
        automation_progress = automation_progress[-200:]

def parse_time_to_minutes(time_str: str) -> int:
    """Parses 12-hour AM/PM ('10:00 AM', '02:00 PM') and 24-hour ('14:00') time strings into minute of day (0-1439)."""
    if not time_str:
        return 0
    clean = str(time_str).strip().upper()
    try:
        if "AM" in clean or "PM" in clean:
            is_pm = "PM" in clean
            clean_time = clean.replace("AM", "").replace("PM", "").strip()
            parts = clean_time.split(":")
            h = int(parts[0]) % 12
            m = int(parts[1]) if len(parts) > 1 else 0
            if is_pm:
                h += 12
            return h * 60 + m
        else:
            parts = clean.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h * 60 + m
    except Exception:
        return 0

def get_active_country_schedule(settings: Dict[str, Any]) -> tuple[str, List[str]]:
    """
    Checks current IST time and matches against country_schedules in settings.
    Supports both 12-hour AM/PM and 24-hour time formats seamlessly.
    Returns (active_country_code, active_locations_list).
    """
    from datetime import datetime, timezone, timedelta
    schedules = settings.get("country_schedules") or {}
    
    # IST = UTC + 5:30
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    current_minutes = now_ist.hour * 60 + now_ist.minute

    for country_code, schedule in schedules.items():
        try:
            start_str = schedule.get("start_time_ist", "00:00")
            end_str = schedule.get("end_time_ist", "23:59")
            
            start_mins = parse_time_to_minutes(start_str)
            end_mins = parse_time_to_minutes(end_str)
            
            if start_mins <= end_mins:
                if start_mins <= current_minutes <= end_mins:
                    locs = schedule.get("locations") or []
                    if locs:
                        return country_code, locs
            else:
                # Overnight time range (e.g. 10:00 PM to 04:00 AM)
                if current_minutes >= start_mins or current_minutes <= end_mins:
                    locs = schedule.get("locations") or []
                    if locs:
                        return country_code, locs
        except Exception:
            pass

    # If outside all specific time windows, return locations from first user-configured country profile
    if schedules:
        first_code = list(schedules.keys())[0]
        first_locs = schedules[first_code].get("locations") or []
        if first_locs:
            return first_code, first_locs

    user_locs = settings.get("locations") or []
    return "USA", user_locs if user_locs else ["Phoenix, AZ"]

def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)

def _apply_template(template: Any, values: Dict[str, Any]) -> str:
    rendered = _safe_str(template, "")
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", _safe_str(value, ""))
    return rendered

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
    "Logistics Companies", "Consulting Agencies", "Corporate Event Planners",
    "General Contractors", "Kitchen Remodeling", "Bathroom Remodeling", "Flooring Contractors",
    "Garage Door Repair", "Pest Control", "Water Damage Restoration", "Mold Remediation",
    "Landscaping Services", "Lawn Care", "Pressure Washing", "Gutter Cleaning",
    "Pool Cleaning Services", "Handyman Services", "Deck Builders", "Masonry Contractors",
    "Glass Repair Services", "Emergency Plumbers", "Emergency Electricians", "Septic Services",
    "Mobile Car Detailing", "Tire Shops", "Auto Body Shops", "Windshield Repair",
    "Transmission Repair", "Brake Repair", "Oil Change Services", "Car Wash",
    "Personal Injury Lawyers", "Immigration Lawyers", "Family Lawyers", "Bankruptcy Lawyers",
    "Tax Consultants", "Bookkeeping Services", "Payroll Services", "Insurance Agencies",
    "Real Estate Agents", "Mortgage Brokers", "Property Management", "Home Inspectors",
    "Dermatology Clinics", "Pediatric Clinics", "Dental Implants Clinics", "Urgent Care Clinics",
    "Psychology Clinics", "Speech Therapy Centers", "Occupational Therapy Centers", "Home Healthcare Services",
    "Med Spa Clinics", "Hair Salons", "Nail Salons", "Barber Shops",
    "Beauty Clinics", "Eyelash Studios", "Tattoo Studios", "Massage Therapy",
    "Gyms", "Personal Trainers", "Pilates Studios", "Crossfit Gyms",
    "Martial Arts Schools", "Music Schools", "Tutoring Centers", "Test Prep Centers",
    "Preschools", "Private Schools", "Senior Care Services", "Assisted Living Facilities",
    "Restaurants", "Coffee Shops", "Bakeries", "Food Trucks",
    "Cafes", "Cloud Kitchens", "Pet Grooming", "Pet Boarding",
    "Printing Services", "Signage Companies", "Security Camera Installation",
    "Beauty Products", "Cosmetics Stores", "Skincare Brands", "Soap and Lotion Brands", "Grocery Stores", "Supermarkets"
]
LOCATIONS = [
    "San Ramon, CA", "Walnut Creek, CA", "Concord, CA", "Bakersfield, CA",
    "Modesto, CA", "Stockton, CA", "Sacramento, CA", "Elk Grove, CA",
    "Rancho Cordova, CA", "Davis, CA", "Woodland, CA", "Napa, CA",
    "San Rafael, CA", "Novato, CA", "Petaluma, CA", "Santa Rosa, CA", "Berkeley, CA",
    "Los Angeles, CA", "San Diego, CA", "San Jose, CA", "San Francisco, CA",
    "Long Beach, CA", "Anaheim, CA", "Irvine, CA", "Riverside, CA",
    "Phoenix, AZ", "Mesa, AZ", "Scottsdale, AZ", "Tempe, AZ",
    "Las Vegas, NV", "Henderson, NV", "Reno, NV", "Portland, OR",
    "Seattle, WA", "Tacoma, WA", "Spokane, WA", "Denver, CO",
    "Colorado Springs, CO", "Dallas, TX", "Houston, TX", "Austin, TX",
    "San Antonio, TX", "Fort Worth, TX", "El Paso, TX", "Chicago, IL",
    "Naperville, IL", "Miami, FL", "Orlando, FL", "Tampa, FL",
    "Jacksonville, FL", "Fort Lauderdale, FL", "Atlanta, GA", "Charlotte, NC",
    "Raleigh, NC", "Nashville, TN", "New York, NY", "Brooklyn, NY",
    "Queens, NY", "Buffalo, NY", "Jersey City, NJ", "Newark, NJ",
    "Philadelphia, PA", "Pittsburgh, PA", "Boston, MA", "Worcester, MA",
    "Washington, DC", "Baltimore, MD", "Detroit, MI", "Minneapolis, MN",
    "St. Paul, MN", "Columbus, OH", "Cleveland, OH", "Cincinnati, OH",
    "Indianapolis, IN", "Kansas City, MO", "St. Louis, MO", "New Orleans, LA",
    "Colombo, Sri Lanka", "Kandy, Sri Lanka", "Galle, Sri Lanka", "Negombo, Sri Lanka",
    "Kathmandu, Nepal", "Pokhara, Nepal", "Lalitpur, Nepal", "Bhaktapur, Nepal", "Biratnagar, Nepal"
]

async def run_automation_cycle(db, batch_targets: list = None) -> Dict[str, Any]:
    """
    Runs a single autopilot lead generation & outreach cycle.
    Queries Google Places, filters for website-less leads, crawls emails,
    checks for Facebook source, SMTP verifies them, and auto-sends pitches.
    """
    global automation_progress, cancel_requested
    
    # Always reset the cancel flag at the start of a new cycle
    # A previous cancellation should not block future runs
    cancel_requested = False
        
    log_progress("Autopilot: Initializing automated outreach cycle...")
    
    repo = AutomationRepository(db)
    co_repo = CompanyRepository(db)
    co_service = CompanyService(co_repo)

    current_settings = await repo.get_settings()
    if not current_settings.get("enabled", False):
        log_progress("Autopilot: Cycle skipped because autopilot is disabled.")
        return {"status": "skipped", "reason": "disabled"}

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
            
    active_country_code, active_locations = get_active_country_schedule(current_settings)

    if not category or not location:
        search_index = current_settings.get("search_index", 0)
        categories = current_settings.get("categories") or CATEGORIES
        category = categories[search_index % len(categories)]
        location = active_locations[(search_index // len(categories)) % len(active_locations)]
        log_progress(f"Autopilot: Selected target category: '{category}' | location: '{location}' [Country: {active_country_code}] (Index: {search_index})")
        # Increment search index
        await repo.update_settings({"search_index": search_index + 1})

    if batch_targets is not None:
        batch_targets.append(f"{category} | {location}")

    if cancel_requested:
        log_progress("Autopilot: Cycle aborted due to cancel request.")
        return {"status": "skipped", "reason": "cancelled"}

    # 3. Search Google Places fallback scraper
    log_progress(f"Autopilot: Fetching local businesses from Google Maps...")
    results, _ = await search_companies_google_places(category, location)
    if not results:
        log_progress("Autopilot: No local businesses found for this category and location.")
        return {"status": "completed", "sent_count": 0, "scanned_count": 0}

    target_new_businesses_only = current_settings.get("target_new_businesses_only", False)
    if target_new_businesses_only:
        initial_count = len(results)
        results = [r for r in results if r.get("rating_count", 999) <= 5]
        log_progress(f"Autopilot: Targeted 'New Businesses Only' (≤ 5 reviews). Kept {len(results)}/{initial_count} leads.")

    log_progress(f"Autopilot: Found {len(results)} target businesses. Starting website filters...")
    scanned_count = 0
    sent_count = 0

    # 5. Process results concurrently
    log_progress(f"Autopilot: Processing {len(results)} businesses concurrently...")
    
    async def process_company(company: Dict[str, Any]) -> int:
        global cancel_requested
        if cancel_requested: return 0
        
        name = company.get("name", "Unknown Business")
        
        # Prevent duplicate outreach: check if already exists in DB early
        existing = await co_repo.collection.find_one({"name": name})
        if existing:
            log_progress(f"Autopilot: Lead '{name}' is already saved in database (skipped)")
            return 0

        website_url = company.get("website_url")
        enable_redesign = current_settings.get("enable_redesign", True)

        is_redesign = False
        seo_score = 0
        ui_score = 0
        performance_score = 0
        suggestions = []

        if website_url and not is_directory_url(website_url):
            # Always audit website companies regardless of enable_redesign.
            # - Score < 60  → queue as redesign candidate (mailer will send only when enable_redesign is ON)
            # - Score >= 60 → skip (healthy site, not a candidate)
            from app.services.audit import perform_live_website_audit
            try:
                audit_results = await perform_live_website_audit(website_url)
                seo_score = audit_results["seo_score"]
                ui_score = audit_results["ui_score"]
                performance_score = audit_results["performance_score"]
                suggestions = audit_results["suggestions"]
                
                avg_score = (seo_score + ui_score + performance_score) / 3
                if avg_score < 60:
                    is_redesign = True
                    log_progress(f"Autopilot: Lead '{name}' has website flaws (Score: {avg_score:.1f}/100 < 60). Added to redesign queue.")
                else:
                    log_progress(f"Autopilot: Lead '{name}' has a healthy website (Score: {avg_score:.1f}/100 >= 60). Skipping.")
                    return 0
            except Exception as audit_err:
                is_redesign = True
                seo_score = 30
                ui_score = 30
                performance_score = 40
                suggestions = ["Website access/security errors or SSL handshake failure detected."]
                log_progress(f"Autopilot: Website '{website_url}' blocked audit/has SSL errors ({audit_err}). Treating as weak website redesign candidate.")
        else:
            # No custom website → primary target: standard new-website pitch
            is_redesign = False
            suggestions = ["No custom website URL was detected; this is a strong new website candidate."]
            log_progress(f"Autopilot: Lead '{name}' has no website. Queueing new website creation pitch.")

        email = None
        discovered_web = None
        email_source = None

        facebook_only = current_settings.get("facebook_only", False)

        # For REDESIGN candidates: they have a website, so always try scraping it first for contact email
        # regardless of facebook_only setting — the website IS the product we want to redesign
        if website_url and is_redesign:
            try:
                website_email, website_email_page = await find_email_from_company_website(website_url)
                if website_email:
                    email = website_email
                    email_source = "Website Contact Page"
                    log_progress(f"Autopilot: Found email for redesign candidate '{name}' via website contact page.")
            except Exception:
                pass

        # For NON-redesign leads (no website): try website page only if facebook_only is OFF
        elif website_url and not facebook_only:
            try:
                website_email, website_email_page = await find_email_from_company_website(website_url)
                if website_email:
                    email = website_email
                    email_source = "Website Contact Page"
            except Exception:
                pass

        # Deep crawl social profiles if still no email found
        try:
            if not email:
                email, discovered_web, email_source = await find_email_for_company(name, location, company.get("phone_number", ""))
            
            # discovered_web = a website found via DDG during social search
            # If redesign is DISABLED: ignore discovered website, keep lead as standard (no-website pitch)
            # If redesign is ENABLED: audit the discovered website like any other
            if discovered_web and enable_redesign:
                from app.services.audit import perform_live_website_audit
                try:
                    audit_results = await perform_live_website_audit(discovered_web)
                    seo_score = audit_results["seo_score"]
                    ui_score = audit_results["ui_score"]
                    performance_score = audit_results["performance_score"]
                    suggestions = audit_results["suggestions"]
                    
                    avg_score = (seo_score + ui_score + performance_score) / 3
                    if avg_score < 60:
                        is_redesign = True
                        website_url = discovered_web
                        log_progress(f"Autopilot: Lead '{name}' has a weak discovered website '{discovered_web}' (Score: {avg_score:.1f}/100 < 60). Queueing redesign outreach.")
                    else:
                        log_progress(f"Autopilot: Lead '{name}' has a healthy discovered website '{discovered_web}' (Score: {avg_score:.1f}/100 >= 60). Skipping lead.")
                        return 0
                except Exception as audit_err:
                    is_redesign = True
                    website_url = discovered_web
                    suggestions = ["Discovered website access/security errors detected."]
                    log_progress(f"Autopilot: Discovered website '{discovered_web}' blocked audit ({audit_err}). Queueing redesign outreach.")

            if not email:
                log_progress(f"Autopilot: No contact emails discovered for '{name}'.")
                return 0

            facebook_only = current_settings.get("facebook_only", False)

            # Redesign leads: always allow Website Contact Page (that's where their email lives)
            # Standard (no-website) leads: respect facebook_only setting
            allowed_sources = [
                "Facebook", "Instagram", "LinkedIn",
                "Website Contact Page", "Direct Search", "Reverse Phone Search",
                "Discovered Website", "Directory Listing"
            ]
            if email_source not in allowed_sources:
                log_progress(f"Autopilot: Email '{email}' found for '{name}' via '{email_source}' (skipped - not in allowed sources {allowed_sources})")
                return 0

            # SMTP Verification Check
            # If SMTP check fails due to blocked Port 25 (e.g. Render network unreachable),
            # we check if the domain has valid MX records. Since the email was actually scraped, 
            # we trust it if the domain has a mail server.
            is_valid, verification_reason = await verify_email_existence(email)
            if not is_valid:
                if "SMTP connection blocked" in verification_reason or "server unreachable" in verification_reason:
                    from app.services.email_verifier import verify_mx_only
                    mx_valid, mx_reason = await verify_mx_only(email)
                    if mx_valid:
                        log_progress(f"Autopilot: Email '{email}' verified via MX backup because SMTP port 25 is blocked on hosting server.")
                    else:
                        log_progress(f"Autopilot: Email '{email}' discarded. MX backup failed: {mx_reason}")
                        return 0
                else:
                    log_progress(f"Autopilot: Email '{email}' is unverified. Reason: {verification_reason} (skipped).")
                    await repo.create_record({
                        "company_name": name, "email": email, "category": category, "location": location,
                        "subject": None, "body": None, "status": "Unverified", "error_message": verification_reason,
                        "email_source": email_source
                    })
                    return 0

            # Resolve Greeting Name: Use company name in all caps followed by TEAM
            greeting_name = f"{name.upper()} TEAM" if name else "TEAM"

            if is_redesign:
                country_templates = current_settings.get("country_templates") or {}
                c_tmpl = country_templates.get(active_country_code) or country_templates.get("USA") or {}
                subject_tmpl = c_tmpl.get("redesign_subject_template") or current_settings.get("redesign_subject_template") or "Quick suggestion for {{company}} about your website"
                body_tmpl = c_tmpl.get("redesign_body_template") or current_settings.get("redesign_body_template") or "Hello {{first_name}}..."
                website_for_template = website_url or "their website"
                sug_bullets = "\n".join([f"• {s}" for s in suggestions]) if suggestions else "• Outdated responsive layout and performance bottlenecks."

                subject = _apply_template(subject_tmpl, {
                    "company": name, "first_name": greeting_name, "website": website_for_template,
                    "industry": category, "location": location or "your area"
                })

                body = _apply_template(body_tmpl, {
                    "company": name, "first_name": greeting_name, "website": website_for_template,
                    "industry": category, "location": location or "your area",
                    "performance_score": performance_score, "ui_score": ui_score, "seo_score": seo_score, "suggestions": sug_bullets
                })
            else:
                country_templates = current_settings.get("country_templates") or {}
                c_tmpl = country_templates.get(active_country_code) or country_templates.get("USA") or {}
                subject_tmpl = c_tmpl.get("subject_template") or current_settings.get("subject_template") or ""
                body_tmpl = c_tmpl.get("body_template") or current_settings.get("body_template") or ""
                co_website = "your business"
                co_industry = category
                co_location = location or "your area"
                current_platform = "Facebook"
                service_type = "custom website design"

                subject = _apply_template(subject_tmpl, {
                    "company": name, "first_name": greeting_name, "website": co_website, "industry": co_industry,
                    "location": co_location, "current_platform": current_platform, "service_type": service_type
                })

                body = _apply_template(body_tmpl, {
                    "company": name, "first_name": greeting_name, "website": co_website, "industry": co_industry,
                    "location": co_location, "current_platform": current_platform, "service_type": service_type
                })

            html_body = f"<html><body><p>{html.escape(_safe_str(body)).replace(chr(10), '<br>')}</p></body></html>"

            new_co = await co_repo.create({
                "name": name, "industry": category, "location": location or address,
                "website": website_url, "phone": company.get("phone_number"),
                "email": email, "email_source": email_source,
                "status": "Audited" if is_redesign else "Emailed"
            })

            if is_redesign:
                from app.repositories.audit import WebsiteAuditRepository
                audit_repo = WebsiteAuditRepository(db)
                await audit_repo.create({
                    "company_id": new_co["id"], "website_url": website_url,
                    "seo_score": seo_score, "ui_score": ui_score, "performance_score": performance_score,
                    "suggestions": suggestions, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()
                })

            await repo.create_record({
                "company_name": name, "email": email, "category": category, "location": location,
                "subject": subject, "body": body, "status": "Pending_Email", "error_message": None,
                "email_source": email_source,
                "metadata": {
                    "first_name": greeting_name,
                    "website": website_url or "your business",
                    "is_redesign": is_redesign,
                    "performance_score": performance_score,
                    "ui_score": ui_score,
                    "seo_score": seo_score,
                    "suggestions": suggestions,
                    "country": active_country_code
                }
            })
            log_progress(f"Autopilot: ✓ Lead '{name}' queued successfully! (Pending Mailer Dispatch)")
            return 1

        except Exception as err:
            log_progress(f"Autopilot: Error processing lead '{name}': {err}")
            from app.routes.notifications import push_notification
            push_notification("error", f"Lead processing error for '{name}': {err}", source="autopilot")
            return 0

    # Execute all companies concurrently but in larger batches to increase speed
    completed_counts = []
    chunk_size = 10
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i+chunk_size]
        tasks = [process_company(co) for co in chunk]
        batch_results = await asyncio.gather(*tasks)
        completed_counts.extend(batch_results)
        
        # Add minimal 1-second delay between batches to avoid extreme rate limiting
        # while keeping the search very fast
        if i + chunk_size < len(results):
            await asyncio.sleep(1)
    
    sent_count = sum(completed_counts)
    scanned_count = len(results)

    log_progress(f"Autopilot: Cycle complete. Scanned: {scanned_count} leads, Sent: {sent_count} emails.")
    return {"status": "completed", "sent_count": sent_count, "scanned_count": scanned_count}

async def run_mailer_cycle(db, exclude_redesign: bool = False) -> Dict[str, Any]:
    """
    Grabs one pending email from the database and sends it safely.
    Dynamically recompiles subject/body at send-time using current active country templates.
    """
    import random
    repo = AutomationRepository(db)
    pending = await repo.get_pending_emails(limit=1, exclude_redesign=exclude_redesign)
    if not pending:
        return {"status": "skipped", "reason": "no_pending"}

    record = pending[0]
    email = record.get("email", "")
    subject = record.get("subject", "")
    body = record.get("body", "")
    name = record.get("company_name", "Valued Business")
    category = record.get("category") or "your business"
    location = record.get("location") or "your area"
    
    current_settings = await repo.get_settings()
    
    # Recompile templates dynamically (runs for both new metadata and older legacy queued emails)
    meta = record.get("metadata") or {}
    first_name_candidate = meta.get("first_name")
    
    # Use the full company name in capitals followed by "TEAM" to ensure a highly relevant greeting.
    first_name = f"{name.upper()} TEAM" if name else "TEAM"
            
    website = meta.get("website") or "your business"
    
    # Strictly determine is_redesign
    is_redesign = meta.get("is_redesign")
    if is_redesign is None:
        web_check = meta.get("website") or website or ""
        has_custom_site = web_check and web_check != "your business" and not any(d in web_check.lower() for d in ["their website", "facebook.com", "instagram.com"])
        is_redesign = has_custom_site or "website" in (subject or "").lower() or "score:" in (body or "").lower()
    
    # HARD GUARD: If company has a custom website but is_redesign is False,
    # this record was queued under old rules (pre-score-check). Discard it silently.
    web_check = meta.get("website") or website or ""
    has_custom_site = web_check and web_check != "your business" and not any(
        d in web_check.lower() for d in ["their website", "facebook.com", "instagram.com", "linkedin.com"]
    )
    if has_custom_site and not is_redesign:
        log_progress(f"Autopilot Mailer: Discarding stale record for '{name}' (website present but not a redesign candidate). Removing from queue.")
        await repo.records_col.delete_one({"_id": record["_id"] if "_id" in record else None} if "_id" in record else {"id": record.get("id")})
        await repo.records_col.delete_one({"_id": ObjectId(record["id"])})
        return {"status": "skipped", "reason": "stale_non_redesign_record"}
        
    # ENFORCE REDESIGN SETTING: If redesign is disabled, do not send redesign emails.
    if is_redesign and exclude_redesign:
        # We fetched a legacy record that didn't have is_redesign explicitly set in DB
        log_progress(f"Autopilot Mailer: Skipping redesign lead '{name}' because Redesign is currently disabled.")
        return {"status": "skipped", "reason": "redesign_disabled"}
    
    # Resolve Country-Specific Templates for Mailer
    target_country = meta.get("country")
    if not target_country:
        target_country, _ = get_active_country_schedule(current_settings)

    country_templates = current_settings.get("country_templates") or {}
    c_tmpl = country_templates.get(target_country) or country_templates.get("USA") or {}
    
    if is_redesign:
        openrouter_key = current_settings.get("openrouter_api_key")
        suggestions = meta.get("suggestions") or ["Outdated responsive layout and performance bottlenecks."]
        perf_score = meta.get("performance_score") or 64
        ui_score = meta.get("ui_score") or 58
        seo_score = meta.get("seo_score") or 62

        ai_generated = None
        if openrouter_key:
            from app.services.llm_service import generate_ai_redesign_email
            log_progress(f"Autopilot Mailer: Generating AI personalized redesign email for {name} based on their website flaws...")
            ai_generated = await generate_ai_redesign_email(
                company_name=name, first_name=first_name, website=website, industry=category, location=location,
                suggestions=suggestions, performance_score=perf_score, ui_score=ui_score, seo_score=seo_score,
                custom_api_key=openrouter_key
            )

        if ai_generated:
            subject = ai_generated["subject"]
            body = ai_generated["body"]
        else:
            # Fallback to static template
            subject_tmpl = c_tmpl.get("redesign_subject_template") or current_settings.get("redesign_subject_template") or "Quick suggestion for {{company}} about your website"
            body_tmpl = c_tmpl.get("redesign_body_template") or current_settings.get("redesign_body_template") or "Hello {{first_name}}..."
            sug_bullets = "\n".join([f"• {s}" for s in suggestions]) if isinstance(suggestions, list) else suggestions
            
            subject = _apply_template(subject_tmpl, {
                "company": name, "first_name": first_name, "website": website,
                "industry": category, "location": location
            })
            body = _apply_template(body_tmpl, {
                "company": name, "first_name": first_name, "website": website,
                "industry": category, "location": location,
                "performance_score": perf_score,
                "ui_score": ui_score,
                "seo_score": seo_score,
                "suggestions": sug_bullets
            })
    else:
        subject_tmpl = c_tmpl.get("subject_template") or current_settings.get("subject_template") or ""
        body_tmpl = c_tmpl.get("body_template") or current_settings.get("body_template") or ""
        
        subject = _apply_template(subject_tmpl, {
            "company": name, "first_name": first_name, "website": "your business", "industry": category,
            "location": location, "current_platform": "Facebook", "service_type": "custom website design"
        })
        body = _apply_template(body_tmpl, {
            "company": name, "first_name": first_name, "website": "your business", "industry": category,
            "location": location, "current_platform": "Facebook", "service_type": "custom website design"
        })

    html_body = f"<html><body><p>{html.escape(_safe_str(body)).replace(chr(10), '<br>')}</p></body></html>"

    log_progress(f"Autopilot Mailer: Dispatching queued email to '{email}'...")
    try:
        success = await send_smtp_email(email, subject, html_body, smtp_config=current_settings)
        if success:
            # Update record with actually sent subject and body for consistency
            await repo.records_col.update_one(
                {"_id": ObjectId(record["id"])},
                {"$set": {"status": "Sent", "subject": subject, "body": body, "sent_at": datetime.utcnow(), "updated_at": datetime.utcnow(), "error_message": None}}
            )
            log_progress(f"Autopilot Mailer: ✓ Outreach email successfully delivered to '{name}' at '{email}'!")
            return {"status": "sent"}
        else:
            raise Exception("SMTP send function returned False")
    except Exception as smtp_err:
        err_msg = str(smtp_err)
        await repo.update_record_status(record["id"], "Failed", err_msg)
        log_progress(f"Autopilot Mailer: ✕ Failed to send SMTP email to '{name}' at '{email}': {err_msg}")
        from app.routes.notifications import push_notification
        push_notification("error", f"SMTP send failed for '{name}' ({email}): {err_msg}", source="email")
        return {"status": "failed"}

def _is_any_country_schedule_active(config: dict) -> tuple[bool, str]:
    """
    Checks if the current IST time falls inside ANY configured country schedule window.
    Returns (is_active: bool, reason: str).
    """
    from datetime import timezone, timedelta
    schedules = config.get("country_schedules") or {}
    
    if not schedules:
        # No country schedules configured — fall back to old 9 AM - 6 PM IST rule
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        current_hour = now_ist.hour
        if 9 <= current_hour < 18:
            return True, "Default window (9 AM - 6 PM IST) is active"
        return False, f"Outside default working hours (9 AM - 6 PM IST). Current IST: {now_ist.strftime('%H:%M')}"
    
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    current_minutes = now_ist.hour * 60 + now_ist.minute
    
    for country_code, schedule in schedules.items():
        try:
            start_str = schedule.get("start_time_ist", "00:00")
            end_str = schedule.get("end_time_ist", "23:59")
            locs = schedule.get("locations") or []
            if not locs:
                continue
            start_mins = parse_time_to_minutes(start_str)
            end_mins = parse_time_to_minutes(end_str)
            
            if start_mins <= end_mins:
                if start_mins <= current_minutes <= end_mins:
                    return True, f"Country '{country_code}' schedule is active ({start_str} - {end_str} IST)"
            else:
                # Overnight window
                if current_minutes >= start_mins or current_minutes <= end_mins:
                    return True, f"Country '{country_code}' overnight schedule is active ({start_str} - {end_str} IST)"
        except Exception:
            pass
    
    return False, f"No country schedule is active right now (IST: {now_ist.strftime('%H:%M')}). Pausing until next window."


async def run_mailer_scheduler():
    """
    Runs continuously, picking up pending emails and sending them with a 3-4 min jitter delay.
    Runs according to country-wise schedule windows configured in Settings.
    """
    import random
    logger.info("Autopilot Mailer: Background loop started.")
    await asyncio.sleep(20)
    
    from app.database.connection import get_database
    db = get_database()
    
    while True:
        try:
            if cancel_requested:
                await asyncio.sleep(5)
                continue

            repo = AutomationRepository(db)
            config = await repo.get_settings()

            # Check country-schedule-based time window
            is_active, schedule_reason = _is_any_country_schedule_active(config)
            if not is_active:
                log_progress(f"Autopilot Mailer: {schedule_reason}. Sleeping 1 min...")
                await asyncio.sleep(60)
                continue
            
            if config.get("enabled", False):
                if config.get("mailer_enabled", True) is False:
                    log_progress("Autopilot Mailer: Mailer is paused in settings. Queueing leads but not sending emails.")
                    await asyncio.sleep(60)
                    continue

                # Count only sent emails for the daily limit
                sent_today = await repo.count_records_today()
                daily_limit = config.get("daily_email_limit", 20)
                enable_redesign = config.get("enable_redesign", True)
                exclude_redesign = not enable_redesign
                
                if sent_today < daily_limit:
                    result = await run_mailer_cycle(db, exclude_redesign=exclude_redesign)
                    if result.get("status") in ["sent", "failed"]:
                        delay = random.randint(60, 90)
                        log_progress(f"Autopilot Mailer: Sleeping for {delay} seconds (1-1.5 mins) before next send.")
                        await asyncio.sleep(delay)
                    else:
                        # Queue might be empty, or no schedule active
                        msg = result.get("message", "")
                        log_progress(f"Autopilot Mailer: {msg}. Sleeping 1 min...")
                        await asyncio.sleep(60)
                else:
                    log_progress(f"Autopilot Mailer: Daily limit of {daily_limit} reached. Pausing until tomorrow.")
                    await asyncio.sleep(3600)
            else:
                await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Autopilot Mailer error: {e}")
            await asyncio.sleep(60)

async def run_scraper_scheduler():
    """
    Runs the scraper periodically to keep the queue filled.
    Runs according to country-wise schedule windows configured in Settings.
    """
    logger.info("Autopilot Scraper: Background loop started.")
    await asyncio.sleep(15)
    
    from app.database.connection import get_database
    db = get_database()
    
    while True:
        try:
            repo = AutomationRepository(db)
            config = await repo.get_settings()

            # Check country-schedule-based time window
            is_active, _ = _is_any_country_schedule_active(config)
            if not is_active:
                await asyncio.sleep(60)
                continue

            if config.get("enabled", False):
                enable_redesign = config.get("enable_redesign", True)
                if enable_redesign:
                    pending_count = await repo.count_pending_records()
                else:
                    pending_count = await repo.count_pending_standard_records()
                
                # Keep queue stocked with at least 50 leads
                if pending_count < 50:
                    log_progress(f"Autopilot Scraper: Queue has {pending_count} active leads (Target: 50). Starting search for more...")
                    await run_automation_cycle(db)
                    await asyncio.sleep(30) # Only wait 30 seconds before searching again if queue is still low
                else:
                    # Plenty of leads in queue, rest.
                    await asyncio.sleep(180) # Check queue size every 3 mins
            else:
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Autopilot Scraper error: {e}")
            await asyncio.sleep(60)
