# Reviews Router for Dexter Marketplace
# Handles reviews and ratings for completed campaigns

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User, UserType
from database.marketplace_models import (
    Review, Campaign, InfluencerProfile,
    CampaignStatusDB
)
from schemas.marketplace import (
    ReviewCreate,
    ReviewResponse,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type, AuthError

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ============================================================================
# REVIEW ENDPOINTS
# ============================================================================

@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Create a review for a completed campaign.
    Both brands and influencers can leave reviews for each other.
    """
    # Get the campaign
    campaign = db.query(Campaign).filter(Campaign.id == review_data.campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Verify campaign is completed
    if campaign.status != CampaignStatusDB.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only review completed campaigns")
    
    # Determine reviewer and reviewee
    is_brand = campaign.brand_id == current_user.id
    
    if is_brand:
        reviewer_id = current_user.id
        # Get influencer user ID
        influencer = db.query(InfluencerProfile).filter(
            InfluencerProfile.id == campaign.influencer_id
        ).first()
        if not influencer:
            raise HTTPException(status_code=404, detail="Influencer not found")
        reviewee_id = influencer.user_id
    else:
        # Get influencer profile to verify access
        profile = db.query(InfluencerProfile).filter(
            InfluencerProfile.user_id == current_user.id
        ).first()
        if not profile or profile.id != campaign.influencer_id:
            raise HTTPException(status_code=403, detail="You cannot review this campaign")
        
        reviewer_id = current_user.id
        reviewee_id = campaign.brand_id
    
    # Check if already reviewed
    existing = db.query(Review).filter(
        Review.campaign_id == review_data.campaign_id,
        Review.reviewer_id == reviewer_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this campaign")
    
    # Create review
    review = Review(
        campaign_id=review_data.campaign_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(review)
    
    # Update reviewee's rating
    _update_user_rating(reviewee_id, db)
    
    db.commit()
    db.refresh(review)
    
    return _review_to_response(review, db)


@router.get("/user/{user_id}", response_model=dict)
async def get_user_reviews(
    user_id: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get reviews for a user (public endpoint).
    """
    query = db.query(Review).filter(Review.reviewee_id == user_id)
    
    total = query.count()
    
    offset = (page - 1) * limit
    reviews = query.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
    
    # Calculate average rating
    avg_rating = db.query(func.avg(Review.rating)).filter(
        Review.reviewee_id == user_id
    ).scalar() or 0.0
    
    return {
        "reviews": [_review_to_response(r, db) for r in reviews],
        "average_rating": round(float(avg_rating), 2),
        "total_reviews": total,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.get("/influencer/{influencer_id}", response_model=dict)
async def get_influencer_reviews(
    influencer_id: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get reviews for an influencer profile (public endpoint).
    """
    influencer = db.query(InfluencerProfile).filter(
        or_(
            InfluencerProfile.id == influencer_id,
            InfluencerProfile.user_id == influencer_id
        )
    ).first()
    
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")
    
    return await get_user_reviews(influencer.user_id, db, page, limit)


@router.post("/{review_id}/respond")
async def respond_to_review(
    review_id: str,
    response: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Respond to a review you received.
    """
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.reviewee_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or you cannot respond")
    
    if review.response:
        raise HTTPException(status_code=400, detail="You have already responded to this review")
    
    review.response = response
    review.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(review)
    
    return {"status": "success", "message": "Response added to review"}


@router.get("/campaign/{campaign_id}", response_model=List[ReviewResponse])
async def get_campaign_reviews(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get reviews for a specific campaign.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Verify access
    has_access = (
        campaign.brand_id == current_user.id or
        current_user.user_type == UserType.ADMIN
    )
    
    if not has_access:
        profile = db.query(InfluencerProfile).filter(
            InfluencerProfile.user_id == current_user.id
        ).first()
        if profile and profile.id == campaign.influencer_id:
            has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    reviews = db.query(Review).filter(Review.campaign_id == campaign_id).all()
    
    return [_review_to_response(r, db) for r in reviews]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _update_user_rating(user_id: str, db: Session):
    """Update user's average rating after new review."""
    # Calculate new average
    avg_rating = db.query(func.avg(Review.rating)).filter(
        Review.reviewee_id == user_id
    ).scalar() or 0.0
    
    review_count = db.query(Review).filter(
        Review.reviewee_id == user_id
    ).count()
    
    # Update influencer profile if exists
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == user_id
    ).first()
    
    if profile:
        profile.rating = round(float(avg_rating), 2)
        profile.review_count = review_count


def _review_to_response(review: Review, db: Session) -> ReviewResponse:
    """Convert review to response."""
    reviewer = db.query(User).filter(User.id == review.reviewer_id).first()
    
    return ReviewResponse(
        id=review.id,
        campaign_id=review.campaign_id,
        reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id,
        rating=review.rating,
        comment=review.comment,
        response=review.response,
        created_at=review.created_at,
        reviewer_name=reviewer.name if reviewer else None
    )
