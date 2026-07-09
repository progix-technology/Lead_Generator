from app.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

class CompanyRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        # Pass the "companies" collection to the base repository
        super().__init__(db["companies"])
        
    # We can add company-specific database queries here in the future
    # For example: search_by_name, filter_by_status, etc.
