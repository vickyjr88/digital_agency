# Affiliate Commerce Database Models for Dexter Platform
# Contact-based e-commerce where customers contact brands directly

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Enum, Boolean, Float, Numeric, CheckConstraint
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

class CommissionTypeDB(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class ProductStatusDB(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AffiliateApprovalStatusDB(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderStatusDB(str, enum.Enum):
    PENDING = "pending"           # Order placed, waiting for customer contact
    CONTACTED = "contacted"       # Customer contacted brand
    IN_PROGRESS = "in_progress"   # Brand processing order
    FULFILLED = "fulfilled"       # Order completed - triggers commission
    CANCELLED = "cancelled"       # Order cancelled


class CommissionStatusDB(str, enum.Enum):
    PENDING = "pending"           # Order not yet fulfilled
    PAID = "paid"                 # Commission paid to influencer
    CANCELLED = "cancelled"       # Order cancelled


class PreferredContactMethodDB(str, enum.Enum):
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    EMAIL = "email"


# ============================================================================
# BRAND PROFILE EXTENSION (Contact Information)
# ============================================================================

class BrandProfile(Base):
    """Extended brand profile with contact information for affiliate commerce."""
    __tablename__ = "brand_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True)  # Link to existing Brand entity

    # Contact Information (REQUIRED for selling products)
    whatsapp_number = Column(String(20), nullable=False)  # Format: +254XXXXXXXXX
    business_location = Column(Text, nullable=False)      # Physical address or description
    business_hours = Column(String(200))                  # e.g., "Mon-Sat, 9AM-6PM"
    preferred_contact_method = Column(
        Enum(PreferredContactMethodDB, values_callable=lambda x: [e.value for e in x], name="preferredcontactmethoddb"),
        default=PreferredContactMethodDB.WHATSAPP
    )

    # Additional contact options
    phone_number = Column(String(20))
    business_email = Column(String(255))
    website_url = Column(String(500))

    # Social media for customer verification
    instagram_handle = Column(String(100))
    facebook_page = Column(String(200))

    # Business details
    business_description = Column(Text)
    business_category = Column(String(100))  # Fashion, Electronics, etc.

    # Settings
    is_active = Column(Boolean, default=True)
    auto_approve_influencers = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="brand_profile")
    brand = relationship("Brand", backref="brand_profile", uselist=False)
    products = relationship("Product", back_populates="brand_profile", cascade="all, delete-orphan")


# ============================================================================
# PRODUCT CATALOG
# ============================================================================

class Product(Base):
    """Products offered by brands for affiliate promotion."""
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    brand_profile_id = Column(String(36), ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False)

    # Basic Information
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)  # Fashion, Electronics, etc.

    # Pricing (for display - actual payment happens offline)
    price = Column(Numeric(10, 2), nullable=False)
    compare_at_price = Column(Numeric(10, 2))  # Original price (for "was $220")
    currency = Column(String(3), default="KES")

    # Commission Configuration
    commission_type = Column(
        Enum(CommissionTypeDB, values_callable=lambda x: [e.value for e in x], name="commissiontypedb"),
        nullable=False,
        default=CommissionTypeDB.PERCENTAGE
    )
    commission_rate = Column(Numeric(5, 2))  # Percentage (e.g., 15.00 for 15%)
    fixed_commission = Column(Numeric(10, 2))  # Fixed amount (e.g., 500.00 KES)

    # Platform Fee Configuration
    platform_fee_type = Column(
        Enum(CommissionTypeDB, values_callable=lambda x: [e.value for e in x], name="platformfeetypedb"),
        nullable=False,
        default=CommissionTypeDB.PERCENTAGE
    )
    platform_fee_rate = Column(Numeric(5, 2), default=10.00)  # Default 10%
    platform_fee_fixed = Column(Numeric(10, 2))  # Or fixed amount

    # Inventory (optional - for display purposes)
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer)
    track_inventory = Column(Boolean, default=False)

    # Media
    images = Column(JSON)  # Array of image URLs
    thumbnail = Column(String(500))
    video_url = Column(String(500))

    # Product Variants (sizes, colors, etc.)
    has_variants = Column(Boolean, default=False)

    # Shipping Information (for customer knowledge)
    requires_shipping = Column(Boolean, default=True)
    weight = Column(Numeric(8, 2))  # kg
    dimensions = Column(JSON)  # {length, width, height} in cm

    # Influencer Approval Settings
    auto_approve = Column(Boolean, default=False)
    approval_criteria = Column(JSON)  # {min_followers: 5000, min_engagement_rate: 2.0, etc.}

    # SEO & Discovery
    tags = Column(JSON)  # Array of tags

    # Status
    status = Column(
        Enum(ProductStatusDB, values_callable=lambda x: [e.value for e in x], name="productstatusdb"),
        default=ProductStatusDB.ACTIVE
    )
    published_at = Column(DateTime)

    # Statistics
    total_clicks = Column(Integer, default=0)
    total_orders = Column(Integer, default=0)
    total_sales_amount = Column(Numeric(12, 2), default=0.00)
    active_affiliates_count = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    brand_profile = relationship("BrandProfile", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    affiliate_approvals = relationship("AffiliateApproval", back_populates="product", cascade="all, delete-orphan")
    affiliate_links = relationship("AffiliateLink", back_populates="product", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    """Product variants (sizes, colors, etc.)."""
    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)  # "Size 9 / Red"
    sku = Column(String(100), unique=True)
    price = Column(Numeric(10, 2))  # Override product price if different
    stock_quantity = Column(Integer)
    attributes = Column(JSON)  # {size: "9", color: "Red"}
    image_url = Column(String(500))

    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="variants")


# ============================================================================
# AFFILIATE APPROVAL SYSTEM
# ============================================================================

class AffiliateApproval(Base):
    """Influencer applications to promote products."""
    __tablename__ = "affiliate_approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    status = Column(
        Enum(AffiliateApprovalStatusDB, values_callable=lambda x: [e.value for e in x], name="affiliateapprovalstatusdb"),
        default=AffiliateApprovalStatusDB.PENDING
    )

    # Application data
    application_message = Column(Text)  # Why they want to promote
    application_data = Column(JSON)  # Additional questionnaire responses

    # Review
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text)

    # Timestamps
    applied_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Unique constraint - one application per influencer per product
    __table_args__ = (
        CheckConstraint('1=1', name='unique_influencer_product'),
    )

    # Relationships
    influencer = relationship("InfluencerProfile", backref="affiliate_applications")
    product = relationship("Product", back_populates="affiliate_approvals")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ============================================================================
# AFFILIATE LINKS
# ============================================================================

class AffiliateLink(Base):
    """Generated affiliate links for tracking."""
    __tablename__ = "affiliate_links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Unique affiliate code for influencer
    affiliate_code = Column(String(50), unique=True, nullable=False, index=True)

    # Generated URLs
    link_url = Column(Text, nullable=False)
    short_url = Column(String(255))
    qr_code_url = Column(String(500))

    # Statistics
    clicks = Column(Integer, default=0)
    orders = Column(Integer, default=0)
    total_sales_amount = Column(Numeric(12, 2), default=0.00)
    total_commission_earned = Column(Numeric(12, 2), default=0.00)

    # Tracking
    generated_at = Column(DateTime, server_default=func.now())
    last_clicked_at = Column(DateTime)

    # Relationships
    influencer = relationship("InfluencerProfile", backref="affiliate_links")
    product = relationship("Product", back_populates="affiliate_links")
    clicks_tracked = relationship("AffiliateClick", back_populates="affiliate_link", cascade="all, delete-orphan")


# ============================================================================
# CLICK TRACKING
# ============================================================================

class AffiliateClick(Base):
    """Track clicks on affiliate links."""
    __tablename__ = "affiliate_clicks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    affiliate_link_id = Column(String(36), ForeignKey("affiliate_links.id", ondelete="CASCADE"), nullable=False)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Tracking data
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    referrer = Column(Text)
    country = Column(String(2))  # ISO country code
    device_type = Column(String(20))  # mobile, tablet, desktop

    # Conversion tracking
    converted = Column(Boolean, default=False)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    clicked_at = Column(DateTime, server_default=func.now())

    # Relationships
    affiliate_link = relationship("AffiliateLink", back_populates="clicks_tracked")
    influencer = relationship("InfluencerProfile")
    product = relationship("Product")
    order = relationship("Order", backref="click_tracking")


# ============================================================================
# ORDERS (No Payment Processing)
# ============================================================================

class Order(Base):
    """Orders placed by customers - NO payment processing, just contact info exchange."""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_number = Column(String(50), unique=True, nullable=False, index=True)

    # Product & Variant
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    # Brand
    brand_profile_id = Column(String(36), ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False)

    # Attribution (which influencer gets credit)
    attributed_influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="SET NULL"), nullable=True)
    affiliate_code = Column(String(50))
    affiliate_link_id = Column(String(36), ForeignKey("affiliate_links.id", ondelete="SET NULL"), nullable=True)

    # Customer Information
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_notes = Column(Text)  # Special requests

    # Pricing (for record keeping)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)  # quantity * unit_price
    currency = Column(String(3), default="KES")

    # Commission Calculation
    commission_type = Column(String(20))  # "percentage" or "fixed"
    commission_rate = Column(Numeric(5, 2))  # If percentage
    commission_amount = Column(Numeric(10, 2))  # Calculated commission

    # Platform Fee Calculation
    platform_fee_type = Column(String(20))
    platform_fee_rate = Column(Numeric(5, 2))
    platform_fee_amount = Column(Numeric(10, 2))

    # Net amounts
    net_commission = Column(Numeric(10, 2))  # commission_amount - platform_fee_amount
    brand_receives = Column(Numeric(10, 2))  # For tracking purposes

    # Order Status
    status = Column(
        Enum(OrderStatusDB, values_callable=lambda x: [e.value for e in x], name="orderstatusdb"),
        default=OrderStatusDB.PENDING
    )

    # Brand notes
    brand_notes = Column(Text)  # Brand's private notes about the order
    cancellation_reason = Column(Text)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    contacted_at = Column(DateTime)  # When customer contacted brand
    fulfilled_at = Column(DateTime)  # When brand marked as fulfilled (triggers commission)
    cancelled_at = Column(DateTime)

    # Relationships
    product = relationship("Product", back_populates="orders")
    variant = relationship("ProductVariant")
    brand_profile = relationship("BrandProfile", backref="orders")
    attributed_influencer = relationship("InfluencerProfile", backref="attributed_orders")
    affiliate_link = relationship("AffiliateLink", backref="orders")
    commission = relationship("AffiliateCommission", back_populates="order", uselist=False, cascade="all, delete-orphan")


# ============================================================================
# AFFILIATE COMMISSIONS
# ============================================================================

class AffiliateCommission(Base):
    """Commission records for influencers."""
    __tablename__ = "affiliate_commissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Amounts
    gross_commission = Column(Numeric(10, 2), nullable=False)  # Before platform fee
    platform_fee = Column(Numeric(10, 2), nullable=False)
    net_commission = Column(Numeric(10, 2), nullable=False)  # What influencer receives

    # Status
    status = Column(
        Enum(CommissionStatusDB, values_callable=lambda x: [e.value for e in x], name="commissionstatusdb"),
        default=CommissionStatusDB.PENDING
    )

    # Payment tracking
    wallet_transaction_id = Column(String(36), ForeignKey("wallet_transactions.id"), nullable=True)
    paid_at = Column(DateTime)

    # Metadata
    commission_type = Column(String(20))  # "percentage" or "fixed"
    commission_rate = Column(Numeric(5, 2))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="commission")
    influencer = relationship("InfluencerProfile", backref="commissions")
    product = relationship("Product")
    wallet_transaction = relationship("WalletTransaction", foreign_keys=[wallet_transaction_id])


# ============================================================================
# AFFILIATE ANALYTICS
# ============================================================================

class AffiliateAnalytics(Base):
    """Daily aggregated analytics for influencers and products."""
    __tablename__ = "affiliate_analytics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    date = Column(DateTime, nullable=False, index=True)

    # Dimension
    influencer_id = Column(String(36), ForeignKey("influencer_profiles.id", ondelete="CASCADE"), nullable=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    brand_profile_id = Column(String(36), ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=True)

    # Metrics
    clicks = Column(Integer, default=0)
    orders = Column(Integer, default=0)
    orders_fulfilled = Column(Integer, default=0)
    orders_cancelled = Column(Integer, default=0)

    # Financial
    total_sales = Column(Numeric(12, 2), default=0.00)
    total_commissions = Column(Numeric(12, 2), default=0.00)
    total_platform_fees = Column(Numeric(12, 2), default=0.00)

    # Rates
    conversion_rate = Column(Numeric(5, 2))  # orders / clicks * 100
    average_order_value = Column(Numeric(10, 2))

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    influencer = relationship("InfluencerProfile")
    product = relationship("Product")
    brand_profile = relationship("BrandProfile")
