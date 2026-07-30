import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://progixtechnology_db_user:mmEgsNkhpORYA345@cluster0.hqkvaho.mongodb.net/?appName=Cluster0")
    db = client.leadgen_pro
    settings = await db.automation_settings.find_one({})
    if not settings:
        print("No settings found in DB.")
        return
    
    categories = settings.get("categories", [])
    current_index = settings.get("last_category_index", 0)
    
    if not categories:
        print("No categories exist.")
        return
        
    next_index = (current_index + 1) % len(categories)
    
    # Update DB
    await db.automation_settings.update_one({}, {"$set": {"last_category_index": next_index}})
    print(f"Skipped category! New target category will be: {categories[next_index]}")

if __name__ == "__main__":
    asyncio.run(main())
