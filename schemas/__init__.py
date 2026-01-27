# Schemas module for Dexter Platform
# Organizes all Pydantic schemas in a modular structure

from schemas.marketplace import (
    # Enums
    UserTypeEnum,
    PlatformType,
    ContentTypeEnum,
    PackageStatus,
    CampaignStatus,
    DeliverableStatus,
    TransactionType,
    TransactionStatus,
    EscrowStatus,
    DisputeStatus,
    VerificationStatus,
    
    # Influencer schemas
    SocialMediaConnect,
    SocialMediaStats,
    InfluencerProfileCreate,
    InfluencerProfileUpdate,
    InfluencerProfileResponse,
    InfluencerSearchParams,
    
    # Package schemas
    PackageRequirements,
    PackageCreate,
    PackageUpdate,
    PackageResponse,
    
    # Wallet schemas
    WalletResponse,
    DepositRequest,
    WithdrawRequest,
    TransactionResponse,
    
    # Campaign schemas
    CampaignBrief,
    CampaignCreate,
    CampaignResponse,
    DeliverableSubmit,
    DeliverableResponse,
    
    # Review schemas
    ReviewCreate,
    ReviewResponse,
    
    # Dispute schemas
    DisputeCreate,
    DisputeResponse,
    DisputeResolve,
    
    # Notification schemas
    NotificationResponse,
)

__all__ = [
    # Enums
    "UserTypeEnum",
    "PlatformType",
    "ContentTypeEnum",
    "PackageStatus",
    "CampaignStatus",
    "DeliverableStatus",
    "TransactionType",
    "TransactionStatus",
    "EscrowStatus",
    "DisputeStatus",
    "VerificationStatus",
    
    # Influencer
    "SocialMediaConnect",
    "SocialMediaStats",
    "InfluencerProfileCreate",
    "InfluencerProfileUpdate",
    "InfluencerProfileResponse",
    "InfluencerSearchParams",
    
    # Package
    "PackageRequirements",
    "PackageCreate",
    "PackageUpdate",
    "PackageResponse",
    
    # Wallet
    "WalletResponse",
    "DepositRequest",
    "WithdrawRequest",
    "TransactionResponse",
    
    # Campaign
    "CampaignBrief",
    "CampaignCreate",
    "CampaignResponse",
    "DeliverableSubmit",
    "DeliverableResponse",
    
    # Review
    "ReviewCreate",
    "ReviewResponse",
    
    # Dispute
    "DisputeCreate",
    "DisputeResponse",
    "DisputeResolve",
    
    # Notification
    "NotificationResponse",
]
