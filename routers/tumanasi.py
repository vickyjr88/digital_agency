# Tumanasi Delivery Service — API Router

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import re
import uuid
import boto3
import os

from database.config import get_db
from database.models import User, UserRole
from database.tumanasi_models import (
    TumansiZone, TumansiDelivery, TumansiRider, TumansiRiderRating,
    DeliveryStatusDB, PaymentStatusDB
)
from schemas.tumanasi import (
    ZoneResponse, ZoneSearchResult,
    RiderRegister, RiderUpdate, RiderAvailability, RiderResponse,
    DeliveryCreate, DeliveryStatusUpdate, DeliveryCancel,
    RateRider, InitiatePayment,
    DeliveryResponse, DeliveryListItem,
    AdminRiderVerify, AdminAssignRider, AdminZoneCreate, AdminZoneUpdate,
    AdminDeliveryUpdate,
    TumansiStats
)
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/tumanasi", tags=["Tumanasi Delivery"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def generate_tracking_number() -> str:
    """TUM-YYYYMMDD-XXXX"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    unique   = str(uuid.uuid4())[:4].upper()
    return f"TUM-{date_str}-{unique}"


def get_rider_from_user(db: Session, user: User) -> TumansiRider:
    rider = db.query(TumansiRider).filter(TumansiRider.user_id == user.id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider profile not found. Please register as a rider first.")
    return rider


def upload_photo_to_storage(file: UploadFile, folder: str) -> str:
    """Upload photo to MinIO / S3 and return public URL."""
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        )
        bucket   = os.getenv("MINIO_BUCKET", "dexter-uploads")
        ext      = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
        key      = f"tumanasi/{folder}/{uuid.uuid4()}.{ext}"
        s3.upload_fileobj(file.file, bucket, key, ExtraArgs={"ACL": "public-read"})
        return f"{os.getenv('MINIO_PUBLIC_URL', 'http://localhost:9000')}/{bucket}/{key}"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {exc}")


def auto_assign_rider(delivery: TumansiDelivery, db: Session) -> Optional[TumansiRider]:
    """
    Smart rider matching:
    Score = zone_match(50) + free(30) + completions(0-20, scaled) + rating(0-10)
    Returns best available rider or None.
    """
    candidates = db.query(TumansiRider).filter(
        TumansiRider.is_active   == True,
        TumansiRider.is_available == True,
        TumansiRider.is_verified  == True,
        TumansiRider.current_delivery_id == None,
    ).all()

    if not candidates:
        return None

    def score(r: TumansiRider) -> float:
        s = 0.0
        if r.current_zone_id == delivery.pickup_area_id:
            s += 50
        s += 30  # free (no active delivery)
        max_completed = max((c.completed_deliveries for c in candidates), default=1) or 1
        s += min(20, (r.completed_deliveries / max_completed) * 20)
        s += float(r.average_rating or 0) * 2   # 0–10
        return s

    best = max(candidates, key=score)
    return best


# ============================================================================
# 1. ZONES — Public
# ============================================================================

@router.get("/zones", response_model=List[ZoneResponse])
def list_zones(db: Session = Depends(get_db)):
    """Return all active pricing zones."""
    return db.query(TumansiZone).filter(TumansiZone.is_active == True).order_by(
        TumansiZone.zone_name, TumansiZone.area_name
    ).all()


@router.get("/zones/search", response_model=List[ZoneSearchResult])
def search_zones(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Fuzzy-search areas by name for the booking wizard dropdown."""
    pattern = f"%{q.lower()}%"
    results = db.query(TumansiZone).filter(
        TumansiZone.is_active == True,
        or_(
            func.lower(TumansiZone.area_name).like(pattern),
            func.lower(TumansiZone.zone_name).like(pattern),
        )
    ).order_by(TumansiZone.area_name).limit(30).all()
    return results


@router.get("/zones/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: str, db: Session = Depends(get_db)):
    zone = db.query(TumansiZone).filter(TumansiZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


# ============================================================================
# 2. BOOKINGS — Customer
# ============================================================================

@router.post("/deliveries", response_model=DeliveryResponse, status_code=201)
def book_delivery(
    body: DeliveryCreate,
    db:   Session = Depends(get_db),
    current_user: Optional[User] = Depends(lambda credentials=None, db=None: None),   # optional auth
):
    """
    Book a new delivery. Works for guests and authenticated users.
    Price is pulled from the dropoff zone.
    """
    # Resolve price from dropoff zone
    dropoff_zone = db.query(TumansiZone).filter(
        TumansiZone.id == body.dropoff_area_id,
        TumansiZone.is_active == True,
    ).first()
    if not dropoff_zone:
        raise HTTPException(status_code=400, detail="Invalid dropoff zone. Please select from the list.")

    tracking = generate_tracking_number()

    delivery = TumansiDelivery(
        id              = str(uuid.uuid4()),
        tracking_number = tracking,

        customer_user_id = getattr(current_user, "id", None),
        customer_name    = body.customer_name,
        customer_phone   = body.customer_phone,
        customer_email   = body.customer_email,

        errand_type          = body.errand_type,
        errand_description   = body.errand_description,
        special_instructions = body.special_instructions,
        is_fragile           = body.is_fragile,
        requires_handling    = body.requires_handling,

        pickup_address       = body.pickup_address,
        pickup_area_id       = body.pickup_area_id,
        pickup_contact_name  = body.pickup_contact_name or body.customer_name,
        pickup_contact_phone = body.pickup_contact_phone or body.customer_phone,

        dropoff_address       = body.dropoff_address,
        dropoff_area_id       = body.dropoff_area_id,
        dropoff_contact_name  = body.dropoff_contact_name or body.customer_name,
        dropoff_contact_phone = body.dropoff_contact_phone or body.customer_phone,

        quoted_price_kes = dropoff_zone.price_kes,
        final_price_kes  = dropoff_zone.price_kes,
        payment_method   = body.payment_method,
        payment_status   = PaymentStatusDB.PENDING,
        status           = DeliveryStatusDB.PENDING_ASSIGNMENT,

        estimated_delivery_at = datetime.utcnow() + timedelta(hours=2),
    )

    db.add(delivery)
    db.flush()   # get delivery.id before assigning rider

    # Try auto-assign
    rider = auto_assign_rider(delivery, db)
    if rider:
        delivery.rider_id          = rider.id
        delivery.assigned_at       = datetime.utcnow()
        delivery.assignment_method = "auto"
        delivery.status            = DeliveryStatusDB.ASSIGNED
        rider.current_delivery_id  = delivery.id
        rider.total_deliveries    += 1

    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/deliveries/track/{tracking_number}", response_model=DeliveryResponse)
def track_delivery(tracking_number: str, db: Session = Depends(get_db)):
    """Public: track a delivery by tracking number."""
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.tracking_number == tracking_number.upper()
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found. Check your tracking number.")
    return delivery


@router.get("/deliveries/my", response_model=List[DeliveryListItem])
def my_deliveries(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Authenticated: get caller's deliveries."""
    rows = db.query(TumansiDelivery).filter(
        TumansiDelivery.customer_user_id == current_user.id
    ).order_by(desc(TumansiDelivery.created_at)).all()

    result = []
    for d in rows:
        result.append(DeliveryListItem(
            id              = d.id,
            tracking_number = d.tracking_number,
            customer_name   = d.customer_name,
            customer_phone  = d.customer_phone,
            errand_type     = d.errand_type,
            pickup_address  = d.pickup_address,
            dropoff_address = d.dropoff_address,
            quoted_price_kes = d.quoted_price_kes,
            payment_method  = d.payment_method,
            payment_status  = d.payment_status,
            status          = d.status,
            rider_name      = d.rider.full_name if d.rider else None,
            created_at      = d.created_at,
        ))
    return result


@router.get("/deliveries/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(
    delivery_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    delivery = db.query(TumansiDelivery).filter(TumansiDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    # Only allow if owner or rider or admin
    is_owner = delivery.customer_user_id == current_user.id
    is_rider = delivery.rider and delivery.rider.user_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    if not (is_owner or is_rider or is_admin):
        raise HTTPException(status_code=403, detail="Not authorised")
    return delivery


@router.post("/deliveries/{delivery_id}/rate")
def rate_rider(
    delivery_id:  str,
    body:         RateRider,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id               == delivery_id,
        TumansiDelivery.customer_user_id == current_user.id,
        TumansiDelivery.status           == DeliveryStatusDB.COMPLETED,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Completed delivery not found or not yours")
    if not delivery.rider_id:
        raise HTTPException(status_code=400, detail="No rider to rate")
    if delivery.rating:
        raise HTTPException(status_code=400, detail="Already rated")

    rating = TumansiRiderRating(
        id          = str(uuid.uuid4()),
        delivery_id = delivery.id,
        rider_id    = delivery.rider_id,
        rating      = body.rating,
        comment     = body.comment,
    )
    db.add(rating)

    # Recalculate rider average
    rider = delivery.rider
    if rider:
        all_ratings = db.query(func.avg(TumansiRiderRating.rating)).filter(
            TumansiRiderRating.rider_id == rider.id
        ).scalar()
        rider.average_rating = round(float(all_ratings or 0), 2)

    db.commit()
    return {"success": True, "message": "Thank you for your rating!"}


@router.post("/deliveries/{delivery_id}/cancel")
def cancel_delivery(
    delivery_id:  str,
    body:         DeliveryCancel,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id               == delivery_id,
        TumansiDelivery.customer_user_id == current_user.id,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if delivery.status not in [DeliveryStatusDB.PENDING_ASSIGNMENT, DeliveryStatusDB.ASSIGNED]:
        raise HTTPException(status_code=400, detail="Cannot cancel at this stage")

    delivery.status              = DeliveryStatusDB.CANCELLED
    delivery.cancellation_reason = body.reason

    # Free up rider
    if delivery.rider:
        delivery.rider.current_delivery_id = None

    db.commit()
    return {"success": True, "message": "Delivery cancelled"}


# ============================================================================
# 3. PAYMENTS — Customer
# ============================================================================

@router.post("/deliveries/{delivery_id}/pay")
def initiate_payment(
    delivery_id: str,
    body: InitiatePayment,
    db: Session = Depends(get_db),
):
    """
    Initiate payment for a delivered order.
    For MPesa: triggers Paystack STK push.
    For Cash: marks as paid immediately (rider confirms physically).
    """
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id     == delivery_id,
        TumansiDelivery.status == DeliveryStatusDB.PAYMENT_REQUESTED,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not ready for payment")

    if body.payment_method == "cash_on_delivery":
        delivery.payment_status = PaymentStatusDB.PAID
        delivery.payment_method = "cash_on_delivery"
        delivery.status         = DeliveryStatusDB.COMPLETED
        delivery.completed_at   = datetime.utcnow()

        if delivery.rider:
            delivery.rider.completed_deliveries += 1
            delivery.rider.current_delivery_id   = None
            delivery.rider.total_earnings_kes    = (delivery.rider.total_earnings_kes or 0) + (delivery.final_price_kes or delivery.quoted_price_kes)

        db.commit()
        return {"success": True, "message": "Payment confirmed. Delivery complete!", "status": "completed"}

    # Mobile money / card — integrate Paystack
    try:
        from core.paystack_service import PaystackService
        service = PaystackService()
        amount  = int((delivery.final_price_kes or delivery.quoted_price_kes) * 100)  # kobo
        phone   = body.phone or delivery.customer_phone

        response = service.initialize_transaction(
            email       = delivery.customer_email or f"{phone}@tumanasi.co.ke",
            amount      = amount,
            callback_url= f"https://dexter.vitaldigitalmedia.net/tumanasi/track/{delivery.tracking_number}",
            metadata    = {
                "type":        "tumanasi_delivery",
                "delivery_id": delivery.id,
                "tracking":    delivery.tracking_number,
            }
        )
        ref = response["data"]["reference"]
        delivery.payment_reference = ref
        delivery.payment_method    = body.payment_method
        db.commit()

        return {
            "success":       True,
            "payment_url":   response["data"]["authorization_url"],
            "reference":     ref,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {exc}")


# ============================================================================
# 4. RIDER REGISTRATION & PROFILE
# ============================================================================

@router.post("/rider/register", response_model=RiderResponse, status_code=201)
def register_rider(
    body:         RiderRegister,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Register current user as a Tumanasi rider."""
    existing = db.query(TumansiRider).filter(
        TumansiRider.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered as a rider")

    phone_conflict = db.query(TumansiRider).filter(TumansiRider.phone == body.phone).first()
    if phone_conflict:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    rider = TumansiRider(
        id           = str(uuid.uuid4()),
        user_id      = current_user.id,
        full_name    = body.full_name,
        phone        = body.phone,
        email        = body.email or current_user.email,
        id_number    = body.id_number,
        vehicle_type = body.vehicle_type,
        vehicle_reg  = body.vehicle_reg,
    )
    db.add(rider)
    db.commit()
    db.refresh(rider)
    return rider


@router.get("/rider/me", response_model=RiderResponse)
def get_my_rider_profile(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    return get_rider_from_user(db, current_user)


@router.put("/rider/me", response_model=RiderResponse)
def update_rider_profile(
    body:         RiderUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    rider = get_rider_from_user(db, current_user)
    if body.full_name:    rider.full_name    = body.full_name
    if body.vehicle_type: rider.vehicle_type = body.vehicle_type
    if body.vehicle_reg:  rider.vehicle_reg  = body.vehicle_reg
    if body.photo_url:    rider.photo_url    = body.photo_url
    if body.current_zone_id is not None:
        rider.current_zone_id = body.current_zone_id or None
    db.commit()
    db.refresh(rider)
    return rider


@router.put("/rider/availability")
def set_availability(
    body:         RiderAvailability,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    rider = get_rider_from_user(db, current_user)
    if not rider.is_verified:
        raise HTTPException(status_code=403, detail="Your profile hasn't been verified yet. Wait for admin approval.")
    rider.is_available = body.is_available
    db.commit()
    return {"success": True, "is_available": rider.is_available}


# ============================================================================
# 5. RIDER — DELIVERY MANAGEMENT
# ============================================================================

@router.post("/rider/log-delivery", response_model=DeliveryResponse)
def rider_log_delivery(
    body:         DeliveryCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Riders can log a delivery on behalf of a client directly.
    It automatically assigns to them and moves to assigned status.
    """
    rider = get_rider_from_user(db, current_user)
    if not rider.is_verified:
        raise HTTPException(status_code=403, detail="Unverified riders cannot log deliveries.")

    # Resolve price from dropoff zone
    dropoff_zone = db.query(TumansiZone).filter(TumansiZone.id == body.dropoff_area_id).first()
    if not dropoff_zone or not dropoff_zone.is_active:
        raise HTTPException(status_code=400, detail="Invalid or inactive dropoff zone.")

    tracking = generate_tracking_number()
    delivery = TumansiDelivery(
        id              = str(uuid.uuid4()),
        tracking_number = tracking,
        customer_user_id = getattr(current_user, "id", None), # rider logs it so they act as customer agent
        customer_name    = body.customer_name,
        customer_phone   = body.customer_phone,
        customer_email   = body.customer_email,
        errand_type          = body.errand_type,
        errand_description   = body.errand_description,
        special_instructions = body.special_instructions,
        is_fragile           = body.is_fragile,
        requires_handling    = body.requires_handling,
        pickup_address       = body.pickup_address,
        pickup_area_id       = body.pickup_area_id,
        pickup_contact_name  = body.pickup_contact_name or body.customer_name,
        pickup_contact_phone = body.pickup_contact_phone or body.customer_phone,
        dropoff_address       = body.dropoff_address,
        dropoff_area_id       = body.dropoff_area_id,
        dropoff_contact_name  = body.dropoff_contact_name or body.customer_name,
        dropoff_contact_phone = body.dropoff_contact_phone or body.customer_phone,
        quoted_price_kes = dropoff_zone.price_kes,
        final_price_kes  = dropoff_zone.price_kes,
        payment_method   = body.payment_method,
        payment_status   = PaymentStatusDB.PENDING,
        status           = DeliveryStatusDB.ASSIGNED,  # Start directly as Assigned
        rider_id         = rider.id,                   # Force self assignment
        assigned_at      = datetime.utcnow(),
        assignment_method = "manual",
        estimated_delivery_at = datetime.utcnow() + timedelta(hours=2),
    )

    rider.current_delivery_id = delivery.id
    rider.total_deliveries   += 1

    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/rider/deliveries", response_model=List[DeliveryListItem])
def rider_deliveries(
    status_filter: Optional[str] = Query(None, alias="status"),
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Get deliveries assigned to the current rider."""
    rider = get_rider_from_user(db, current_user)
    q = db.query(TumansiDelivery).filter(TumansiDelivery.rider_id == rider.id)
    if status_filter:
        q = q.filter(TumansiDelivery.status == status_filter)
    rows = q.order_by(desc(TumansiDelivery.created_at)).all()
    return [DeliveryListItem(
        id              = d.id,
        tracking_number = d.tracking_number,
        customer_name   = d.customer_name,
        customer_phone  = d.customer_phone,
        errand_type     = d.errand_type,
        pickup_address  = d.pickup_address,
        dropoff_address = d.dropoff_address,
        quoted_price_kes = d.quoted_price_kes,
        payment_method  = d.payment_method,
        payment_status  = d.payment_status,
        status          = d.status,
        rider_name      = rider.full_name,
        created_at      = d.created_at,
    ) for d in rows]


@router.get("/rider/deliveries/available", response_model=List[DeliveryListItem])
def available_jobs(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Unassigned deliveries the rider can pick up."""
    rider = get_rider_from_user(db, current_user)
    if not rider.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified yet.")
    rows = db.query(TumansiDelivery).filter(
        TumansiDelivery.status == DeliveryStatusDB.PENDING_ASSIGNMENT
    ).order_by(TumansiDelivery.created_at).limit(20).all()
    return [DeliveryListItem(
        id              = d.id,
        tracking_number = d.tracking_number,
        customer_name   = d.customer_name,
        customer_phone  = d.customer_phone,
        errand_type     = d.errand_type,
        pickup_address  = d.pickup_address,
        dropoff_address = d.dropoff_address,
        quoted_price_kes = d.quoted_price_kes,
        payment_method  = d.payment_method,
        payment_status  = d.payment_status,
        status          = d.status,
        rider_name      = None,
        created_at      = d.created_at,
    ) for d in rows]


@router.put("/rider/deliveries/{delivery_id}/accept")
def accept_delivery(
    delivery_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    rider = get_rider_from_user(db, current_user)
    if not rider.is_available or rider.current_delivery_id:
        raise HTTPException(status_code=400, detail="You already have an active delivery or are offline.")

    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id     == delivery_id,
        TumansiDelivery.status == DeliveryStatusDB.PENDING_ASSIGNMENT,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery no longer available.")

    delivery.rider_id          = rider.id
    delivery.assigned_at       = datetime.utcnow()
    delivery.assignment_method = "auto"
    delivery.status            = DeliveryStatusDB.ASSIGNED
    rider.current_delivery_id  = delivery.id
    rider.total_deliveries    += 1

    db.commit()
    return {"success": True, "message": "Delivery accepted!", "tracking_number": delivery.tracking_number}


# Valid status transitions (rider side)
RIDER_STATUS_TRANSITIONS = {
    DeliveryStatusDB.ASSIGNED:           DeliveryStatusDB.EN_ROUTE_PICKUP,
    DeliveryStatusDB.EN_ROUTE_PICKUP:    DeliveryStatusDB.COLLECTED,
    DeliveryStatusDB.COLLECTED:          DeliveryStatusDB.EN_ROUTE_DELIVERY,
    DeliveryStatusDB.EN_ROUTE_DELIVERY:  DeliveryStatusDB.DELIVERED,
    DeliveryStatusDB.DELIVERED:          DeliveryStatusDB.PAYMENT_REQUESTED,
}


@router.put("/rider/deliveries/{delivery_id}/status")
def update_delivery_status(
    delivery_id:  str,
    body:         DeliveryStatusUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Rider advances delivery through the status pipeline."""
    rider    = get_rider_from_user(db, current_user)
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id       == delivery_id,
        TumansiDelivery.rider_id == rider.id,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not assigned to you")

    current = DeliveryStatusDB(delivery.status)
    expected_next = RIDER_STATUS_TRANSITIONS.get(current)

    if DeliveryStatusDB(body.status) != expected_next:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {current} → {body.status}. Expected next: {expected_next}"
        )

    delivery.status = body.status

    # When payment requested, rider is still holding delivery
    if body.status == DeliveryStatusDB.PAYMENT_REQUESTED:
        pass   # wait for payment confirmation

    db.commit()
    return {"success": True, "status": delivery.status}


@router.post("/rider/deliveries/{delivery_id}/pickup-photo")
def upload_pickup_photo(
    delivery_id:  str,
    photo:        UploadFile = File(...),
    notes:        Optional[str] = None,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Rider uploads photo proof of collection."""
    rider    = get_rider_from_user(db, current_user)
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id       == delivery_id,
        TumansiDelivery.rider_id == rider.id,
        TumansiDelivery.status   == DeliveryStatusDB.EN_ROUTE_PICKUP,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not at pickup stage")

    url = upload_photo_to_storage(photo, "pickups")
    delivery.pickup_photo_url = url
    delivery.pickup_photo_at  = datetime.utcnow()
    delivery.pickup_notes     = notes
    delivery.status           = DeliveryStatusDB.COLLECTED

    db.commit()
    return {"success": True, "photo_url": url, "status": "collected"}


@router.post("/rider/deliveries/{delivery_id}/delivery-photo")
def upload_delivery_photo(
    delivery_id:  str,
    photo:        UploadFile = File(...),
    notes:        Optional[str] = None,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Rider uploads photo proof of delivery."""
    rider    = get_rider_from_user(db, current_user)
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id       == delivery_id,
        TumansiDelivery.rider_id == rider.id,
        TumansiDelivery.status   == DeliveryStatusDB.EN_ROUTE_DELIVERY,
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not at delivery stage")

    url = upload_photo_to_storage(photo, "deliveries")
    delivery.delivery_photo_url = url
    delivery.delivery_photo_at  = datetime.utcnow()
    delivery.delivery_notes     = notes
    delivery.status             = DeliveryStatusDB.DELIVERED

    db.commit()
    return {"success": True, "photo_url": url, "status": "delivered"}


@router.put("/rider/deliveries/{delivery_id}/confirm-payment")
def confirm_cash_payment(
    delivery_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Rider confirms cash was collected from customer."""
    rider    = get_rider_from_user(db, current_user)
    delivery = db.query(TumansiDelivery).filter(
        TumansiDelivery.id             == delivery_id,
        TumansiDelivery.rider_id       == rider.id,
        TumansiDelivery.status         == DeliveryStatusDB.PAYMENT_REQUESTED,
        TumansiDelivery.payment_method == "cash_on_delivery",
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not awaiting cash payment")

    delivery.payment_status = PaymentStatusDB.PAID
    delivery.status         = DeliveryStatusDB.COMPLETED
    delivery.completed_at   = datetime.utcnow()
    rider.completed_deliveries += 1
    rider.current_delivery_id = None
    rider.total_earnings_kes  = (rider.total_earnings_kes or 0) + (
        delivery.final_price_kes or delivery.quoted_price_kes
    )

    db.commit()
    return {"success": True, "message": "Payment confirmed. Delivery complete!"}


# ============================================================================
# 6. ADMIN ENDPOINTS
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency: raises 403 if the caller is not an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/admin/stats", response_model=TumansiStats)
def admin_stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total      = db.query(TumansiDelivery).count()
    active     = db.query(TumansiDelivery).filter(
        TumansiDelivery.status.in_([
            DeliveryStatusDB.ASSIGNED, DeliveryStatusDB.EN_ROUTE_PICKUP,
            DeliveryStatusDB.COLLECTED, DeliveryStatusDB.EN_ROUTE_DELIVERY,
            DeliveryStatusDB.DELIVERED, DeliveryStatusDB.PAYMENT_REQUESTED,
        ])
    ).count()
    completed_today = db.query(TumansiDelivery).filter(
        TumansiDelivery.completed_at >= today_start,
        TumansiDelivery.status == DeliveryStatusDB.COMPLETED,
    ).count()
    revenue_today = db.query(func.sum(TumansiDelivery.final_price_kes)).filter(
        TumansiDelivery.completed_at >= today_start,
        TumansiDelivery.status       == DeliveryStatusDB.COMPLETED,
    ).scalar() or 0
    revenue_total = db.query(func.sum(TumansiDelivery.final_price_kes)).filter(
        TumansiDelivery.status == DeliveryStatusDB.COMPLETED,
    ).scalar() or 0

    total_riders    = db.query(TumansiRider).count()
    active_riders   = db.query(TumansiRider).filter(TumansiRider.is_available == True).count()
    verified_riders = db.query(TumansiRider).filter(TumansiRider.is_verified == True).count()

    completed_all = db.query(TumansiDelivery).filter(TumansiDelivery.status == DeliveryStatusDB.COMPLETED).count()
    rate = round((completed_all / total) * 100, 1) if total else 0

    return TumansiStats(
        total_deliveries    = total,
        active_deliveries   = active,
        completed_today     = completed_today,
        revenue_today_kes   = revenue_today,
        revenue_total_kes   = revenue_total,
        total_riders        = total_riders,
        active_riders       = active_riders,
        verified_riders     = verified_riders,
        avg_completion_rate = rate,
    )


@router.get("/admin/deliveries", response_model=List[DeliveryListItem])
def admin_list_deliveries(
    status_filter: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None),
    skip:          int           = Query(0, ge=0),
    limit:         int           = Query(50, le=200),
    db:            Session       = Depends(get_db),
    _:             User          = Depends(require_admin),
):
    q = db.query(TumansiDelivery)
    if status_filter:
        q = q.filter(TumansiDelivery.status == status_filter)
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(
            TumansiDelivery.tracking_number.like(pattern),
            TumansiDelivery.customer_name.like(pattern),
            TumansiDelivery.customer_phone.like(pattern),
        ))
    rows = q.order_by(desc(TumansiDelivery.created_at)).offset(skip).limit(limit).all()
    return [DeliveryListItem(
        id              = d.id,
        tracking_number = d.tracking_number,
        customer_name   = d.customer_name,
        customer_phone  = d.customer_phone,
        errand_type     = d.errand_type,
        pickup_address  = d.pickup_address,
        dropoff_address = d.dropoff_address,
        quoted_price_kes = d.quoted_price_kes,
        payment_method  = d.payment_method,
        payment_status  = d.payment_status,
        status          = d.status,
        rider_name      = d.rider.full_name if d.rider else None,
        created_at      = d.created_at,
    ) for d in rows]


@router.put("/admin/deliveries/{delivery_id}", response_model=DeliveryResponse)
def admin_update_delivery(
    delivery_id: str,
    body: AdminDeliveryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Admin: freely edit any mutable field on a delivery.
    Changing final_price_kes overrides what customer is billed.
    Changing status bypasses the normal rider state-machine.
    """
    delivery = db.query(TumansiDelivery).filter(TumansiDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Apply each field only when explicitly provided
    if body.customer_name  is not None: delivery.customer_name  = body.customer_name
    if body.customer_phone is not None: delivery.customer_phone = body.customer_phone
    if body.customer_email is not None: delivery.customer_email = body.customer_email

    if body.errand_type          is not None: delivery.errand_type          = body.errand_type
    if body.errand_description   is not None: delivery.errand_description   = body.errand_description
    if body.special_instructions is not None: delivery.special_instructions = body.special_instructions
    if body.is_fragile           is not None: delivery.is_fragile           = body.is_fragile
    if body.requires_handling    is not None: delivery.requires_handling    = body.requires_handling

    if body.pickup_address       is not None: delivery.pickup_address       = body.pickup_address
    if body.pickup_contact_name  is not None: delivery.pickup_contact_name  = body.pickup_contact_name
    if body.pickup_contact_phone is not None: delivery.pickup_contact_phone = body.pickup_contact_phone

    if body.dropoff_address       is not None: delivery.dropoff_address       = body.dropoff_address
    if body.dropoff_contact_name  is not None: delivery.dropoff_contact_name  = body.dropoff_contact_name
    if body.dropoff_contact_phone is not None: delivery.dropoff_contact_phone = body.dropoff_contact_phone

    if body.final_price_kes is not None:
        delivery.final_price_kes  = body.final_price_kes
        # also update quoted so UI shows the override consistently
        delivery.quoted_price_kes = body.final_price_kes

    if body.status         is not None: delivery.status         = body.status
    if body.payment_status is not None: delivery.payment_status = body.payment_status
    if body.payment_method is not None: delivery.payment_method = body.payment_method

    if body.cancellation_reason is not None: delivery.cancellation_reason = body.cancellation_reason

    db.commit()
    db.refresh(delivery)
    return delivery


@router.put("/admin/deliveries/{delivery_id}/assign")
def admin_assign_rider(
    delivery_id: str,
    body: AdminAssignRider,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    delivery = db.query(TumansiDelivery).filter(TumansiDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    rider = db.query(TumansiRider).filter(TumansiRider.id == body.rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Free previous rider if any
    if delivery.rider and delivery.rider.current_delivery_id == delivery.id:
        delivery.rider.current_delivery_id = None

    delivery.rider_id          = rider.id
    delivery.assigned_at       = datetime.utcnow()
    delivery.assignment_method = "manual"
    delivery.status            = DeliveryStatusDB.ASSIGNED
    rider.current_delivery_id  = delivery.id

    db.commit()
    return {"success": True, "message": f"Assigned to {rider.full_name}"}


@router.get("/admin/riders", response_model=List[RiderResponse])
def admin_list_riders(
    verified: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(TumansiRider)
    if verified is not None:
        q = q.filter(TumansiRider.is_verified == verified)
    return q.order_by(desc(TumansiRider.created_at)).all()


@router.put("/admin/riders/{rider_id}/verify")
def admin_verify_rider(
    rider_id: str,
    body: AdminRiderVerify,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rider = db.query(TumansiRider).filter(TumansiRider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    rider.is_verified          = body.is_verified
    rider.verification_notes   = body.verification_notes
    if not body.is_verified:
        rider.is_available = False
    db.commit()
    return {"success": True, "is_verified": rider.is_verified}


@router.post("/admin/zones", response_model=ZoneResponse, status_code=201)
def admin_create_zone(
    body: AdminZoneCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    zone = TumansiZone(
        id        = str(uuid.uuid4()),
        zone_name = body.zone_name,
        area_name = body.area_name,
        price_kes = body.price_kes,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/admin/zones/{zone_id}", response_model=ZoneResponse)
def admin_update_zone(
    zone_id: str,
    body: AdminZoneUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    zone = db.query(TumansiZone).filter(TumansiZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    if body.zone_name is not None: zone.zone_name = body.zone_name
    if body.area_name is not None: zone.area_name = body.area_name
    if body.price_kes is not None: zone.price_kes = body.price_kes
    if body.is_active is not None: zone.is_active = body.is_active
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/admin/zones/{zone_id}", status_code=204)
def admin_delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Permanently delete a zone. Fails if any deliveries reference it."""
    zone = db.query(TumansiZone).filter(TumansiZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    # Safety: check if zone has deliveries referencing it
    from database.tumanasi_models import TumansiDelivery as _D
    refs = db.query(_D).filter(
        (_D.pickup_area_id == zone_id) | (_D.dropoff_area_id == zone_id)
    ).count()
    if refs:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {refs} delivery/deliveries reference this zone. Deactivate it instead."
        )
    db.delete(zone)
    db.commit()


@router.get("/admin/riders/available")
def admin_available_riders(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return all verified, active riders for manual assignment dropdown."""
    riders = db.query(TumansiRider).filter(
        TumansiRider.is_verified == True,
        TumansiRider.is_active   == True,
    ).order_by(TumansiRider.is_available.desc(), TumansiRider.full_name).all()
    return [
        {
            "id":           r.id,
            "full_name":    r.full_name,
            "phone":        r.phone,
            "vehicle_type": r.vehicle_type,
            "is_available": r.is_available,
            "current_delivery_id": r.current_delivery_id,
        }
        for r in riders
    ]
