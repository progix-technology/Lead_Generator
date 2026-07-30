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
    schedules = settings.get("country_schedules", {})
    print(json.dumps(schedules, indent=4))

if __name__ == "__main__":
    asyncio.run(main())
