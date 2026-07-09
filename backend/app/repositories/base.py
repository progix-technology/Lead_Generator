from motor.motor_asyncio import AsyncIOMotorCollection
from typing import Any, Dict, List, Optional
from bson import ObjectId
from datetime import datetime

class BaseRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    def _format_id(self, doc: dict) -> dict:
        """Converts MongoDB ObjectId to string for Pydantic compatibility."""
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return self._format_id(doc) if doc else None

    async def get_all(self, skip: int = 0, limit: int = 100, query: dict = None) -> List[Dict[str, Any]]:
        query = query or {}
        cursor = self.collection.find(query).skip(skip).limit(limit)
        return [self._format_id(doc) async for doc in cursor]

    async def count(self, query: dict = None) -> int:
        query = query or {}
        return await self.collection.count_documents(query)

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(data)
        created_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._format_id(created_doc)

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(id):
            return None
            
        # Clean out any null values if you only want to update provided fields
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            return await self.get_by_id(id)

        update_data["updated_at"] = datetime.utcnow()
        
        await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        return await self.get_by_id(id)

    async def delete(self, id: str) -> bool:
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
