# Authentication Dependencies for Dexter Platform
# Provides dependencies for getting the current user from JWT token

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import os

from database.config import get_db
from database.models import User


# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


class TokenData(BaseModel):
    email: Optional[str] = None


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email") or payload.get("sub")
        if email is None:
            return None
        return TokenData(email=email)
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
    This is the core authentication dependency.
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


security_optional = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Return user if authenticated, else None."""
    if not credentials:
        return None
    
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None:
        return None
    
    return db.query(User).filter(User.email == token_data.email).first()
