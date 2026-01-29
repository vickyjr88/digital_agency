"""
Admin Withdrawal Management Router
Allows admins to view and process pending withdrawals
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import httpx

from database.config import get_db
from database.models import User, UserTypeRole
from database.marketplace_models import (
    Wallet, WalletTransaction, WalletTransactionTypeDB, 
    WalletTransactionStatusDB, PaymentMethod, Notification
)
from auth.decorators import get_current_user, require_user_type

router = APIRouter(prefix="/admin/withdrawals", tags=["Admin - Withdrawals"])


# Pydantic models
class ProcessWithdrawalRequest(BaseModel):
    method: str  # "manual" or "paystack"
    admin_notes: Optional[str] = None


class RejectWithdrawalRequest(BaseModel):
    reason: str


# ============================================================================
# ADMIN WITHDRAWAL ENDPOINTS
# ============================================================================

@router.get("/pending")
async def get_pending_withdrawals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all pending withdrawal requests."""
    
    query = db.query(WalletTransaction).options(
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.user),
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.payment_methods)
    ).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).order_by(desc(WalletTransaction.created_at))
    
    total = query.count()
    withdrawals = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for w in withdrawals:
        user = w.from_wallet.user if w.from_wallet else None
        payment_methods = w.from_wallet.payment_methods if w.from_wallet else []
        primary_method = next((pm for pm in payment_methods if pm.is_primary), None)
        
        result.append({
            "id": w.id,
            "amount": w.amount,
            "fee": w.fee,
            "net_amount": w.net_amount,
            "status": w.status.value,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "description": w.description,
            "user": {
                "id": user.id if user else None,
                "name": user.name if user else "Unknown",
                "email": user.email if user else None
            } if user else None,
            "payment_method": {
                "id": primary_method.id,
                "type": primary_method.method_type.value,
                "phone_number": primary_method.phone_number,
                "account_name": primary_method.account_name,
                "bank_name": primary_method.bank_name,
                "account_number": primary_method.account_number,
                "is_verified": primary_method.is_verified
            } if primary_method else None
        })
    
    return {
        "withdrawals": result,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/history")
async def get_withdrawal_history(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all withdrawal requests with optional status filter."""
    
    query = db.query(WalletTransaction).options(
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.user)
    ).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL
    )
    
    if status_filter:
        query = query.filter(WalletTransaction.status == status_filter)
    
    query = query.order_by(desc(WalletTransaction.created_at))
    
    total = query.count()
    withdrawals = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for w in withdrawals:
        user = w.from_wallet.user if w.from_wallet else None
        metadata = w.metadata_json or {}
        
        result.append({
            "id": w.id,
            "amount": w.amount,
            "fee": w.fee,
            "net_amount": w.net_amount,
            "status": w.status.value,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "completed_at": w.completed_at.isoformat() if w.completed_at else None,
            "description": w.description,
            "payment_method": w.payment_method,
            "external_id": w.external_id,
            "admin_notes": metadata.get("admin_notes"),
            "processed_by": metadata.get("processed_by"),
            "user": {
                "id": user.id if user else None,
                "name": user.name if user else "Unknown",
                "email": user.email if user else None
            } if user else None
        })
    
    return {
        "withdrawals": result,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{withdrawal_id}")
async def get_withdrawal_detail(
    withdrawal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get detailed info about a withdrawal request."""
    
    withdrawal = db.query(WalletTransaction).options(
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.user),
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.payment_methods)
    ).filter(
        WalletTransaction.id == withdrawal_id,
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL
    ).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    user = withdrawal.from_wallet.user if withdrawal.from_wallet else None
    wallet = withdrawal.from_wallet
    payment_methods = wallet.payment_methods if wallet else []
    
    return {
        "id": withdrawal.id,
        "amount": withdrawal.amount,
        "fee": withdrawal.fee,
        "net_amount": withdrawal.net_amount,
        "status": withdrawal.status.value,
        "created_at": withdrawal.created_at.isoformat() if withdrawal.created_at else None,
        "completed_at": withdrawal.completed_at.isoformat() if withdrawal.completed_at else None,
        "description": withdrawal.description,
        "external_id": withdrawal.external_id,
        "metadata": withdrawal.metadata_json,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        } if user else None,
        "wallet": {
            "id": wallet.id,
            "balance": wallet.balance,
            "hold_balance": wallet.hold_balance,
            "total_earned": wallet.total_earned
        } if wallet else None,
        "payment_methods": [
            {
                "id": pm.id,
                "type": pm.method_type.value,
                "phone_number": pm.phone_number,
                "account_name": pm.account_name,
                "bank_name": pm.bank_name,
                "account_number": pm.account_number,
                "is_primary": pm.is_primary,
                "is_verified": pm.is_verified,
                "paystack_recipient_code": pm.paystack_recipient_code
            }
            for pm in payment_methods
        ]
    }


@router.post("/{withdrawal_id}/process")
async def process_withdrawal(
    withdrawal_id: str,
    request: ProcessWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Process a pending withdrawal (manual or via Paystack)."""
    
    withdrawal = db.query(WalletTransaction).options(
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.user),
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.payment_methods)
    ).filter(
        WalletTransaction.id == withdrawal_id,
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found or already processed")
    
    wallet = withdrawal.from_wallet
    user = wallet.user if wallet else None
    
    if request.method == "paystack":
        # Process via Paystack Transfer API
        result = await process_paystack_transfer(withdrawal, wallet, db)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        withdrawal.external_id = result.get("transfer_code")
        withdrawal.payment_method = "paystack_transfer"
    else:
        # Manual processing - just mark as complete
        withdrawal.payment_method = "manual"
    
    # Update withdrawal status
    if request.method == "paystack":
        withdrawal.status = WalletTransactionStatusDB.PROCESSING
        # We don't deduct balance yet, it stays in hold_balance
    else:
        withdrawal.status = WalletTransactionStatusDB.SUCCESS
        withdrawal.completed_at = datetime.utcnow()
        # Release the hold on the wallet and deduct balance
        wallet.hold_balance -= withdrawal.amount
        wallet.balance -= withdrawal.amount
    
    withdrawal.metadata_json = {
        **(withdrawal.metadata_json or {}),
        "admin_notes": request.admin_notes,
        "processed_by": current_user.id,
        "processed_at": datetime.utcnow().isoformat(),
        "process_method": request.method
    }
    
    # Notify user (if manual, otherwise wait for webhook)
    if request.method != "paystack":
        notification = Notification(
            user_id=user.id,
            title="Withdrawal Processed",
            message=f"Your withdrawal of KES {withdrawal.net_amount / 100:,.0f} has been processed.",
            notification_type="wallet",
            is_read=False
        )
        db.add(notification)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Withdrawal processed successfully via {request.method}",
        "withdrawal_id": withdrawal.id,
        "amount": withdrawal.net_amount
    }


@router.post("/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: str,
    request: RejectWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Reject a pending withdrawal and refund to wallet."""
    
    withdrawal = db.query(WalletTransaction).options(
        joinedload(WalletTransaction.from_wallet).joinedload(Wallet.user)
    ).filter(
        WalletTransaction.id == withdrawal_id,
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).first()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found or already processed")
    
    wallet = withdrawal.from_wallet
    user = wallet.user if wallet else None
    
    # Update withdrawal status
    withdrawal.status = WalletTransactionStatusDB.FAILED
    withdrawal.metadata_json = {
        **(withdrawal.metadata_json or {}),
        "rejection_reason": request.reason,
        "rejected_by": current_user.id,
        "rejected_at": datetime.utcnow().isoformat()
    }
    
    # Release the hold (funds go back to available balance)
    wallet.hold_balance -= withdrawal.amount
    
    # Notify user
    if user:
        notification = Notification(
            user_id=user.id,
            title="Withdrawal Rejected",
            message=f"Your withdrawal request was rejected. Reason: {request.reason}. Funds have been returned to your wallet.",
            notification_type="wallet",
            is_read=False
        )
        db.add(notification)
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Withdrawal rejected and funds returned to wallet",
        "withdrawal_id": withdrawal.id
    }


@router.get("/stats/summary")
async def get_withdrawal_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get withdrawal statistics for admin dashboard."""
    
    from sqlalchemy import func
    
    # Pending withdrawals
    pending = db.query(
        func.count(WalletTransaction.id),
        func.sum(WalletTransaction.net_amount)
    ).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).first()
    
    # Completed this month
    from datetime import date
    first_day = date.today().replace(day=1)
    
    completed_month = db.query(
        func.count(WalletTransaction.id),
        func.sum(WalletTransaction.net_amount)
    ).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.SUCCESS,
        WalletTransaction.completed_at >= first_day
    ).first()
    
    # Total completed
    total_completed = db.query(
        func.count(WalletTransaction.id),
        func.sum(WalletTransaction.net_amount)
    ).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.SUCCESS
    ).first()
    
    return {
        "pending": {
            "count": pending[0] or 0,
            "total_amount": pending[1] or 0
        },
        "completed_this_month": {
            "count": completed_month[0] or 0,
            "total_amount": completed_month[1] or 0
        },
        "total_completed": {
            "count": total_completed[0] or 0,
            "total_amount": total_completed[1] or 0
        }
    }


# ============================================================================
# PAYSTACK TRANSFER HELPER
# ============================================================================

async def process_paystack_transfer(withdrawal: WalletTransaction, wallet: Wallet, db: Session):
    """Process withdrawal via Paystack Transfer API."""
    
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
    
    if not PAYSTACK_SECRET_KEY:
        return {"success": False, "message": "Paystack not configured"}
    
    # Get primary payment method
    primary_method = next((pm for pm in wallet.payment_methods if pm.is_primary), None)
    
    if not primary_method:
        return {"success": False, "message": "No payment method configured"}
    
    # Create or use existing recipient
    recipient_code = primary_method.paystack_recipient_code
    
    if not recipient_code:
        # Create transfer recipient
        recipient_result = await create_paystack_recipient(primary_method, wallet.user, PAYSTACK_SECRET_KEY)
        if not recipient_result["success"]:
            return recipient_result
        recipient_code = recipient_result["recipient_code"]
        
        # Save recipient code
        primary_method.paystack_recipient_code = recipient_code
        db.flush()
    
    # Initiate transfer
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/transfer",
                headers={
                    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "source": "balance",
                    "amount": withdrawal.net_amount,  # Amount in kobo/cents
                    "recipient": recipient_code,
                    "reason": f"Withdrawal - {withdrawal.id}"
                },
                timeout=30.0
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "success": True,
                    "transfer_code": data["data"].get("transfer_code"),
                    "reference": data["data"].get("reference")
                }
            else:
                return {
                    "success": False,
                    "message": data.get("message", "Transfer failed")
                }
    except Exception as e:
        return {"success": False, "message": str(e)}


async def create_paystack_recipient(payment_method, user, secret_key: str):
    """Create a Paystack transfer recipient for mobile money."""
    
    try:
        # Determine recipient type based on payment method
        if payment_method.method_type.value == "mpesa":
            recipient_type = "mobile_money"
            details = {
                "type": "mobile_money",
                "name": payment_method.account_name or user.name,
                "account_number": payment_method.phone_number,
                "bank_code": "MPESA"  # Paystack code for M-Pesa
            }
        elif payment_method.method_type.value == "airtel_money":
            recipient_type = "mobile_money"
            details = {
                "type": "mobile_money",
                "name": payment_method.account_name or user.name,
                "account_number": payment_method.phone_number,
                "bank_code": "AIRTEL"
            }
        else:
            # Bank transfer
            recipient_type = "nuban"
            details = {
                "type": "nuban",
                "name": payment_method.account_name or user.name,
                "account_number": payment_method.account_number,
                "bank_code": payment_method.bank_code
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/transferrecipient",
                headers={
                    "Authorization": f"Bearer {secret_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "type": recipient_type,
                    "name": details["name"],
                    "account_number": details["account_number"],
                    "bank_code": details.get("bank_code"),
                    "currency": "KES"
                },
                timeout=30.0
            )
            
            data = response.json()
            
            if response.status_code in [200, 201] and data.get("status"):
                return {
                    "success": True,
                    "recipient_code": data["data"]["recipient_code"]
                }
            else:
                return {
                    "success": False,
                    "message": data.get("message", "Failed to create recipient")
                }
    except Exception as e:
        return {"success": False, "message": str(e)}
