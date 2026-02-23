# Tumanasi Delivery Service — Pydantic Schemas

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ErrandType(str, Enum):
    PARCEL   = "parcel"
    DOCUMENT = "document"
    FOOD     = "food"
    SHOPPING = "shopping"
    ERRAND   = "errand"


class VehicleType(str, Enum):
    BICYCLE    = "bicycle"
    MOTORCYCLE = "motorcycle"
    TUK_TUK   = "tuk_tuk"
    CAR        = "car"
    COMMUTE_WALK = "commute_walk"
    COURIER    = "courier"


class PaymentMethod(str, Enum):
    CASH         = "cash_on_delivery"
    MOBILE_MONEY = "mobile_money"
    CARD         = "card"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID    = "paid"
    FAILED  = "failed"


class DeliveryStatus(str, Enum):
    PENDING_ASSIGNMENT = "pending_assignment"
    ASSIGNED           = "assigned"
    EN_ROUTE_PICKUP    = "en_route_pickup"
    COLLECTED          = "collected"
    EN_ROUTE_DELIVERY  = "en_route_delivery"
    DELIVERED          = "delivered"
    PAYMENT_REQUESTED  = "payment_requested"
    COMPLETED          = "completed"
    CANCELLED          = "cancelled"
    FAILED             = "failed"


# ============================================================================
# ZONE SCHEMAS
# ============================================================================

class ZoneResponse(BaseModel):
    id: str
    zone_name: str
    area_name: str
    price_kes: Decimal
    is_active: bool

    class Config:
        from_attributes = True


class ZoneSearchResult(BaseModel):
    id: str
    zone_name: str
    area_name: str
    price_kes: Decimal

    class Config:
        from_attributes = True


# ============================================================================
# RIDER SCHEMAS
# ============================================================================

class RiderRegister(BaseModel):
    full_name:    str = Field(..., min_length=2)
    phone:        str = Field(..., description="Phone e.g. +254712345678")
    email:        Optional[str] = None
    id_number:    Optional[str] = None
    vehicle_type: VehicleType = VehicleType.MOTORCYCLE
    vehicle_reg:  Optional[str] = None

    @validator("phone")
    def validate_phone(cls, v):
        if not v.startswith("+"):
            raise ValueError("Phone must include country code e.g. +254712345678")
        return v


class RiderUpdate(BaseModel):
    full_name:    Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    vehicle_reg:  Optional[str] = None
    photo_url:    Optional[str] = None
    current_zone_id: Optional[str] = None


class RiderAvailability(BaseModel):
    is_available: bool


class RiderResponse(BaseModel):
    id:                  str
    full_name:           str
    phone:               str
    email:               Optional[str]
    vehicle_type:        str
    vehicle_reg:         Optional[str]
    photo_url:           Optional[str]
    is_active:           bool
    is_available:        bool
    is_verified:         bool
    total_deliveries:    int
    completed_deliveries: int
    average_rating:      Optional[Decimal]
    total_earnings_kes:  Optional[Decimal]
    current_zone_id:     Optional[str]
    created_at:          datetime

    class Config:
        from_attributes = True


class RiderPublicInfo(BaseModel):
    """Minimal info exposed to customer during tracking."""
    id:           str
    full_name:    str
    phone:        str
    vehicle_type: str
    photo_url:    Optional[str]
    average_rating: Optional[Decimal]

    class Config:
        from_attributes = True


# ============================================================================
# DELIVERY SCHEMAS
# ============================================================================

class DeliveryCreate(BaseModel):
    # Customer details (prefilled from auth or filled manually)
    customer_name:  str = Field(..., min_length=2)
    customer_phone: str
    customer_email: Optional[str] = None

    # Errand
    errand_type:          ErrandType = ErrandType.PARCEL
    errand_description:   str = Field(..., min_length=5)
    special_instructions: Optional[str] = None
    is_fragile:           bool = False
    requires_handling:    bool = False

    # Pickup
    pickup_address:       str = Field(..., min_length=5)
    pickup_area_id:       Optional[str] = None   # Zone ID (optional for CBD)
    pickup_contact_name:  Optional[str] = None
    pickup_contact_phone: Optional[str] = None

    # Dropoff
    dropoff_address:       str = Field(..., min_length=5)
    dropoff_area_id:       str                   # Zone ID (required — determines price)
    dropoff_contact_name:  Optional[str] = None
    dropoff_contact_phone: Optional[str] = None

    # Payment
    payment_method: PaymentMethod = PaymentMethod.CASH

    @validator("customer_phone")
    def validate_phone(cls, v):
        if v and not v.startswith("+"):
            raise ValueError("Phone must include country code e.g. +254712345678")
        return v


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    note:   Optional[str] = None


class DeliveryCancel(BaseModel):
    reason: str


class RateRider(BaseModel):
    rating:  int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class InitiatePayment(BaseModel):
    payment_method: PaymentMethod
    phone:          Optional[str] = None   # for MPesa STK push


class ZoneInfo(BaseModel):
    id:        str
    zone_name: str
    area_name: str
    price_kes: Decimal

    class Config:
        from_attributes = True


class DeliveryResponse(BaseModel):
    id:              str
    tracking_number: str

    customer_name:  str
    customer_phone: str
    customer_email: Optional[str]

    errand_type:          str
    errand_description:   str
    special_instructions: Optional[str]
    is_fragile:           bool
    requires_handling:    bool

    pickup_address:       str
    pickup_contact_name:  Optional[str]
    pickup_contact_phone: Optional[str]
    pickup_zone:          Optional[ZoneInfo]

    dropoff_address:       str
    dropoff_contact_name:  Optional[str]
    dropoff_contact_phone: Optional[str]
    dropoff_zone:          Optional[ZoneInfo]

    quoted_price_kes: Decimal
    final_price_kes:  Optional[Decimal]
    payment_method:   str
    payment_status:   str

    rider:             Optional[RiderPublicInfo]
    assigned_at:       Optional[datetime]

    pickup_photo_url:   Optional[str]
    pickup_photo_at:    Optional[datetime]
    pickup_notes:       Optional[str]
    delivery_photo_url: Optional[str]
    delivery_photo_at:  Optional[datetime]
    delivery_notes:     Optional[str]

    status:             str
    cancellation_reason: Optional[str]

    created_at:            datetime
    updated_at:            datetime
    estimated_delivery_at: Optional[datetime]
    completed_at:          Optional[datetime]

    class Config:
        from_attributes = True


class DeliveryListItem(BaseModel):
    """Compact delivery for list views."""
    id:              str
    tracking_number: str
    customer_name:   str
    customer_phone:  str
    errand_type:     str
    pickup_address:  str
    dropoff_address: str
    quoted_price_kes: Decimal
    payment_method:  str
    payment_status:  str
    status:          str
    rider_name:      Optional[str] = None
    created_at:      datetime

    class Config:
        from_attributes = True


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class AdminRiderVerify(BaseModel):
    is_verified:        bool
    verification_notes: Optional[str] = None


class AdminAssignRider(BaseModel):
    rider_id: str


class AdminZoneCreate(BaseModel):
    zone_name: str
    area_name: str
    price_kes: Decimal = Field(..., gt=0)


class AdminZoneUpdate(BaseModel):
    zone_name: Optional[str] = None
    area_name: Optional[str] = None
    price_kes: Optional[Decimal] = None
    is_active: Optional[bool] = None


class AdminDeliveryUpdate(BaseModel):
    """Admin-only: freely edit any mutable field of a delivery."""
    # Customer
    customer_name:  Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

    # Errand
    errand_type:          Optional[str] = None
    errand_description:   Optional[str] = None
    special_instructions: Optional[str] = None
    is_fragile:           Optional[bool] = None
    requires_handling:    Optional[bool] = None

    # Pickup
    pickup_address:       Optional[str] = None
    pickup_contact_name:  Optional[str] = None
    pickup_contact_phone: Optional[str] = None

    # Dropoff
    dropoff_address:       Optional[str] = None
    dropoff_contact_name:  Optional[str] = None
    dropoff_contact_phone: Optional[str] = None

    # Pricing
    final_price_kes: Optional[Decimal] = Field(None, gt=0)

    # Status & payment
    status:           Optional[str] = None
    payment_status:   Optional[str] = None
    payment_method:   Optional[str] = None

    # Internal notes
    cancellation_reason: Optional[str] = None


class TumansiStats(BaseModel):
    total_deliveries:    int
    active_deliveries:   int
    completed_today:     int
    revenue_today_kes:   Decimal
    revenue_total_kes:   Decimal
    total_riders:        int
    active_riders:       int
    verified_riders:     int
    avg_completion_rate: Optional[Decimal]
