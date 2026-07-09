from typing import List, Dict, Any
from app.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

class WebsiteAuditRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        # Pass the "website_audits" collection to the base repository
        super().__init__(db["website_audits"])

    async def get_by_company_id(self, company_id: str) -> List[Dict[str, Any]]:
        """Fetch all website audits belonging to a specific company."""
        cursor = self.collection.find({"company_id": company_id}).sort("created_at", -1)
        return [self._format_id(doc) async for doc in cursor]
