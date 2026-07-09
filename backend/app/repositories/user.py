from typing import Optional, Dict, Any
from app.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

class UserRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        # Pass the "users" collection to the base repository
        super().__init__(db["users"])

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by their email address."""
        doc = await self.collection.find_one({"email": email})
        return self._format_id(doc) if doc else None
