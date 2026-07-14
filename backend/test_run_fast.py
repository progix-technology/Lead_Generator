import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

sys.path.insert(0, r"c:\Users\Vivang Mishra\Desktop\LeadGenerator\backend")

from app.config.settings import get_settings
from app.services.automation_worker import run_automation_cycle
from app.database.connection import db_instance

async def mock_search_companies(*args, **kwargs):
    return [{"name": "Test Co", "address": "Test addr", "website_url": "https://test.com", "phone_number": "123"}], "Test"

async def mock_find_email(*args, **kwargs):
    return "test@test.com", "https://test.com", "Website"

async def mock_live_audit(*args, **kwargs):
    return {"seo_score": 50, "ui_score": 50, "performance_score": 50, "suggestions": ["Fix this"]}

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    db_instance.client = client
    db_instance.db = db
    
    import app.services.automation_worker as worker
    worker.search_companies_google_places = mock_search_companies
    worker.find_email_for_company = mock_find_email
    
    import app.services.audit as audit
    audit.perform_live_website_audit = mock_live_audit
    
    try:
        print("Starting cycle...")
        result = await worker.run_automation_cycle(db)
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
