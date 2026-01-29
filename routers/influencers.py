# Influencer Router for Dexter Marketplace
# Handles influencer profile management and marketplace listing

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User, UserType
from database.marketplace_models import InfluencerProfile, Package
from schemas.marketplace import (
    InfluencerProfileCreate,
    InfluencerProfileUpdate,
    InfluencerProfileResponse,
    InfluencerSearchParams,
    SocialMediaStats,
    PlatformType,
    VerificationStatus,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type, require_permission, AuthError

router = APIRouter(prefix="/influencers", tags=["Influencers"])


# ============================================================================
# PRIVATE ENDPOINTS (Authenticated)
# ============================================================================

@router.post("/onboard", response_model=InfluencerProfileResponse, status_code=status.HTTP_201_CREATED)
async def onboard_as_influencer(
    profile_data: InfluencerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER))
):
    """
    Start influencer onboarding. Creates influencer profile and updates user type.
    Can be called by brands wanting to also be influencers.
    """
    # Check if user already has an influencer profile
    existing_profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an influencer profile"
        )
    
    # Create influencer profile
    profile = InfluencerProfile(
        user_id=current_user.id,
        display_name=profile_data.display_name,
        bio=profile_data.bio,
        niche=profile_data.niche,
        location=profile_data.location,
        instagram_handle=profile_data.instagram_handle,
        tiktok_handle=profile_data.tiktok_handle,
        youtube_channel=profile_data.youtube_channel,
        twitter_handle=profile_data.twitter_handle,
        facebook_handle=profile_data.facebook_handle,
        whatsapp_number=profile_data.whatsapp_number,
        
        # Social Media Links
        instagram_link=profile_data.instagram_link,
        tiktok_link=profile_data.tiktok_link,
        youtube_link=profile_data.youtube_link,
        twitter_link=profile_data.twitter_link,
        facebook_link=profile_data.facebook_link,
        
        # Initial follower counts
        instagram_followers=profile_data.instagram_followers or 0,
        tiktok_followers=profile_data.tiktok_followers or 0,
        youtube_subscribers=profile_data.youtube_subscribers or 0,
        twitter_followers=profile_data.twitter_followers or 0,
        facebook_followers=profile_data.facebook_followers or 0,
        
        verification_status=VerificationStatus.PENDING,
    )
    
    db.add(profile)
    
    # Update user type to influencer (if not admin)
    if current_user.user_type != UserType.ADMIN:
        current_user.user_type = UserType.INFLUENCER
    
    db.commit()
    db.refresh(profile)
    
    return _profile_to_response(profile)


@router.get("/me", response_model=InfluencerProfileResponse)
async def get_my_influencer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """Get the current user's influencer profile."""
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found. Please complete onboarding first."
        )
    
    return _profile_to_response(profile)


@router.put("/me", response_model=InfluencerProfileResponse)
async def update_my_influencer_profile(
    profile_data: InfluencerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """Update the current user's influencer profile."""
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found"
        )
    
    # Update only provided fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(profile)
    
    return _profile_to_response(profile)


@router.get("/me/stats", response_model=dict)
async def get_my_influencer_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """Get statistics for the current user's influencer account."""
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found"
        )
    
    # Get package stats
    active_packages = db.query(Package).filter(
        Package.influencer_id == profile.id,
        Package.status == "active"
    ).count()
    
    total_purchases = db.query(Package).filter(
        Package.influencer_id == profile.id
    ).with_entities(Package.times_purchased).all()
    
    total_purchased = sum(p[0] for p in total_purchases)
    
    return {
        "profile": _profile_to_response(profile),
        "stats": {
            "active_packages": active_packages,
            "total_purchases": total_purchased,
            "rating": profile.rating,
            "review_count": profile.review_count,
            "completed_campaigns": profile.completed_campaigns,
            "is_verified": profile.is_verified,
            "verification_status": profile.verification_status.value if profile.verification_status else "pending",
        }
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin", response_model=dict)
async def get_all_influencers_admin(
    query: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all influencers for admin dashboard."""
    base_query = db.query(InfluencerProfile)
    
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                InfluencerProfile.display_name.ilike(search_term),
                InfluencerProfile.bio.ilike(search_term),
                InfluencerProfile.niche.ilike(search_term),
            )
        )
    
    total = base_query.count()
    offset = (page - 1) * limit
    profiles = base_query.order_by(InfluencerProfile.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "influencers": [_profile_to_response(p) for p in profiles],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }


@router.get("/admin/pending", response_model=list)
async def get_pending_influencers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get list of influencers pending verification (Admin only)."""
    profiles = db.query(InfluencerProfile).filter(
        InfluencerProfile.verification_status == VerificationStatus.PENDING
    ).order_by(InfluencerProfile.created_at.desc()).all()
    
    return [_profile_to_response(p) for p in profiles]


@router.put("/admin/{influencer_id}/verify", response_model=InfluencerProfileResponse)
async def verify_influencer(
    influencer_id: str,
    action: str = Query(..., description="approve or reject"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Approve or reject an influencer's verification (Admin only)."""
    profile = db.query(InfluencerProfile).filter(
        or_(
            InfluencerProfile.id == influencer_id,
            InfluencerProfile.user_id == influencer_id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    if action == "approve":
        profile.verification_status = VerificationStatus.APPROVED
        profile.is_verified = True
        profile.identity_verified_at = datetime.utcnow()
    elif action == "reject":
        profile.verification_status = VerificationStatus.REJECTED
        profile.is_verified = False
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'"
        )
    
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    
    return _profile_to_response(profile)


# ============================================================================
# PUBLIC ENDPOINTS (Marketplace)
# ============================================================================

@router.get("", response_model=dict)
async def search_influencers(
    db: Session = Depends(get_db),
    query: Optional[str] = Query(None, description="Search query"),
    niche: Optional[str] = Query(None, description="Filter by niche"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    min_followers: Optional[int] = Query(None, ge=0, description="Minimum followers"),
    max_followers: Optional[int] = Query(None, le=100000000, description="Maximum followers"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum package price"),
    max_price: Optional[int] = Query(None, description="Maximum package price"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    location: Optional[str] = Query(None, description="Filter by location"),
    verified_only: bool = Query(False, description="Only show verified influencers"),
    sort_by: str = Query("rating", description="Sort by: rating, followers, price_low, price_high"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """
    Search and browse influencers in the marketplace.
    Returns paginated list of verified influencers with their packages.
    """
    # Base query - only show verified or approved influencers publicly
    base_query = db.query(InfluencerProfile)
    
    if verified_only:
        base_query = base_query.filter(InfluencerProfile.is_verified == True)
    else:
        # Show influencers with pending or approved status (not rejected)
        base_query = base_query.filter(
            InfluencerProfile.verification_status.in_([
                VerificationStatus.PENDING,
                VerificationStatus.APPROVED
            ])
        )
    
    # Apply filters
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                InfluencerProfile.display_name.ilike(search_term),
                InfluencerProfile.bio.ilike(search_term),
                InfluencerProfile.niche.ilike(search_term),
            )
        )
    
    if niche:
        base_query = base_query.filter(InfluencerProfile.niche.ilike(f"%{niche}%"))
    
    if location:
        base_query = base_query.filter(InfluencerProfile.location.ilike(f"%{location}%"))
    
    if min_rating is not None:
        base_query = base_query.filter(InfluencerProfile.rating >= min_rating)
    
    # Platform filter - check if they have connected the platform
    if platform:
        if platform == PlatformType.INSTAGRAM:
            base_query = base_query.filter(InfluencerProfile.instagram_handle.isnot(None))
        elif platform == PlatformType.TIKTOK:
            base_query = base_query.filter(InfluencerProfile.tiktok_handle.isnot(None))
        elif platform == PlatformType.YOUTUBE:
            base_query = base_query.filter(InfluencerProfile.youtube_channel.isnot(None))
        elif platform == PlatformType.TWITTER:
            base_query = base_query.filter(InfluencerProfile.twitter_handle.isnot(None))
        elif platform == PlatformType.FACEBOOK:
            base_query = base_query.filter(InfluencerProfile.facebook_handle.isnot(None))
    
    # Follower count filter (across all platforms)
    if min_followers is not None:
        base_query = base_query.filter(
            or_(
                InfluencerProfile.instagram_followers >= min_followers,
                InfluencerProfile.tiktok_followers >= min_followers,
                InfluencerProfile.youtube_subscribers >= min_followers,
                InfluencerProfile.twitter_followers >= min_followers,
                InfluencerProfile.facebook_followers >= min_followers,
            )
        )
    
    if max_followers is not None:
        base_query = base_query.filter(
            or_(
                and_(
                    InfluencerProfile.instagram_followers <= max_followers,
                    InfluencerProfile.instagram_handle.isnot(None)
                ),
                and_(
                    InfluencerProfile.tiktok_followers <= max_followers,
                    InfluencerProfile.tiktok_handle.isnot(None)
                ),
                and_(
                    InfluencerProfile.youtube_subscribers <= max_followers,
                    InfluencerProfile.youtube_channel.isnot(None)
                ),
                and_(
                    InfluencerProfile.twitter_followers <= max_followers,
                    InfluencerProfile.twitter_handle.isnot(None)
                ),
                and_(
                    InfluencerProfile.facebook_followers <= max_followers,
                    InfluencerProfile.facebook_handle.isnot(None)
                ),
            )
        )
    
    # Apply sorting
    if sort_by == "rating":
        base_query = base_query.order_by(InfluencerProfile.rating.desc())
    elif sort_by == "followers":
        # Sort by max follower count across platforms
        base_query = base_query.order_by(
            (InfluencerProfile.instagram_followers + 
             InfluencerProfile.tiktok_followers + 
             InfluencerProfile.youtube_subscribers + 
             InfluencerProfile.twitter_followers +
             InfluencerProfile.facebook_followers).desc()
        )
    # price_low and price_high would require joining with packages
    
    # Get total count
    total = base_query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    influencers = base_query.offset(offset).limit(limit).all()
    
    # Convert to response with packages
    results = []
    for profile in influencers:
        response = _profile_to_response(profile)
        
        # Get active packages for this influencer
        packages = db.query(Package).filter(
            Package.influencer_id == profile.id,
            Package.status == "active"
        ).all()
        
        response_dict = response.model_dump()
        response_dict["packages"] = [
            {
                "id": p.id,
                "name": p.name,
                "platform": p.platform.value if p.platform else None,
                "content_type": p.content_type,
                "price": p.price,
                "currency": p.currency,
            }
            for p in packages
        ]
        
        # Apply price filter at the result level if needed
        if min_price is not None or max_price is not None:
            package_prices = [p.price for p in packages]
            if not package_prices:
                continue  # Skip influencers with no active packages
            min_package_price = min(package_prices)
            max_package_price = max(package_prices)
            
            if min_price is not None and max_package_price < min_price:
                continue
            if max_price is not None and min_package_price > max_price:
                continue
        
        results.append(response_dict)
    
    return {
        "influencers": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }


@router.get("/{influencer_id}", response_model=InfluencerProfileResponse)
async def get_influencer_profile(
    influencer_id: str,
    db: Session = Depends(get_db),
):
    """Get a public influencer profile by ID."""
    # Try fetching by InfluencerProfile.id first, then fallback to user_id
    profile = db.query(InfluencerProfile).filter(
        or_(
            InfluencerProfile.id == influencer_id,
            InfluencerProfile.user_id == influencer_id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    # Don't show rejected profiles publicly
    if profile.verification_status == VerificationStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    return _profile_to_response(profile)


@router.get("/{influencer_id}/packages", response_model=list)
async def get_influencer_packages(
    influencer_id: str,
    db: Session = Depends(get_db),
):
    """Get all active packages for an influencer."""
    profile = db.query(InfluencerProfile).filter(
        or_(
            InfluencerProfile.id == influencer_id,
            InfluencerProfile.user_id == influencer_id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    packages = db.query(Package).filter(
        Package.influencer_id == profile.id,
        Package.status == "active"
    ).all()
    
    return [
        {
            "id": p.id,
            "influencer_id": p.influencer_id,
            "name": p.name,
            "description": p.description,
            "platform": p.platform.value if p.platform else None,
            "content_type": p.content_type,
            "deliverables_count": p.deliverables_count,
            "price": p.price,
            "currency": p.currency,
            "timeline_days": p.timeline_days,
            "revisions_included": p.revisions_included,
            "requirements": p.requirements,
            "exclusions": p.exclusions,
            "times_purchased": p.times_purchased,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in packages
    ]


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin", response_model=dict)
async def get_all_influencers_admin(
    query: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all influencers for admin dashboard."""
    base_query = db.query(InfluencerProfile)
    
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                InfluencerProfile.display_name.ilike(search_term),
                InfluencerProfile.bio.ilike(search_term),
                InfluencerProfile.niche.ilike(search_term),
            )
        )
    
    total = base_query.count()
    offset = (page - 1) * limit
    profiles = base_query.order_by(InfluencerProfile.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "influencers": [_profile_to_response(p) for p in profiles],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }


@router.get("/admin/pending", response_model=list)
async def get_pending_influencers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get list of influencers pending verification (Admin only)."""
    profiles = db.query(InfluencerProfile).filter(
        InfluencerProfile.verification_status == VerificationStatus.PENDING
    ).order_by(InfluencerProfile.created_at.desc()).all()
    
    return [_profile_to_response(p) for p in profiles]


@router.put("/admin/{influencer_id}/verify", response_model=InfluencerProfileResponse)
async def verify_influencer(
    influencer_id: str,
    action: str = Query(..., description="approve or reject"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Approve or reject an influencer's verification (Admin only)."""
    profile = db.query(InfluencerProfile).filter(
        or_(
            InfluencerProfile.id == influencer_id,
            InfluencerProfile.user_id == influencer_id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer not found"
        )
    
    if action == "approve":
        profile.verification_status = VerificationStatus.APPROVED
        profile.is_verified = True
        profile.identity_verified_at = datetime.utcnow()
    elif action == "reject":
        profile.verification_status = VerificationStatus.REJECTED
        profile.is_verified = False
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'"
        )
    
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    
    return _profile_to_response(profile)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _profile_to_response(profile: InfluencerProfile) -> InfluencerProfileResponse:
    """Convert database profile to response schema."""
    return InfluencerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        bio=profile.bio,
        profile_picture_url=profile.profile_picture_url,
        niche=profile.niche,
        location=profile.location,
        
        # Social media stats
        instagram=SocialMediaStats(
            handle=profile.instagram_handle,
            followers=profile.instagram_followers or 0,
            engagement_rate=profile.instagram_engagement_rate or 0.0,
            verified=profile.instagram_verified or False,
            connected_at=profile.instagram_connected_at,
        ) if profile.instagram_handle else None,
        
        tiktok=SocialMediaStats(
            handle=profile.tiktok_handle,
            followers=profile.tiktok_followers or 0,
            engagement_rate=profile.tiktok_engagement_rate or 0.0,
            verified=profile.tiktok_verified or False,
            connected_at=profile.tiktok_connected_at,
        ) if profile.tiktok_handle else None,
        
        youtube=SocialMediaStats(
            handle=profile.youtube_channel,
            followers=profile.youtube_subscribers or 0,
            engagement_rate=profile.youtube_engagement_rate or 0.0,
            verified=profile.youtube_verified or False,
            connected_at=profile.youtube_connected_at,
        ) if profile.youtube_channel else None,
        
        twitter=SocialMediaStats(
            handle=profile.twitter_handle,
            followers=profile.twitter_followers or 0,
            engagement_rate=profile.twitter_engagement_rate or 0.0,
            verified=profile.twitter_verified or False,
            connected_at=profile.twitter_connected_at,
        ) if profile.twitter_handle else None,
        
        facebook=SocialMediaStats(
            handle=profile.facebook_handle,
            followers=profile.facebook_followers or 0,
            engagement_rate=profile.facebook_engagement_rate or 0.0,
            verified=profile.facebook_verified or False,
            connected_at=profile.facebook_connected_at,
        ) if profile.facebook_handle else None,
        
        whatsapp_number=profile.whatsapp_number,
        
        # Social Media Links
        instagram_link=profile.instagram_link,
        tiktok_link=profile.tiktok_link,
        youtube_link=profile.youtube_link,
        twitter_link=profile.twitter_link,
        facebook_link=profile.facebook_link,
        
        # Reputation
        rating=profile.rating or 0.0,
        review_count=profile.review_count or 0,
        completed_campaigns=profile.completed_campaigns or 0,
        
        # Verification
        is_verified=profile.is_verified or False,
        verification_status=VerificationStatus(profile.verification_status.value) if profile.verification_status else VerificationStatus.PENDING,
        
        contact_email=profile.user.email if profile.user else None,
        
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
