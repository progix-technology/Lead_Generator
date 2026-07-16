from fastapi import APIRouter, Depends, status, Query, HTTPException, BackgroundTasks
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
    redesign_subject_template: Optional[str] = None
    redesign_body_template: Optional[str] = None
    categories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    facebook_only: Optional[bool] = None
    enable_redesign: Optional[bool] = None
    daily_email_limit: Optional[int] = None
    batch_email_limit: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    email_service_provider: Optional[str] = None
    resend_api_key: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    sendgrid_sender: Optional[str] = None

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
    
    # If the user disables autopilot, cancel any active background batch immediately
    if "enabled" in update_data and not update_data["enabled"]:
        from app.services.automation_worker import request_cancellation
        request_cancellation()
        
    result = await repo.update_settings(update_data)
    return result

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

@router.get("/queue-status", response_model=Dict[str, Any])
async def get_queue_status(
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Retrieve the real-time queue counts for the live dashboard."""
    pending_count = await repo.count_pending_records()
    pending_standard_count = await repo.count_pending_standard_records()
    pending_redesign_count = await repo.count_pending_redesign_records()
    sent_today = await repo.count_records_today()
    
    return {
        "pending_count": pending_count,
        "pending_standard_count": pending_standard_count,
        "pending_redesign_count": pending_redesign_count,
        "sent_today": sent_today
    }

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_cycle(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    try:
        repo = AutomationRepository(db)
        config = await repo.get_settings()
        if not config.get("enabled", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Autopilot is OFF. Please enable it before triggering a batch run."
            )
        batch_target = config.get("batch_email_limit", 5)
        
        # Dispatch task to background to prevent HTTP gateway timeouts (e.g. 504) during long runs
        background_tasks.add_task(run_automation_cycle, db)
        return {"status": "success", "message": "Autopilot scraper run triggered in the background."}
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

@router.post("/resend/{record_id}", response_model=Dict[str, Any])
async def resend_failed_email(
    record_id: str,
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Re-queues a failed outreach record back to Pending_Email status so that Autopilot Mailer will pick it up again."""
    from bson import ObjectId
    from datetime import datetime
    try:
        record = await repo.records_col.find_one({"_id": ObjectId(record_id)})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
            
        await repo.records_col.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {
                "status": "Pending_Email", 
                "error_message": None, 
                "updated_at": datetime.utcnow()
            }}
        )
        return {"status": "success", "message": "Email has been re-queued for sending."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean-stale-queue", response_model=Dict[str, Any])
async def clean_stale_queue(
    repo: AutomationRepository = Depends(get_automation_repo),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Removes stale Pending_Email records that have a website but is_redesign=False (queued under old rules)."""
    pending = await repo.records_col.find({"status": "Pending_Email"}).to_list(length=5000)
    
    delete_ids = []
    for record in pending:
        meta = record.get("metadata") or {}
        is_redesign = meta.get("is_redesign")
        website = meta.get("website") or "your business"
        
        has_custom_site = (
            website
            and website != "your business"
            and "their website" not in website.lower()
            and "facebook.com" not in website.lower()
            and "instagram.com" not in website.lower()
            and "linkedin.com" not in website.lower()
        )
        
        if has_custom_site and not is_redesign:
            delete_ids.append(record["_id"])
    
    deleted_count = 0
    if delete_ids:
        result = await repo.records_col.delete_many({"_id": {"$in": delete_ids}})
        deleted_count = result.deleted_count
    
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Removed {deleted_count} stale non-redesign records from the Pending queue."
    }

@router.get("/test-ddg")
async def test_ddg(query: str = "Drywall", location: str = "Canton, OH"):
    from app.services.places import scrape_google_maps_fallback
    try:
        results = await scrape_google_maps_fallback(query, location)
        return {"status": "success", "results_count": len(results), "results": results[:5]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Trigger reload
