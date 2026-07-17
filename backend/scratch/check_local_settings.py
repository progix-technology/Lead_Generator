import asyncio
import os
import sys

# Add backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.settings import settings
from motor.motor_asyncio import AsyncIOMotorClient
from app.repositories.automation import AutomationRepository

async def run():
    print("MONGODB_URI:", settings.MONGODB_URI)
    print("DATABASE_NAME:", settings.DATABASE_NAME)
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    repo = AutomationRepository(db)
    
    doc = await repo.get_settings()
    print("--- LIVE DB CONFIG ---")
    print("Provider:", doc.get("email_service_provider"))
    print("Resend API Key:", doc.get("resend_api_key"))
    print("SMTP Email:", doc.get("smtp_email"))
    print("SMTP Host:", doc.get("smtp_host"))
    print("SMTP Port:", doc.get("smtp_port"))
    print("SMTP Password:", doc.get("smtp_password"))

if __name__ == '__main__':
    asyncio.run(run())
