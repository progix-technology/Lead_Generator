"""
Script to clean up stale Pending_Email records where:
- The company has a custom website (in metadata.website)
- But is_redesign = False (queued under old rules)
These should be deleted from the queue to prevent sending wrong templates.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings

async def clean_stale_records():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    col = db["automation_records"]
    
    # Find all Pending_Email records
    pending = await col.find({"status": "Pending_Email"}).to_list(length=1000)
    print(f"Total Pending_Email records: {len(pending)}")
    
    delete_ids = []
    for record in pending:
        meta = record.get("metadata") or {}
        is_redesign = meta.get("is_redesign")
        website = meta.get("website") or "your business"
        
        # Check if it has a real custom website
        has_custom_site = (
            website 
            and website != "your business" 
            and "their website" not in website.lower()
            and "facebook.com" not in website.lower()
            and "instagram.com" not in website.lower()
            and "linkedin.com" not in website.lower()
        )
        
        # Stale record = has website but is_redesign is False
        if has_custom_site and not is_redesign:
            delete_ids.append(record["_id"])
            print(f"  Stale -> DELETE: {record.get('company_name')} | website: {website} | is_redesign: {is_redesign}")
        else:
            print(f"  OK: {record.get('company_name')} | website: {website} | is_redesign: {is_redesign}")
    
    if delete_ids:
        result = await col.delete_many({"_id": {"$in": delete_ids}})
        print(f"\n✓ Deleted {result.deleted_count} stale non-redesign records from queue.")
    else:
        print("\n✓ No stale records found. Queue is clean.")
    
    client.close()

asyncio.run(clean_stale_records())
