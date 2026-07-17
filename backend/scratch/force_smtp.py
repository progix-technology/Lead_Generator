import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.settings import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    col = db.automation_settings
    
    result = await col.update_one({}, {"$set": {"email_service_provider": "SMTP"}})
    print("Updated email_service_provider to SMTP. modified_count:", result.modified_count)

if __name__ == '__main__':
    asyncio.run(run())
