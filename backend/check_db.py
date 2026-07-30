import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://progixtechnology_db_user:mmEgsNkhpORYA345@cluster0.hqkvaho.mongodb.net/?appName=Cluster0")
    db = client.leadgen_pro
    p = await db.outreach_records.find_one({'company_name': 'Priyanshu Decorators'})
    if p:
        p['_id'] = str(p['_id'])
        print(json.dumps(p, indent=2))
    else:
        print('Not found')

if __name__ == "__main__":
    asyncio.run(main())
