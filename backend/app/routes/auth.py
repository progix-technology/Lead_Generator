from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any

from app.database.connection import get_database
from app.repositories.user import UserRepository
from app.services.user import UserService
from app.schemas.user import UserCreate, UserResponse, Token
from app.auth.utils import verify_password, create_access_token

router = APIRouter()

# Dependency to get UserService
def get_user_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> UserService:
    return UserService(UserRepository(db))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    Register a new user.
    """
    user = await user_service.register_user(user_in)
    return user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncIOMotorDatabase = Depends(get_database),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(form_data.username) # OAuth2 form uses 'username' for the email
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
        
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate JWT token
    access_token = create_access_token(subject=user["email"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
