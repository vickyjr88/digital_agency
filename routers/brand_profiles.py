# Brand Profile Management Endpoints for Affiliate Commerce
# One BrandProfile per Brand (not per User).

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from database.models import User, Brand
from database.affiliate_models import BrandProfile
from schemas.affiliate import (
    BrandProfileCreate,
    BrandProfileUpdate,
    BrandProfileResponse,
    BrandContactInfo,
    SuccessResponse
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/brand-profiles", tags=["Brand Profiles"])


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


def _profile_to_response(profile: BrandProfile) -> BrandProfileResponse:
    """Serialize a BrandProfile ORM object, injecting brand_name from the relationship."""
    data = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
    data["brand_name"] = profile.brand.name if profile.brand else None
    return BrandProfileResponse(**data)


# ── Authenticated helpers ─────────────────────────────────────────────────────

def _get_owned_brand(brand_id: str, user_id: str, db: Session) -> Brand:
    """Return brand if it belongs to the current user, else 404/403."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    if brand.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this brand")
    return brand


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/my-profiles", response_model=List[BrandProfileResponse])
async def list_my_brand_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return all brand profiles owned by the current user
    (one per brand the user has set up for affiliate commerce).
    """
    profiles = (
        db.query(BrandProfile)
        .join(Brand, BrandProfile.brand_id == Brand.id)
        .filter(Brand.user_id == current_user.id)
        .all()
    )
    return [_profile_to_response(p) for p in profiles]


@router.post("/", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_profile(
    profile_data: BrandProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a brand profile for one of the user's brands.
    Each brand can have at most one profile.
    """
    # Verify brand ownership
    _get_owned_brand(profile_data.brand_id, current_user.id, db)

    # Prevent duplicates
    existing = db.query(BrandProfile).filter(
        BrandProfile.brand_id == profile_data.brand_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A profile already exists for this brand. Use PUT to update it."
        )

    new_profile = BrandProfile(
        id=generate_uuid(),
        user_id=current_user.id,
        **profile_data.dict()
    )

    try:
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return _profile_to_response(new_profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create brand profile. Please check your data."
        )


@router.get("/brand/{brand_id}", response_model=BrandProfileResponse)
async def get_brand_profile_for_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the brand profile for a specific brand (must be the owner)."""
    _get_owned_brand(brand_id, current_user.id, db)

    profile = db.query(BrandProfile).filter(
        BrandProfile.brand_id == brand_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found. Create one first."
        )
    return _profile_to_response(profile)


@router.put("/brand/{brand_id}", response_model=BrandProfileResponse)
async def update_brand_profile_for_brand(
    brand_id: str,
    profile_data: BrandProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the brand profile for a specific brand (must be the owner)."""
    _get_owned_brand(brand_id, current_user.id, db)

    profile = db.query(BrandProfile).filter(
        BrandProfile.brand_id == brand_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found. Create one first with POST /api/brand-profiles/"
        )

    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    try:
        db.commit()
        db.refresh(profile)
        return _profile_to_response(profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update brand profile."
        )


@router.delete("/brand/{brand_id}", response_model=SuccessResponse)
async def delete_brand_profile_for_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete the brand profile for a specific brand (must be the owner)."""
    _get_owned_brand(brand_id, current_user.id, db)

    profile = db.query(BrandProfile).filter(
        BrandProfile.brand_id == brand_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found"
        )

    from database.affiliate_models import Product
    active_products = db.query(Product).filter(
        Product.brand_profile_id == profile.id,
        Product.status == "active"
    ).count()

    if active_products > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete profile. You have {active_products} active products. Archive them first."
        )

    db.delete(profile)
    db.commit()
    return SuccessResponse(success=True, message="Brand profile deleted successfully")


# ── Legacy /me endpoints (kept for backward compatibility, use first profile) ─

@router.get("/me", response_model=BrandProfileResponse)
async def get_my_brand_profile_legacy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy: returns the first brand profile for the current user."""
    profile = (
        db.query(BrandProfile)
        .join(Brand, BrandProfile.brand_id == Brand.id)
        .filter(Brand.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found. Create one first at /api/brand-profiles/"
        )
    return _profile_to_response(profile)


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("/{brand_profile_id}", response_model=BrandProfileResponse)
async def get_brand_profile_public(
    brand_profile_id: str,
    db: Session = Depends(get_db)
):
    """Get any brand profile by ID (public view)."""
    profile = db.query(BrandProfile).filter(BrandProfile.id == brand_profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return _profile_to_response(profile)


@router.get("/{brand_profile_id}/contact", response_model=BrandContactInfo)
async def get_brand_contact_info(
    brand_profile_id: str,
    db: Session = Depends(get_db)
):
    """Get brand contact information (public endpoint, shown to customers after order)."""
    profile = db.query(BrandProfile).filter(
        BrandProfile.id == brand_profile_id,
        BrandProfile.is_active == True
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand contact information not available"
        )

    return BrandContactInfo(
        whatsapp_number=profile.whatsapp_number,
        business_location=profile.business_location,
        business_hours=profile.business_hours,
        preferred_contact_method=profile.preferred_contact_method,
        phone_number=profile.phone_number,
        business_email=profile.business_email,
        website_url=profile.website_url,
        instagram_handle=profile.instagram_handle,
        facebook_page=profile.facebook_page
    )
