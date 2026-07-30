import asyncio
import json
import re
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://progixtechnology_db_user:mmEgsNkhpORYA345@cluster0.hqkvaho.mongodb.net/?appName=Cluster0")
    db = client.leadgen_pro
    
    bad_keywords = [r"\bit\b", r"software", r"web design", r"marketing", r"seo", r"digital", r"tech", r"cybersecurity", r"cyber"]
    
    # 1. Delete pending records that match these keywords in the query or company name
    pending = await db.outreach_records.find({"status": {"$in": ["Pending_Email", "Pending_Scrape"]}}).to_list(length=5000)
    
    delete_ids = []
    for p in pending:
        query = p.get("search_query", "")
        company = p.get("company_name", "")
        
        is_bad = False
        for bk in bad_keywords:
            if re.search(bk, query, re.IGNORECASE) or re.search(bk, company, re.IGNORECASE):
                is_bad = True
                break
                
        if is_bad:
            delete_ids.append(p["_id"])
            
    if delete_ids:
        res = await db.outreach_records.delete_many({"_id": {"$in": delete_ids}})
        print(f"Deleted {res.deleted_count} pending records containing IT/Cybersecurity/Software.")
    else:
        print("No pending IT records found.")

if __name__ == "__main__":
    asyncio.run(main())
