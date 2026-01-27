# Packages Router for Dexter Marketplace
# Handles package CRUD operations for influencers

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User
from database.marketplace_models import InfluencerProfile, Package, PackageStatusDB
from schemas.marketplace import (
    PackageCreate,
    PackageUpdate,
    PackageResponse,
    PackageStatus,
    PlatformType,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type, AuthError

router = APIRouter(prefix="/packages", tags=["Packages"])


# ============================================================================
# INFLUENCER ENDPOINTS (Create/Manage Own Packages)
# ============================================================================

@router.post("", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    package_data: PackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Create a new package. Influencers can create packages to offer their services.
    """
    # Get influencer profile
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your influencer profile first"
        )
    
    # Create package
    package = Package(
        influencer_id=profile.id,
        name=package_data.name,
        description=package_data.description,
        platform=PackageStatusDB(package_data.platform.value) if package_data.platform else None,
        content_type=package_data.content_type.value,
        deliverables_count=package_data.deliverables_count,
        price=package_data.price,
        currency="KES",  # Default to KES for now
        timeline_days=package_data.timeline_days,
        revisions_included=package_data.revisions_included,
        requirements=package_data.requirements.model_dump() if package_data.requirements else None,
        exclusions=package_data.exclusions,
        status=PackageStatusDB.ACTIVE,
    )
    
    db.add(package)
    db.commit()
    db.refresh(package)
    
    return _package_to_response(package, profile)


@router.get("/mine", response_model=List[PackageResponse])
async def get_my_packages(
    status_filter: Optional[PackageStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get all packages owned by the current influencer.
    """
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile not found"
        )
    
    query = db.query(Package).filter(Package.influencer_id == profile.id)
    
    if status_filter:
        query = query.filter(Package.status == status_filter.value)
    else:
        # Exclude deleted by default
        query = query.filter(Package.status != PackageStatusDB.DELETED)
    
    packages = query.order_by(Package.created_at.desc()).all()
    
    return [_package_to_response(p, profile) for p in packages]


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: str,
    db: Session = Depends(get_db),
):
    """
    Get package details by ID. Public endpoint.
    """
    package = db.query(Package).filter(
        Package.id == package_id,
        Package.status != PackageStatusDB.DELETED
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.id == package.influencer_id
    ).first()
    
    return _package_to_response(package, profile)


@router.put("/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: str,
    package_data: PackageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Update a package. Only the package owner can update.
    """
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile not found"
        )
    
    package = db.query(Package).filter(
        Package.id == package_id,
        Package.influencer_id == profile.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found or you don't have permission to edit"
        )
    
    # Update only provided fields
    update_data = package_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "status" and value:
            value = PackageStatusDB(value.value)
        elif field == "requirements" and value:
            value = value.model_dump() if hasattr(value, 'model_dump') else value
        setattr(package, field, value)
    
    package.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(package)
    
    return _package_to_response(package, profile)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    package_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Soft delete a package. Sets status to 'deleted'.
    """
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile not found"
        )
    
    package = db.query(Package).filter(
        Package.id == package_id,
        Package.influencer_id == profile.id
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found or you don't have permission to delete"
        )
    
    # Soft delete
    package.status = PackageStatusDB.DELETED
    package.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


@router.post("/{package_id}/pause", response_model=PackageResponse)
async def pause_package(
    package_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Pause a package. It won't be visible in marketplace but can be reactivated.
    """
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile not found"
        )
    
    package = db.query(Package).filter(
        Package.id == package_id,
        Package.influencer_id == profile.id,
        Package.status == PackageStatusDB.ACTIVE
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active package not found or you don't have permission"
        )
    
    package.status = PackageStatusDB.PAUSED
    package.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(package)
    
    return _package_to_response(package, profile)


@router.post("/{package_id}/activate", response_model=PackageResponse)
async def activate_package(
    package_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Activate a paused package.
    """
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile not found"
        )
    
    package = db.query(Package).filter(
        Package.id == package_id,
        Package.influencer_id == profile.id,
        Package.status == PackageStatusDB.PAUSED
    ).first()
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paused package not found or you don't have permission"
        )
    
    package.status = PackageStatusDB.ACTIVE
    package.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(package)
    
    return _package_to_response(package, profile)


# ============================================================================
# MARKETPLACE ENDPOINTS (Browse Packages)
# ============================================================================

@router.get("", response_model=dict)
async def browse_packages(
    db: Session = Depends(get_db),
    query: Optional[str] = Query(None, description="Search query"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[int] = Query(None, description="Maximum price"),
    min_deliverables: Optional[int] = Query(None, ge=1, description="Minimum deliverables"),
    max_timeline: Optional[int] = Query(None, ge=1, description="Maximum days to complete"),
    sort_by: str = Query("popular", description="Sort by: popular, price_low, price_high, newest"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """
    Browse and search packages in the marketplace.
    Returns paginated list of active packages.
    """
    # Base query - only active packages
    base_query = db.query(Package).filter(Package.status == PackageStatusDB.ACTIVE)
    
    # Apply search
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                Package.name.ilike(search_term),
                Package.description.ilike(search_term),
            )
        )
    
    # Apply filters
    if platform:
        base_query = base_query.filter(Package.platform == platform.value)
    
    if content_type:
        base_query = base_query.filter(Package.content_type == content_type)
    
    if min_price is not None:
        base_query = base_query.filter(Package.price >= min_price)
    
    if max_price is not None:
        base_query = base_query.filter(Package.price <= max_price)
    
    if min_deliverables is not None:
        base_query = base_query.filter(Package.deliverables_count >= min_deliverables)
    
    if max_timeline is not None:
        base_query = base_query.filter(Package.timeline_days <= max_timeline)
    
    # Apply sorting
    if sort_by == "popular":
        base_query = base_query.order_by(Package.times_purchased.desc())
    elif sort_by == "price_low":
        base_query = base_query.order_by(Package.price.asc())
    elif sort_by == "price_high":
        base_query = base_query.order_by(Package.price.desc())
    elif sort_by == "newest":
        base_query = base_query.order_by(Package.created_at.desc())
    
    # Get total count
    total = base_query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    packages = base_query.offset(offset).limit(limit).all()
    
    # Get influencer profiles for packages
    influencer_ids = list(set(p.influencer_id for p in packages))
    profiles = db.query(InfluencerProfile).filter(
        InfluencerProfile.id.in_(influencer_ids)
    ).all()
    profiles_map = {p.id: p for p in profiles}
    
    results = []
    for package in packages:
        profile = profiles_map.get(package.influencer_id)
        results.append(_package_to_response(package, profile))
    
    return {
        "packages": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _package_to_response(package: Package, profile: Optional[InfluencerProfile] = None) -> PackageResponse:
    """Convert database package to response schema."""
    from routers.influencers import _profile_to_response
    
    return PackageResponse(
        id=package.id,
        influencer_id=package.influencer_id,
        name=package.name,
        description=package.description,
        platform=PlatformType(package.platform.value) if package.platform else PlatformType.MULTI,
        content_type=package.content_type,
        deliverables_count=package.deliverables_count,
        price=package.price,
        currency=package.currency or "KES",
        timeline_days=package.timeline_days,
        revisions_included=package.revisions_included,
        requirements=package.requirements,
        exclusions=package.exclusions,
        status=PackageStatus(package.status.value) if package.status else PackageStatus.ACTIVE,
        times_purchased=package.times_purchased or 0,
        created_at=package.created_at,
        updated_at=package.updated_at,
        influencer=_profile_to_response(profile) if profile else None,
    )
