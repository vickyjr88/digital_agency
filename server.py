# FastAPI Server with User Authentication and Brand Management

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Import database and auth utilities
from database.config import get_db, init_db, SessionLocal
from database.models import User, Brand, Content, SubscriptionTier, SubscriptionStatus, ContentStatus, UserRole, Usage, Trend, Transaction, PaymentStatus, generate_uuid, generate_uuid
from auth.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    Token
)
from core.sheets_handler import SheetsHandler
from core.generator import ContentGenerator
from config.personas import PERSONAS
from core.paystack_service import PaystackService, PaystackConfig, PaystackWebhookHandler

# Import marketplace routers (v2 API)
from routers.influencers import router as influencers_router
from routers.packages import router as packages_router
from routers.wallet import router as wallet_router
from routers.campaigns import router as campaigns_router
from routers.reviews import router as reviews_router
from routers.notifications import router as notifications_router
from routers.disputes import router as disputes_router

load_dotenv()

app = FastAPI(
    title="Dexter API",
    description="AI Content Marketing Platform API",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    # Initialize database tables using SQLAlchemy create_all
    # This is safer than Alembic auto-migrations which can fail if tables exist
    init_db()
    
    # Import marketplace models to ensure they're created
    try:
        from database import marketplace_models
        from database.config import engine
        from database.models import Base
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized!")
    except Exception as e:
        print(f"⚠️ Marketplace tables init warning: {e}")

    
    # Seed Admin User and Brands
    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_USER", "admin@dexter.com")
        admin_pass = os.getenv("ADMIN_PASS", "changeme")
        
        # Check if admin exists
        admin = db.query(User).filter(User.email == admin_email).first()
        
        if not admin:
            print(f"🌱 Seeding Admin User: {admin_email}")
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_pass),
                name="Dexter Admin",
                role=UserRole.ADMIN,
                subscription_tier=SubscriptionTier.AGENCY,
                subscription_status=SubscriptionStatus.ACTIVE
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
        # Seed Predefined Brands (owned by Admin)
        for key, data in PERSONAS.items():
            existing_brand = db.query(Brand).filter(Brand.name == data["name"], Brand.user_id == admin.id).first()
            if not existing_brand:
                print(f"🌱 Seeding Brand: {data['name']}")
                brand = Brand(
                    user_id=admin.id,
                    name=data["name"],
                    industry="General", # Default
                    description=data.get("role", "Predefined Brand"),
                    voice=data.get("voice", "Professional"),
                    content_focus=data.get("content_focus", []),
                    hashtags=data.get("hashtags", []),
                    is_active=True
                )
                db.add(brand)
        
        db.commit()
        
    except Exception as e:
        print(f"⚠️ Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

    # Initialize Scheduler for Trend Updates
    from apscheduler.schedulers.background import BackgroundScheduler
    from core.trend_service import TrendService
    
    def scheduled_trend_refresh():
        print("⏰ Running scheduled trend refresh...")
        db = SessionLocal()
        try:
            service = TrendService(db)
            service.fetch_and_store_trends()
        except Exception as e:
            print(f"❌ Scheduled trend refresh failed: {e}")
        finally:
            db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_trend_refresh, 'interval', hours=1)
    scheduler.start()
    print("✅ Scheduler started: Trends will refresh every hour.")

# CORS Setup - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Required when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)



# ============================================================================
# MARKETPLACE ROUTERS (v2 API)
# ============================================================================
# Mount new modular routers under /api/v2 for marketplace features
# Keeps backward compatibility with existing /api endpoints
app.include_router(influencers_router, prefix="/api/v2")
app.include_router(packages_router, prefix="/api/v2")
app.include_router(wallet_router, prefix="/api/v2")
app.include_router(campaigns_router, prefix="/api/v2")
app.include_router(reviews_router, prefix="/api/v2")
app.include_router(notifications_router, prefix="/api/v2")
app.include_router(disputes_router, prefix="/api/v2")

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

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

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
    scheduled_at: Optional[datetime] = None

class ContentSchedule(BaseModel):
    scheduled_at: datetime

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
def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current user information with simple usage stats.
    """
    usage = db.query(Usage).filter(
        Usage.user_id == current_user.id,
        Usage.month == datetime.utcnow().strftime("%Y-%m")
    ).first()
    
    current_usage = usage.content_generated_count if (usage and usage.content_generated_count is not None) else 0
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "subscription_tier": current_user.subscription_tier,
        "subscription_status": current_user.subscription_status,
        "trial_ends_at": current_user.trial_ends_at,
        "created_at": current_user.created_at,
        "usage": {
            "current": current_usage,
            "limit": current_user.content_limit
        }
    }

# ============================================================================
# BILLING & SUBSCRIPTION ENDPOINTS (Paystack / Kenya)
# ============================================================================

@app.get("/api/billing/plans")
def get_billing_plans():
    """
    Get available subscription plans (KES).
    """
    return PaystackService.get_all_plans()

class SubscriptionRequest(BaseModel):
    plan_id: str
    callback_url: Optional[str] = "https://dexter.vitaldigitalmedia.net/dashboard/billing/callback"

@app.post("/api/billing/subscribe")
def subscribe_to_plan(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize a subscription transaction.
    """
    plan = PaystackService.get_plan_details(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    service = PaystackService()
    
    # Amount is in kobo (cents)
    amount = plan["amount"]
    
    try:
        # Initialize transaction with Paystack
        response = service.initialize_transaction(
            email=current_user.email,
            amount=amount,
            plan_id=request.plan_id,
            user_id=current_user.id,
            callback_url=request.callback_url,
            metadata={
                "user_id": current_user.id,
                "plan_id": request.plan_id,
                "plan_name": plan["name"],
                "amount": amount
            }
        )
        
        # Record Pending Transaction
        new_tx = Transaction(
            id=generate_uuid(),
            user_id=current_user.id,
            reference=response['data']['reference'],
            amount=amount / 100, # Store as main currency unit (KES) not kobo
            currency='KES',
            status=PaymentStatus.PENDING,
            plan_id=request.plan_id,
            provider='paystack',
            metadata_json=response
        )
        db.add(new_tx)
        db.commit()
        
        return response
    except Exception as e:
        print(f"Subscription Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/billing/verify/{reference}")
def verify_payment(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a payment reference.
    """
    service = PaystackService()
    try:
        verification = service.verify_transaction(reference)
        
        if verification["status"] == True and verification["data"]["status"] == "success":
            # Update User Subscription
            metadata = verification["data"]["metadata"]
            plan_id = metadata.get("plan_id")
            
            if plan_id:
                # Map plan_id to SubscriptionTier
                tier_map = {
                    "day_pass": SubscriptionTier.STARTER,
                    "free": SubscriptionTier.FREE,
                    "starter": SubscriptionTier.STARTER,
                    "professional": SubscriptionTier.PROFESSIONAL,
                    "agency": SubscriptionTier.AGENCY
                }
                
                if plan_id in tier_map:
                    current_user.subscription_tier = tier_map[plan_id]
                    current_user.subscription_status = SubscriptionStatus.ACTIVE
                    
                    # Handle Day Pass Expiry (24 hours)
                    if plan_id == "day_pass":
                         current_user.trial_ends_at = datetime.utcnow() + timedelta(days=1)
                    
                    # Here we would ideally store the Paystack customer/sub codes too
                    db.commit()
            
            return {"status": "success", "data": verification["data"]}
        else:
             return {"status": "success", "data": verification["data"]}
        
    except Exception as e:
        print(f"Verification Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/billing/transactions")
def get_user_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's transaction history.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    
    return transactions

@app.post("/api/billing/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Paystack webhooks
    """
    # Verify signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="No signature")
    
    body = await request.body()
    secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    
    if not PaystackWebhookHandler.verify_webhook(body, signature, secret):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event = await request.json()
    event_type = event.get("event")
    data = event.get("data", {})
    
    print(f"🔔 Paystack Webhook received: {event_type}")
    
    # Extract reference
    reference = data.get("reference")
    
    if event_type == "charge.success":
        # Handle successful charge
        info = PaystackWebhookHandler.handle_charge_success(data)
        user_email = info.get("customer_email")
        
        # Update Transaction Status
        if reference:
            tx = db.query(Transaction).filter(Transaction.reference == reference).first()
            if tx:
                tx.status = PaymentStatus.SUCCESS
                tx.updated_at = datetime.utcnow()
                # Update user_id if missing (e.g. from metadata)
                if not tx.user_id and "metadata" in data:
                     meta_uid = data["metadata"].get("user_id")
                     if meta_uid:
                         tx.user_id = meta_uid
                db.commit()
                print(f"✅ Transaction {reference} marked SUCCESS")
        
        if user_email:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                # Ensure active status and update tier
                user.subscription_status = SubscriptionStatus.ACTIVE
                
                # Check metadata for plan info
                if "metadata" in data:
                    plan_name = data["metadata"].get("plan_name", "").lower()
                    
                    # Map plan names to tiers
                    if "day pass" in plan_name or "day_pass" in plan_name:
                        user.subscription_tier = SubscriptionTier.DAY_PASS
                        # Set 24 hour expiry
                        user.trial_ends_at = datetime.utcnow() + timedelta(hours=24)
                    elif "starter" in plan_name:
                        user.subscription_tier = SubscriptionTier.STARTER
                    elif "professional" in plan_name:
                        user.subscription_tier = SubscriptionTier.PROFESSIONAL
                    elif "agency" in plan_name:
                        user.subscription_tier = SubscriptionTier.AGENCY
                
                db.commit()
                print(f"✅ Activated subscription for {user_email} to {user.subscription_tier}")
                    
    elif event_type == "subscription.disable":
        # Handle cancellation
        email = data.get("customer", {}).get("email")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.subscription_status = SubscriptionStatus.CANCELLED
                db.commit()
                print(f"⚠️ Cancelled subscription for {email}")

    return {"status": "received"}

@app.put("/api/auth/profile")
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile.
    """
    if user_data.name:
        current_user.name = user_data.name
        
    if user_data.email and user_data.email != current_user.email:
        # Check uniqueness
        exists = db.query(User).filter(User.email == user_data.email).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = user_data.email
            
    if user_data.password:
        current_user.password_hash = get_password_hash(user_data.password)
        
    db.commit()
    db.refresh(current_user)
    
    return {"status": "success", "message": "Profile updated"}

@app.get("/api/admin/transactions")
def get_admin_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all transactions (Admin).
    Mocked for MVP since we don't store transaction logs in DB yet.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # In a full systems, query Payment/Transaction table
    return []

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
    query = db.query(Brand).filter(Brand.id == brand_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Brand.user_id == current_user.id)
    brand = query.first()
    
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
    query = db.query(Brand).filter(Brand.id == brand_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Brand.user_id == current_user.id)
    brand = query.first()
    
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

@app.post("/api/content/{content_id}/schedule")
def schedule_content(
    content_id: str,
    schedule_data: ContentSchedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Schedule content for future publishing.
    """
    content = db.query(Content).join(Brand).filter(
        Content.id == content_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    content.scheduled_at = schedule_data.scheduled_at
    content.status = ContentStatus.APPROVED
    
    db.commit()
    db.refresh(content)
    
    return content

# ============================================================================
# TRENDS & GENERATION ENDPOINTS
# ============================================================================

class GenerateRequest(BaseModel):
    trend: str
    trend_id: Optional[str] = None

@app.get("/api/trends")
def get_trends(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get latest trends from the database.
    This is a public endpoint for the landing page.
    """
    try:
        from core.trend_service import TrendService
        service = TrendService(db)
        return service.get_latest_trends(limit)
    except Exception as e:
        # Return empty list if trends table doesn't exist or other error
        print(f"⚠️ Trends error: {e}")
        return []

@app.post("/api/trends/refresh")
def refresh_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a fresh fetch of trends (Admin only).
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from core.trend_service import TrendService
    service = TrendService(db)
    trends = service.fetch_and_store_trends()
    return {"status": "success", "count": len(trends)}

@app.post("/api/generate/{brand_id}")
def generate_content_on_demand(
    brand_id: str,
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content for a specific brand and trend.
    """
    # 1. Verify Brand Ownership
    query = db.query(Brand).filter(Brand.id == brand_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Brand.user_id == current_user.id)
    brand = query.first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # 1.5. Check Monthly Limit (Exempt Admins)
    if current_user.role != UserRole.ADMIN:
        usage = db.query(Usage).filter(
            Usage.user_id == current_user.id,
            Usage.month == datetime.utcnow().strftime("%Y-%m")
        ).first()
        
        current_count = usage.content_generated_count if (usage and usage.content_generated_count is not None) else 0
        if current_count >= current_user.content_limit:
            raise HTTPException(
                status_code=403, 
                detail=f"Monthly content limit reached ({current_user.content_limit} posts). Upgrade your plan to generate more."
            )
    
    # 2. Prepare Persona for AI
    persona = {
        "name": brand.name,
        "role": brand.industry or "Brand",
        "voice": brand.voice,
        "content_focus": brand.content_focus or [],
        "key_message": brand.description,
        "hashtags": brand.hashtags or []
    }
    
    # 3. Generate Content
    generator = ContentGenerator()
    content_data = generator.generate_content(request.trend, persona)
    
    if not content_data:
        raise HTTPException(status_code=500, detail="Content generation failed")
    
    # 4. Save to Database
    new_content = Content(
        brand_id=brand.id,
        trend_id=request.trend_id,
        trend=request.trend,
        trend_category="On-Demand",
        tweet=content_data.get("tweet"),
        facebook_post=content_data.get("facebook_post"),
        instagram_reel_script=content_data.get("instagram_reel_script"),
        tiktok_idea=content_data.get("tiktok_idea"),
        status=ContentStatus.PENDING,
        generated_at=datetime.utcnow()
    )
    
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    
    # 5. Update Usage
    usage = db.query(Usage).filter(
        Usage.user_id == current_user.id,
        Usage.month == datetime.utcnow().strftime("%Y-%m")
    ).first()
    
    if not usage:
        usage = Usage(
            user_id=current_user.id,
            month=datetime.utcnow().strftime("%Y-%m"),
            content_generated_count=0,
            api_calls_count=0
        )
        db.add(usage)
    
    if usage.content_generated_count is None:
        usage.content_generated_count = 0
        
    usage.content_generated_count += 1
    db.commit()
    
    return new_content

# ============================================================================
# LEGACY ENDPOINTS (Backward Compatibility)
# ============================================================================

@app.get("/api/admin/users")
def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all users (Admin only).
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    users = db.query(User).all()
    return users


class SubscriptionUpdate(BaseModel):
    subscription_tier: Optional[str] = None  # FREE, DAY_PASS, STARTER, PROFESSIONAL, AGENCY
    subscription_status: Optional[str] = None  # ACTIVE, INACTIVE, CANCELLED, EXPIRED


@app.put("/api/admin/users/{user_id}/subscription")
def update_user_subscription(
    user_id: str,
    update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user subscription (Admin only).
    Use this to manually upgrade users who paid but weren't upgraded.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update subscription tier
    if update.subscription_tier:
        try:
            tier = SubscriptionTier(update.subscription_tier.upper())
            user.subscription_tier = tier
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {[t.value for t in SubscriptionTier]}"
            )
    
    # Update subscription status
    if update.subscription_status:
        try:
            status_val = SubscriptionStatus(update.subscription_status.upper())
            user.subscription_status = status_val
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in SubscriptionStatus]}"
            )
    
    # For Day Pass, set trial_ends_at to 24 hours from now
    if update.subscription_tier and update.subscription_tier.upper() == "DAY_PASS":
        user.trial_ends_at = datetime.utcnow() + timedelta(hours=24)
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Subscription updated successfully",
        "user_id": user.id,
        "email": user.email,
        "subscription_tier": user.subscription_tier.value if user.subscription_tier else None,
        "subscription_status": user.subscription_status.value if user.subscription_status else None,
        "trial_ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else None
    }


@app.get("/api/admin/users/{user_id}/transactions")
def get_user_transactions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for a specific user (Admin only).
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).all()
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "subscription_tier": user.subscription_tier.value if user.subscription_tier else None,
            "subscription_status": user.subscription_status.value if user.subscription_status else None,
        },
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "currency": t.currency,
                "status": t.status.value if t.status else None,
                "payment_reference": t.payment_reference,
                "plan": t.plan,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ]
    }


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

# ADMIN STATISTICS ENDPOINTS
# ============================================================================

@app.get("/api/admin/stats")
def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Financial Stats
    total_revenue_amount = db.query(func.sum(Transaction.amount)).filter(Transaction.status == PaymentStatus.SUCCESS).scalar() or 0
    active_subscriptions = db.query(User).filter(User.subscription_status == SubscriptionStatus.ACTIVE).count()
    pending_transactions = db.query(Transaction).filter(Transaction.status == PaymentStatus.PENDING).count()
    
    # Usage Stats
    total_users = db.query(User).count()
    total_brands = db.query(Brand).count()
    total_trends = db.query(Trend).count()
    total_content = db.query(Content).count()
    
    # Recent Transactions
    recent_txs = db.query(Transaction).join(User).order_by(Transaction.created_at.desc()).limit(5).all()
    recent_transactions_data = []
    for tx in recent_txs:
        recent_transactions_data.append({
            "id": tx.id,
            "created_at": tx.created_at,
            "user_email": tx.user.email,
            "amount": tx.amount,
            "currency": tx.currency,
            "status": tx.status
        })
    
    return {
        "total_revenue": f"KES {total_revenue_amount:,.2f}",
        "active_subscriptions": active_subscriptions,
        "pending_transactions": pending_transactions,
        "recent_transactions": recent_transactions_data,
        "users": total_users,
        "brands": total_brands,
        "trends": total_trends,
        "content_generated": total_content
    }

@app.get("/api/admin/latest")
def get_admin_latest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    latest_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    latest_brands = db.query(Brand).order_by(Brand.created_at.desc()).limit(5).all()
    latest_trends = db.query(Trend).order_by(Trend.timestamp.desc()).limit(5).all()
    latest_content = db.query(Content).order_by(Content.generated_at.desc()).limit(5).all()
    
    return {
        "users": latest_users,
        "brands": latest_brands,
        "trends": latest_trends,
        "content": latest_content
    }

@app.get("/api/admin/brands")
def get_all_brands_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Join Brand with User to get owner details
    brands = db.query(Brand).join(User).all()
    
    result = []
    for brand in brands:
        result.append({
            "id": brand.id,
            "name": brand.name,
            "industry": brand.industry,
            "created_at": brand.created_at,
            "is_active": brand.is_active,
            "owner": {
                "id": brand.user.id,
                "name": brand.user.name,
                "email": brand.user.email
            }
        })
        
    return result

@app.get("/api/admin/users/{user_id}")
def get_admin_user_details(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Manually construct response
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "subscription_tier": user.subscription_tier,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at,
        "brands": [
            {
                "id": b.id,
                "name": b.name,
                "industry": b.industry,
                "is_active": b.is_active,
                "created_at": b.created_at
            } for b in user.brands
        ],
        "usage": [
            {
                "month": u.month,
                "content_generated_count": u.content_generated_count,
                "api_calls_count": u.api_calls_count
            } for u in user.usage
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
