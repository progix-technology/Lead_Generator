from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict
from bson import ObjectId

from app.database.connection import get_database
from app.schemas.user import UserResponse, UserUpdate
from app.auth.deps import get_current_user
from app.repositories.user import UserRepository
from app.auth.utils import verify_password, get_password_hash

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

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    payload: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Update logged-in user profile details (first name, last name, email) or change password.
    """
    repo = UserRepository(db)
    update_data = {}
    
    # 1. Update Email (Check for unique constraints)
    if payload.email and payload.email != current_user.get("email"):
        existing_user = await repo.get_by_email(payload.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another user."
            )
        update_data["email"] = payload.email

    # 2. Update Basic Fields
    if payload.first_name is not None:
        update_data["first_name"] = payload.first_name
    if payload.last_name is not None:
        update_data["last_name"] = payload.last_name

    # 3. Update Password (Verify current password)
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password."
            )
        
        user_doc = await repo.collection.find_one({"_id": ObjectId(current_user["id"])})
        if not user_doc or not verify_password(payload.current_password, user_doc.get("hashed_password", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password."
            )
            
        update_data["hashed_password"] = get_password_hash(payload.new_password)

    if not update_data:
        return current_user

    updated_user = await repo.update(current_user["id"], update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found."
        )
    return updated_user

