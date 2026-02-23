# Tumanasi Delivery Service — Database Models

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey,
    Text, Boolean, Numeric, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database.models import Base, generate_uuid


# ============================================================================
# ENUMS
# ============================================================================

class ErrandTypeDB(str, enum.Enum):
    PARCEL     = "parcel"
    DOCUMENT   = "document"
    FOOD       = "food"
    SHOPPING   = "shopping"
    ERRAND     = "errand"


class VehicleTypeDB(str, enum.Enum):
    BICYCLE    = "bicycle"
    MOTORCYCLE = "motorcycle"
    TUK_TUK   = "tuk_tuk"
    CAR        = "car"


class PaymentMethodDB(str, enum.Enum):
    CASH            = "cash_on_delivery"
    MOBILE_MONEY    = "mobile_money"
    CARD            = "card"


class PaymentStatusDB(str, enum.Enum):
    PENDING  = "pending"
    PAID     = "paid"
    FAILED   = "failed"


class AssignmentMethodDB(str, enum.Enum):
    AUTO   = "auto"
    MANUAL = "manual"


class DeliveryStatusDB(str, enum.Enum):
    PENDING_ASSIGNMENT  = "pending_assignment"
    ASSIGNED            = "assigned"
    EN_ROUTE_PICKUP     = "en_route_pickup"
    COLLECTED           = "collected"
    EN_ROUTE_DELIVERY   = "en_route_delivery"
    DELIVERED           = "delivered"
    PAYMENT_REQUESTED   = "payment_requested"
    COMPLETED           = "completed"
    CANCELLED           = "cancelled"
    FAILED              = "failed"


# ============================================================================
# PRICING ZONES
# ============================================================================

class TumansiZone(Base):
    """Price zones parsed from Tumanasi's physical price list."""
    __tablename__ = "tumanasi_zones"

    id         = Column(String(36), primary_key=True, default=generate_uuid)
    zone_name  = Column(String(100), nullable=False, index=True)  # e.g. "Ngong Road"
    area_name  = Column(String(200), nullable=False, index=True)  # e.g. "Karen"
    price_kes  = Column(Numeric(10, 2), nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    pickup_deliveries  = relationship("TumansiDelivery", foreign_keys="TumansiDelivery.pickup_area_id",  back_populates="pickup_zone")
    dropoff_deliveries = relationship("TumansiDelivery", foreign_keys="TumansiDelivery.dropoff_area_id", back_populates="dropoff_zone")

    def __repr__(self):
        return f"<Zone {self.zone_name} / {self.area_name} = KES {self.price_kes}>"


# ============================================================================
# RIDERS
# ============================================================================

class TumansiRider(Base):
    """Delivery rider profiles."""
    __tablename__ = "tumanasi_riders"

    id              = Column(String(36), primary_key=True, default=generate_uuid)
    user_id         = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    full_name       = Column(String(200), nullable=False)
    phone           = Column(String(20), nullable=False, unique=True)
    email           = Column(String(255))
    id_number       = Column(String(50))           # National ID
    vehicle_type    = Column(
        Enum(VehicleTypeDB, values_callable=lambda x: [e.value for e in x], name="vehicletypedb"),
        default=VehicleTypeDB.MOTORCYCLE
    )
    vehicle_reg     = Column(String(20))
    photo_url       = Column(String(500))

    # Status flags
    is_active       = Column(Boolean, default=True)
    is_available    = Column(Boolean, default=False)  # Online toggle
    is_verified     = Column(Boolean, default=False)  # Admin approved
    verification_notes = Column(Text)

    # Current assignment (null = free)
    current_delivery_id = Column(String(36), ForeignKey("tumanasi_deliveries.id", ondelete="SET NULL"), nullable=True)
    current_zone_id     = Column(String(36), ForeignKey("tumanasi_zones.id", ondelete="SET NULL"), nullable=True)

    # Lifetime stats
    total_deliveries     = Column(Integer, default=0)
    completed_deliveries = Column(Integer, default=0)
    cancelled_deliveries = Column(Integer, default=0)
    average_rating       = Column(Numeric(3, 2), default=0.00)
    total_earnings_kes   = Column(Numeric(12, 2), default=0.00)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user         = relationship("User", backref="rider_profile")
    current_zone = relationship("TumansiZone", foreign_keys=[current_zone_id])
    ratings      = relationship("TumansiRiderRating", back_populates="rider")


# ============================================================================
# DELIVERIES
# ============================================================================

class TumansiDelivery(Base):
    """Full delivery record — booking through completion."""
    __tablename__ = "tumanasi_deliveries"

    id              = Column(String(36), primary_key=True, default=generate_uuid)
    tracking_number = Column(String(30), unique=True, nullable=False, index=True)

    # ── Customer details ─────────────────────────────────────
    customer_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_name    = Column(String(200), nullable=False)
    customer_phone   = Column(String(20), nullable=False)
    customer_email   = Column(String(255))

    # ── Errand details ────────────────────────────────────────
    errand_type = Column(
        Enum(ErrandTypeDB, values_callable=lambda x: [e.value for e in x], name="errandtypedb"),
        nullable=False,
        default=ErrandTypeDB.PARCEL
    )
    errand_description   = Column(Text, nullable=False)
    special_instructions = Column(Text)
    is_fragile           = Column(Boolean, default=False)
    requires_handling    = Column(Boolean, default=False)

    # ── Pickup location ───────────────────────────────────────
    pickup_address       = Column(Text, nullable=False)
    pickup_area_id       = Column(String(36), ForeignKey("tumanasi_zones.id"), nullable=True)
    pickup_contact_name  = Column(String(200))
    pickup_contact_phone = Column(String(20))

    # ── Dropoff location ─────────────────────────────────────
    dropoff_address       = Column(Text, nullable=False)
    dropoff_area_id       = Column(String(36), ForeignKey("tumanasi_zones.id"), nullable=False)
    dropoff_contact_name  = Column(String(200))
    dropoff_contact_phone = Column(String(20))

    # ── Pricing & payment ─────────────────────────────────────
    quoted_price_kes = Column(Numeric(10, 2), nullable=False)
    final_price_kes  = Column(Numeric(10, 2))
    payment_method   = Column(
        Enum(PaymentMethodDB, values_callable=lambda x: [e.value for e in x], name="paymentmethoddb"),
        default=PaymentMethodDB.CASH
    )
    payment_status    = Column(
        Enum(PaymentStatusDB, values_callable=lambda x: [e.value for e in x], name="paymentstatusdb"),
        default=PaymentStatusDB.PENDING
    )
    payment_reference = Column(String(100))

    # ── Rider assignment ──────────────────────────────────────
    rider_id          = Column(String(36), ForeignKey("tumanasi_riders.id", ondelete="SET NULL"), nullable=True)
    assigned_at       = Column(DateTime)
    assignment_method = Column(
        Enum(AssignmentMethodDB, values_callable=lambda x: [e.value for e in x], name="assignmentmethoddb"),
        nullable=True
    )

    # ── Photo proof ───────────────────────────────────────────
    pickup_photo_url   = Column(String(500))
    pickup_photo_at    = Column(DateTime)
    pickup_notes       = Column(Text)
    delivery_photo_url = Column(String(500))
    delivery_photo_at  = Column(DateTime)
    delivery_notes     = Column(Text)

    # ── Status ────────────────────────────────────────────────
    status = Column(
        Enum(DeliveryStatusDB, values_callable=lambda x: [e.value for e in x], name="deliverystatusdb"),
        default=DeliveryStatusDB.PENDING_ASSIGNMENT,
        nullable=False
    )
    cancellation_reason = Column(Text)

    # ── Timestamps ────────────────────────────────────────────
    created_at             = Column(DateTime, server_default=func.now())
    updated_at             = Column(DateTime, server_default=func.now(), onupdate=func.now())
    estimated_delivery_at  = Column(DateTime)
    completed_at           = Column(DateTime)

    # Relationships
    customer    = relationship("User", foreign_keys=[customer_user_id], backref="deliveries")
    rider       = relationship("TumansiRider", foreign_keys=[rider_id], backref="deliveries")
    pickup_zone  = relationship("TumansiZone", foreign_keys=[pickup_area_id],  back_populates="pickup_deliveries")
    dropoff_zone = relationship("TumansiZone", foreign_keys=[dropoff_area_id], back_populates="dropoff_deliveries")
    rating       = relationship("TumansiRiderRating", back_populates="delivery", uselist=False)


# ============================================================================
# RIDER RATINGS
# ============================================================================

class TumansiRiderRating(Base):
    """Post-delivery customer rating for the rider."""
    __tablename__ = "tumanasi_rider_ratings"

    id          = Column(String(36), primary_key=True, default=generate_uuid)
    delivery_id = Column(String(36), ForeignKey("tumanasi_deliveries.id", ondelete="CASCADE"), unique=True, nullable=False)
    rider_id    = Column(String(36), ForeignKey("tumanasi_riders.id", ondelete="CASCADE"), nullable=False)
    rating      = Column(Integer, nullable=False)   # 1–5
    comment     = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())

    # Relationships
    delivery = relationship("TumansiDelivery", back_populates="rating")
    rider    = relationship("TumansiRider", back_populates="ratings")
