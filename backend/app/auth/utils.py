from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from typing import Union, Any

from app.config.settings import get_settings

settings = get_settings()

# Setup Passlib with bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Creates a JWT Access Token.
    The 'subject' is usually the user's ID or email.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # We store the subject in the "sub" claim and the expiration in "exp"
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Sign the token using our secret key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
