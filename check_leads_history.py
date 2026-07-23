import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

BACKEND_DIR = r"c:\Users\Vivang Mishra\Downloads\LeadGenerator_1\LeadGenerator\LeadGenerator\backend"
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "leadgen_db")

async def inspect_companies():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    cursor = db["companies"].find({}).limit(10)
    docs = [doc async for doc in cursor]
    print(f"Sample companies (total 410):")
    for d in docs:
        print(d.get('name'), '| Email:', d.get('email') or d.get('contact_email'), '| Website:', d.get('website'), '| Status:', d.get('status'))

    # Check how many have email
    with_email = await db["companies"].count_documents({"$or": [{"email": {"$ne": None, "$ne": ""}}, {"contact_email": {"$ne": None, "$ne": ""}}]})
    print(f"\nCompanies with email: {with_email}")

if __name__ == "__main__":
    asyncio.run(inspect_companies())
