# Disputes Router for Dexter Marketplace
# Handles dispute resolution for campaigns

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User, UserType
from database.marketplace_models import (
    Dispute, Campaign, EscrowHold, Wallet, WalletTransaction,
    DisputeStatusDB, CampaignStatusDB, EscrowStatusDB,
    WalletTransactionTypeDB, WalletTransactionStatusDB,
    InfluencerProfile
)
from schemas.marketplace import (
    DisputeCreate,
    DisputeResponse,
    DisputeResolve,
    DisputeStatus,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type

router = APIRouter(prefix="/disputes", tags=["Disputes"])


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@router.get("", response_model=List[DisputeResponse])
async def get_my_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN)),
    status_filter: Optional[DisputeStatus] = Query(None, description="Filter by status"),
):
    """
    Get disputes related to the current user.
    """
    # Get user's campaigns
    if current_user.user_type == UserType.ADMIN:
        query = db.query(Dispute)
    else:
        # Get campaigns where user is brand
        brand_campaigns = db.query(Campaign.id).filter(
            Campaign.brand_id == current_user.id
        ).subquery()
        
        # Get campaigns where user is influencer
        profile = db.query(InfluencerProfile).filter(
            InfluencerProfile.user_id == current_user.id
        ).first()
        
        if profile:
            influencer_campaigns = db.query(Campaign.id).filter(
                Campaign.influencer_id == profile.id
            ).subquery()
            
            query = db.query(Dispute).filter(
                Dispute.campaign_id.in_(brand_campaigns) |
                Dispute.campaign_id.in_(influencer_campaigns)
            )
        else:
            query = db.query(Dispute).filter(
                Dispute.campaign_id.in_(brand_campaigns)
            )
    
    if status_filter:
        query = query.filter(Dispute.status == status_filter.value)
    
    disputes = query.order_by(Dispute.created_at.desc()).all()
    
    return [_dispute_to_response(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get dispute details.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    # Verify access
    if current_user.user_type != UserType.ADMIN:
        campaign = db.query(Campaign).filter(Campaign.id == dispute.campaign_id).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        has_access = campaign.brand_id == current_user.id
        
        if not has_access:
            profile = db.query(InfluencerProfile).filter(
                InfluencerProfile.user_id == current_user.id
            ).first()
            has_access = profile and profile.id == campaign.influencer_id
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return _dispute_to_response(dispute)


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin/all", response_model=dict)
async def get_all_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN)),
    status_filter: Optional[DisputeStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get all disputes (Admin only).
    """
    query = db.query(Dispute)
    
    if status_filter:
        query = query.filter(Dispute.status == status_filter.value)
    
    total = query.count()
    
    offset = (page - 1) * limit
    disputes = query.order_by(Dispute.created_at.desc()).offset(offset).limit(limit).all()
    
    # Enrich with campaign and user info
    result = []
    for d in disputes:
        campaign = db.query(Campaign).filter(Campaign.id == d.campaign_id).first()
        raiser = db.query(User).filter(User.id == d.raised_by).first()
        
        dispute_data = _dispute_to_response(d).model_dump()
        dispute_data["campaign_status"] = campaign.status.value if campaign else None
        dispute_data["raiser_name"] = raiser.name if raiser else None
        dispute_data["raiser_email"] = raiser.email if raiser else None
        
        result.append(dispute_data)
    
    return {
        "disputes": result,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.put("/admin/{dispute_id}/review")
async def start_review(
    dispute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Mark a dispute as under review (Admin only).
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    if dispute.status != DisputeStatusDB.OPEN:
        raise HTTPException(status_code=400, detail="Dispute is not in open state")
    
    dispute.status = DisputeStatusDB.UNDER_REVIEW
    dispute.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "under_review", "message": "Dispute is now under review"}


@router.post("/admin/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    resolution_data: DisputeResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Resolve a dispute (Admin only).
    Handles partial or full refund/release of escrow.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    if dispute.status in [DisputeStatusDB.RESOLVED, DisputeStatusDB.CLOSED]:
        raise HTTPException(status_code=400, detail="Dispute is already resolved")
    
    # Get campaign and escrow
    campaign = db.query(Campaign).filter(Campaign.id == dispute.campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Verify resolved_in_favor_of is valid
    valid_user_ids = [campaign.brand_id]
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.id == campaign.influencer_id
    ).first()
    if influencer:
        valid_user_ids.append(influencer.user_id)
    
    if resolution_data.resolved_in_favor_of not in valid_user_ids:
        raise HTTPException(status_code=400, detail="Invalid user for resolution")
    
    # Process escrow based on resolution
    if campaign.escrow_id:
        escrow = db.query(EscrowHold).filter(EscrowHold.id == campaign.escrow_id).first()
        
        if escrow and escrow.status == EscrowStatusDB.DISPUTED:
            brand_wallet = db.query(Wallet).filter(Wallet.user_id == campaign.brand_id).first()
            influencer_wallet = None
            if influencer:
                influencer_wallet = db.query(Wallet).filter(
                    Wallet.user_id == influencer.user_id
                ).first()
            
            refund_amount = int(escrow.amount * resolution_data.refund_percentage / 100)
            release_amount = escrow.amount - refund_amount
            
            # Release hold from brand
            if brand_wallet:
                brand_wallet.hold_balance -= escrow.amount
            
            # Refund to brand if any
            if refund_amount > 0 and brand_wallet:
                refund_tx = WalletTransaction(
                    to_wallet_id=brand_wallet.id,
                    amount=refund_amount,
                    fee=0,
                    net_amount=refund_amount,
                    transaction_type=WalletTransactionTypeDB.ESCROW_REFUND,
                    status=WalletTransactionStatusDB.COMPLETED,
                    description=f"Partial refund from dispute {dispute_id}",
                    completed_at=datetime.utcnow()
                )
                db.add(refund_tx)
            
            # Pay influencer if any
            if release_amount > 0 and influencer_wallet:
                platform_fee = int(release_amount * 10 / 100)  # 10% fee
                net_release = release_amount - platform_fee
                
                influencer_wallet.balance += net_release
                influencer_wallet.total_earned += net_release
                
                release_tx = WalletTransaction(
                    from_wallet_id=brand_wallet.id if brand_wallet else None,
                    to_wallet_id=influencer_wallet.id,
                    amount=release_amount,
                    fee=platform_fee,
                    net_amount=net_release,
                    transaction_type=WalletTransactionTypeDB.ESCROW_RELEASE,
                    status=WalletTransactionStatusDB.COMPLETED,
                    description=f"Partial release from dispute {dispute_id}",
                    completed_at=datetime.utcnow()
                )
                db.add(release_tx)
            
            # Update escrow status
            if resolution_data.refund_percentage == 100:
                escrow.status = EscrowStatusDB.REFUNDED
            else:
                escrow.status = EscrowStatusDB.RELEASED
            escrow.released_at = datetime.utcnow()
    
    # Update dispute
    dispute.status = DisputeStatusDB.RESOLVED
    dispute.resolution = resolution_data.resolution
    dispute.resolved_in_favor_of = resolution_data.resolved_in_favor_of
    dispute.resolved_by = current_user.id
    dispute.resolved_at = datetime.utcnow()
    dispute.updated_at = datetime.utcnow()
    
    # Update campaign status
    if resolution_data.refund_percentage == 100:
        campaign.status = CampaignStatusDB.CANCELLED
    else:
        campaign.status = CampaignStatusDB.COMPLETED
    campaign.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "status": "resolved",
        "message": f"Dispute resolved. {resolution_data.refund_percentage}% refunded to brand, {100 - resolution_data.refund_percentage}% released to influencer."
    }


@router.post("/admin/{dispute_id}/close")
async def close_dispute(
    dispute_id: str,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Close a dispute without resolution (Admin only).
    Used for invalid or withdrawn disputes.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    dispute.status = DisputeStatusDB.CLOSED
    dispute.resolution = f"Closed: {reason}"
    dispute.resolved_by = current_user.id
    dispute.resolved_at = datetime.utcnow()
    dispute.updated_at = datetime.utcnow()
    
    # Revert campaign status if needed
    campaign = db.query(Campaign).filter(Campaign.id == dispute.campaign_id).first()
    if campaign and campaign.status == CampaignStatusDB.DISPUTED:
        # Revert to previous status (default to PUBLISHED as safe state)
        if campaign.published_at:
            campaign.status = CampaignStatusDB.PUBLISHED
        elif campaign.started_at:
            campaign.status = CampaignStatusDB.IN_PROGRESS
        else:
            campaign.status = CampaignStatusDB.PENDING
        
        # Revert escrow status
        if campaign.escrow_id:
            escrow = db.query(EscrowHold).filter(EscrowHold.id == campaign.escrow_id).first()
            if escrow and escrow.status == EscrowStatusDB.DISPUTED:
                escrow.status = EscrowStatusDB.LOCKED
    
    db.commit()
    
    return {"status": "closed", "message": "Dispute closed"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _dispute_to_response(dispute: Dispute) -> DisputeResponse:
    """Convert dispute to response."""
    return DisputeResponse(
        id=dispute.id,
        campaign_id=dispute.campaign_id,
        raised_by=dispute.raised_by,
        reason=dispute.reason,
        evidence_urls=dispute.evidence_urls or [],
        status=DisputeStatus(dispute.status.value),
        resolution=dispute.resolution,
        resolved_in_favor_of=dispute.resolved_in_favor_of,
        resolved_by=dispute.resolved_by,
        resolved_at=dispute.resolved_at,
        created_at=dispute.created_at
    )
