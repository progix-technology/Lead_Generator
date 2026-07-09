from fastapi import APIRouter, Depends, status, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from app.database.connection import get_database
from app.repositories.automation import AutomationRepository
from app.auth.deps import get_current_user
from app.services.automation_worker import run_automation_cycle

router = APIRouter()

def get_automation_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> AutomationRepository:
    return AutomationRepository(db)

class AutomationSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    categories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    facebook_only: Optional[bool] = None

@router.get("/settings", response_model=Dict[str, Any])
async def get_settings(
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Retrieve the Autopilot settings (ON/OFF status, email templates)."""
    return await repo.get_settings()

@router.post("/settings", response_model=Dict[str, Any])
async def update_settings(
    payload: AutomationSettingsUpdate,
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Update Autopilot configurations."""
    update_data = payload.model_dump(exclude_unset=True)
    return await repo.update_settings(update_data)

@router.get("/records", response_model=Dict[str, Any])
async def get_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Retrieve logs of automatically sent cold outreach emails."""
    records = await repo.get_records(skip, limit)
    total_count = await repo.count_records()
    today_count = await repo.count_records_today()
    return {
        "total_count": total_count,
        "today_count": today_count,
        "data": records
    }

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_cycle(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Manually trigger one autopilot run cycle now (scans category, location and auto-sends up to daily limit)."""
    try:
        res = await run_automation_cycle(db)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autopilot manual run failed: {str(e)}"
        )

@router.get("/progress", response_model=Dict[str, Any])
async def get_progress(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Retrieve real-time progress logs of the currently running autopilot cycle."""
    from app.services.automation_worker import automation_progress
    return {"progress": automation_progress}
