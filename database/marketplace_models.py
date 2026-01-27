# Extended Database Models for Dexter Marketplace
# These models extend the base Dexter platform with marketplace functionality
# Import these in addition to the existing models in database/models.py

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Enum, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

# Use the same Base from existing models
from database.models import Base, generate_uuid


# ============================================================================
# ENUMS
# ============================================================================

class UserTypeDB(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"


class PlatformTypeDB(str, enum.Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    MULTI = "multi"


class PackageStatusDB(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class CampaignStatusDB(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DRAFT_SUBMITTED = "draft_submitted"
    REVISION_REQUESTED = "revision_requested"
    DRAFT_APPROVED = "draft_approved"
    PUBLISHED = "published"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class DeliverableStatusDB(str, enum.Enum):
    PENDING = "pending"
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    VERIFIED = "verified"


class WalletTransactionTypeDB(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    ESCROW_LOCK = "escrow_lock"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_REFUND = "escrow_refund"
    PLATFORM_FEE = "platform_fee"
    TRANSFER = "transfer"


class WalletTransactionStatusDB(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EscrowStatusDB(str, enum.Enum):
    LOCKED = "locked"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class DisputeStatusDB(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class VerificationStatusDB(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# INFLUENCER PROFILE
# ============================================================================

class InfluencerProfile(Base):
    """Extended profile for influencer users."""
    __tablename__ = "influencer_profiles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Basic info
    display_name = Column(String(100), nullable=False)
    bio = Column(Text)
    profile_picture_url = Column(String(500))
    niche = Column(String(100), nullable=False)
    location = Column(String(100))
    
    # Instagram
    instagram_handle = Column(String(100))
    instagram_id = Column(String(100))
    instagram_followers = Column(Integer, default=0)
    instagram_engagement_rate = Column(Float, default=0.0)
    instagram_verified = Column(Boolean, default=False)
    instagram_connected_at = Column(DateTime)
    instagram_access_token = Column(String(500))  # Encrypted
    
    # TikTok
    tiktok_handle = Column(String(100))
    tiktok_id = Column(String(100))
    tiktok_followers = Column(Integer, default=0)
    tiktok_engagement_rate = Column(Float, default=0.0)
    tiktok_verified = Column(Boolean, default=False)
    tiktok_connected_at = Column(DateTime)
    tiktok_access_token = Column(String(500))  # Encrypted
    
    # YouTube
    youtube_channel = Column(String(100))
    youtube_id = Column(String(100))
    youtube_subscribers = Column(Integer, default=0)
    youtube_engagement_rate = Column(Float, default=0.0)
    youtube_verified = Column(Boolean, default=False)
    youtube_connected_at = Column(DateTime)
    youtube_access_token = Column(String(500))  # Encrypted
    
    # Twitter/X
    twitter_handle = Column(String(100))
    twitter_id = Column(String(100))
    twitter_followers = Column(Integer, default=0)
    twitter_engagement_rate = Column(Float, default=0.0)
    twitter_verified = Column(Boolean, default=False)
    twitter_connected_at = Column(DateTime)
    twitter_access_token = Column(String(500))  # Encrypted
    
    # Reputation
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    completed_campaigns = Column(Integer, default=0)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_status = Column(Enum(VerificationStatusDB), default=VerificationStatusDB.PENDING)
    identity_verified_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="influencer_profile")
    packages = relationship("Package", back_populates="influencer", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="influencer", foreign_keys="Campaign.influencer_id")


# ============================================================================
# PACKAGE
# ============================================================================

class Package(Base):
    """Marketing packages offered by influencers."""
    __tablename__ = "packages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    platform = Column(Enum(PlatformTypeDB), nullable=False)
    content_type = Column(String(50), nullable=False)  # post, story, reel, video
    deliverables_count = Column(Integer, nullable=False, default=1)
    price = Column(Integer, nullable=False)  # In cents (smallest currency unit)
    currency = Column(String(3), default="KES")
    timeline_days = Column(Integer, nullable=False)
    revisions_included = Column(Integer, default=2)
    
    requirements = Column(JSON)  # What's needed from brand
    exclusions = Column(Text)    # What's NOT included
    
    status = Column(Enum(PackageStatusDB), default=PackageStatusDB.ACTIVE)
    times_purchased = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    influencer = relationship("InfluencerProfile", back_populates="packages")
    campaigns = relationship("Campaign", back_populates="package")


# ============================================================================
# WALLET
# ============================================================================

class Wallet(Base):
    """User wallet for marketplace transactions."""
    __tablename__ = "wallets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    balance = Column(Integer, default=0)  # In cents
    hold_balance = Column(Integer, default=0)  # Amount in escrow
    total_earned = Column(Integer, default=0)  # Lifetime earnings (influencers)
    total_spent = Column(Integer, default=0)   # Lifetime spending (brands)
    currency = Column(String(3), default="KES")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="wallet")
    sent_transactions = relationship("WalletTransaction", 
                                     foreign_keys="WalletTransaction.from_wallet_id",
                                     back_populates="from_wallet")
    received_transactions = relationship("WalletTransaction",
                                        foreign_keys="WalletTransaction.to_wallet_id", 
                                        back_populates="to_wallet")


class WalletTransaction(Base):
    """Record of wallet transactions."""
    __tablename__ = "wallet_transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    from_wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=True)
    to_wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=True)
    
    amount = Column(Integer, nullable=False)  # In cents
    fee = Column(Integer, default=0)  # Platform fee
    net_amount = Column(Integer, nullable=False)  # amount - fee
    
    transaction_type = Column(Enum(WalletTransactionTypeDB), nullable=False)
    status = Column(Enum(WalletTransactionStatusDB), default=WalletTransactionStatusDB.PENDING)
    
    payment_method = Column(String(30))  # stripe_card, mpesa, bank_transfer
    external_id = Column(String(255))    # Paystack reference, etc.
    description = Column(Text)
    metadata_json = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    from_wallet = relationship("Wallet", foreign_keys=[from_wallet_id], back_populates="sent_transactions")
    to_wallet = relationship("Wallet", foreign_keys=[to_wallet_id], back_populates="received_transactions")
    escrow_holds = relationship("EscrowHold", foreign_keys="EscrowHold.transaction_id", back_populates="transaction")


# ============================================================================
# ESCROW
# ============================================================================

class EscrowHold(Base):
    """Escrow holds for campaign payments."""
    __tablename__ = "escrow_holds"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(36), ForeignKey("wallet_transactions.id"), nullable=False)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True)  # Set after campaign created
    
    amount = Column(Integer, nullable=False)  # In cents
    status = Column(Enum(EscrowStatusDB), default=EscrowStatusDB.LOCKED)
    
    locked_at = Column(DateTime, server_default=func.now())
    auto_release_at = Column(DateTime)  # 14 days from locked_at
    released_at = Column(DateTime)
    
    release_transaction_id = Column(String(36), ForeignKey("wallet_transactions.id"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transaction = relationship("WalletTransaction", foreign_keys=[transaction_id], back_populates="escrow_holds")
    # Note: campaign relationship is one-way due to circular FK


# ============================================================================
# CAMPAIGN
# ============================================================================

class Campaign(Base):
    """Marketing campaigns between brands and influencers."""
    __tablename__ = "campaigns"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    brand_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id"), nullable=False)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    escrow_id = Column(String(36), ForeignKey("escrow_holds.id"), nullable=True)
    
    # Campaign details
    brief = Column(JSON)  # CampaignBrief as JSON
    custom_requirements = Column(Text)
    
    status = Column(Enum(CampaignStatusDB), default=CampaignStatusDB.PENDING)
    
    # Timeline
    deadline = Column(DateTime)
    started_at = Column(DateTime)
    draft_submitted_at = Column(DateTime)
    published_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Revision tracking
    revisions_used = Column(Integer, default=0)
    revisions_allowed = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    brand = relationship("User", backref="brand_campaigns")
    influencer = relationship("InfluencerProfile", back_populates="campaigns")
    package = relationship("Package", back_populates="campaigns")
    escrow = relationship("EscrowHold", foreign_keys=[escrow_id], uselist=False)  # One-to-one
    deliverables = relationship("Deliverable", back_populates="campaign", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="campaign", cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="campaign", cascade="all, delete-orphan")


# ============================================================================
# DELIVERABLE
# ============================================================================

class Deliverable(Base):
    """Content deliverables for campaigns."""
    __tablename__ = "deliverables"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    content_type = Column(String(50), nullable=False)  # post, story, reel, video
    platform = Column(Enum(PlatformTypeDB), nullable=False)
    
    # Draft content
    draft_url = Column(String(500))
    draft_description = Column(Text)
    draft_caption = Column(Text)
    draft_media_urls = Column(JSON)  # Array of URLs
    
    # Published content
    published_url = Column(String(500))
    published_at = Column(DateTime)
    verified_at = Column(DateTime)
    
    status = Column(Enum(DeliverableStatusDB), default=DeliverableStatusDB.PENDING)
    
    # Performance metrics (captured post-publication)
    views = Column(Integer)
    likes = Column(Integer)
    comments = Column(Integer)
    shares = Column(Integer)
    engagement_rate = Column(Float)
    metrics_updated_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="deliverables")


# ============================================================================
# REVIEW
# ============================================================================

class Review(Base):
    """Reviews for completed campaigns."""
    __tablename__ = "reviews"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    response = Column(Text)  # Reviewee can respond
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="given_reviews")
    reviewee = relationship("User", foreign_keys=[reviewee_id], backref="received_reviews")


# ============================================================================
# DISPUTE
# ============================================================================

class Dispute(Base):
    """Disputes raised on campaigns."""
    __tablename__ = "disputes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    raised_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    reason = Column(Text, nullable=False)
    evidence_urls = Column(JSON)  # Array of URLs
    
    status = Column(Enum(DisputeStatusDB), default=DisputeStatusDB.OPEN)
    
    resolution = Column(Text)
    resolved_in_favor_of = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # Admin
    resolved_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="disputes")
    raiser = relationship("User", foreign_keys=[raised_by], backref="raised_disputes")
    resolved_for = relationship("User", foreign_keys=[resolved_in_favor_of])
    resolver = relationship("User", foreign_keys=[resolved_by])


# ============================================================================
# NOTIFICATION
# ============================================================================

class Notification(Base):
    """User notifications."""
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(String(50), nullable=False)  # campaign_update, payment_received, etc.
    title = Column(String(200), nullable=False)
    message = Column(Text)
    data = Column(JSON)  # Additional context (campaign_id, amount, etc.)
    
    read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="notifications")
