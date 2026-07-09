from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Shared properties for a User
class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    role: str = "admin"

# Properties required to create a new user (Register)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

# Properties required to login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Properties to return in API responses (Notice it doesn't include password!)
class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        # Allows Pydantic to read data even if it's not a strict dict 
        # (useful when converting from MongoDB documents)
        from_attributes = True

# Schema for the JWT Token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
