from fastapi import HTTPException, status
from typing import Dict, Any, List

from app.repositories.audit import WebsiteAuditRepository
from app.repositories.company import CompanyRepository
from app.schemas.audit import WebsiteAuditCreate, WebsiteAuditUpdate

class WebsiteAuditService:
    def __init__(self, audit_repo: WebsiteAuditRepository, company_repo: CompanyRepository):
        self.audit_repo = audit_repo
        self.company_repo = company_repo

    async def create_audit(self, audit_in: WebsiteAuditCreate) -> Dict[str, Any]:
        # 1. Verify the company exists before adding an audit
        company = await self.company_repo.get_by_id(audit_in.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            
        audit_data = audit_in.model_dump()
        return await self.audit_repo.create(audit_data)

    async def get_audit(self, audit_id: str) -> Dict[str, Any]:
        audit = await self.audit_repo.get_by_id(audit_id)
        if not audit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
        return audit

    async def get_audits_for_company(self, company_id: str) -> List[Dict[str, Any]]:
        return await self.audit_repo.get_by_company_id(company_id)

    async def update_audit(self, audit_id: str, audit_in: WebsiteAuditUpdate) -> Dict[str, Any]:
        await self.get_audit(audit_id) # Validates existence
        
        update_data = audit_in.model_dump(exclude_unset=True)
        return await self.audit_repo.update(audit_id, update_data)

    async def delete_audit(self, audit_id: str):
        await self.get_audit(audit_id) # Validates existence
        success = await self.audit_repo.delete(audit_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete audit")
