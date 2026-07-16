import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings

async def print_settings():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    col = db["automation_settings"]
    
    config = await col.find_one({})
    print("ALL AUTOMATION SETTINGS (Safe Print):")
    if config:
        for k, v in config.items():
            if k in ["enabled", "facebook_only", "categories", "locations"]:
                print(f"  {k}: {v}")
    else:
        print("No document found!")
    client.close()

asyncio.run(print_settings())
