from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict

from app.database.connection import get_database
from app.repositories.score import LeadScoreRepository
from app.repositories.company import CompanyRepository
from app.services.score import LeadScoreService
from app.schemas.score import LeadScoreCreate, LeadScoreResponse, LeadScoreUpdate
from app.auth.deps import get_current_user

router = APIRouter()

def get_score_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> LeadScoreService:
    return LeadScoreService(LeadScoreRepository(db), CompanyRepository(db))

@router.post("/", response_model=LeadScoreResponse, status_code=status.HTTP_201_CREATED)
async def create_score(
    score_in: LeadScoreCreate,
    score_service: LeadScoreService = Depends(get_score_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Create a new lead score for a company."""
    return await score_service.create_score(score_in)

@router.get("/company/{company_id}", response_model=LeadScoreResponse)
async def get_score_for_company(
    company_id: str,
    score_service: LeadScoreService = Depends(get_score_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Get the latest lead score for a specific company."""
    return await score_service.get_score_for_company(company_id)

@router.get("/{id}", response_model=LeadScoreResponse)
async def get_score(
    id: str,
    score_service: LeadScoreService = Depends(get_score_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Get a specific lead score by its ID."""
    return await score_service.get_score(id)

@router.put("/{id}", response_model=LeadScoreResponse)
async def update_score(
    id: str,
    score_in: LeadScoreUpdate,
    score_service: LeadScoreService = Depends(get_score_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Update a lead score."""
    return await score_service.update_score(id, score_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score(
    id: str,
    score_service: LeadScoreService = Depends(get_score_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a lead score."""
    await score_service.delete_score(id)
