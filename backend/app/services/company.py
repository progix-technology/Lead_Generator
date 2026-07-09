from fastapi import HTTPException, status
from typing import Dict, Any, List

from app.repositories.company import CompanyRepository
from app.schemas.company import CompanyCreate, CompanyUpdate

class CompanyService:
    def __init__(self, company_repo: CompanyRepository):
        self.company_repo = company_repo

    async def create_company(self, company_in: CompanyCreate) -> Dict[str, Any]:
        company_data = company_in.model_dump()
        # Here we could add logic to auto-generate a lead score in Phase 3
        return await self.company_repo.create(company_data)

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return company

    async def get_companies(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.company_repo.get_all(skip=skip, limit=limit)
        
    async def get_total_count(self) -> int:
        return await self.company_repo.count()

    async def update_company(self, company_id: str, company_in: CompanyUpdate) -> Dict[str, Any]:
        company = await self.get_company(company_id) # Validates existence
        
        update_data = company_in.model_dump(exclude_unset=True)
        updated_company = await self.company_repo.update(company_id, update_data)
        return updated_company

    async def delete_company(self, company_id: str):
        company = await self.get_company(company_id) # Validates existence
        success = await self.company_repo.delete(company_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete company")
