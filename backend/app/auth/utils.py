import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from typing import Union, Any

from app.config.settings import get_settings

settings = get_settings()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password using raw bcrypt."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hashes a password using raw bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

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
