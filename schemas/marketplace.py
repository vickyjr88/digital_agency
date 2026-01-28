# Pydantic Schemas for Influencer Marketplace
# Organized in a modular structure for maintainability

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserTypeEnum(str, Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"


class PlatformType(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    MULTI = "multi"


class ContentTypeEnum(str, Enum):
    POST = "post"
    STORY = "story"
    REEL = "reel"
    VIDEO = "video"
    TWEET = "tweet"
    CAROUSEL = "carousel"


class PackageStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class CampaignStatus(str, Enum):
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


class DeliverableStatus(str, Enum):
    PENDING = "pending"
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    VERIFIED = "verified"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    ESCROW_LOCK = "escrow_lock"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_REFUND = "escrow_refund"
    PLATFORM_FEE = "platform_fee"
    TRANSFER = "transfer"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EscrowStatus(str, Enum):
    LOCKED = "locked"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# INFLUENCER SCHEMAS
# ============================================================================

class SocialMediaConnect(BaseModel):
    """Schema for connecting a social media account."""
    platform: PlatformType
    access_token: str
    refresh_token: Optional[str] = None


class SocialMediaStats(BaseModel):
    """Schema for social media statistics."""
    handle: Optional[str] = None
    followers: int = 0
    engagement_rate: float = 0.0
    verified: bool = False
    connected_at: Optional[datetime] = None


class InfluencerProfileCreate(BaseModel):
    """Schema for creating an influencer profile."""
    display_name: str = Field(..., min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    niche: str = Field(..., max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    
    # Social handles (will be verified via OAuth)
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    twitter_handle: Optional[str] = None


class InfluencerProfileUpdate(BaseModel):
    """Schema for updating an influencer profile."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    niche: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    profile_picture_url: Optional[str] = None


class InfluencerProfileResponse(BaseModel):
    """Schema for influencer profile response."""
    id: str
    user_id: str
    display_name: str
    bio: Optional[str]
    profile_picture_url: Optional[str]
    niche: str
    location: Optional[str]
    
    # Social media stats
    instagram: Optional[SocialMediaStats] = None
    tiktok: Optional[SocialMediaStats] = None
    youtube: Optional[SocialMediaStats] = None
    twitter: Optional[SocialMediaStats] = None
    
    # Reputation
    rating: float = 0.0
    review_count: int = 0
    completed_campaigns: int = 0
    
    # Verification
    is_verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.PENDING
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InfluencerSearchParams(BaseModel):
    """Schema for marketplace search parameters."""
    query: Optional[str] = None
    niche: Optional[str] = None
    platform: Optional[PlatformType] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_rating: Optional[float] = None
    location: Optional[str] = None
    verified_only: bool = False
    sort_by: str = "rating"  # rating, followers, price_low, price_high
    page: int = 1
    limit: int = 20


# ============================================================================
# PACKAGE SCHEMAS
# ============================================================================

class PackageRequirements(BaseModel):
    """Schema for package requirements from brand."""
    brand_guidelines: bool = True
    product_samples: bool = False
    hashtags_required: List[str] = []
    mentions_required: List[str] = []
    content_rights: str = "shared"  # shared, exclusive


class PackageCreate(BaseModel):
    """Schema for creating a package."""
    name: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)
    platform: PlatformType
    content_type: ContentTypeEnum
    deliverables_count: int = Field(..., ge=1, le=20)
    price: int = Field(..., ge=10)  # Minimum 10 KSH
    timeline_days: int = Field(..., ge=1, le=60)
    revisions_included: int = Field(2, ge=0, le=5)
    requirements: Optional[PackageRequirements] = None
    exclusions: Optional[str] = None


class PackageUpdate(BaseModel):
    """Schema for updating a package."""
    name: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=2000)
    price: Optional[int] = Field(None, ge=10)
    timeline_days: Optional[int] = Field(None, ge=1, le=60)
    revisions_included: Optional[int] = Field(None, ge=0, le=5)
    requirements: Optional[PackageRequirements] = None
    exclusions: Optional[str] = None
    status: Optional[PackageStatus] = None


class PackageResponse(BaseModel):
    """Schema for package response."""
    id: str
    influencer_id: str
    name: str
    description: str
    platform: PlatformType
    content_type: ContentTypeEnum
    deliverables_count: int
    price: int
    currency: str = "KES"
    timeline_days: int
    revisions_included: int
    requirements: Optional[PackageRequirements] = None
    exclusions: Optional[str] = None
    status: PackageStatus
    times_purchased: int = 0
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Included when fetching from marketplace
    influencer: Optional[InfluencerProfileResponse] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# WALLET SCHEMAS
# ============================================================================

class WalletResponse(BaseModel):
    """Schema for wallet response."""
    id: str
    user_id: str
    balance: int  # In cents
    hold_balance: int  # In escrow
    total_earned: int  # Lifetime
    total_spent: int  # Lifetime
    currency: str = "KES"
    
    class Config:
        from_attributes = True


class DepositRequest(BaseModel):
    """Schema for deposit request."""
    amount: int = Field(..., ge=10)  # Minimum 10 KES
    callback_url: Optional[str] = None


class WithdrawRequest(BaseModel):
    """Schema for withdrawal request."""
    amount: int = Field(..., ge=10)  # Minimum 10 KES
    payment_method: str = "bank_transfer"  # bank_transfer, mpesa


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    id: str
    from_wallet_id: Optional[str]
    to_wallet_id: Optional[str]
    amount: int
    fee: int = 0
    net_amount: int
    transaction_type: TransactionType
    status: TransactionStatus
    external_id: Optional[str]
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# CAMPAIGN SCHEMAS
# ============================================================================

class CampaignBrief(BaseModel):
    """Schema for campaign brief from brand."""
    product_description: str = Field(..., max_length=2000)
    target_audience: Optional[str] = Field(None, max_length=500)
    key_messages: List[str] = []
    hashtags: List[str] = []
    dos: List[str] = []  # Do's
    donts: List[str] = []  # Don'ts
    reference_links: List[str] = []
    additional_notes: Optional[str] = None


class CampaignCreate(BaseModel):
    """Schema for creating a campaign (purchasing a package)."""
    package_id: str
    brief: CampaignBrief
    custom_requirements: Optional[str] = None


class CampaignResponse(BaseModel):
    """Schema for campaign response."""
    id: str
    brand_id: str
    influencer_id: str
    package_id: str
    escrow_id: Optional[str]
    
    brief: Optional[CampaignBrief]
    custom_requirements: Optional[str]
    
    status: CampaignStatus
    
    deadline: Optional[datetime]
    started_at: Optional[datetime]
    draft_submitted_at: Optional[datetime]
    published_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    revisions_used: int = 0
    revisions_allowed: int
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Included relations
    package: Optional[PackageResponse] = None
    influencer: Optional[InfluencerProfileResponse] = None
    deliverables: List["DeliverableResponse"] = []
    
    class Config:
        from_attributes = True


class DeliverableSubmit(BaseModel):
    """Schema for submitting a deliverable."""
    content_type: ContentTypeEnum
    platform: PlatformType
    draft_url: Optional[str] = None
    draft_description: Optional[str] = None
    draft_caption: Optional[str] = None
    draft_media_urls: List[str] = []


class DeliverableResponse(BaseModel):
    """Schema for deliverable response."""
    id: str
    campaign_id: str
    content_type: ContentTypeEnum
    platform: PlatformType
    
    draft_url: Optional[str]
    draft_description: Optional[str]
    draft_caption: Optional[str]
    draft_media_urls: List[str] = []
    
    published_url: Optional[str]
    published_at: Optional[datetime]
    verified_at: Optional[datetime]
    
    status: DeliverableStatus
    
    # Performance metrics
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    shares: Optional[int]
    engagement_rate: Optional[float]
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# REVIEW SCHEMAS
# ============================================================================

class ReviewCreate(BaseModel):
    """Schema for creating a review."""
    campaign_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    """Schema for review response."""
    id: str
    campaign_id: str
    reviewer_id: str
    reviewee_id: str
    rating: int
    comment: Optional[str]
    response: Optional[str]
    created_at: datetime
    
    # Included when fetching
    reviewer_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# DISPUTE SCHEMAS
# ============================================================================

class DisputeCreate(BaseModel):
    """Schema for creating a dispute."""
    campaign_id: str
    reason: str = Field(..., min_length=20, max_length=2000)
    evidence_urls: List[str] = []


class DisputeResponse(BaseModel):
    """Schema for dispute response."""
    id: str
    campaign_id: str
    raised_by: str
    reason: str
    evidence_urls: List[str] = []
    status: DisputeStatus
    resolution: Optional[str]
    resolved_in_favor_of: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DisputeResolve(BaseModel):
    """Schema for resolving a dispute (admin only)."""
    resolution: str = Field(..., min_length=20, max_length=2000)
    resolved_in_favor_of: str  # user_id of brand or influencer
    refund_percentage: int = Field(0, ge=0, le=100)  # 0 = full release, 100 = full refund


# ============================================================================
# NOTIFICATION SCHEMAS
# ============================================================================

class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: str
    type: str
    title: str
    message: str
    data: Optional[dict] = None
    read: bool = False
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Update forward references
CampaignResponse.model_rebuild()
