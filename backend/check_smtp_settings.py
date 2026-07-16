import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings

async def show_smtp_config():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    col = db["automation_settings"]
    
    config = await col.find_one({})
    print("DATABASE SMTP CONFIG keys:")
    if config:
        for k, v in config.items():
            if k in ["smtp_port", "smtp_host", "smtp_email"]:
                print(f"  {k}: {v}")
    else:
        print("  No config document found!")
        
    print("\n.ENV CONFIG:")
    print("  SMTP_PORT:", settings.SMTP_PORT)
    print("  SMTP_HOST:", settings.SMTP_HOST)
    client.close()

asyncio.run(show_smtp_config())
