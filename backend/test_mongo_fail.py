import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://invalid.dns.name.local:27017/?serverSelectionTimeoutMS=1000")
    db = client["test"]
    try:
        await db["test"].find_one({})
    except Exception as e:
        print("Exception:", type(e), e)

asyncio.run(main())
