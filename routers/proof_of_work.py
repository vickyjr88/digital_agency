# Proof of Work Router for Dexter Marketplace
# Handles submission, approval, and release of funds for campaign deliverables

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from database.config import get_db
from database.models import User
from database.marketplace_models import (
    ProofOfWork, ProofOfWorkStatus,
    Bid, BidStatusDB,
    Campaign, CampaignStatusDB,
    InfluencerProfile,
    EscrowHold, EscrowStatusDB,
    Wallet, WalletTransaction,
    WalletTransactionTypeDB, WalletTransactionStatusDB,
    Notification
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type

router = APIRouter(prefix="/proof-of-work", tags=["Proof of Work"])

from config.app_config import PLATFORM_FEE_PERCENT, MIN_WITHDRAWAL_AMOUNT_CENTS


# ============================================================================
# SCHEMAS
# ============================================================================

class SubmitProofRequest(BaseModel):
    bid_id: str = Field(..., description="ID of the accepted bid")
    title: str = Field(..., min_length=5, max_length=255, description="Title of submission")
    description: Optional[str] = Field(None, description="Description of what was delivered")
    content_links: List[str] = Field(..., min_items=1, description="Links to posted content")
    screenshot_urls: Optional[List[str]] = Field(None, description="Screenshots as evidence")
    views_count: Optional[int] = Field(0, ge=0)
    likes_count: Optional[int] = Field(0, ge=0)
    comments_count: Optional[int] = Field(0, ge=0)
    shares_count: Optional[int] = Field(0, ge=0)


class ReviewProofRequest(BaseModel):
    approved: bool = Field(..., description="Whether to approve the proof")
    notes: Optional[str] = Field(None, description="Feedback notes")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (if rejecting)")


class ProofResponse(BaseModel):
    id: str
    bid_id: str
    campaign_id: str
    title: str
    description: Optional[str]
    content_links: List[str]
    screenshot_urls: Optional[List[str]]
    views_count: int
    likes_count: int
    comments_count: int
    shares_count: int
    status: str
    brand_notes: Optional[str]
    rejection_reason: Optional[str]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    approved_at: Optional[datetime]
    campaign_title: Optional[str] = None
    brand_name: Optional[str] = None
    influencer_name: Optional[str] = None
    bid_amount: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# INFLUENCER ENDPOINTS
# ============================================================================

@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_proof_of_work(
    request: SubmitProofRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER))
):
    """
    Submit proof of work for an accepted bid.
    Influencer provides links to posted content as evidence.
    """
    # Get influencer profile
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found"
        )
    
    # Get the bid
    bid = db.query(Bid).options(
        joinedload(Bid.campaign)
    ).filter(
        Bid.id == request.bid_id,
        Bid.influencer_id == influencer.id
    ).first()
    
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found or doesn't belong to you"
        )
    
    # Check bid is accepted
    if bid.status != BidStatusDB.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit proof for accepted bids"
        )
    
    # Check if proof already exists
    existing_proof = db.query(ProofOfWork).filter(
        ProofOfWork.bid_id == bid.id,
        ProofOfWork.status.in_([ProofOfWorkStatus.PENDING, ProofOfWorkStatus.APPROVED])
    ).first()
    
    if existing_proof:
        if existing_proof.status == ProofOfWorkStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proof has already been approved for this bid"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A proof submission is already pending review"
        )
    
    # Create proof of work
    proof = ProofOfWork(
        bid_id=bid.id,
        campaign_id=bid.campaign_id,
        influencer_id=influencer.id,
        title=request.title,
        description=request.description,
        content_links=request.content_links,
        screenshot_urls=request.screenshot_urls,
        views_count=request.views_count or 0,
        likes_count=request.likes_count or 0,
        comments_count=request.comments_count or 0,
        shares_count=request.shares_count or 0,
        status=ProofOfWorkStatus.PENDING
    )
    
    db.add(proof)
    
    # Update campaign status
    if bid.campaign:
        bid.campaign.status = CampaignStatusDB.PENDING_REVIEW
    
    # Notify brand
    notification = Notification(
        user_id=bid.campaign.brand_id,
        type="proof_submitted",
        title="Proof of Work Submitted",
        message=f"Proof submitted for campaign: {bid.campaign.title}",
        data={
            "proof_id": proof.id,
            "campaign_id": bid.campaign_id,
            "bid_id": bid.id
        }
    )
    db.add(notification)
    
    db.commit()
    db.refresh(proof)
    
    return {
        "message": "Proof of work submitted successfully",
        "proof_id": proof.id,
        "status": proof.status.value
    }


@router.get("/my-submissions")
async def get_my_proof_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER))
):
    """Get all proof submissions by the current influencer."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    if not influencer:
        return {"submissions": []}
    
    query = db.query(ProofOfWork).options(
        joinedload(ProofOfWork.campaign),
        joinedload(ProofOfWork.bid)
    ).filter(
        ProofOfWork.influencer_id == influencer.id
    )
    
    if status_filter:
        try:
            status_enum = ProofOfWorkStatus(status_filter)
            query = query.filter(ProofOfWork.status == status_enum)
        except ValueError:
            pass
    
    proofs = query.order_by(ProofOfWork.submitted_at.desc()).all()
    
    return {
        "submissions": [
            {
                "id": p.id,
                "bid_id": p.bid_id,
                "campaign_id": p.campaign_id,
                "campaign_title": p.campaign.title if p.campaign else None,
                "title": p.title,
                "description": p.description,
                "content_links": p.content_links,
                "status": p.status.value,
                "brand_notes": p.brand_notes,
                "rejection_reason": p.rejection_reason,
                "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "approved_at": p.approved_at.isoformat() if p.approved_at else None,
                "bid_amount": p.bid.amount if p.bid else None
            }
            for p in proofs
        ]
    }


# ============================================================================
# BRAND ENDPOINTS
# ============================================================================

@router.get("/pending-reviews")
async def get_pending_proof_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND))
):
    """Get all pending proof submissions for brand's campaigns."""
    # Get campaigns owned by brand
    proofs = db.query(ProofOfWork).options(
        joinedload(ProofOfWork.campaign),
        joinedload(ProofOfWork.influencer),
        joinedload(ProofOfWork.bid)
    ).join(Campaign).filter(
        Campaign.brand_id == current_user.id,
        ProofOfWork.status == ProofOfWorkStatus.PENDING
    ).order_by(ProofOfWork.submitted_at.desc()).all()
    
    return {
        "pending_reviews": [
            {
                "id": p.id,
                "bid_id": p.bid_id,
                "campaign_id": p.campaign_id,
                "campaign_title": p.campaign.title if p.campaign else None,
                "influencer_name": p.influencer.display_name if p.influencer else None,
                "title": p.title,
                "description": p.description,
                "content_links": p.content_links,
                "screenshot_urls": p.screenshot_urls,
                "views_count": p.views_count,
                "likes_count": p.likes_count,
                "comments_count": p.comments_count,
                "shares_count": p.shares_count,
                "status": p.status.value,
                "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
                "bid_amount": p.bid.amount if p.bid else None
            }
            for p in proofs
        ]
    }


@router.get("/{proof_id}")
async def get_proof_detail(
    proof_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER))
):
    """Get details of a specific proof submission."""
    proof = db.query(ProofOfWork).options(
        joinedload(ProofOfWork.campaign),
        joinedload(ProofOfWork.influencer),
        joinedload(ProofOfWork.bid)
    ).filter(ProofOfWork.id == proof_id).first()
    
    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proof not found"
        )
    
    # Verify access
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()
    
    is_owner = influencer and proof.influencer_id == influencer.id
    is_brand = proof.campaign and proof.campaign.brand_id == current_user.id
    
    if not is_owner and not is_brand:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this proof"
        )
    
    return {
        "id": proof.id,
        "bid_id": proof.bid_id,
        "campaign_id": proof.campaign_id,
        "campaign_title": proof.campaign.title if proof.campaign else None,
        "influencer_name": proof.influencer.display_name if proof.influencer else None,
        "title": proof.title,
        "description": proof.description,
        "content_links": proof.content_links,
        "screenshot_urls": proof.screenshot_urls,
        "views_count": proof.views_count,
        "likes_count": proof.likes_count,
        "comments_count": proof.comments_count,
        "shares_count": proof.shares_count,
        "status": proof.status.value,
        "brand_notes": proof.brand_notes,
        "rejection_reason": proof.rejection_reason,
        "submitted_at": proof.submitted_at.isoformat() if proof.submitted_at else None,
        "reviewed_at": proof.reviewed_at.isoformat() if proof.reviewed_at else None,
        "approved_at": proof.approved_at.isoformat() if proof.approved_at else None,
        "bid_amount": proof.bid.amount if proof.bid else None
    }


@router.post("/{proof_id}/review")
async def review_proof_of_work(
    proof_id: str,
    request: ReviewProofRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND))
):
    """
    Review and approve/reject a proof of work submission.
    On approval, funds are released from escrow to influencer's wallet.
    """
    proof = db.query(ProofOfWork).options(
        joinedload(ProofOfWork.campaign),
        joinedload(ProofOfWork.bid),
        joinedload(ProofOfWork.influencer)
    ).filter(ProofOfWork.id == proof_id).first()
    
    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proof not found"
        )
    
    # Verify brand owns the campaign
    if not proof.campaign or proof.campaign.brand_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this campaign"
        )
    
    # Check proof is pending
    if proof.status != ProofOfWorkStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proof has already been {proof.status.value}"
        )
    
    now = datetime.utcnow()
    
    if request.approved:
        # APPROVE: Release funds from escrow
        proof.status = ProofOfWorkStatus.APPROVED
        proof.approved_at = now
        proof.reviewed_at = now
        proof.brand_notes = request.notes
        
        # Update campaign status
        proof.campaign.status = CampaignStatusDB.COMPLETED
        
        # Release escrow to influencer
        bid = proof.bid
        if bid and bid.escrow_id:
            escrow = db.query(EscrowHold).filter(
                EscrowHold.id == bid.escrow_id
            ).first()
            
            if escrow and escrow.status == EscrowStatusDB.LOCKED:
                # Get influencer wallet
                influencer_wallet = db.query(Wallet).filter(
                    Wallet.user_id == proof.influencer.user_id
                ).first()
                
                if not influencer_wallet:
                    # Create wallet
                    influencer_wallet = Wallet(
                        user_id=proof.influencer.user_id,
                        balance=0,
                        hold_balance=0,
                        total_earned=0,
                        total_spent=0,
                        currency="KES"
                    )
                    db.add(influencer_wallet)
                    db.flush()
                
                # Calculate amounts
                bid_amount = bid.amount
                platform_fee = int(bid_amount * PLATFORM_FEE_PERCENT / 100)
                net_amount = bid_amount - platform_fee
                
                # Create release transaction
                release_transaction = WalletTransaction(
                    to_wallet_id=influencer_wallet.id,
                    amount=net_amount,
                    fee=platform_fee,
                    net_amount=net_amount,
                    transaction_type=WalletTransactionTypeDB.ESCROW_RELEASE,
                    status=WalletTransactionStatusDB.COMPLETED,
                    description=f"Payment for campaign: {proof.campaign.title}",
                    completed_at=now
                )
                db.add(release_transaction)
                db.flush()
                
                # Update escrow
                escrow.status = EscrowStatusDB.RELEASED
                escrow.released_at = now
                escrow.release_transaction_id = release_transaction.id
                
                # Credit influencer wallet
                influencer_wallet.balance += net_amount
                influencer_wallet.total_earned += net_amount
                
                # Update influencer stats
                proof.influencer.completed_campaigns = (proof.influencer.completed_campaigns or 0) + 1
                
                # Notify influencer
                notification = Notification(
                    user_id=proof.influencer.user_id,
                    type="payment_received",
                    title="Payment Received!",
                    message=f"KES {net_amount / 100:,.0f} has been added to your wallet for completing '{proof.campaign.title}'",
                    data={
                        "amount": net_amount,
                        "campaign_id": proof.campaign_id,
                        "transaction_id": release_transaction.id
                    }
                )
                db.add(notification)
                
                logging.info(f"Released {net_amount} cents to influencer {proof.influencer.user_id}")
        
        db.commit()
        
        return {
            "message": "Proof approved! Funds released to influencer.",
            "proof_id": proof.id,
            "status": "approved",
            "released_amount": net_amount if bid and bid.escrow_id else 0
        }
    
    else:
        # REJECT
        proof.status = ProofOfWorkStatus.REJECTED
        proof.reviewed_at = now
        proof.brand_notes = request.notes
        proof.rejection_reason = request.rejection_reason
        
        # Notify influencer
        notification = Notification(
            user_id=proof.influencer.user_id,
            type="proof_rejected",
            title="Proof of Work Rejected",
            message=f"Your proof for '{proof.campaign.title}' was rejected. Reason: {request.rejection_reason or 'No reason provided'}",
            data={
                "proof_id": proof.id,
                "campaign_id": proof.campaign_id
            }
        )
        db.add(notification)
        
        db.commit()
        
        return {
            "message": "Proof rejected. Influencer has been notified.",
            "proof_id": proof.id,
            "status": "rejected"
        }


# ============================================================================
# HELPER ENDPOINT - Get minimum withdrawal amount
# ============================================================================

@router.get("/config/minimum-withdrawal")
async def get_minimum_withdrawal():
    """Get the minimum withdrawal amount."""
    return {
        "minimum_amount_cents": MIN_WITHDRAWAL_AMOUNT_CENTS,
        "minimum_amount_kes": MIN_WITHDRAWAL_AMOUNT_CENTS / 100,
        "currency": "KES"
    }
