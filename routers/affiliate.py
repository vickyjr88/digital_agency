# Affiliate System Endpoints (for Influencers)

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import re

from database.models import User
from database.marketplace_models import InfluencerProfile
from database.affiliate_models import (
    Product,
    AffiliateApproval,
    AffiliateLink,
    AffiliateClick,
    BrandProfile
)
from schemas.affiliate import (
    AffiliateApprovalCreate,
    AffiliateApprovalResponse,
    AffiliateApprovalReview,
    AffiliateLinkResponse,
    SuccessResponse
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/affiliate", tags=["Affiliate System"])


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


def generate_affiliate_code(influencer_id: str, db: Session) -> str:
    """Generate unique affiliate code for influencer."""
    # Get influencer profile
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.id == influencer_id
    ).first()

    if not profile:
        raise ValueError("Influencer profile not found")

    # Try to use Instagram handle or display name
    base_name = profile.instagram_handle or profile.display_name
    # Clean it up
    cleaned = re.sub(r'[^A-Za-z0-9]', '', base_name).upper()[:10]

    # Add year
    year = datetime.now().year
    code = f"{cleaned}{year}"

    # Ensure uniqueness
    counter = 1
    original_code = code
    while db.query(AffiliateLink).filter(AffiliateLink.affiliate_code == code).first():
        code = f"{original_code}_{counter}"
        counter += 1

    return code


# ============================================================================
# AFFILIATE APPLICATIONS (Influencers applying to promote products)
# ============================================================================

@router.post("/apply", response_model=AffiliateApprovalResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_promote_product(
    application: AffiliateApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Influencer applies to promote a product.
    May be auto-approved based on product settings.
    """
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile required. Complete your profile first."
        )

    # Get product
    product = db.query(Product).filter(
        Product.id == application.product_id,
        Product.status == "active"
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available"
        )

    # Check if already applied
    existing = db.query(AffiliateApproval).filter(
        AffiliateApproval.influencer_id == influencer.id,
        AffiliateApproval.product_id == application.product_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already applied. Status: {existing.status}"
        )

    # Determine if auto-approve
    approval_status = "pending"

    if product.auto_approve:
        # Check criteria
        criteria = product.approval_criteria or {}
        meets_criteria = True

        if criteria.get('min_followers'):
            total_followers = (
                (influencer.instagram_followers or 0) +
                (influencer.tiktok_followers or 0) +
                (influencer.youtube_subscribers or 0)
            )
            if total_followers < criteria['min_followers']:
                meets_criteria = False

        if criteria.get('min_engagement_rate'):
            avg_engagement = (
                (influencer.instagram_engagement_rate or 0) +
                (influencer.tiktok_engagement_rate or 0)
            ) / 2
            if avg_engagement < criteria['min_engagement_rate']:
                meets_criteria = False

        if criteria.get('min_rating'):
            if (influencer.rating or 0) < criteria['min_rating']:
                meets_criteria = False

        if meets_criteria:
            approval_status = "approved"

    # Create application
    new_approval = AffiliateApproval(
        id=generate_uuid(),
        influencer_id=influencer.id,
        product_id=application.product_id,
        status=approval_status,
        application_message=application.application_message,
        application_data=application.application_data,
        approved_at=datetime.utcnow() if approval_status == "approved" else None
    )

    db.add(new_approval)

    # If auto-approved, generate affiliate link immediately
    if approval_status == "approved":
        try:
            affiliate_code = generate_affiliate_code(influencer.id, db)
            link_url = f"https://dexter.vitaldigitalmedia.net/shop/p/{product.slug}?ref={affiliate_code}"

            affiliate_link = AffiliateLink(
                id=generate_uuid(),
                influencer_id=influencer.id,
                product_id=product.id,
                affiliate_code=affiliate_code,
                link_url=link_url
            )
            db.add(affiliate_link)

            # Update product affiliates count
            product.active_affiliates_count = (product.active_affiliates_count or 0) + 1

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate affiliate link: {str(e)}"
            )

    try:
        db.commit()
        db.refresh(new_approval)
        return new_approval
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to submit application: {str(e)}"
        )


@router.get("/applications", response_model=List[AffiliateApprovalResponse])
async def get_my_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all applications submitted by current influencer."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        return []

    query = db.query(AffiliateApproval).filter(
        AffiliateApproval.influencer_id == influencer.id
    )

    if status:
        query = query.filter(AffiliateApproval.status == status)

    return query.order_by(AffiliateApproval.created_at.desc()).all()


@router.put("/applications/{approval_id}/review", response_model=AffiliateApprovalResponse)
async def review_affiliate_application(
    approval_id: str,
    review: AffiliateApprovalReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Brand reviews and approves/rejects affiliate application.
    Only brand that owns the product can review.
    """
    # Get brand profile
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Brand profile required."
        )

    # Get application
    approval = db.query(AffiliateApproval).filter(
        AffiliateApproval.id == approval_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Verify brand owns the product
    product = db.query(Product).filter(
        Product.id == approval.product_id,
        Product.brand_profile_id == brand_profile.id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to review this application"
        )

    # Update approval
    approval.status = review.status
    approval.reviewed_at = datetime.utcnow()
    approval.reviewed_by = current_user.id
    approval.rejection_reason = review.rejection_reason

    if review.status == "approved":
        approval.approved_at = datetime.utcnow()

        # Generate affiliate link
        try:
            affiliate_code = generate_affiliate_code(approval.influencer_id, db)
            link_url = f"https://dexter.vitaldigitalmedia.net/shop/p/{product.slug}?ref={affiliate_code}"

            affiliate_link = AffiliateLink(
                id=generate_uuid(),
                influencer_id=approval.influencer_id,
                product_id=product.id,
                affiliate_code=affiliate_code,
                link_url=link_url
            )
            db.add(affiliate_link)

            # Update product affiliates count
            product.active_affiliates_count = (product.active_affiliates_count or 0) + 1

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate affiliate link: {str(e)}"
            )

    try:
        db.commit()
        db.refresh(approval)
        return approval
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to review application: {str(e)}"
        )


# ============================================================================
# AFFILIATE LINKS
# ============================================================================

@router.get("/links", response_model=List[AffiliateLinkResponse])
async def get_my_affiliate_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all affiliate links for current influencer."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        return []

    links = db.query(AffiliateLink).filter(
        AffiliateLink.influencer_id == influencer.id
    ).order_by(AffiliateLink.generated_at.desc()).all()

    return links


@router.get("/links/{product_id}", response_model=AffiliateLinkResponse)
async def get_affiliate_link_for_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get affiliate link for a specific product."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Influencer profile required"
        )

    link = db.query(AffiliateLink).filter(
        AffiliateLink.influencer_id == influencer.id,
        AffiliateLink.product_id == product_id
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate link not found. Apply to promote this product first."
        )

    return link


# ============================================================================
# CLICK TRACKING
# ============================================================================

@router.get("/track-click")
async def track_affiliate_click(
    ref: str,
    product_slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Track affiliate link click.
    Called when customer clicks affiliate link.
    Sets cookie for attribution.
    """
    # Get affiliate link
    affiliate_link = db.query(AffiliateLink).filter(
        AffiliateLink.affiliate_code == ref
    ).first()

    if not affiliate_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid affiliate code"
        )

    # Get product
    product = db.query(Product).filter(
        Product.slug == product_slug
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Record click
    click = AffiliateClick(
        id=generate_uuid(),
        affiliate_link_id=affiliate_link.id,
        influencer_id=affiliate_link.influencer_id,
        product_id=product.id,
        ip_address=request.client.host,
        user_agent=request.headers.get('user-agent'),
        referrer=request.headers.get('referer')
    )

    # Update link stats
    affiliate_link.clicks += 1
    affiliate_link.last_clicked_at = datetime.utcnow()

    # Update product stats
    product.total_clicks += 1

    try:
        db.add(click)
        db.commit()

        return SuccessResponse(
            success=True,
            message="Click tracked",
            data={
                "affiliate_code": ref,
                "product_slug": product_slug,
                "click_id": click.id
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track click: {str(e)}"
        )


@router.get("/pending-approvals", response_model=List[AffiliateApprovalResponse])
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pending affiliate applications for brand's products.
    Brand endpoint.
    """
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        return []

    # Get all product IDs for this brand
    product_ids = db.query(Product.id).filter(
        Product.brand_profile_id == brand_profile.id
    ).all()
    product_ids = [p[0] for p in product_ids]

    # Get pending approvals for these products
    approvals = db.query(AffiliateApproval).filter(
        AffiliateApproval.product_id.in_(product_ids),
        AffiliateApproval.status == "pending"
    ).order_by(AffiliateApproval.applied_at.desc()).all()

    return approvals
