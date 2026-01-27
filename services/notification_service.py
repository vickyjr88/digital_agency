# Notification Service for Dexter Marketplace
# Provides centralized notification creation and management

from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from enum import Enum

from database.marketplace_models import Notification, NotificationTypeDB


class NotificationType(str, Enum):
    """Notification types matching NotificationTypeDB."""
    CAMPAIGN_REQUEST = "campaign_request"
    CAMPAIGN_ACCEPTED = "campaign_accepted"
    CAMPAIGN_REJECTED = "campaign_rejected"
    DRAFT_SUBMITTED = "draft_submitted"
    DRAFT_APPROVED = "draft_approved"
    REVISION_REQUESTED = "revision_requested"
    CAMPAIGN_COMPLETED = "campaign_completed"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_SENT = "payment_sent"
    ESCROW_LOCKED = "escrow_locked"
    ESCROW_RELEASED = "escrow_released"
    NEW_REVIEW = "new_review"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"
    PROFILE_VERIFIED = "profile_verified"
    PACKAGE_PURCHASED = "package_purchased"
    WITHDRAWAL_COMPLETED = "withdrawal_completed"
    DEPOSIT_COMPLETED = "deposit_completed"
    SYSTEM = "system"


class NotificationService:
    """
    Service for creating and managing user notifications.
    Use this service from any router to send notifications.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        user_id: str,
        type: NotificationType | str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: The user to notify
            type: Notification type (use NotificationType enum)
            title: Short notification title
            message: Full notification message
            action_url: Optional URL for the notification action
            data: Optional additional data as JSON
        
        Returns:
            The created Notification object
        """
        # Convert string type to NotificationTypeDB enum
        if isinstance(type, str):
            try:
                type_db = NotificationTypeDB(type)
            except ValueError:
                type_db = NotificationTypeDB.SYSTEM
        else:
            try:
                type_db = NotificationTypeDB(type.value)
            except ValueError:
                type_db = NotificationTypeDB.SYSTEM
        
        notification = Notification(
            user_id=user_id,
            type=type_db,
            title=title,
            message=message,
            action_url=action_url,
            data=data or {},
        )
        self.db.add(notification)
        self.db.flush()  # Get the ID without committing
        return notification
    
    def create_batch(
        self,
        user_ids: List[str],
        type: NotificationType | str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> List[Notification]:
        """
        Create notifications for multiple users.
        
        Args:
            user_ids: List of user IDs to notify
            type: Notification type
            title: Short notification title
            message: Full notification message
            action_url: Optional URL for the notification action
            data: Optional additional data as JSON
        
        Returns:
            List of created Notification objects
        """
        notifications = []
        for user_id in user_ids:
            notification = self.create(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                action_url=action_url,
                data=data,
            )
            notifications.append(notification)
        return notifications
    
    def mark_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark a notification as read.
        
        Returns:
            True if notification was marked read, False if not found
        """
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            return True
        return False
    
    def mark_all_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user.
        
        Returns:
            Number of notifications marked as read
        """
        count = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        return count
    
    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user."""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
    
    # =========================================================================
    # CAMPAIGN NOTIFICATION HELPERS
    # =========================================================================
    
    def notify_campaign_request(
        self,
        influencer_user_id: str,
        brand_name: str,
        campaign_id: str,
        package_name: str,
        price: float,
    ):
        """Notify influencer of new campaign request."""
        return self.create(
            user_id=influencer_user_id,
            type=NotificationType.CAMPAIGN_REQUEST,
            title="New Campaign Request! 🎯",
            message=f"{brand_name} wants to work with you on {package_name} for KES {price:,.0f}",
            action_url=f"/campaigns/{campaign_id}",
            data={
                "campaign_id": campaign_id,
                "brand_name": brand_name,
                "package_name": package_name,
                "price": price,
            }
        )
    
    def notify_campaign_accepted(
        self,
        brand_user_id: str,
        influencer_name: str,
        campaign_id: str,
    ):
        """Notify brand that influencer accepted campaign."""
        return self.create(
            user_id=brand_user_id,
            type=NotificationType.CAMPAIGN_ACCEPTED,
            title="Campaign Accepted! ✅",
            message=f"{influencer_name} accepted your campaign and is working on deliverables.",
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id, "influencer_name": influencer_name}
        )
    
    def notify_campaign_rejected(
        self,
        brand_user_id: str,
        influencer_name: str,
        campaign_id: str,
        reason: Optional[str] = None,
    ):
        """Notify brand that influencer rejected campaign."""
        return self.create(
            user_id=brand_user_id,
            type=NotificationType.CAMPAIGN_REJECTED,
            title="Campaign Declined",
            message=f"{influencer_name} declined your campaign request. Funds have been returned to your wallet.",
            action_url=f"/wallet",
            data={"campaign_id": campaign_id, "reason": reason}
        )
    
    def notify_draft_submitted(
        self,
        brand_user_id: str,
        influencer_name: str,
        campaign_id: str,
    ):
        """Notify brand that influencer submitted draft."""
        return self.create(
            user_id=brand_user_id,
            type=NotificationType.DRAFT_SUBMITTED,
            title="Draft Submitted! 📤",
            message=f"{influencer_name} submitted a draft for your review.",
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id, "influencer_name": influencer_name}
        )
    
    def notify_draft_approved(
        self,
        influencer_user_id: str,
        brand_name: str,
        campaign_id: str,
    ):
        """Notify influencer that draft was approved."""
        return self.create(
            user_id=influencer_user_id,
            type=NotificationType.DRAFT_APPROVED,
            title="Draft Approved! 🎉",
            message=f"{brand_name} approved your draft. Please publish the content.",
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id, "brand_name": brand_name}
        )
    
    def notify_revision_requested(
        self,
        influencer_user_id: str,
        brand_name: str,
        campaign_id: str,
        feedback: str,
    ):
        """Notify influencer that revision was requested."""
        return self.create(
            user_id=influencer_user_id,
            type=NotificationType.REVISION_REQUESTED,
            title="Revision Requested 🔄",
            message=f"{brand_name} requested changes to your draft.",
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id, "feedback": feedback}
        )
    
    def notify_campaign_completed(
        self,
        user_id: str,
        campaign_id: str,
        is_influencer: bool,
        other_party_name: str,
        amount: Optional[float] = None,
    ):
        """Notify user that campaign was completed."""
        if is_influencer and amount:
            message = f"Campaign with {other_party_name} completed! KES {amount:,.0f} has been added to your wallet."
        else:
            message = f"Campaign with {other_party_name} completed successfully!"
        
        return self.create(
            user_id=user_id,
            type=NotificationType.CAMPAIGN_COMPLETED,
            title="Campaign Completed! 🎉",
            message=message,
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id, "amount": amount}
        )
    
    # =========================================================================
    # PAYMENT NOTIFICATION HELPERS
    # =========================================================================
    
    def notify_payment_received(
        self,
        user_id: str,
        amount: float,
        source: str,
        transaction_id: Optional[str] = None,
    ):
        """Notify user of payment received."""
        return self.create(
            user_id=user_id,
            type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Received! 💰",
            message=f"You received KES {amount:,.0f} from {source}",
            action_url="/wallet",
            data={"amount": amount, "source": source, "transaction_id": transaction_id}
        )
    
    def notify_deposit_completed(
        self,
        user_id: str,
        amount: float,
    ):
        """Notify user of successful deposit."""
        return self.create(
            user_id=user_id,
            type=NotificationType.DEPOSIT_COMPLETED,
            title="Deposit Successful! 💳",
            message=f"KES {amount:,.0f} has been added to your wallet",
            action_url="/wallet",
            data={"amount": amount}
        )
    
    def notify_withdrawal_completed(
        self,
        user_id: str,
        amount: float,
        method: str,
    ):
        """Notify user of successful withdrawal."""
        return self.create(
            user_id=user_id,
            type=NotificationType.WITHDRAWAL_COMPLETED,
            title="Withdrawal Complete! 🏦",
            message=f"KES {amount:,.0f} has been sent to your {method}",
            action_url="/wallet",
            data={"amount": amount, "method": method}
        )
    
    def notify_escrow_locked(
        self,
        influencer_user_id: str,
        brand_name: str,
        amount: float,
        campaign_id: str,
    ):
        """Notify influencer that funds are in escrow."""
        return self.create(
            user_id=influencer_user_id,
            type=NotificationType.ESCROW_LOCKED,
            title="Funds Secured 🔒",
            message=f"{brand_name} has locked KES {amount:,.0f} for your campaign",
            action_url=f"/campaigns/{campaign_id}",
            data={"amount": amount, "campaign_id": campaign_id}
        )
    
    # =========================================================================
    # REVIEW NOTIFICATION HELPERS
    # =========================================================================
    
    def notify_new_review(
        self,
        user_id: str,
        reviewer_name: str,
        rating: float,
        campaign_id: Optional[str] = None,
    ):
        """Notify user of new review."""
        return self.create(
            user_id=user_id,
            type=NotificationType.NEW_REVIEW,
            title="New Review! ⭐",
            message=f"{reviewer_name} left you a {rating:.1f}-star review",
            action_url="/influencer/dashboard?tab=reviews" if not campaign_id else f"/campaigns/{campaign_id}",
            data={"rating": rating, "campaign_id": campaign_id}
        )
    
    # =========================================================================
    # DISPUTE NOTIFICATION HELPERS
    # =========================================================================
    
    def notify_dispute_opened(
        self,
        user_id: str,
        campaign_id: str,
        opened_by: str,
    ):
        """Notify user that a dispute was opened."""
        return self.create(
            user_id=user_id,
            type=NotificationType.DISPUTE_OPENED,
            title="Dispute Opened ⚠️",
            message=f"{opened_by} opened a dispute on your campaign. Our team will review it.",
            action_url=f"/campaigns/{campaign_id}",
            data={"campaign_id": campaign_id}
        )
    
    def notify_dispute_resolved(
        self,
        user_id: str,
        campaign_id: str,
        resolution: str,
        refund_amount: Optional[float] = None,
    ):
        """Notify user that dispute was resolved."""
        message = f"Your dispute has been resolved: {resolution}"
        if refund_amount:
            message += f" (KES {refund_amount:,.0f} refunded)"
        
        return self.create(
            user_id=user_id,
            type=NotificationType.DISPUTE_RESOLVED,
            title="Dispute Resolved ✅",
            message=message,
            action_url=f"/campaigns/{campaign_id}",
            data={"resolution": resolution, "refund_amount": refund_amount}
        )
    
    # =========================================================================
    # PROFILE NOTIFICATION HELPERS
    # =========================================================================
    
    def notify_profile_verified(
        self,
        user_id: str,
    ):
        """Notify influencer that their profile was verified."""
        return self.create(
            user_id=user_id,
            type=NotificationType.PROFILE_VERIFIED,
            title="Profile Verified! ✓",
            message="Congratulations! Your profile has been verified. You now have a verification badge.",
            action_url="/influencer/dashboard",
            data={}
        )
    
    def notify_package_purchased(
        self,
        influencer_user_id: str,
        brand_name: str,
        package_name: str,
        price: float,
        campaign_id: str,
    ):
        """Notify influencer that their package was purchased."""
        return self.create(
            user_id=influencer_user_id,
            type=NotificationType.PACKAGE_PURCHASED,
            title="Package Purchased! 🛒",
            message=f"{brand_name} purchased your {package_name} package for KES {price:,.0f}",
            action_url=f"/campaigns/{campaign_id}",
            data={"package_name": package_name, "price": price, "campaign_id": campaign_id}
        )


# Convenience function to get service
def get_notification_service(db: Session) -> NotificationService:
    """Get NotificationService instance."""
    return NotificationService(db)
