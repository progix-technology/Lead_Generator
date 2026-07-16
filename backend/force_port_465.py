import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings

async def force_port_465_accurate():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    col = db["automation_settings"]
    
    # Check if a settings document exists at all
    doc = await col.find_one({})
    if doc:
        # Update both string and integer formats to be safe
        result = await col.update_one({"_id": doc["_id"]}, {"$set": {"smtp_port": 465}})
        print(f"Updated smtp_port to integer 465: modified_count={result.modified_count}")
    else:
        # Insert a default settings block with port 465
        result = await col.insert_one({
            "enabled": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "smtp_email": "progixtechnology@gmail.com",
            "smtp_password": "YOUR_GMAIL_APP_PASSWORD", # User needs to verify this
            "daily_email_limit": 35
        })
        print(f"Created default settings with port 465. Inserted ID: {result.inserted_id}")
        
    client.close()

asyncio.run(force_port_465_accurate())
