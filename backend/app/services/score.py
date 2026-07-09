from fastapi import HTTPException, status
from typing import Dict, Any, List

from app.repositories.score import LeadScoreRepository
from app.repositories.company import CompanyRepository
from app.schemas.score import LeadScoreCreate, LeadScoreUpdate

class LeadScoreService:
    def __init__(self, score_repo: LeadScoreRepository, company_repo: CompanyRepository):
        self.score_repo = score_repo
        self.company_repo = company_repo

    async def create_score(self, score_in: LeadScoreCreate) -> Dict[str, Any]:
        # Verify the company exists
        company = await self.company_repo.get_by_id(score_in.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            
        score_data = score_in.model_dump()
        return await self.score_repo.create(score_data)

    async def get_score(self, score_id: str) -> Dict[str, Any]:
        score = await self.score_repo.get_by_id(score_id)
        if not score:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead Score not found")
        return score

    async def get_score_for_company(self, company_id: str) -> Dict[str, Any]:
        score = await self.score_repo.get_by_company_id(company_id)
        if not score:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Lead Score found for this company")
        return score

    async def update_score(self, score_id: str, score_in: LeadScoreUpdate) -> Dict[str, Any]:
        await self.get_score(score_id) # Validates existence
        
        update_data = score_in.model_dump(exclude_unset=True)
        return await self.score_repo.update(score_id, update_data)

    async def delete_score(self, score_id: str):
        await self.get_score(score_id) # Validates existence
        success = await self.score_repo.delete(score_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete Lead Score")
