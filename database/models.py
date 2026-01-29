# Database Models for Dexter SaaS Platform

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

# Enums
class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    AGENCY = "agency"
    DAY_PASS = "day_pass"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"

class ContentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"

class TeamRole(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


# New enum for marketplace user types
class UserType(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.USER)
    user_type = Column(Enum(UserType), default=UserType.BRAND)  # Marketplace user type
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL)
    stripe_customer_id = Column(String(255), unique=True)
    trial_ends_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    brands = relationship("Brand", back_populates="user", cascade="all, delete-orphan")
    usage = relationship("Usage", back_populates="user", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    @property
    def content_limit(self):
        from database.models import SubscriptionTier
        limits = {
            SubscriptionTier.FREE: 5,
            SubscriptionTier.STARTER: 100,
            SubscriptionTier.PROFESSIONAL: 500,
            SubscriptionTier.AGENCY: 2000
        }
        return limits.get(self.subscription_tier, 5)

class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    industry = Column(String(255))
    description = Column(Text)
    voice = Column(String(100))  # casual, professional, humorous, etc.
    content_focus = Column(JSON)  # Array of focus areas
    hashtags = Column(JSON)  # Array of hashtags
    custom_instructions = Column(Text)
    logo_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="brands")
    content = relationship("Content", back_populates="brand", cascade="all, delete-orphan")
    team_members = relationship("TeamMember", back_populates="brand", cascade="all, delete-orphan")

class Trend(Base):
    __tablename__ = "trends"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic = Column(String(255), nullable=False)
    volume = Column(String(50)) # e.g. "10k+" or "High"
    url = Column(String(500))
    source = Column(String(50)) # "Google", "Twitter", "Trends24"
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    contents = relationship("Content", back_populates="trend_ref")

class Content(Base):
    __tablename__ = "content"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    trend_id = Column(String(36), ForeignKey("trends.id", ondelete="SET NULL"), nullable=True)
    trend = Column(String(500), nullable=False) # Keep for backward compatibility or direct text
    trend_category = Column(String(50))  # viral, local, niche
    tweet = Column(Text)
    facebook_post = Column(Text)
    instagram_reel_script = Column(JSON)
    tiktok_idea = Column(JSON)
    status = Column(Enum(ContentStatus), default=ContentStatus.PENDING)
    generated_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime)
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    meta_data = Column(JSON)  # Analytics, engagement data (renamed from metadata to avoid SQLAlchemy conflict)
    
    # Relationships
    brand = relationship("Brand", back_populates="content")
    trend_ref = relationship("Trend", back_populates="contents")

class Usage(Base):
    __tablename__ = "usage"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM format
    content_generated_count = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage")
    
    # Composite unique constraint
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Owner
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    member_email = Column(String(255), nullable=False)
    role = Column(Enum(TeamRole), default=TeamRole.VIEWER)
    invited_at = Column(DateTime, server_default=func.now())
    accepted_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="team_memberships")
    brand = relationship("Brand", back_populates="team_members")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reference = Column(String(100), unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), default="KES")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    plan_id = Column(String(50))
    provider = Column(String(20), default="paystack")
    metadata_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    

class GenerationFailure(Base):
    __tablename__ = "generation_failures"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True)
    trend = Column(String(500))
    error_message = Column(Text)
    timestamp = Column(DateTime, server_default=func.now())
