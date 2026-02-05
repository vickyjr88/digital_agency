# Brand Profile Management Endpoints for Affiliate Commerce

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional

from database.models import User
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


@router.post("/", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_profile(
    profile_data: BrandProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update brand profile with contact information.
    Required for brands to sell products.
    """
    # Check if profile already exists
    existing_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand profile already exists. Use PUT to update."
        )

    # Get user's brand entity if exists
    from database.models import Brand
    brand = db.query(Brand).filter(Brand.user_id == current_user.id).first()

    # Create new profile
    new_profile = BrandProfile(
        id=generate_uuid(),
        user_id=current_user.id,
        brand_id=brand.id if brand else None,
        **profile_data.dict()
    )

    try:
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create brand profile. Please check your data."
        )


@router.get("/me", response_model=BrandProfileResponse)
async def get_my_brand_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's brand profile."""
    profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found. Create one first."
        )

    return profile


@router.put("/me", response_model=BrandProfileResponse)
async def update_my_brand_profile(
    profile_data: BrandProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user's brand profile."""
    profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found. Create one first with POST /api/brand-profiles/"
        )

    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    try:
        db.commit()
        db.refresh(profile)
        return profile
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update brand profile."
        )


@router.get("/{brand_profile_id}", response_model=BrandProfileResponse)
async def get_brand_profile(
    brand_profile_id: str,
    db: Session = Depends(get_db)
):
    """Get any brand profile by ID (public view)."""
    profile = db.query(BrandProfile).filter(
        BrandProfile.id == brand_profile_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found"
        )

    return profile


@router.get("/{brand_profile_id}/contact", response_model=BrandContactInfo)
async def get_brand_contact_info(
    brand_profile_id: str,
    db: Session = Depends(get_db)
):
    """
    Get brand contact information (public endpoint).
    Shown to customers after they place an order.
    """
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


@router.delete("/me", response_model=SuccessResponse)
async def delete_my_brand_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete current user's brand profile."""
    profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found"
        )

    # Check if brand has active products
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

    return SuccessResponse(
        success=True,
        message="Brand profile deleted successfully"
    )
