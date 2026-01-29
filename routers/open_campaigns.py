"""
Open Campaigns Router
Handles brand-created campaigns with influencer bidding system.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta

from database.config import get_db
from database.models import User, Brand
from database.marketplace_models import (
    Campaign, CampaignStatusDB, Bid, BidStatusDB,
    InfluencerProfile, Package, Wallet, WalletTransaction,
    WalletTransactionTypeDB, WalletTransactionStatusDB,
    EscrowHold, EscrowStatusDB
)
from auth.dependencies import get_current_user
from auth.decorators import require_user_type
from auth.roles import UserType

router = APIRouter(prefix="/open-campaigns", tags=["Open Campaigns"])
MIN_CAMPAIGN_BUDGET = 100  # Minimum budget in cents (configurable)


# ============================================================================
# SCHEMAS
# ============================================================================

class CreateOpenCampaignRequest(BaseModel):
    brand_id: str = Field(..., description="ID of the brand entity")
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    budget: int = Field(..., gt=0, description="Budget in cents")
    platforms: List[str] = Field(default=["instagram"])
    content_types: List[str] = Field(default=["post"])
    deadline: Optional[datetime] = None
    requirements: Optional[str] = None
    
    # Content Generation Fields
    voice: Optional[str] = Field(None, description="Brand voice: professional, casual, playful, etc.")
    sample_tone: Optional[str] = Field(None, description="Example of desired writing style")
    key_messages: Optional[List[str]] = Field(None, description="Key messages to convey")
    hashtags: Optional[List[str]] = Field(None, description="Brand hashtags to use")
    target_audience: Optional[str] = Field(None, description="Who is the content for")
    content_style: Optional[str] = Field(None, description="educational, entertaining, inspirational, promotional")
    content_themes: Optional[List[str]] = Field(None, description="Themes like sustainability, innovation")
    product_name: Optional[str] = Field(None, description="Product or service being promoted")
    product_description: Optional[str] = Field(None, description="Description of the product")
    product_url: Optional[str] = Field(None, description="Link to product")
    content_dos: Optional[List[str]] = Field(None, description="Things to include in content")
    content_donts: Optional[List[str]] = Field(None, description="Things to avoid in content")


class SubmitBidRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Bid amount in cents")
    package_id: Optional[str] = None  # Use existing package
    deliverables_description: str = Field(..., min_length=10)
    deliverables_count: int = Field(default=1, ge=1)
    platform: str = Field(default="instagram")
    content_type: str = Field(default="post")
    timeline_days: int = Field(default=7, ge=1, le=90)
    proposal: str = Field(..., min_length=20, description="Cover letter")


class BidActionRequest(BaseModel):
    reason: Optional[str] = None


# ============================================================================
# BRAND ENDPOINTS - Create & Manage Open Campaigns
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_open_campaign(
    request: CreateOpenCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new open campaign for influencers to bid on."""

    if request.budget < MIN_CAMPAIGN_BUDGET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum budget is KES {MIN_CAMPAIGN_BUDGET / 100:.0f}"
        )
    
    # Verify brand ownership    
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found or you don't own it"
        )
    
    # Create campaign with content generation fields
    campaign = Campaign(
        brand_id=current_user.id,
        brand_entity_id=request.brand_id,
        title=request.title,
        description=request.description,
        budget=request.budget,
        budget_spent=0,
        platforms=request.platforms,
        content_types=request.content_types,
        deadline=request.deadline,
        custom_requirements=request.requirements,
        # Content generation fields
        voice=request.voice,
        sample_tone=request.sample_tone,
        key_messages=request.key_messages,
        hashtags=request.hashtags,
        target_audience=request.target_audience,
        content_style=request.content_style,
        content_themes=request.content_themes,
        product_name=request.product_name,
        product_description=request.product_description,
        product_url=request.product_url,
        content_dos=request.content_dos,
        content_donts=request.content_donts,
        status=CampaignStatusDB.OPEN
    )
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    return {
        "message": "Campaign created successfully",
        "campaign_id": campaign.id,
        "status": campaign.status.value
    }


@router.get("")
async def list_open_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None),
    min_budget: Optional[int] = Query(None),
    max_budget: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List open campaigns. Influencers see all open, Brands see their own."""
    
    query = db.query(Campaign).options(
        joinedload(Campaign.brand_entity),
        joinedload(Campaign.brand)
    )
    
    # Check if user is influencer
    influencer_profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if influencer_profile:
        # Influencers see all open campaigns
        query = query.filter(Campaign.status == CampaignStatusDB.OPEN)
    else:
        # Brands see their own campaigns
        query = query.filter(Campaign.brand_id == current_user.id)
        if status:
            query = query.filter(Campaign.status == status)
    
    # Filters
    if platform:
        query = query.filter(Campaign.platforms.contains([platform]))
    if min_budget:
        query = query.filter(Campaign.budget >= min_budget)
    if max_budget:
        query = query.filter(Campaign.budget <= max_budget)
    
    # Pagination
    total = query.count()
    campaigns = query.order_by(Campaign.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "campaigns": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "budget": c.budget,
                "budget_spent": c.budget_spent,
                "budget_remaining": c.budget - c.budget_spent,
                "platforms": c.platforms,
                "content_types": c.content_types,
                "deadline": c.deadline.isoformat() if c.deadline else None,
                "status": c.status.value,
                "brand": {
                    "id": c.brand_entity.id if c.brand_entity else None,
                    "name": c.brand_entity.name if c.brand_entity else c.brand.name,
                } if c.brand_entity or c.brand else None,
                "bids_count": len(c.bids) if hasattr(c, 'bids') else 0,
                "created_at": c.created_at.isoformat()
            }
            for c in campaigns
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{campaign_id}")
async def get_open_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of an open campaign."""
    
    campaign = db.query(Campaign).options(
        joinedload(Campaign.brand_entity),
        joinedload(Campaign.brand),
        joinedload(Campaign.bids).joinedload(Bid.influencer)
    ).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    is_owner = campaign.brand_id == current_user.id
    influencer_profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not is_owner and campaign.status != CampaignStatusDB.OPEN:
        raise HTTPException(status_code=403, detail="Campaign is not open")
    
    # Get user's bid if influencer
    user_bid = None
    if influencer_profile:
        user_bid = next(
            (b for b in campaign.bids if b.influencer_id == influencer_profile.id),
            None
        )
    
    return {
        "id": campaign.id,
        "title": campaign.title,
        "description": campaign.description,
        "budget": campaign.budget,
        "budget_spent": campaign.budget_spent,
        "budget_remaining": campaign.budget - campaign.budget_spent,
        "platforms": campaign.platforms,
        "content_types": campaign.content_types,
        "requirements": campaign.custom_requirements,
        "deadline": campaign.deadline.isoformat() if campaign.deadline else None,
        "status": campaign.status.value,
        "brand": {
            "id": campaign.brand_entity.id if campaign.brand_entity else None,
            "name": campaign.brand_entity.name if campaign.brand_entity else None,
        } if campaign.brand_entity else None,
        "is_owner": is_owner,
        "bids": [
            {
                "id": b.id,
                "amount": b.amount,
                "deliverables_description": b.deliverables_description,
                "deliverables_count": b.deliverables_count,
                "platform": b.platform,
                "content_type": b.content_type,
                "timeline_days": b.timeline_days,
                "proposal": b.proposal if is_owner else None,  # Only owner sees proposals
                "status": b.status.value,
                "influencer": {
                    "id": b.influencer.id,
                    "display_name": b.influencer.display_name,
                    "profile_picture_url": b.influencer.profile_picture_url,
                    "rating": b.influencer.rating,
                    "completed_campaigns": b.influencer.completed_campaigns,
                    "niche": b.influencer.niche
                } if b.influencer else None,
                "created_at": b.created_at.isoformat()
            }
            for b in campaign.bids
        ] if is_owner else [],
        "user_bid": {
            "id": user_bid.id,
            "amount": user_bid.amount,
            "status": user_bid.status.value,
            "proposal": user_bid.proposal,
            "created_at": user_bid.created_at.isoformat()
        } if user_bid else None,
        "bids_count": len(campaign.bids),
        "created_at": campaign.created_at.isoformat()
    }


@router.patch("/{campaign_id}/close")
async def close_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close a campaign to new bids."""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.brand_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatusDB.OPEN:
        raise HTTPException(status_code=400, detail="Campaign is not open")
    
    campaign.status = CampaignStatusDB.CLOSED
    db.commit()
    
    return {"message": "Campaign closed", "status": campaign.status.value}


# ============================================================================
# INFLUENCER ENDPOINTS - Submit Bids
# ============================================================================

@router.post("/{campaign_id}/bids", status_code=status.HTTP_201_CREATED)
async def submit_bid(
    campaign_id: str,
    request: SubmitBidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a bid on an open campaign."""
    
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only influencers can submit bids"
        )
    
    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatusDB.OPEN:
        raise HTTPException(status_code=400, detail="Campaign is not accepting bids")
    
    # Check if already bid
    existing_bid = db.query(Bid).filter(
        Bid.campaign_id == campaign_id,
        Bid.influencer_id == influencer.id,
        Bid.status == BidStatusDB.PENDING
    ).first()
    
    if existing_bid:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending bid on this campaign"
        )
    
    # Check budget
    budget_remaining = campaign.budget - campaign.budget_spent
    if request.amount > budget_remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Bid amount exceeds remaining budget of {budget_remaining}"
        )
    
    # Create bid
    bid = Bid(
        campaign_id=campaign_id,
        influencer_id=influencer.id,
        package_id=request.package_id,
        amount=request.amount,
        deliverables_description=request.deliverables_description,
        deliverables_count=request.deliverables_count,
        platform=request.platform,
        content_type=request.content_type,
        timeline_days=request.timeline_days,
        proposal=request.proposal,
        status=BidStatusDB.PENDING
    )
    
    db.add(bid)
    db.commit()
    db.refresh(bid)
    
    return {
        "message": "Bid submitted successfully",
        "bid_id": bid.id,
        "amount": bid.amount
    }


@router.delete("/{campaign_id}/bids/{bid_id}")
async def withdraw_bid(
    campaign_id: str,
    bid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Withdraw a pending bid."""
    
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(status_code=403, detail="Influencer profile required")
    
    bid = db.query(Bid).filter(
        Bid.id == bid_id,
        Bid.campaign_id == campaign_id,
        Bid.influencer_id == influencer.id
    ).first()
    
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(status_code=400, detail="Can only withdraw pending bids")
    
    bid.status = BidStatusDB.WITHDRAWN
    bid.withdrawn_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Bid withdrawn"}


# ============================================================================
# BRAND ENDPOINTS - Accept/Reject Bids
# ============================================================================

@router.post("/{campaign_id}/bids/{bid_id}/accept")
async def accept_bid(
    campaign_id: str,
    bid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a bid. Moves funds to escrow."""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.brand_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    bid = db.query(Bid).options(
        joinedload(Bid.influencer)
    ).filter(
        Bid.id == bid_id,
        Bid.campaign_id == campaign_id
    ).first()
    
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(status_code=400, detail="Bid is not pending")
    
    # Check budget
    budget_remaining = campaign.budget - campaign.budget_spent
    if bid.amount > budget_remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Bid amount exceeds remaining budget ({budget_remaining})"
        )
    
    # Get brand's wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found. Please set up your wallet.")
    
    if wallet.balance < bid.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Need {bid.amount}, have {wallet.balance}"
        )
    
    # Create escrow transaction
    transaction = WalletTransaction(
        from_wallet_id=wallet.id,
        amount=bid.amount,
        fee=0,
        net_amount=bid.amount,
        transaction_type=WalletTransactionTypeDB.ESCROW_LOCK,
        status=WalletTransactionStatusDB.COMPLETED,
        description=f"Escrow for campaign: {campaign.title}",
        completed_at=datetime.utcnow()
    )
    db.add(transaction)
    db.flush()
    
    # Create escrow hold
    escrow = EscrowHold(
        transaction_id=transaction.id,
        campaign_id=campaign.id,
        amount=bid.amount,
        status=EscrowStatusDB.LOCKED,
        auto_release_at=datetime.utcnow() + timedelta(days=14)
    )
    db.add(escrow)
    db.flush()
    
    # Update wallet
    wallet.balance -= bid.amount
    wallet.hold_balance += bid.amount
    
    # Update bid
    bid.status = BidStatusDB.ACCEPTED
    bid.accepted_at = datetime.utcnow()
    bid.escrow_id = escrow.id
    
    # Update campaign budget spent
    campaign.budget_spent += bid.amount
    
    db.commit()
    
    return {
        "message": "Bid accepted! Funds moved to escrow.",
        "bid_id": bid.id,
        "escrow_id": escrow.id,
        "amount": bid.amount,
        "budget_remaining": campaign.budget - campaign.budget_spent
    }


@router.post("/{campaign_id}/bids/{bid_id}/reject")
async def reject_bid(
    campaign_id: str,
    bid_id: str,
    request: BidActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a bid."""
    
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.brand_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    bid = db.query(Bid).filter(
        Bid.id == bid_id,
        Bid.campaign_id == campaign_id
    ).first()
    
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(status_code=400, detail="Bid is not pending")
    
    bid.status = BidStatusDB.REJECTED
    bid.rejected_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Bid rejected"}


@router.get("/my-bids")
async def get_my_bids(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get influencer's own bids."""
    
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(status_code=403, detail="Influencer profile required")
    
    query = db.query(Bid).options(
        joinedload(Bid.campaign).joinedload(Campaign.brand_entity)
    ).filter(Bid.influencer_id == influencer.id)
    
    if status:
        query = query.filter(Bid.status == status)
    
    total = query.count()
    bids = query.order_by(Bid.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "bids": [
            {
                "id": b.id,
                "amount": b.amount,
                "status": b.status.value,
                "platform": b.platform,
                "content_type": b.content_type,
                "timeline_days": b.timeline_days,
                "deliverables_description": b.deliverables_description,
                "proposal": b.proposal[:100] + "..." if len(b.proposal or "") > 100 else b.proposal,
                "campaign": {
                    "id": b.campaign.id,
                    "title": b.campaign.title,
                    "brand_name": b.campaign.brand_entity.name if b.campaign.brand_entity else "Unknown",
                    "budget": b.campaign.budget,
                    "status": b.campaign.status.value
                } if b.campaign else None,
                "created_at": b.created_at.isoformat()
            }
            for b in bids
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }
