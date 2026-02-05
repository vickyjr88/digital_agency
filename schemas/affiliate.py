# Pydantic Schemas for Affiliate Commerce API

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class CommissionType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AffiliateApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class CommissionStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class PreferredContactMethod(str, Enum):
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    EMAIL = "email"


# ============================================================================
# BRAND PROFILE SCHEMAS
# ============================================================================

class BrandProfileCreate(BaseModel):
    whatsapp_number: str = Field(..., description="WhatsApp number in format +254XXXXXXXXX")
    business_location: str = Field(..., description="Physical business location or address")
    business_hours: Optional[str] = Field(None, description="e.g., 'Mon-Sat, 9AM-6PM'")
    preferred_contact_method: PreferredContactMethod = PreferredContactMethod.WHATSAPP
    phone_number: Optional[str] = None
    business_email: Optional[EmailStr] = None
    website_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    facebook_page: Optional[str] = None
    business_description: Optional[str] = None
    business_category: Optional[str] = None
    auto_approve_influencers: bool = False

    @validator('whatsapp_number')
    def validate_whatsapp(cls, v):
        if not v.startswith('+'):
            raise ValueError('WhatsApp number must start with country code (e.g., +254)')
        return v


class BrandProfileUpdate(BaseModel):
    whatsapp_number: Optional[str] = None
    business_location: Optional[str] = None
    business_hours: Optional[str] = None
    preferred_contact_method: Optional[PreferredContactMethod] = None
    phone_number: Optional[str] = None
    business_email: Optional[EmailStr] = None
    website_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    facebook_page: Optional[str] = None
    business_description: Optional[str] = None
    business_category: Optional[str] = None
    is_active: Optional[bool] = None
    auto_approve_influencers: Optional[bool] = None


class BrandProfileResponse(BaseModel):
    id: str
    user_id: str
    brand_id: Optional[str]
    whatsapp_number: str
    business_location: str
    business_hours: Optional[str]
    preferred_contact_method: PreferredContactMethod
    phone_number: Optional[str]
    business_email: Optional[str]
    website_url: Optional[str]
    instagram_handle: Optional[str]
    facebook_page: Optional[str]
    business_description: Optional[str]
    business_category: Optional[str]
    is_active: bool
    auto_approve_influencers: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandContactInfo(BaseModel):
    """Public contact info shown to customers"""
    whatsapp_number: str
    business_location: str
    business_hours: Optional[str]
    preferred_contact_method: PreferredContactMethod
    phone_number: Optional[str]
    business_email: Optional[str]
    website_url: Optional[str]
    instagram_handle: Optional[str]
    facebook_page: Optional[str]


# ============================================================================
# PRODUCT SCHEMAS
# ============================================================================

class ProductVariantCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None


class ProductVariantResponse(BaseModel):
    id: str
    product_id: str
    name: str
    sku: Optional[str]
    price: Optional[Decimal]
    stock_quantity: Optional[int]
    attributes: Optional[Dict[str, Any]]
    image_url: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    category: str
    price: Decimal = Field(..., gt=0, description="Product price")
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    currency: str = "KES"

    # Commission settings
    commission_type: CommissionType = CommissionType.PERCENTAGE
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="Percentage if commission_type is percentage")
    fixed_commission: Optional[Decimal] = Field(None, ge=0, description="Fixed amount if commission_type is fixed")

    # Platform fee settings
    platform_fee_type: CommissionType = CommissionType.PERCENTAGE
    platform_fee_rate: Decimal = Field(Decimal("10.00"), ge=0, le=100, description="Platform fee percentage")
    platform_fee_fixed: Optional[Decimal] = Field(None, ge=0)

    # Inventory
    in_stock: bool = True
    stock_quantity: Optional[int] = Field(None, ge=0)
    track_inventory: bool = False

    # Media
    images: Optional[List[str]] = None
    thumbnail: Optional[str] = None
    video_url: Optional[str] = None

    # Variants
    has_variants: bool = False
    variants: Optional[List[ProductVariantCreate]] = None

    # Shipping
    requires_shipping: bool = True
    weight: Optional[Decimal] = Field(None, gt=0)
    dimensions: Optional[Dict[str, float]] = None

    # Approval settings
    auto_approve: bool = False
    approval_criteria: Optional[Dict[str, Any]] = None

    # SEO
    tags: Optional[List[str]] = None

    @validator('commission_rate')
    def validate_commission_rate(cls, v, values):
        if values.get('commission_type') == CommissionType.PERCENTAGE and not v:
            raise ValueError('commission_rate is required when commission_type is percentage')
        return v

    @validator('fixed_commission')
    def validate_fixed_commission(cls, v, values):
        if values.get('commission_type') == CommissionType.FIXED and not v:
            raise ValueError('fixed_commission is required when commission_type is fixed')
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    compare_at_price: Optional[Decimal] = None
    commission_type: Optional[CommissionType] = None
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    fixed_commission: Optional[Decimal] = Field(None, ge=0)
    platform_fee_type: Optional[CommissionType] = None
    platform_fee_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    platform_fee_fixed: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    stock_quantity: Optional[int] = None
    track_inventory: Optional[bool] = None
    images: Optional[List[str]] = None
    thumbnail: Optional[str] = None
    video_url: Optional[str] = None
    has_variants: Optional[bool] = None
    requires_shipping: Optional[bool] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, float]] = None
    auto_approve: Optional[bool] = None
    approval_criteria: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[ProductStatus] = None


class ProductResponse(BaseModel):
    id: str
    brand_profile_id: str
    name: str
    slug: str
    description: str
    category: str
    price: Decimal
    compare_at_price: Optional[Decimal]
    currency: str
    commission_type: str
    commission_rate: Optional[Decimal]
    fixed_commission: Optional[Decimal]
    platform_fee_type: str
    platform_fee_rate: Decimal
    platform_fee_fixed: Optional[Decimal]
    in_stock: bool
    stock_quantity: Optional[int]
    track_inventory: bool
    images: Optional[List[str]]
    thumbnail: Optional[str]
    video_url: Optional[str]
    has_variants: bool
    requires_shipping: bool
    weight: Optional[Decimal]
    dimensions: Optional[Dict[str, Any]]
    auto_approve: bool
    approval_criteria: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    status: str
    published_at: Optional[datetime]
    total_clicks: int
    total_orders: int
    total_sales_amount: Decimal
    active_affiliates_count: int
    created_at: datetime
    updated_at: datetime
    variants: List[ProductVariantResponse] = []

    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    """Simplified product for list views"""
    id: str
    name: str
    slug: str
    category: str
    price: Decimal
    compare_at_price: Optional[Decimal]
    currency: str
    commission_type: str
    commission_rate: Optional[Decimal]
    fixed_commission: Optional[Decimal]
    thumbnail: Optional[str]
    in_stock: bool
    status: str
    total_clicks: int
    total_orders: int
    active_affiliates_count: int

    class Config:
        from_attributes = True


# ============================================================================
# AFFILIATE APPROVAL SCHEMAS
# ============================================================================

class AffiliateApprovalCreate(BaseModel):
    product_id: str
    application_message: Optional[str] = None
    application_data: Optional[Dict[str, Any]] = None


class AffiliateApprovalResponse(BaseModel):
    id: str
    influencer_id: str
    product_id: str
    status: AffiliateApprovalStatus
    application_message: Optional[str]
    application_data: Optional[Dict[str, Any]]
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    rejection_reason: Optional[str]
    applied_at: datetime
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AffiliateApprovalReview(BaseModel):
    status: AffiliateApprovalStatus
    rejection_reason: Optional[str] = None


# ============================================================================
# AFFILIATE LINK SCHEMAS
# ============================================================================

class AffiliateLinkResponse(BaseModel):
    id: str
    influencer_id: str
    product_id: str
    affiliate_code: str
    link_url: str
    short_url: Optional[str]
    qr_code_url: Optional[str]
    clicks: int
    orders: int
    total_sales_amount: Decimal
    total_commission_earned: Decimal
    generated_at: datetime
    last_clicked_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# ORDER SCHEMAS
# ============================================================================

class OrderCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = Field(1, gt=0)
    customer_name: str = Field(..., min_length=2)
    customer_email: EmailStr
    customer_phone: str = Field(..., description="Phone number with country code")
    customer_notes: Optional[str] = None
    affiliate_code: Optional[str] = Field(None, description="Affiliate tracking code from URL")

    @validator('customer_phone')
    def validate_phone(cls, v):
        if not v.startswith('+'):
            raise ValueError('Phone number must include country code (e.g., +254)')
        return v


class OrderResponse(BaseModel):
    id: str
    order_number: str
    product_id: str
    variant_id: Optional[str]
    quantity: int
    brand_profile_id: str
    attributed_influencer_id: Optional[str]
    affiliate_code: Optional[str]
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_notes: Optional[str]
    unit_price: Decimal
    total_amount: Decimal
    currency: str
    commission_type: Optional[str]
    commission_rate: Optional[Decimal]
    commission_amount: Optional[Decimal]
    platform_fee_type: Optional[str]
    platform_fee_rate: Optional[Decimal]
    platform_fee_amount: Optional[Decimal]
    net_commission: Optional[Decimal]
    brand_receives: Optional[Decimal]
    status: OrderStatus
    brand_notes: Optional[str]
    cancellation_reason: Optional[str]
    created_at: datetime
    contacted_at: Optional[datetime]
    fulfilled_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    # Additional data
    brand_contact: Optional[BrandContactInfo] = None
    product: Optional[ProductListItem] = None

    class Config:
        from_attributes = True


class OrderUpdateStatus(BaseModel):
    status: OrderStatus
    brand_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


# ============================================================================
# COMMISSION SCHEMAS
# ============================================================================

class CommissionResponse(BaseModel):
    id: str
    order_id: str
    influencer_id: str
    product_id: str
    gross_commission: Decimal
    platform_fee: Decimal
    net_commission: Decimal
    status: CommissionStatus
    wallet_transaction_id: Optional[str]
    paid_at: Optional[datetime]
    commission_type: Optional[str]
    commission_rate: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class InfluencerDashboardStats(BaseModel):
    total_clicks: int
    total_orders: int
    total_orders_fulfilled: int
    total_sales: Decimal
    total_commissions_earned: Decimal
    pending_commissions: Decimal
    available_to_withdraw: Decimal
    conversion_rate: Optional[Decimal]
    average_order_value: Optional[Decimal]


class BrandDashboardStats(BaseModel):
    total_products: int
    active_products: int
    total_affiliates: int
    active_affiliates: int
    total_clicks: int
    total_orders: int
    total_orders_fulfilled: int
    total_sales: Decimal
    total_commissions_paid: Decimal
    total_platform_fees: Decimal
    conversion_rate: Optional[Decimal]


class TopPerformingProduct(BaseModel):
    product_id: str
    product_name: str
    sales_count: int
    total_sales: Decimal
    commission_earned: Decimal


class TopPerformingAffiliate(BaseModel):
    influencer_id: str
    display_name: str
    sales_count: int
    total_sales: Decimal
    commission_earned: Decimal


# ============================================================================
# RESPONSE WRAPPERS
# ============================================================================

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None
