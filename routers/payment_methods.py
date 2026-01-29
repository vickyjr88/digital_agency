"""
Payment Methods Router
Allows users to manage their withdrawal payment methods (mobile money, bank accounts)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import re

from database.config import get_db
from database.models import User, UserTypeRole
from database.marketplace_models import Wallet, PaymentMethod, PaymentMethodType
from auth.decorators import get_current_user, require_user_type

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


# Pydantic models
class CreatePaymentMethodRequest(BaseModel):
    method_type: str  # mpesa, airtel_money, bank_transfer
    phone_number: Optional[str] = None
    account_name: str
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    is_primary: bool = True
    
    @validator('phone_number')
    def validate_phone(cls, v, values):
        if v and values.get('method_type') in ['mpesa', 'airtel_money']:
            # Clean and validate Kenyan phone number
            phone = re.sub(r'\D', '', v)
            if phone.startswith('0'):
                phone = '254' + phone[1:]
            elif phone.startswith('+'):
                phone = phone[1:]
            elif not phone.startswith('254'):
                phone = '254' + phone
            
            if not re.match(r'^254[17]\d{8}$', phone):
                raise ValueError('Invalid Kenyan phone number')
            return phone
        return v

    @validator('method_type')
    def validate_method_type(cls, v):
        valid_types = ['mpesa', 'airtel_money', 'bank_transfer']
        if v not in valid_types:
            raise ValueError(f'Invalid method type. Must be one of: {valid_types}')
        return v


class UpdatePaymentMethodRequest(BaseModel):
    phone_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None


# ============================================================================
# PAYMENT METHOD ENDPOINTS
# ============================================================================

@router.get("")
async def get_my_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all payment methods for current user."""
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        return {"payment_methods": [], "has_primary": False}
    
    methods = db.query(PaymentMethod).filter(
        PaymentMethod.wallet_id == wallet.id
    ).order_by(PaymentMethod.is_primary.desc(), PaymentMethod.created_at.desc()).all()
    
    return {
        "payment_methods": [
            {
                "id": m.id,
                "method_type": m.method_type.value,
                "phone_number": m.phone_number,
                "phone_display": format_phone_display(m.phone_number) if m.phone_number else None,
                "account_name": m.account_name,
                "bank_name": m.bank_name,
                "bank_code": m.bank_code,
                "account_number": mask_account_number(m.account_number) if m.account_number else None,
                "is_primary": m.is_primary,
                "is_verified": m.is_verified,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in methods
        ],
        "has_primary": any(m.is_primary for m in methods)
    }


@router.post("")
async def create_payment_method(
    request: CreatePaymentMethodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new payment method."""
    
    # Get or create wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        wallet = Wallet(
            user_id=current_user.id,
            balance=0,
            hold_balance=0,
            currency="KES"
        )
        db.add(wallet)
        db.flush()
    
    # Validate required fields based on method type
    if request.method_type in ['mpesa', 'airtel_money']:
        if not request.phone_number:
            raise HTTPException(
                status_code=400, 
                detail="Phone number required for mobile money"
            )
    elif request.method_type == 'bank_transfer':
        if not request.bank_name or not request.account_number:
            raise HTTPException(
                status_code=400, 
                detail="Bank name and account number required for bank transfer"
            )
    
    # Check for duplicate
    existing = db.query(PaymentMethod).filter(
        PaymentMethod.wallet_id == wallet.id,
        PaymentMethod.method_type == request.method_type,
        PaymentMethod.phone_number == request.phone_number if request.phone_number else True,
        PaymentMethod.account_number == request.account_number if request.account_number else True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Payment method already exists")
    
    # If setting as primary, unset other primary methods
    if request.is_primary:
        db.query(PaymentMethod).filter(
            PaymentMethod.wallet_id == wallet.id,
            PaymentMethod.is_primary == True
        ).update({"is_primary": False})
    
    # Create payment method
    payment_method = PaymentMethod(
        wallet_id=wallet.id,
        user_id=current_user.id,
        method_type=PaymentMethodType(request.method_type),
        phone_number=request.phone_number,
        account_name=request.account_name,
        bank_name=request.bank_name,
        bank_code=request.bank_code,
        account_number=request.account_number,
        is_primary=request.is_primary,
        is_verified=False
    )
    
    db.add(payment_method)
    db.commit()
    db.refresh(payment_method)
    
    return {
        "status": "success",
        "message": "Payment method added successfully",
        "payment_method": {
            "id": payment_method.id,
            "method_type": payment_method.method_type.value,
            "phone_number": payment_method.phone_number,
            "account_name": payment_method.account_name,
            "is_primary": payment_method.is_primary
        }
    }


@router.put("/{method_id}")
async def update_payment_method(
    method_id: str,
    request: UpdatePaymentMethodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a payment method."""
    
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # Update fields
    if request.phone_number is not None:
        # Validate and format phone number
        phone = re.sub(r'\D', '', request.phone_number)
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        payment_method.phone_number = phone
        payment_method.is_verified = False  # Re-verification needed
        payment_method.paystack_recipient_code = None  # Reset recipient code
    
    if request.account_name is not None:
        payment_method.account_name = request.account_name
    
    if request.bank_name is not None:
        payment_method.bank_name = request.bank_name
    
    if request.bank_code is not None:
        payment_method.bank_code = request.bank_code
    
    if request.account_number is not None:
        payment_method.account_number = request.account_number
        payment_method.is_verified = False
        payment_method.paystack_recipient_code = None
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Payment method updated"
    }


@router.post("/{method_id}/set-primary")
async def set_primary_payment_method(
    method_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set a payment method as primary."""
    
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # Unset all other primary methods
    db.query(PaymentMethod).filter(
        PaymentMethod.wallet_id == payment_method.wallet_id,
        PaymentMethod.is_primary == True
    ).update({"is_primary": False})
    
    # Set this as primary
    payment_method.is_primary = True
    db.commit()
    
    return {
        "status": "success",
        "message": "Payment method set as primary"
    }


@router.delete("/{method_id}")
async def delete_payment_method(
    method_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment method."""
    
    payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not payment_method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    was_primary = payment_method.is_primary
    wallet_id = payment_method.wallet_id
    
    db.delete(payment_method)
    db.commit()
    
    # If deleted method was primary, set another one as primary
    if was_primary:
        next_method = db.query(PaymentMethod).filter(
            PaymentMethod.wallet_id == wallet_id
        ).first()
        if next_method:
            next_method.is_primary = True
            db.commit()
    
    return {"status": "success", "message": "Payment method deleted"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_phone_display(phone: str) -> str:
    """Format phone number for display (e.g., +254 7** *** *89)"""
    if not phone or len(phone) < 10:
        return phone
    # Show first 4 and last 2 digits
    return f"+{phone[:3]} {phone[3]}** *** *{phone[-2:]}"


def mask_account_number(account: str) -> str:
    """Mask account number for display (e.g., ****1234)"""
    if not account or len(account) < 4:
        return account
    return "*" * (len(account) - 4) + account[-4:]
