# FastAPI Server with User Authentication and Brand Management

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Import database and auth utilities
from database.config import get_db, init_db
from database.models import User, Brand, Content, SubscriptionTier, SubscriptionStatus, ContentStatus
from auth.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    Token
)
from core.sheets_handler import SheetsHandler

load_dotenv()

app = FastAPI(
    title="Dexter API",
    description="AI Content Marketing Platform API",
    version="1.0.0"
)

# CORS Setup
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
    "http://localhost:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BrandCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    voice: Optional[str] = "professional"
    content_focus: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    custom_instructions: Optional[str] = None

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    voice: Optional[str] = None
    content_focus: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    custom_instructions: Optional[str] = None
    is_active: Optional[bool] = None

class ContentUpdate(BaseModel):
    tweet: Optional[str] = None
    facebook_post: Optional[str] = None
    status: Optional[str] = None

# Legacy models (for backward compatibility)
class LoginRequest(BaseModel):
    username: str
    password: str

class UpdateRequest(BaseModel):
    row_id: int
    data: Dict[str, Any]

# Dependency to get current user from JWT token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user.
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

# Health Check
@app.get("/")
def root():
    return {
        "message": "Dexter API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    Returns JWT token on success.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
        subscription_tier=SubscriptionTier.FREE,
        subscription_status=SubscriptionStatus.TRIAL,
        trial_ends_at=datetime.utcnow() + timedelta(days=14)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login_new(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns JWT token on success.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "subscription_tier": current_user.subscription_tier,
        "subscription_status": current_user.subscription_status,
        "trial_ends_at": current_user.trial_ends_at,
        "created_at": current_user.created_at
    }

# ============================================================================
# BRAND MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/brands")
def get_brands(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all brands for the current user.
    """
    brands = db.query(Brand).filter(Brand.user_id == current_user.id).all()
    return brands

@app.post("/api/brands", status_code=status.HTTP_201_CREATED)
def create_brand(
    brand_data: BrandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new brand for the current user.
    """
    # Check brand limit based on subscription tier
    brand_count = db.query(Brand).filter(Brand.user_id == current_user.id).count()
    
    limits = {
        SubscriptionTier.FREE: 1,
        SubscriptionTier.STARTER: 3,
        SubscriptionTier.PROFESSIONAL: 10,
        SubscriptionTier.AGENCY: float('inf')
    }
    
    if brand_count >= limits.get(current_user.subscription_tier, 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Brand limit reached for {current_user.subscription_tier} tier"
        )
    
    new_brand = Brand(
        user_id=current_user.id,
        name=brand_data.name,
        industry=brand_data.industry,
        description=brand_data.description,
        voice=brand_data.voice,
        content_focus=brand_data.content_focus,
        hashtags=brand_data.hashtags,
        custom_instructions=brand_data.custom_instructions
    )
    
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    
    return new_brand

@app.get("/api/brands/{brand_id}")
def get_brand(
    brand_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific brand by ID.
    """
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return brand

@app.put("/api/brands/{brand_id}")
def update_brand(
    brand_id: str,
    brand_data: BrandUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a brand.
    """
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Update fields
    update_data = brand_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand, field, value)
    
    db.commit()
    db.refresh(brand)
    
    return brand

@app.delete("/api/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a brand.
    """
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    db.delete(brand)
    db.commit()
    
    return None

# ============================================================================
# CONTENT ENDPOINTS
# ============================================================================

@app.get("/api/brands/{brand_id}/content")
def get_brand_content(
    brand_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all content for a specific brand.
    """
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    content = db.query(Content).filter(Content.brand_id == brand_id).order_by(Content.generated_at.desc()).all()
    return content

@app.put("/api/content/{content_id}")
def update_content_item(
    content_id: str,
    content_data: ContentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a content item.
    """
    content = db.query(Content).join(Brand).filter(
        Content.id == content_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Update fields
    update_data = content_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(content, field, value)
    
    if content_data.status == "approved":
        content.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(content)
    
    return content

# ============================================================================
# LEGACY ENDPOINTS (Backward Compatibility)
# ============================================================================

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

@app.post("/api/login")
def login_legacy(creds: LoginRequest):
    """
    Legacy login endpoint for old dashboard.
    """
    if creds.username == ADMIN_USER and creds.password == ADMIN_PASS:
        return {"status": "success", "token": "fake-jwt-token-for-demo"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/content")
def get_content_legacy():
    """
    Legacy endpoint - returns Google Sheets data.
    """
    handler = SheetsHandler()
    data = handler.get_all_content()
    return data

@app.put("/api/content/{row_id}")
def update_content_legacy(row_id: int, update: UpdateRequest):
    """
    Legacy endpoint - updates Google Sheets.
    """
    handler = SheetsHandler()
    success = handler.update_content(row_id, update.data)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update content")

# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize database on startup.
    """
    try:
        init_db()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
