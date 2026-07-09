from typing import Optional, Dict, Any
from app.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

class LeadScoreRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        # Pass the "lead_scores" collection to the base repository
        super().__init__(db["lead_scores"])

    async def get_by_company_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the most recent lead score belonging to a specific company."""
        # A company typically has one active lead score, but we sort to get the latest just in case
        doc = await self.collection.find_one(
            {"company_id": company_id},
            sort=[("created_at", -1)]
        )
        return self._format_id(doc) if doc else None
