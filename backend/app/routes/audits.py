from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict, List

from app.database.connection import get_database
from app.repositories.audit import WebsiteAuditRepository
from app.repositories.company import CompanyRepository
from app.services.audit import WebsiteAuditService
from app.schemas.audit import WebsiteAuditCreate, WebsiteAuditResponse, WebsiteAuditUpdate
from app.auth.deps import get_current_user

router = APIRouter()

def get_audit_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> WebsiteAuditService:
    return WebsiteAuditService(WebsiteAuditRepository(db), CompanyRepository(db))

@router.post("/", response_model=WebsiteAuditResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    audit_in: WebsiteAuditCreate,
    audit_service: WebsiteAuditService = Depends(get_audit_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Create a new website audit result for a company."""
    return await audit_service.create_audit(audit_in)

@router.get("/company/{company_id}", response_model=List[WebsiteAuditResponse])
async def get_audits_for_company(
    company_id: str,
    audit_service: WebsiteAuditService = Depends(get_audit_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Get all website audits belonging to a specific company."""
    return await audit_service.get_audits_for_company(company_id)

@router.get("/{id}", response_model=WebsiteAuditResponse)
async def get_audit(
    id: str,
    audit_service: WebsiteAuditService = Depends(get_audit_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Get a specific website audit by its ID."""
    return await audit_service.get_audit(id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    id: str,
    audit_service: WebsiteAuditService = Depends(get_audit_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a website audit."""
    await audit_service.delete_audit(id)
