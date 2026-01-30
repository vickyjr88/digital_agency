# Campaigns Router for Dexter Marketplace
# Handles the complete campaign lifecycle between brands and influencers

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime, timedelta

from auth.dependencies import get_optional_current_user

from database.config import get_db
from database.models import User, UserType, Brand
from database.marketplace_models import (
    InfluencerProfile, Package, Campaign, Deliverable, Wallet, 
    WalletTransaction, EscrowHold,
    CampaignStatusDB, DeliverableStatusDB, PackageStatusDB,
    WalletTransactionTypeDB, WalletTransactionStatusDB, EscrowStatusDB
)
from schemas.marketplace import (
    CampaignCreate,
    CampaignResponse,
    CampaignBrief,
    CampaignStatus,
    DeliverableSubmit,
    DeliverableResponse,
    DeliverableStatus,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type, AuthError
from services.notification_service import get_notification_service, NotificationType

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

from config.app_config import PLATFORM_FEE_PERCENT, ESCROW_AUTO_RELEASE_DAYS


# ============================================================================
# BRAND ENDPOINTS (Create & Manage Campaigns)
# ============================================================================

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Create a new campaign by purchasing a package.
    This locks funds in escrow.
    """
    # Get the package
    package = db.query(Package).filter(
        Package.id == campaign_data.package_id,
        Package.status == PackageStatusDB.ACTIVE
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found or not available")

    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.id == package.influencer_id
    ).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")

    # Validate Brand Ownership if brand identifier provided
    if campaign_data.brand_entity_id:
        brand_entity = db.query(Brand).filter(Brand.id == campaign_data.brand_entity_id).first()
        if not brand_entity:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        # Check ownership (unless admin)
        is_admin = False
        if hasattr(current_user, 'user_type'):
             # Handle both string "admin" and Enum UserTypeRole.ADMIN
             if current_user.user_type == UserTypeRole.ADMIN or str(current_user.user_type).lower() == 'admin':
                 is_admin = True
        
        if not is_admin and brand_entity.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only create campaigns for brands you own.")

    # Get buyer's wallet (Brand or Influencer acting as buyer)
    brand_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not brand_wallet:
        raise HTTPException(
            status_code=400, 
            detail="Please set up your wallet and deposit funds first"
        )
    
    # Check available balance
    available = brand_wallet.balance - brand_wallet.hold_balance
    if available < package.price:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. Required: KES {package.price / 100}, Available: KES {available / 100}"
        )
    
    # Create escrow lock transaction
    escrow_tx = WalletTransaction(
        from_wallet_id=brand_wallet.id,
        amount=package.price,
        fee=0,
        net_amount=package.price,
        transaction_type=WalletTransactionTypeDB.ESCROW_LOCK,
        status=WalletTransactionStatusDB.COMPLETED,
        description=f"Escrow for package: {package.name}",
        completed_at=datetime.utcnow()
    )
    db.add(escrow_tx)
    db.flush()  # Get the transaction ID
    
    # Create escrow hold
    escrow = EscrowHold(
        transaction_id=escrow_tx.id,
        amount=package.price,
        status=EscrowStatusDB.LOCKED,
        auto_release_at=datetime.utcnow() + timedelta(days=ESCROW_AUTO_RELEASE_DAYS + package.timeline_days)
    )
    db.add(escrow)
    db.flush()
    
    # Update wallet balances
    brand_wallet.hold_balance += package.price
    
    # Calculate deadline
    deadline = datetime.utcnow() + timedelta(days=package.timeline_days)
    
    # Create campaign
    campaign = Campaign(
        brand_id=current_user.id,
        brand_entity_id=campaign_data.brand_entity_id,
        influencer_id=influencer.id,
        package_id=package.id,
        escrow_id=escrow.id,
        brief=campaign_data.brief.model_dump() if campaign_data.brief else None,
        custom_requirements=campaign_data.custom_requirements,
        status=CampaignStatusDB.PENDING,
        deadline=deadline,
        revisions_allowed=package.revisions_included
    )
    db.add(campaign)
    db.flush()
    
    # Link escrow to campaign
    escrow.campaign_id = campaign.id
    
    # Update package purchase count
    package.times_purchased = (package.times_purchased or 0) + 1
    
    # Send notifications
    notification_svc = get_notification_service(db)
    
    # Notify influencer of new campaign request
    notification_svc.notify_campaign_request(
        influencer_user_id=influencer.user_id,
        brand_name=current_user.name or current_user.email,
        campaign_id=campaign.id,
        package_name=package.name,
        price=package.price
    )
    
    # Notify influencer of escrow
    notification_svc.notify_escrow_locked(
        influencer_user_id=influencer.user_id,
        brand_name=current_user.name or current_user.email,
        amount=package.price,
        campaign_id=campaign.id
    )
    
    db.commit()
    db.refresh(campaign)
    
    return _campaign_to_response(campaign, db)


@router.get("", response_model=dict)

async def list_campaigns(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    status_filter: Optional[CampaignStatus] = Query(None, alias="status", description="Filter by status"),
    role: Optional[str] = Query(None, description="Filter by role: brand or influencer"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List campaigns for the current user.
    Brands see their purchased campaigns, influencers see received campaigns.
    """
    query = db.query(Campaign)

    # If request is for open campaigns, allow anyone (authenticated or not)
    if status_filter and status_filter.value == "open":
        query = query.filter(Campaign.status == "open")
    else:
        # Require authentication for all other queries
        if not current_user:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        user_type = current_user.user_type
        if user_type == UserType.BRAND or role == "brand":
            query = query.filter(Campaign.brand_id == current_user.id)
        elif user_type == UserType.INFLUENCER or role == "influencer":
            profile = db.query(InfluencerProfile).filter(
                InfluencerProfile.user_id == current_user.id
            ).first()
            if profile:
                query = query.filter(Campaign.influencer_id == profile.id)
            else:
                return {"campaigns": [], "pagination": {"page": 1, "limit": limit, "total": 0}}
        # Admin can see all campaigns (no filter)
        if status_filter:
            query = query.filter(Campaign.status == status_filter.value)

    total = query.count()
    offset = (page - 1) * limit
    campaigns = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "campaigns": [_campaign_to_response(c, db) for c in campaigns],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }



# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin", response_model=dict)
async def get_all_campaigns_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all campaigns for admin dashboard."""
    query = db.query(Campaign)
    total = query.count()
    offset = (page - 1) * limit
    campaigns = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "campaigns": [_campaign_to_response(c, db) for c in campaigns],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }


@router.post("/admin/{campaign_id}/resolve-dispute")
async def resolve_dispute(
    campaign_id: str,
    decision: str = Query(..., description="refund_brand or pay_influencer"),
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Resolve a campaign dispute (Admin only).
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.status != CampaignStatusDB.DISPUTED:
        raise HTTPException(status_code=400, detail="Campaign is not disputed")
        
    # Get dispute record - assuming one active dispute per campaign for MVP
    from database.marketplace_models import Dispute, DisputeStatusDB
    dispute = db.query(Dispute).filter(
        Dispute.campaign_id == campaign_id,
        Dispute.status == DisputeStatusDB.OPEN
    ).first()
    
    if decision == "refund_brand":
        _release_escrow(campaign, db, refund=True)
        campaign.status = CampaignStatusDB.CANCELLED
        if dispute:
            dispute.status = DisputeStatusDB.RESOLVED_REFUND
            dispute.resolution_notes = resolution_notes
            dispute.resolved_at = datetime.utcnow()
            dispute.resolved_by = current_user.id
            
    elif decision == "pay_influencer":
        _release_escrow(campaign, db, refund=False)
        campaign.status = CampaignStatusDB.COMPLETED
        if dispute:
            dispute.status = DisputeStatusDB.RESOLVED_PAYOUT
            dispute.resolution_notes = resolution_notes
            dispute.resolved_at = datetime.utcnow()
            dispute.resolved_by = current_user.id
            
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")
        
    db.commit()
    return {"status": "resolved", "decision": decision}


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get campaign details.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if not _can_access_campaign(current_user, campaign, db):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _campaign_to_response(campaign, db, include_deliverables=True)


# ============================================================================
# INFLUENCER ENDPOINTS (Accept/Reject, Submit Deliverables)
# ============================================================================

@router.post("/{campaign_id}/accept")
async def accept_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Accept a campaign (Influencer only).
    """
    campaign = _get_campaign_for_influencer(campaign_id, current_user, db)
    
    if campaign.status != CampaignStatusDB.PENDING:
        raise HTTPException(status_code=400, detail="Campaign is not in pending state")
    
    campaign.status = CampaignStatusDB.ACCEPTED
    campaign.started_at = datetime.utcnow()
    
    # Send notification to brand
    notification_svc = get_notification_service(db)
    profile = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    notification_svc.notify_campaign_accepted(
        brand_user_id=campaign.brand_id,
        influencer_name=profile.display_name if profile else "Influencer",
        campaign_id=campaign.id
    )
    
    db.commit()
    
    return {"status": "accepted", "message": "Campaign accepted. Start working on deliverables."}


@router.post("/{campaign_id}/reject")
async def reject_campaign(
    campaign_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Reject a campaign (Influencer only).
    This releases the escrow back to the brand.
    """
    campaign = _get_campaign_for_influencer(campaign_id, current_user, db)
    
    if campaign.status != CampaignStatusDB.PENDING:
        raise HTTPException(status_code=400, detail="Campaign is not in pending state")
    
    # Release escrow
    _release_escrow(campaign, db, refund=True)
    
    campaign.status = CampaignStatusDB.CANCELLED
    campaign.custom_requirements = f"{campaign.custom_requirements or ''}\n\nRejection reason: {reason}" if reason else campaign.custom_requirements
    
    # Send notification to brand
    notification_svc = get_notification_service(db)
    profile = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    notification_svc.notify_campaign_rejected(
        brand_user_id=campaign.brand_id,
        influencer_name=profile.display_name if profile else "Influencer",
        campaign_id=campaign.id,
        reason=reason
    )
    
    db.commit()
    
    return {"status": "rejected", "message": "Campaign rejected. Funds returned to brand."}


@router.post("/{campaign_id}/submit-draft")
async def submit_deliverable(
    campaign_id: str,
    deliverable_data: DeliverableSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Submit a draft deliverable for review.
    """
    campaign = _get_campaign_for_influencer(campaign_id, current_user, db)
    
    if campaign.status not in [CampaignStatusDB.ACCEPTED, CampaignStatusDB.IN_PROGRESS, CampaignStatusDB.REVISION_REQUESTED]:
        raise HTTPException(status_code=400, detail="Campaign is not accepting deliverables")
    
    # Create deliverable
    deliverable = Deliverable(
        campaign_id=campaign.id,
        content_type=deliverable_data.content_type.value,
        platform=deliverable_data.platform.value,
        draft_url=deliverable_data.draft_url,
        draft_description=deliverable_data.draft_description,
        draft_caption=deliverable_data.draft_caption,
        draft_media_urls=deliverable_data.draft_media_urls,
        status=DeliverableStatusDB.SUBMITTED
    )
    db.add(deliverable)
    
    # Update campaign status
    campaign.status = CampaignStatusDB.DRAFT_SUBMITTED
    campaign.draft_submitted_at = datetime.utcnow()
    
    # Send notification to brand
    notification_svc = get_notification_service(db)
    profile = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    notification_svc.notify_draft_submitted(
        brand_user_id=campaign.brand_id,
        influencer_name=profile.display_name if profile else "Influencer",
        campaign_id=campaign.id
    )
    
    db.commit()
    db.refresh(deliverable)
    
    return {"status": "submitted", "deliverable_id": deliverable.id}


# ============================================================================
# BRAND REVIEW ENDPOINTS (Approve/Request Revision)
# ============================================================================

@router.post("/{campaign_id}/deliverables/{deliverable_id}/approve")
async def approve_deliverable(
    campaign_id: str,
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.ADMIN))
):
    """
    Approve a deliverable (Brand only).
    """
    campaign = _get_campaign_for_brand(campaign_id, current_user, db)
    
    deliverable = db.query(Deliverable).filter(
        Deliverable.id == deliverable_id,
        Deliverable.campaign_id == campaign_id
    ).first()
    
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    deliverable.status = DeliverableStatusDB.APPROVED
    campaign.status = CampaignStatusDB.DRAFT_APPROVED
    
    # Send notification to influencer
    notification_svc = get_notification_service(db)
    profile = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    if profile:
        notification_svc.notify_draft_approved(
            influencer_user_id=profile.user_id,
            brand_name=current_user.name or current_user.email,
            campaign_id=campaign.id
        )
    
    db.commit()
    
    return {"status": "approved", "message": "Deliverable approved. Waiting for influencer to publish."}


@router.post("/{campaign_id}/deliverables/{deliverable_id}/request-revision")
async def request_revision(
    campaign_id: str,
    deliverable_id: str,
    feedback: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.ADMIN))
):
    """
    Request revision on a deliverable (Brand only).
    """
    campaign = _get_campaign_for_brand(campaign_id, current_user, db)
    
    # Check revision limit
    if campaign.revisions_used >= (campaign.revisions_allowed or 0):
        raise HTTPException(
            status_code=400,
            detail=f"Revision limit reached ({campaign.revisions_allowed} revisions allowed)"
        )
    
    deliverable = db.query(Deliverable).filter(
        Deliverable.id == deliverable_id,
        Deliverable.campaign_id == campaign_id
    ).first()
    
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    deliverable.status = DeliverableStatusDB.REJECTED
    deliverable.draft_description = f"{deliverable.draft_description or ''}\n\n--- REVISION REQUESTED ---\n{feedback}"
    
    campaign.status = CampaignStatusDB.REVISION_REQUESTED
    campaign.revisions_used = (campaign.revisions_used or 0) + 1
    
    # Send notification to influencer
    notification_svc = get_notification_service(db)
    profile = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    if profile:
        notification_svc.notify_revision_requested(
            influencer_user_id=profile.user_id,
            brand_name=current_user.name or current_user.email,
            campaign_id=campaign.id,
            feedback=feedback
        )
    
    db.commit()
    
    return {
        "status": "revision_requested",
        "message": f"Revision requested. {campaign.revisions_allowed - campaign.revisions_used} revisions remaining."
    }


# ============================================================================
# PUBLICATION & COMPLETION
# ============================================================================

@router.post("/{campaign_id}/mark-published")
async def mark_published(
    campaign_id: str,
    published_url: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Mark content as published (Influencer only).
    """
    campaign = _get_campaign_for_influencer(campaign_id, current_user, db)
    
    if campaign.status != CampaignStatusDB.DRAFT_APPROVED:
        raise HTTPException(status_code=400, detail="Draft must be approved before publishing")
    
    # Update deliverables
    deliverables = db.query(Deliverable).filter(
        Deliverable.campaign_id == campaign_id,
        Deliverable.status == DeliverableStatusDB.APPROVED
    ).all()
    
    for d in deliverables:
        d.status = DeliverableStatusDB.PUBLISHED
        d.published_url = published_url
        d.published_at = datetime.utcnow()
    
    campaign.status = CampaignStatusDB.PUBLISHED
    campaign.published_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "published", "message": "Content marked as published. Awaiting brand confirmation."}


@router.post("/{campaign_id}/complete")
async def complete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.ADMIN))
):
    """
    Complete a campaign and release funds (Brand only).
    """
    campaign = _get_campaign_for_brand(campaign_id, current_user, db)
    
    if campaign.status not in [CampaignStatusDB.PUBLISHED, CampaignStatusDB.PENDING_REVIEW]:
        raise HTTPException(status_code=400, detail="Campaign must be published before completion")
    
    # Release escrow to influencer
    _release_escrow(campaign, db, refund=False)
    
    campaign.status = CampaignStatusDB.COMPLETED
    campaign.completed_at = datetime.utcnow()
    
    # Update influencer stats
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.id == campaign.influencer_id
    ).first()
    if influencer:
        influencer.completed_campaigns = (influencer.completed_campaigns or 0) + 1
    
    # Send notifications to both parties
    notification_svc = get_notification_service(db)
    
    # Get package price for the payment notification
    package = db.query(Package).filter(Package.id == campaign.package_id).first()
    payment_amount = package.price * 0.9 if package else 0  # After 10% fee
    
    # Notify influencer
    if influencer:
        notification_svc.notify_campaign_completed(
            user_id=influencer.user_id,
            campaign_id=campaign.id,
            is_influencer=True,
            other_party_name=current_user.name or current_user.email,
            amount=payment_amount
        )
        # Also notify of payment
        notification_svc.notify_payment_received(
            user_id=influencer.user_id,
            amount=payment_amount,
            source="Campaign completion",
            transaction_id=None
        )
    
    # Notify brand
    notification_svc.notify_campaign_completed(
        user_id=current_user.id,
        campaign_id=campaign.id,
        is_influencer=False,
        other_party_name=influencer.display_name if influencer else "Influencer"
    )
    
    db.commit()
    
    return {"status": "completed", "message": "Campaign completed. Funds released to influencer."}


# ============================================================================
# DISPUTE
# ============================================================================

@router.post("/{campaign_id}/dispute")
async def raise_dispute(
    campaign_id: str,
    reason: str,
    evidence_urls: List[str] = [],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Raise a dispute on a campaign.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if not _can_access_campaign(current_user, campaign, db):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from database.marketplace_models import Dispute, DisputeStatusDB
    
    # Create dispute
    dispute = Dispute(
        campaign_id=campaign_id,
        raised_by=current_user.id,
        reason=reason,
        evidence_urls=evidence_urls,
        status=DisputeStatusDB.OPEN
    )
    db.add(dispute)
    
    # Update escrow and campaign status
    if campaign.escrow_id:
        escrow = db.query(EscrowHold).filter(EscrowHold.id == campaign.escrow_id).first()
        if escrow:
            escrow.status = EscrowStatusDB.DISPUTED
    
    campaign.status = CampaignStatusDB.DISPUTED
    
    db.commit()
    
    return {"status": "disputed", "message": "Dispute raised. Admin will review within 48 hours."}





# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_campaign_for_influencer(campaign_id: str, user: User, db: Session) -> Campaign:
    """Get campaign and verify influencer access."""
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == user.id
    ).first()
    
    if not profile and user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Influencer profile required")
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if user.user_type != UserType.ADMIN and campaign.influencer_id != profile.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return campaign


def _get_campaign_for_brand(campaign_id: str, user: User, db: Session) -> Campaign:
    """Get campaign and verify brand access."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if user.user_type != UserType.ADMIN and campaign.brand_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return campaign


def _can_access_campaign(user: User, campaign: Campaign, db: Session) -> bool:
    """Check if user can access campaign."""
    if user.user_type == UserType.ADMIN:
        return True
    
    if campaign.brand_id == user.id:
        return True
    
    profile = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == user.id
    ).first()
    
    if profile and campaign.influencer_id == profile.id:
        return True
    
    return False


def _release_escrow(campaign: Campaign, db: Session, refund: bool = False):
    """Release escrow funds - either refund to brand or pay influencer."""
    if not campaign.escrow_id:
        return
    
    escrow = db.query(EscrowHold).filter(EscrowHold.id == campaign.escrow_id).first()
    if not escrow or escrow.status != EscrowStatusDB.LOCKED:
        return
    
    # Get wallets
    brand_wallet = db.query(Wallet).filter(Wallet.user_id == campaign.brand_id).first()
    
    if refund:
        # Refund to brand
        if brand_wallet:
            brand_wallet.hold_balance -= escrow.amount
        
        escrow.status = EscrowStatusDB.REFUNDED
        escrow.released_at = datetime.utcnow()
        
        # Create refund transaction
        refund_tx = WalletTransaction(
            to_wallet_id=brand_wallet.id if brand_wallet else None,
            amount=escrow.amount,
            fee=0,
            net_amount=escrow.amount,
            transaction_type=WalletTransactionTypeDB.ESCROW_REFUND,
            status=WalletTransactionStatusDB.COMPLETED,
            description=f"Escrow refund for campaign {campaign.id}",
            completed_at=datetime.utcnow()
        )
        db.add(refund_tx)
        escrow.release_transaction_id = refund_tx.id
    else:
        # Pay influencer
        influencer = db.query(InfluencerProfile).filter(
            InfluencerProfile.id == campaign.influencer_id
        ).first()
        
        if influencer:
            influencer_wallet = db.query(Wallet).filter(
                Wallet.user_id == influencer.user_id
            ).first()
            
            if not influencer_wallet:
                # Create wallet if missing
                influencer_wallet = Wallet(user_id=influencer.user_id)
                db.add(influencer_wallet)
                db.flush()
            
            # Calculate platform fee
            platform_fee = int(escrow.amount * PLATFORM_FEE_PERCENT / 100)
            influencer_payment = escrow.amount - platform_fee
            
            # Update brand wallet
            if brand_wallet:
                brand_wallet.hold_balance -= escrow.amount
                brand_wallet.total_spent += escrow.amount
            
            # Pay influencer
            influencer_wallet.balance += influencer_payment
            influencer_wallet.total_earned += influencer_payment
            
            # Create release transaction
            release_tx = WalletTransaction(
                from_wallet_id=brand_wallet.id if brand_wallet else None,
                to_wallet_id=influencer_wallet.id,
                amount=escrow.amount,
                fee=platform_fee,
                net_amount=influencer_payment,
                transaction_type=WalletTransactionTypeDB.ESCROW_RELEASE,
                status=WalletTransactionStatusDB.COMPLETED,
                description=f"Payment for campaign {campaign.id}",
                completed_at=datetime.utcnow()
            )
            db.add(release_tx)
            escrow.release_transaction_id = release_tx.id
        
        escrow.status = EscrowStatusDB.RELEASED
        escrow.released_at = datetime.utcnow()


def _campaign_to_response(campaign: Campaign, db: Session, include_deliverables: bool = False) -> CampaignResponse:
    """Convert campaign to response."""
    from routers.influencers import _profile_to_response
    from routers.packages import _package_to_response

    # Get related data
    package = db.query(Package).filter(Package.id == campaign.package_id).first()
    influencer = db.query(InfluencerProfile).filter(InfluencerProfile.id == campaign.influencer_id).first()
    
    # Get Brand data
    brand_entity = None
    if campaign.brand_entity_id:
        brand_obj = db.query(Brand).filter(Brand.id == campaign.brand_entity_id).first()
        if brand_obj:
            brand_entity = {
                "id": brand_obj.id,
                "name": brand_obj.name,
                "industry": brand_obj.industry,
                "description": brand_obj.description,
                "logo_url": brand_obj.logo_url
            }

    deliverables = []
    if include_deliverables:
        deliverables_db = db.query(Deliverable).filter(Deliverable.campaign_id == campaign.id).all()
        deliverables = [
            DeliverableResponse(
                id=d.id,
                campaign_id=d.campaign_id,
                content_type=d.content_type,
                platform=d.platform.value if d.platform else "multi",
                draft_url=d.draft_url,
                draft_description=d.draft_description,
                draft_caption=d.draft_caption,
                draft_media_urls=d.draft_media_urls or [],
                published_url=d.published_url,
                published_at=d.published_at,
                verified_at=d.verified_at,
                status=DeliverableStatus(d.status.value),
                views=d.views,
                likes=d.likes,
                comments=d.comments,
                shares=d.shares,
                engagement_rate=d.engagement_rate,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
            for d in deliverables_db
        ]
    
    return CampaignResponse(
        id=campaign.id,
        brand_id=campaign.brand_id,
        influencer_id=campaign.influencer_id,
        package_id=campaign.package_id,
        escrow_id=campaign.escrow_id,
        brief=CampaignBrief(**campaign.brief) if campaign.brief else None,
        custom_requirements=campaign.custom_requirements,
        status=CampaignStatus(campaign.status.value),
        deadline=campaign.deadline,
        started_at=campaign.started_at,
        draft_submitted_at=campaign.draft_submitted_at,
        published_at=campaign.published_at,
        completed_at=campaign.completed_at,
        revisions_used=campaign.revisions_used or 0,
        revisions_allowed=campaign.revisions_allowed or 0,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        package=_package_to_response(package, influencer) if package and influencer else None,
        influencer=_profile_to_response(influencer) if influencer else None,
        deliverables=deliverables,
        brand_entity=brand_entity
    )
