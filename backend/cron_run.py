import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from zoneinfo import ZoneInfo

# Add backend directory to sys.path dynamically
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config.settings import get_settings
from app.repositories.automation import AutomationRepository
from app.services.automation_worker import run_automation_cycle, run_mailer_cycle
from app.database.connection import db_instance

async def main():
    # 1. Connect to MongoDB using settings
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    db_instance.client = client
    db_instance.db = db
    
    repo = AutomationRepository(db)
    config = await repo.get_settings()
    
    # 2. Check if autopilot is enabled in settings
    if not config.get("enabled", False):
        print("Autopilot is disabled in settings. Exiting.")
        client.close()
        return

    # 3. Check working hours constraint (9 AM - 5 PM IST)
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_hour = ist_now.hour
    if current_hour < 9 or current_hour >= 17:
        print(f"Current time ({ist_now.strftime('%H:%M:%S')} IST) is outside working hours (9 AM - 5 PM). Exiting.")
        client.close()
        return

    print("--- Autopilot Cron Run Starting ---")
    
    # 4. Scraper phase: if active queue is low, run scraper
    enable_redesign = config.get("enable_redesign", True)
    if enable_redesign:
        pending_count = await repo.count_pending_records()
    else:
        pending_count = await repo.count_pending_standard_records()
        
    if pending_count < 20:
        print(f"Queue has {pending_count} active leads. Scraping new leads...")
        try:
            scraper_result = await run_automation_cycle(db)
            print("Scraper result:", scraper_result)
        except Exception as e:
            print(f"Scraper failed: {e}")
    else:
        print(f"Queue has plenty of leads ({pending_count}). Skipping scraping.")

    # 5. Mailer phase: send a batch of emails (up to batch_email_limit, default 5)
    sent_today = await repo.count_records_today()
    daily_limit = config.get("daily_email_limit", 20)
    batch_limit = config.get("batch_email_limit", 5)
    
    if sent_today >= daily_limit:
        print(f"Daily email limit ({daily_limit}) already reached. Skipping sending.")
        client.close()
        return
        
    to_send = min(batch_limit, daily_limit - sent_today)
    print(f"Sending up to {to_send} emails in this batch...")
    
    exclude_redesign = not enable_redesign
    sent_count = 0
    for i in range(to_send):
        try:
            result = await run_mailer_cycle(db, exclude_redesign=exclude_redesign)
            if result.get("status") in ["sent", "failed"]:
                sent_count += 1
                if i < to_send - 1:
                    # Short delay between emails to protect SMTP reputation
                    await asyncio.sleep(20)
            else:
                print(f"No more pending emails to send. Mailer cycle status: {result.get('status')}")
                break
        except Exception as e:
            print(f"Failed to send email: {e}")
            break
            
    print(f"Sent {sent_count} emails in this cron run.")
    print("--- Autopilot Cron Run Complete ---")
    client.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
