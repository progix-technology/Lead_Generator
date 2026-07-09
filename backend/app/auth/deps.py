from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any

from app.config.settings import get_settings
from app.database.connection import get_database
from app.repositories.user import UserRepository

settings = get_settings()

# This tells FastAPI where the client can go to get a token (used for Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> UserRepository:
    """Dependency to inject the UserRepository."""
    return UserRepository(db)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user.
    Use this in your routes to protect endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Fetch user from database
    user = await user_repo.get_by_email(email)
    if user is None:
        raise credentials_exception
        
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
