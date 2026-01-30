"""
Bids Router
Handles influencer bids on open campaigns
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User
from database.marketplace_models import (
    Bid, BidStatusDB, Campaign, CampaignStatusDB,
    InfluencerProfile, Package, EscrowHold, Notification
)
from auth.dependencies import get_current_user
from schemas.marketplace import BidCreate, BidResponse, BidUpdate

router = APIRouter(prefix="/bids", tags=["bids"])


@router.post("", response_model=BidResponse, status_code=http_status.HTTP_201_CREATED)
async def create_bid(
    bid_data: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new bid on an open campaign.
    Influencer must attach a package or provide bid details.
    """
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You must have an influencer profile to place bids"
        )
    
    # Verify campaign exists and is open
    campaign = db.query(Campaign).filter(Campaign.id == bid_data.campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatusDB.OPEN:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not accepting bids"
        )
    
    # Check if already bid
    existing_bid = db.query(Bid).filter(
        Bid.campaign_id == bid_data.campaign_id,
        Bid.influencer_id == influencer.id,
        Bid.status == BidStatusDB.PENDING
    ).first()
    
    if existing_bid:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending bid on this campaign"
        )
    
    # If package_id provided, validate and use package details
    package = None
    if bid_data.package_id:
        package = db.query(Package).filter(
            Package.id == bid_data.package_id,
            Package.influencer_id == influencer.id,
            Package.status == "active"
        ).first()
        
        if not package:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Package not found or not active"
            )
    
    # Create bid
    bid = Bid(
        campaign_id=bid_data.campaign_id,
        influencer_id=influencer.id,
        package_id=bid_data.package_id,
        amount=bid_data.amount or (package.price if package else 0),
        deliverables_description=bid_data.deliverables_description or (package.description if package else ""),
        deliverables_count=bid_data.deliverables_count or (package.deliverables_count if package else 1),
        platform=bid_data.platform or (package.platform if package else ""),
        content_type=bid_data.content_type or (package.content_type if package else ""),
        timeline_days=bid_data.timeline_days or (package.timeline_days if package else 7),
        proposal=bid_data.proposal or "",
        status=BidStatusDB.PENDING
    )
    
    db.add(bid)
    
    # Create notification for brand
    notification = Notification(
        user_id=campaign.brand_id,
        type="new_bid",
        title="New Bid Received",
        message=f"{influencer.display_name} placed a bid on your campaign '{campaign.title}'",
        data={"campaign_id": campaign.id, "bid_id": bid.id}
    )
    db.add(notification)
    
    db.commit()
    db.refresh(bid)
    
    return _bid_to_response(bid, db)


@router.get("/my-bids", response_model=dict)
async def get_my_bids(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all bids placed by the current influencer."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        return {"bids": [], "pagination": {"page": 1, "limit": limit, "total": 0}}
    
    query = db.query(Bid).filter(Bid.influencer_id == influencer.id)
    
    if status:
        query = query.filter(Bid.status == status)
    
    total = query.count()
    offset = (page - 1) * limit
    
    bids = query.options(
        joinedload(Bid.campaign),
        joinedload(Bid.package),
        joinedload(Bid.influencer)
    ).order_by(Bid.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "bids": [_bid_to_response(bid, db) for bid in bids],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.get("/campaign/{campaign_id}", response_model=dict)
async def get_campaign_bids(
    campaign_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all bids for a campaign (brand owner only)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.brand_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You can only view bids on your own campaigns"
        )
    
    query = db.query(Bid).filter(Bid.campaign_id == campaign_id)
    total = query.count()
    offset = (page - 1) * limit
    
    bids = query.options(
        joinedload(Bid.influencer),
        joinedload(Bid.package)
    ).order_by(Bid.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "bids": [_bid_to_response(bid, db) for bid in bids],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.patch("/{bid_id}/accept", response_model=BidResponse)
async def accept_bid(
    bid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a bid (brand owner only). Creates campaign assignment."""
    bid = db.query(Bid).options(
        joinedload(Bid.campaign),
        joinedload(Bid.influencer)
    ).filter(Bid.id == bid_id).first()
    
    if not bid:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Bid not found"
        )
    
    if bid.campaign.brand_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only the campaign owner can accept bids"
        )
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Bid is not in pending status"
        )
    
    # Update bid
    bid.status = BidStatusDB.ACCEPTED
    bid.accepted_at = datetime.utcnow()
    
    # Update campaign
    bid.campaign.influencer_id = bid.influencer_id
    bid.campaign.package_id = bid.package_id
    bid.campaign.status = CampaignStatusDB.ACCEPTED
    
    # Reject other pending bids
    db.query(Bid).filter(
        Bid.campaign_id == bid.campaign_id,
        Bid.id != bid_id,
        Bid.status == BidStatusDB.PENDING
    ).update({"status": BidStatusDB.REJECTED, "rejected_at": datetime.utcnow()})
    
    # Create notification for influencer
    notification = Notification(
        user_id=bid.influencer.user_id,
        type="bid_accepted",
        title="Bid Accepted!",
        message=f"Your bid on '{bid.campaign.title}' has been accepted",
        data={"campaign_id": bid.campaign_id, "bid_id": bid.id}
    )
    db.add(notification)
    
    db.commit()
    db.refresh(bid)
    
    return _bid_to_response(bid, db)


@router.patch("/{bid_id}/reject", response_model=BidResponse)
async def reject_bid(
    bid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a bid (brand owner only)."""
    bid = db.query(Bid).options(
        joinedload(Bid.campaign),
        joinedload(Bid.influencer)
    ).filter(Bid.id == bid_id).first()
    
    if not bid:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Bid not found"
        )
    
    if bid.campaign.brand_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only the campaign owner can reject bids"
        )
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Bid is not in pending status"
        )
    
    bid.status = BidStatusDB.REJECTED
    bid.rejected_at = datetime.utcnow()
    
    # Notify influencer
    notification = Notification(
        user_id=bid.influencer.user_id,
        type="bid_rejected",
        title="Bid Not Selected",
        message=f"Your bid on '{bid.campaign.title}' was not selected",
        data={"campaign_id": bid.campaign_id, "bid_id": bid.id}
    )
    db.add(notification)
    
    db.commit()
    db.refresh(bid)
    
    return _bid_to_response(bid, db)


@router.delete("/{bid_id}")
async def withdraw_bid(
    bid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Withdraw a bid (influencer only)."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Influencer profile required"
        )
    
    bid = db.query(Bid).filter(
        Bid.id == bid_id,
        Bid.influencer_id == influencer.id
    ).first()
    
    if not bid:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Bid not found"
        )
    
    if bid.status != BidStatusDB.PENDING:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Can only withdraw pending bids"
        )
    
    bid.status = BidStatusDB.WITHDRAWN
    bid.withdrawn_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Bid withdrawn successfully"}


def _bid_to_response(bid: Bid, db: Session) -> dict:
    """Convert Bid model to response dict."""
    return {
        "id": bid.id,
        "campaign_id": bid.campaign_id,
        "campaign": {
            "id": bid.campaign.id,
            "title": bid.campaign.title,
            "description": bid.campaign.description,
            "budget": bid.campaign.budget,
            "status": bid.campaign.status.value if bid.campaign.status else None
        } if bid.campaign else None,
        "influencer_id": bid.influencer_id,
        "influencer": {
            "id": bid.influencer.id,
            "display_name": bid.influencer.display_name,
            "profile_picture_url": bid.influencer.profile_picture_url,
            "niche": bid.influencer.niche
        } if bid.influencer else None,
        "package_id": bid.package_id,
        "package": {
            "id": bid.package.id,
            "name": bid.package.name,
            "price": bid.package.price
        } if bid.package else None,
        "amount": bid.amount,
        "currency": bid.currency,
        "deliverables_description": bid.deliverables_description,
        "deliverables_count": bid.deliverables_count,
        "platform": bid.platform,
        "content_type": bid.content_type,
        "timeline_days": bid.timeline_days,
        "proposal": bid.proposal,
        "status": bid.status.value if bid.status else "pending",
        "accepted_at": bid.accepted_at,
        "rejected_at": bid.rejected_at,
        "withdrawn_at": bid.withdrawn_at,
        "created_at": bid.created_at,
        "updated_at": bid.updated_at
    }
