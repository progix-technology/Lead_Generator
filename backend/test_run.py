import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add backend dir to sys.path
sys.path.insert(0, r"c:\Users\Vivang Mishra\Desktop\LeadGenerator\backend")

from app.config.settings import get_settings
from app.repositories.automation import AutomationRepository
from app.services.automation_worker import run_automation_cycle
from app.database.connection import db_instance

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    db_instance.client = client
    db_instance.db = db
    
    try:
        print("Starting cycle...")
        result = await run_automation_cycle(db)
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
