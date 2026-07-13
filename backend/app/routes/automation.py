from fastapi import APIRouter, Depends, status, Query, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from app.database.connection import get_database
from app.repositories.automation import AutomationRepository
from app.auth.deps import get_current_user
from app.services.automation_worker import run_automation_cycle, run_automation_batch

router = APIRouter()

def get_automation_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> AutomationRepository:
    return AutomationRepository(db)

class AutomationSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    redesign_subject_template: Optional[str] = None
    redesign_body_template: Optional[str] = None
    categories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    facebook_only: Optional[bool] = None
    daily_email_limit: Optional[int] = None
    batch_email_limit: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None
    openrouter_api_key: Optional[str] = None

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
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    from app.services.automation_worker import is_batch_running
    if is_batch_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Autopilot is already actively running a campaign batch. Please wait for the current run to finish."
        )
    try:
        repo = AutomationRepository(db)
        config = await repo.get_settings()
        batch_target = config.get("batch_email_limit", 5)
        
        # Dispatch task to background to prevent HTTP gateway timeouts (e.g. 504) during long runs
        background_tasks.add_task(run_automation_batch, db, batch_target)
        return {"status": "success", "message": "Autopilot batch run triggered in the background."}
    except HTTPException:
        raise
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
    from app.services.automation_worker import automation_progress, is_batch_running
    return {"progress": automation_progress, "is_running": is_batch_running}

@router.get("/test-ddg")
async def test_ddg(query: str = "Drywall", location: str = "Canton, OH"):
    from app.services.places import scrape_google_maps_fallback
    try:
        results = await scrape_google_maps_fallback(query, location)
        return {"status": "success", "results_count": len(results), "results": results[:5]}
    except Exception as e:
        return {"status": "error", "message": str(e)}
