# Wallet Router for Dexter Marketplace
# Handles wallet management, deposits, withdrawals, and transaction history

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from database.config import get_db
from database.models import User, UserType
from database.marketplace_models import (
    Wallet, WalletTransaction, EscrowHold,
    WalletTransactionTypeDB, WalletTransactionStatusDB, EscrowStatusDB
)
from schemas.marketplace import (
    WalletResponse,
    DepositRequest,
    WithdrawRequest,
    TransactionResponse,
    TransactionType,
    TransactionStatus,
)
from auth.roles import UserType as UserTypeRole
from auth.decorators import require_user_type, AuthError
from core.paystack_service import PaystackService

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# Platform fee percentage (10%)
PLATFORM_FEE_PERCENT = 10


# ============================================================================
# WALLET ENDPOINTS
# ============================================================================

@router.get("", response_model=WalletResponse)
async def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get current user's wallet balance and stats.
    Creates wallet if it doesn't exist.
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        # Auto-create wallet
        wallet = Wallet(
            user_id=current_user.id,
            balance=0,
            hold_balance=0,
            total_earned=0,
            total_spent=0,
            currency="KES"
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        balance=wallet.balance,
        hold_balance=wallet.hold_balance,
        total_earned=wallet.total_earned,
        total_spent=wallet.total_spent,
        currency=wallet.currency or "KES"
    )


@router.post("/deposit")
async def initiate_deposit(
    deposit_data: DepositRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Initiate a deposit to wallet via Paystack.
    Returns Paystack authorization URL.
    """
    print(f"DEBUG: Initiating deposit for user {current_user.id}, amount {deposit_data.amount}")
    # Get or create wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        print(f"DEBUG: Creating new wallet for user {current_user.id}")
        wallet = Wallet(user_id=current_user.id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    # Initialize Paystack transaction
    amount_kobo = deposit_data.amount * 100  # Convert to kobo/cents
    
    try:
        print("DEBUG: Initializing Paystack Service")
        service = PaystackService()
        print(f"DEBUG: Sending request to Paystack for {current_user.email}, {amount_kobo}")
        response = service.initialize_transaction(
            email=current_user.email,
            amount=amount_kobo,
            user_id=current_user.id,
            callback_url=deposit_data.callback_url or "https://dexter.vitaldigitalmedia.net/wallet/callback",
            metadata={
                "type": "wallet_deposit",
                "user_id": current_user.id,
                "wallet_id": wallet.id,
                "amount": deposit_data.amount
            }
        )
        print(f"DEBUG: Paystack Response: {response}")
        
        # Create pending transaction record
        transaction = WalletTransaction(
            to_wallet_id=wallet.id,
            amount=amount_kobo,
            fee=0,
            net_amount=amount_kobo,
            transaction_type=WalletTransactionTypeDB.DEPOSIT,
            status=WalletTransactionStatusDB.PENDING,
            payment_method="paystack",
            external_id=response['data']['reference'],
            description=f"Wallet deposit of KES {deposit_data.amount}",
            metadata_json=response
        )
        db.add(transaction)
        db.commit()
        
        return {
            "status": "success",
            "authorization_url": response['data']['authorization_url'],
            "reference": response['data']['reference'],
            "transaction_id": transaction.id
        }
        
    except Exception as e:
        import traceback
        print(f"ERROR: Failed to initialize deposit: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize deposit: {str(e)}"
        )


@router.get("/deposit/verify/{reference}")
async def verify_deposit(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Verify a deposit transaction and credit wallet.
    """
    # Find the transaction
    transaction = db.query(WalletTransaction).filter(
        WalletTransaction.external_id == reference
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Already processed?
    if transaction.status == WalletTransactionStatusDB.COMPLETED:
        return {"status": "already_completed", "message": "Deposit already processed"}
    
    # Verify with Paystack
    service = PaystackService()
    verification = service.verify_transaction(reference)
    
    if verification["status"] and verification["data"]["status"] == "success":
        # Get wallet
        wallet = db.query(Wallet).filter(Wallet.id == transaction.to_wallet_id).first()
        
        if wallet:
            # Credit wallet
            wallet.balance += transaction.amount
            
            # Update transaction
            transaction.status = WalletTransactionStatusDB.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "status": "success",
                "message": f"KES {transaction.amount} deposited successfully",
                "new_balance": wallet.balance
            }
    
    # Failed
    transaction.status = WalletTransactionStatusDB.FAILED
    db.commit()
    
    return {"status": "failed", "message": "Payment verification failed"}


@router.post("/withdraw")
async def request_withdrawal(
    withdraw_data: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Request a withdrawal from wallet (Influencers only).
    Funds will be transferred to their registered payment method.
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Calculate fee (if any)
    amount_cents = withdraw_data.amount * 100
    fee_cents = 0  # Could add withdrawal fee here
    net_amount_cents = amount_cents - fee_cents
    
    # Check available balance (excluding held funds)
    available_balance = wallet.balance - wallet.hold_balance
    
    if amount_cents > available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: KES {available_balance / 100}"
        )
    
    # Create withdrawal transaction (pending admin approval)
    transaction = WalletTransaction(
        from_wallet_id=wallet.id,
        amount=amount_cents,
        fee=fee_cents,
        net_amount=net_amount_cents,
        transaction_type=WalletTransactionTypeDB.WITHDRAWAL,
        status=WalletTransactionStatusDB.PENDING,
        payment_method=withdraw_data.payment_method,
        description=f"Withdrawal request of KES {withdraw_data.amount}"
    )
    
    db.add(transaction)
    
    # Hold the withdrawal amount
    wallet.hold_balance += amount_cents
    
    db.commit()
    db.refresh(transaction)
    
    return {
        "status": "pending",
        "message": "Withdrawal request submitted. Processing within 24-48 hours.",
        "transaction_id": transaction.id,
        "amount": withdraw_data.amount,
        "fee": fee,
        "net_amount": net_amount
    }


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transaction_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN)),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by type"),
    status_filter: Optional[TransactionStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get wallet transaction history.
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        return []
    
    # Query transactions where user is sender or receiver
    query = db.query(WalletTransaction).filter(
        or_(
            WalletTransaction.from_wallet_id == wallet.id,
            WalletTransaction.to_wallet_id == wallet.id
        )
    )
    
    if transaction_type:
        query = query.filter(WalletTransaction.transaction_type == transaction_type.value)
    
    if status_filter:
        query = query.filter(WalletTransaction.status == status_filter.value)
    
    # Order by date descending
    query = query.order_by(WalletTransaction.created_at.desc())
    
    # Pagination
    offset = (page - 1) * limit
    transactions = query.offset(offset).limit(limit).all()
    
    return [
        TransactionResponse(
            id=t.id,
            from_wallet_id=t.from_wallet_id,
            to_wallet_id=t.to_wallet_id,
            amount=t.amount,
            fee=t.fee or 0,
            net_amount=t.net_amount,
            transaction_type=TransactionType(t.transaction_type.value),
            status=TransactionStatus(t.status.value),
            external_id=t.external_id,
            description=t.description,
            created_at=t.created_at,
            completed_at=t.completed_at
        )
        for t in transactions
    ]


# ============================================================================
# ESCROW ENDPOINTS
# ============================================================================

@router.get("/escrow")
async def get_escrow_holds(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.BRAND, UserTypeRole.INFLUENCER, UserTypeRole.ADMIN))
):
    """
    Get active escrow holds for the current user.
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        return {"escrow_holds": [], "total_held": 0}
    
    # Get holds from transactions linked to this wallet
    holds = db.query(EscrowHold).join(WalletTransaction).filter(
        or_(
            WalletTransaction.from_wallet_id == wallet.id,
            WalletTransaction.to_wallet_id == wallet.id
        ),
        EscrowHold.status == EscrowStatusDB.LOCKED
    ).all()
    
    return {
        "escrow_holds": [
            {
                "id": h.id,
                "campaign_id": h.campaign_id,
                "amount": h.amount,
                "status": h.status.value,
                "locked_at": h.locked_at.isoformat() if h.locked_at else None,
                "auto_release_at": h.auto_release_at.isoformat() if h.auto_release_at else None
            }
            for h in holds
        ],
        "total_held": wallet.hold_balance
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin/transactions", response_model=dict)
async def get_all_transactions_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """Get all transactions for admin dashboard."""
    query = db.query(WalletTransaction)
    total = query.count()
    offset = (page - 1) * limit
    transactions = query.order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "transactions": [
            TransactionResponse(
                id=t.id,
                from_wallet_id=t.from_wallet_id,
                to_wallet_id=t.to_wallet_id,
                amount=t.amount,
                fee=t.fee or 0,
                net_amount=t.net_amount,
                transaction_type=TransactionType(t.transaction_type.value),
                status=TransactionStatus(t.status.value),
                external_id=t.external_id,
                description=t.description,
                created_at=t.created_at,
                completed_at=t.completed_at
            ) for t in transactions
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }

@router.get("/admin/pending-withdrawals")
async def get_pending_withdrawals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Get all pending withdrawal requests (Admin only).
    """
    withdrawals = db.query(WalletTransaction).filter(
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).order_by(WalletTransaction.created_at.asc()).all()
    
    result = []
    for w in withdrawals:
        # Get wallet and user info
        wallet = db.query(Wallet).filter(Wallet.id == w.from_wallet_id).first()
        user = db.query(User).filter(User.id == wallet.user_id).first() if wallet else None
        
        result.append({
            "transaction_id": w.id,
            "user_id": user.id if user else None,
            "user_email": user.email if user else None,
            "user_name": user.name if user else None,
            "amount": w.amount,
            "net_amount": w.net_amount,
            "payment_method": w.payment_method,
            "requested_at": w.created_at.isoformat()
        })
    
    return {"pending_withdrawals": result, "total": len(result)}


@router.post("/admin/process-withdrawal/{transaction_id}")
async def process_withdrawal(
    transaction_id: str,
    action: str = Query(..., description="approve or reject"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Process a withdrawal request (Admin only).
    """
    transaction = db.query(WalletTransaction).filter(
        WalletTransaction.id == transaction_id,
        WalletTransaction.transaction_type == WalletTransactionTypeDB.WITHDRAWAL,
        WalletTransaction.status == WalletTransactionStatusDB.PENDING
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    
    wallet = db.query(Wallet).filter(Wallet.id == transaction.from_wallet_id).first()
    
    if action == "approve":
        # Mark as processing
        transaction.status = WalletTransactionStatusDB.PROCESSING
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "approved_by": current_user.id,
            "approved_at": datetime.utcnow().isoformat()
        }
        
        # Deduct from wallet
        if wallet:
            wallet.balance -= transaction.amount
            wallet.hold_balance -= transaction.amount
            wallet.total_earned -= transaction.net_amount  # Reduce lifetime earnings
        
        # In production, initiate actual transfer here
        # For now, mark as completed
        transaction.status = WalletTransactionStatusDB.COMPLETED
        transaction.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {"status": "approved", "message": "Withdrawal processed successfully"}
    
    elif action == "reject":
        # Release hold
        if wallet:
            wallet.hold_balance -= transaction.amount
        
        transaction.status = WalletTransactionStatusDB.CANCELLED
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "rejected_by": current_user.id,
            "rejected_at": datetime.utcnow().isoformat()
        }
        
        db.commit()
        
        return {"status": "rejected", "message": "Withdrawal request rejected"}
    
    raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
