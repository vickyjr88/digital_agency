# Notifications Router for Dexter Marketplace
# Handles user notifications

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from database.config import get_db
from database.models import User
from database.marketplace_models import Notification
from schemas.marketplace import NotificationResponse
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================================
# NOTIFICATION TYPES
# ============================================================================

class NotificationType:
    # Campaign notifications
    CAMPAIGN_NEW = "campaign_new"
    CAMPAIGN_ACCEPTED = "campaign_accepted"
    CAMPAIGN_REJECTED = "campaign_rejected"
    CAMPAIGN_DRAFT_SUBMITTED = "campaign_draft_submitted"
    CAMPAIGN_DRAFT_APPROVED = "campaign_draft_approved"
    CAMPAIGN_REVISION_REQUESTED = "campaign_revision_requested"
    CAMPAIGN_PUBLISHED = "campaign_published"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_DISPUTED = "campaign_disputed"
    
    # Payment notifications
    PAYMENT_RECEIVED = "payment_received"
    DEPOSIT_COMPLETED = "deposit_completed"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"
    
    # Review notifications
    REVIEW_RECEIVED = "review_received"
    
    # System notifications
    PROFILE_VERIFIED = "profile_verified"
    PROFILE_REJECTED = "profile_rejected"


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN)),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get user's notifications.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.read == False)
    
    offset = (page - 1) * limit
    notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    
    return [
        NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            message=n.message,
            data=n.data,
            read=n.read,
            read_at=n.read_at,
            created_at=n.created_at
        )
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get count of unread notifications.
    """
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).count()
    
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Mark a notification as read.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.read = True
    notification.read_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "success"}


@router.post("/read-all")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Mark all notifications as read.
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).update({
        "read": True,
        "read_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Delete a notification.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"status": "success"}


# ============================================================================
# NOTIFICATION SERVICE (for internal use)
# ============================================================================

class NotificationService:
    """Service for creating notifications across the application."""
    
    @staticmethod
    def create(
        db: Session,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: dict = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    
    @staticmethod
    def notify_new_campaign(db: Session, influencer_user_id: str, campaign_id: str, brand_name: str, package_name: str):
        """Notify influencer of new campaign request."""
        return NotificationService.create(
            db=db,
            user_id=influencer_user_id,
            notification_type=NotificationType.CAMPAIGN_NEW,
            title="New Campaign Request",
            message=f"{brand_name} wants to work with you on '{package_name}'",
            data={"campaign_id": campaign_id}
        )
    
    @staticmethod
    def notify_campaign_accepted(db: Session, brand_user_id: str, campaign_id: str, influencer_name: str):
        """Notify brand that influencer accepted."""
        return NotificationService.create(
            db=db,
            user_id=brand_user_id,
            notification_type=NotificationType.CAMPAIGN_ACCEPTED,
            title="Campaign Accepted",
            message=f"{influencer_name} accepted your campaign request!",
            data={"campaign_id": campaign_id}
        )
    
    @staticmethod
    def notify_draft_submitted(db: Session, brand_user_id: str, campaign_id: str, influencer_name: str):
        """Notify brand that draft was submitted."""
        return NotificationService.create(
            db=db,
            user_id=brand_user_id,
            notification_type=NotificationType.CAMPAIGN_DRAFT_SUBMITTED,
            title="Draft Submitted for Review",
            message=f"{influencer_name} submitted a draft for your review",
            data={"campaign_id": campaign_id}
        )
    
    @staticmethod
    def notify_draft_approved(db: Session, influencer_user_id: str, campaign_id: str):
        """Notify influencer that draft was approved."""
        return NotificationService.create(
            db=db,
            user_id=influencer_user_id,
            notification_type=NotificationType.CAMPAIGN_DRAFT_APPROVED,
            title="Draft Approved!",
            message="Your draft has been approved. Please publish the content.",
            data={"campaign_id": campaign_id}
        )
    
    @staticmethod
    def notify_revision_requested(db: Session, influencer_user_id: str, campaign_id: str):
        """Notify influencer that revision was requested."""
        return NotificationService.create(
            db=db,
            user_id=influencer_user_id,
            notification_type=NotificationType.CAMPAIGN_REVISION_REQUESTED,
            title="Revision Requested",
            message="The brand has requested changes to your draft.",
            data={"campaign_id": campaign_id}
        )
    
    @staticmethod
    def notify_payment_received(db: Session, influencer_user_id: str, amount: int, campaign_id: str):
        """Notify influencer of payment."""
        return NotificationService.create(
            db=db,
            user_id=influencer_user_id,
            notification_type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Received!",
            message=f"You received KES {amount} for your campaign",
            data={"campaign_id": campaign_id, "amount": amount}
        )
    
    @staticmethod
    def notify_review_received(db: Session, user_id: str, rating: int, reviewer_name: str):
        """Notify user of new review."""
        stars = "⭐" * rating
        return NotificationService.create(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.REVIEW_RECEIVED,
            title="New Review Received",
            message=f"{reviewer_name} left you a {rating}-star review {stars}",
            data={"rating": rating}
        )
    
    @staticmethod
    def notify_profile_verified(db: Session, user_id: str):
        """Notify user that their profile was verified."""
        return NotificationService.create(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.PROFILE_VERIFIED,
            title="Profile Verified! ✅",
            message="Congratulations! Your influencer profile has been verified.",
            data={}
        )
