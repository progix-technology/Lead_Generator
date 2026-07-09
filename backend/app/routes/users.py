from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict

from app.database.connection import get_database
from app.schemas.user import UserResponse
from app.auth.deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Get current logged-in user profile.
    This route is protected; it requires a valid JWT token.
    """
    return current_user
