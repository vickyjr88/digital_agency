# Orders Endpoints for Affiliate Commerce
# Includes Paystack payment processing integration

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import random
import string
import os
import secrets

from core.minio_service import generate_download_url
from core.paystack_service import PaystackService

from database.models import User, UserRole
from database.marketplace_models import InfluencerProfile, Wallet, WalletTransaction
from database.affiliate_models import (
    Product,
    ProductVariant,
    Order,
    AffiliateLink,
    AffiliateClick,
    AffiliateCommission,
    BrandProfile,
    DigitalPurchase
)
from schemas.affiliate import (
    OrderCreate,
    OrderResponse,
    OrderUpdateStatus,
    BrandContactInfo,
    SuccessResponse
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


def generate_order_number() -> str:
    """Generate unique order number like DEX-2024-001234."""
    year = datetime.now().year
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"DEX-{year}-{random_part}"


def calculate_commission(product: Product, total_amount: Decimal) -> dict:
    """
    Calculate commission based on product settings.
    Returns dict with commission details.
    """
    if product.commission_type == "percentage":
        gross_commission = total_amount * (product.commission_rate / 100)
    else:  # fixed
        gross_commission = product.fixed_commission

    # Calculate platform fee
    if product.platform_fee_type == "percentage":
        platform_fee = gross_commission * (product.platform_fee_rate / 100)
    else:  # fixed
        platform_fee = product.platform_fee_fixed

    net_commission = gross_commission - platform_fee
    brand_receives = total_amount - gross_commission

    return {
        "commission_type": product.commission_type,
        "commission_rate": product.commission_rate if product.commission_type == "percentage" else None,
        "commission_amount": gross_commission,
        "platform_fee_type": product.platform_fee_type,
        "platform_fee_rate": product.platform_fee_rate if product.platform_fee_type == "percentage" else None,
        "platform_fee_amount": platform_fee,
        "net_commission": net_commission,
        "brand_receives": brand_receives
    }


# ============================================================================
# ORDER PLACEMENT (NO PAYMENT)
# ============================================================================

@router.post("/place", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: OrderCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Place an order (NO PAYMENT required).
    Customer fills form, gets brand contact info.
    """
    # Get product
    product = db.query(Product).filter(
        Product.id == order_data.product_id,
        Product.status == "active"
    ).options(joinedload(Product.brand_profile)).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available"
        )

    # Get variant if specified
    variant = None
    if order_data.variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == order_data.variant_id,
            ProductVariant.product_id == product.id
        ).first()

        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found"
            )

    # Check stock if tracking
    if product.track_inventory:
        available_stock = variant.stock_quantity if variant else product.stock_quantity
        if available_stock is not None and available_stock < order_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Only {available_stock} available."
            )

    # Calculate pricing
    unit_price = variant.price if (variant and variant.price) else product.price
    total_amount = unit_price * order_data.quantity

    # Calculate commission
    commission_info = calculate_commission(product, total_amount)

    # Attribution - check affiliate code
    attributed_influencer_id = None
    affiliate_link_id = None

    if order_data.affiliate_code:
        affiliate_link = db.query(AffiliateLink).filter(
            AffiliateLink.affiliate_code == order_data.affiliate_code,
            AffiliateLink.product_id == product.id
        ).first()

        if affiliate_link:
            attributed_influencer_id = affiliate_link.influencer_id
            affiliate_link_id = affiliate_link.id

    # Generate order number
    order_number = generate_order_number()

    # Digital products are auto-fulfilled on order placement
    initial_status = "fulfilled" if product.is_digital else "pending"
    now = datetime.utcnow()

    # Create order
    new_order = Order(
        id=generate_uuid(),
        order_number=order_number,
        product_id=product.id,
        variant_id=variant.id if variant else None,
        quantity=order_data.quantity,
        brand_profile_id=product.brand_profile_id,
        attributed_influencer_id=attributed_influencer_id,
        affiliate_code=order_data.affiliate_code,
        affiliate_link_id=affiliate_link_id,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        customer_phone=order_data.customer_phone,
        customer_notes=order_data.customer_notes,
        unit_price=unit_price,
        total_amount=total_amount,
        currency=product.currency,
        **commission_info,
        status=initial_status,
        fulfilled_at=now if product.is_digital else None,
    )

    db.add(new_order)

    # Create commission record (pending)
    if attributed_influencer_id:
        commission = AffiliateCommission(
            id=generate_uuid(),
            order_id=new_order.id,
            influencer_id=attributed_influencer_id,
            product_id=product.id,
            gross_commission=commission_info["commission_amount"],
            platform_fee=commission_info["platform_fee_amount"],
            net_commission=commission_info["net_commission"],
            status="pending",
            commission_type=commission_info["commission_type"],
            commission_rate=commission_info["commission_rate"]
        )
        db.add(commission)

        # Update affiliate link stats
        if affiliate_link_id:
            affiliate_link = db.query(AffiliateLink).filter(
                AffiliateLink.id == affiliate_link_id
            ).first()
            if affiliate_link:
                affiliate_link.orders += 1

        # Mark click as converted
        recent_click = db.query(AffiliateClick).filter(
            AffiliateClick.affiliate_link_id == affiliate_link_id,
            AffiliateClick.converted == False
        ).order_by(AffiliateClick.clicked_at.desc()).first()

        if recent_click:
            recent_click.converted = True
            recent_click.order_id = new_order.id

    # Update product stats
    product.total_orders += 1

    # Deduct inventory if tracking
    if product.track_inventory:
        if variant:
            variant.stock_quantity -= order_data.quantity
            if variant.stock_quantity <= 0:
                variant.status = "out_of_stock"
        else:
            product.stock_quantity -= order_data.quantity
            if product.stock_quantity <= 0:
                product.in_stock = False

    try:
        db.commit()
        db.refresh(new_order)

        # === DIGITAL PRODUCT AUTO-FULFILLMENT ===
        if product.is_digital:
            # Auto-fulfill digital orders immediately
            new_order.status = "fulfilled"
            new_order.fulfilled_at = datetime.utcnow()

            # Generate secure access token for downloads
            access_token = secrets.token_urlsafe(32)

            digital_purchase = DigitalPurchase(
                id=generate_uuid(),
                order_id=new_order.id,
                product_id=product.id,
                customer_email=order_data.customer_email,
                access_token=access_token,
                download_count=0,
                max_downloads=5,
                status="completed"
            )
            db.add(digital_purchase)

            # Pay commission immediately for digital products
            if attributed_influencer_id:
                commission = db.query(AffiliateCommission).filter(
                    AffiliateCommission.order_id == new_order.id,
                    AffiliateCommission.status == "pending"
                ).first()

                if commission:
                    influencer = db.query(InfluencerProfile).filter(
                        InfluencerProfile.id == commission.influencer_id
                    ).first()

                    wallet = db.query(Wallet).filter(
                        Wallet.user_id == influencer.user_id
                    ).first()

                    if not wallet:
                        wallet = Wallet(
                            id=generate_uuid(),
                            user_id=influencer.user_id,
                            balance=0,
                            hold_balance=0,
                            total_earned=0,
                            total_spent=0
                        )
                        db.add(wallet)
                        db.flush()

                    wallet_transaction = WalletTransaction(
                        id=generate_uuid(),
                        to_wallet_id=wallet.id,
                        amount=int(commission.net_commission * 100),
                        fee=int(commission.platform_fee * 100),
                        net_amount=int(commission.net_commission * 100),
                        transaction_type="affiliate_commission",
                        status="completed",
                        payment_method="affiliate_commission",
                        description=f"Digital sale commission - order #{new_order.order_number}",
                        completed_at=datetime.utcnow()
                    )
                    db.add(wallet_transaction)
                    db.flush()

                    wallet.balance += int(commission.net_commission * 100)
                    wallet.total_earned += int(commission.net_commission * 100)

                    commission.status = "paid"
                    commission.paid_at = datetime.utcnow()
                    commission.wallet_transaction_id = wallet_transaction.id

                    if order_data.affiliate_code and affiliate_link_id:
                        aff_link = db.query(AffiliateLink).filter(
                            AffiliateLink.id == affiliate_link_id
                        ).first()
                        if aff_link:
                            aff_link.total_sales_amount += total_amount
                            aff_link.total_commission_earned += commission.net_commission

                product.total_sales_amount += total_amount

            db.commit()
            db.refresh(new_order)

            # Return response with access token for digital products
            response_data = OrderResponse.from_orm(new_order)
            response_data.brand_contact = BrandContactInfo(
                whatsapp_number=product.brand_profile.whatsapp_number,
                business_location=product.brand_profile.business_location,
                business_hours=product.brand_profile.business_hours,
                preferred_contact_method=product.brand_profile.preferred_contact_method,
                phone_number=product.brand_profile.phone_number,
                business_email=product.brand_profile.business_email,
                website_url=product.brand_profile.website_url,
                instagram_handle=product.brand_profile.instagram_handle,
                facebook_page=product.brand_profile.facebook_page
            )
            return response_data

        # === PHYSICAL PRODUCT - Return brand contact info ===
        # Load brand profile for contact info
        brand_profile = db.query(BrandProfile).filter(
            BrandProfile.id == product.brand_profile_id
        ).first()

        # Prepare response with brand contact
        response_data = OrderResponse.from_orm(new_order)
        response_data.brand_contact = BrandContactInfo(
            whatsapp_number=brand_profile.whatsapp_number,
            business_location=brand_profile.business_location,
            business_hours=brand_profile.business_hours,
            preferred_contact_method=brand_profile.preferred_contact_method,
            phone_number=brand_profile.phone_number,
            business_email=brand_profile.business_email,
            website_url=brand_profile.website_url,
            instagram_handle=brand_profile.instagram_handle,
            facebook_page=brand_profile.facebook_page
        )

        # For digital products: auto-pay commission immediately (order is already fulfilled)
        if product.is_digital and attributed_influencer_id:
            try:
                commission = db.query(AffiliateCommission).filter(
                    AffiliateCommission.order_id == new_order.id,
                    AffiliateCommission.status == "pending"
                ).first()

                if commission:
                    influencer = db.query(InfluencerProfile).filter(
                        InfluencerProfile.id == commission.influencer_id
                    ).first()

                    if influencer:
                        wallet = db.query(Wallet).filter(
                            Wallet.user_id == influencer.user_id
                        ).first()

                        if not wallet:
                            wallet = Wallet(
                                id=generate_uuid(),
                                user_id=influencer.user_id,
                                balance=0,
                                hold_balance=0,
                                total_earned=0,
                                total_spent=0
                            )
                            db.add(wallet)
                            db.flush()

                        commission_cents = int(commission.net_commission * 100)
                        wallet_tx = WalletTransaction(
                            id=generate_uuid(),
                            to_wallet_id=wallet.id,
                            amount=commission_cents,
                            fee=int(commission.platform_fee * 100),
                            net_amount=commission_cents,
                            transaction_type="affiliate_commission",
                            status="completed",
                            payment_method="affiliate_commission",
                            description=f"Commission from digital order #{new_order.order_number}",
                            completed_at=now,
                        )
                        db.add(wallet_tx)
                        db.flush()

                        wallet.balance += commission_cents
                        wallet.total_earned = (wallet.total_earned or 0) + commission_cents

                        commission.status = "paid"
                        commission.paid_at = now
                        commission.wallet_transaction_id = wallet_tx.id

                        db.commit()
            except Exception:
                # Don't fail the order if commission payout has an issue
                db.rollback()

        # For digital products: include presigned download URL in the response
        if product.is_digital and product.digital_file_key:
            try:
                response_data.download_url = generate_download_url(product.digital_file_key)
                response_data.download_file_name = product.digital_file_name
            except Exception:
                pass  # Don't fail the order if URL generation has an issue

        return response_data

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place order: {str(e)}"
        )


# ============================================================================
# PAYMENT PROCESSING WITH PAYSTACK
# ============================================================================

@router.post("/initialize-payment")
async def initialize_order_payment(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    """
    Initialize Paystack payment for a product purchase.
    Returns payment URL for customer to complete payment.
    """
    # Get product
    product = db.query(Product).filter(
        Product.id == order_data.product_id,
        Product.status == "active"
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not available"
        )

    # Get variant if specified
    variant = None
    if order_data.variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == order_data.variant_id,
            ProductVariant.product_id == product.id
        ).first()

    # Check stock if tracking
    if product.track_inventory:
        available_stock = variant.stock_quantity if variant else product.stock_quantity
        if available_stock is not None and available_stock < order_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Only {available_stock} available."
            )

    # Calculate pricing
    unit_price = variant.price if (variant and variant.price) else product.price
    total_amount = unit_price * order_data.quantity

    # Convert to kobo (Paystack uses lowest currency unit)
    amount_in_kobo = int(float(total_amount) * 100)

    # Build callback URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    callback_url = f"{frontend_url}/shop/payment/verify"

    # Prepare metadata
    metadata = {
        "product_id": order_data.product_id,
        "product_name": product.name,
        "quantity": order_data.quantity,
        "variant_id": order_data.variant_id,
        "customer_name": order_data.customer_name,
        "customer_phone": order_data.customer_phone,
        "customer_notes": order_data.customer_notes,
        "affiliate_code": order_data.affiliate_code,
        "is_digital": product.is_digital,
        "type": "product_purchase",
        "custom_fields": [
            {
                "display_name": "Product",
                "variable_name": "product_name",
                "value": product.name
            },
            {
                "display_name": "Quantity",
                "variable_name": "quantity",
                "value": str(order_data.quantity)
            }
        ]
    }

    try:
        # Initialize Paystack transaction
        paystack = PaystackService()
        response = paystack.initialize_transaction(
            email=order_data.customer_email,
            amount=amount_in_kobo,
            callback_url=callback_url,
            metadata=metadata
        )

        if not response.get("status"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize payment"
            )

        data = response.get("data", {})

        return {
            "status": "success",
            "authorization_url": data.get("authorization_url"),
            "access_code": data.get("access_code"),
            "reference": data.get("reference"),
            "amount": total_amount,
            "currency": product.currency or "KES"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )


@router.get("/verify-payment/{reference}")
async def verify_order_payment(
    reference: str,
    db: Session = Depends(get_db)
):
    """
    Verify Paystack payment and create order if successful.
    """
    try:
        # Verify transaction with Paystack
        paystack = PaystackService()
        response = paystack.verify_transaction(reference)

        if not response.get("status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed"
            )

        data = response.get("data", {})

        # Check if payment was successful
        if data.get("status") != "success":
            return {
                "status": "failed",
                "reference": reference,
                "amount": data.get("amount", 0),
                "currency": data.get("currency", "KES"),
                "message": "Payment was not successful"
            }

        # Check if order already exists for this reference
        existing_order = db.query(Order).filter(
            Order.payment_reference == reference
        ).first()

        if existing_order:
            # Return existing order
            response_data = {
                "status": "success",
                "reference": reference,
                "amount": data.get("amount", 0),
                "currency": data.get("currency", "KES"),
                "order_id": existing_order.id,
                "order_number": existing_order.order_number,
                "message": "Order already created"
            }

            # Add download URL for digital products
            product = db.query(Product).filter(
                Product.id == existing_order.product_id
            ).first()

            if product and product.is_digital and product.digital_file_key:
                try:
                    response_data["download_url"] = generate_download_url(product.digital_file_key)
                    response_data["download_file_name"] = product.digital_file_name
                except Exception:
                    pass

            # Add brand contact for physical products
            if product and not product.is_digital:
                brand_profile = db.query(BrandProfile).filter(
                    BrandProfile.id == product.brand_profile_id
                ).first()

                if brand_profile:
                    response_data["brand_contact"] = {
                        "whatsapp_number": brand_profile.whatsapp_number,
                        "business_location": brand_profile.business_location,
                        "business_hours": brand_profile.business_hours,
                        "preferred_contact_method": brand_profile.preferred_contact_method,
                        "phone_number": brand_profile.phone_number,
                        "business_email": brand_profile.business_email,
                        "website_url": brand_profile.website_url,
                        "instagram_handle": brand_profile.instagram_handle,
                        "facebook_page": brand_profile.facebook_page
                    }

            return response_data

        # Extract metadata
        metadata = data.get("metadata", {})

        # Get product
        product = db.query(Product).filter(
            Product.id == metadata.get("product_id")
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Get variant if specified
        variant = None
        if metadata.get("variant_id"):
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == metadata.get("variant_id"),
                ProductVariant.product_id == product.id
            ).first()

        # Calculate pricing
        unit_price = variant.price if (variant and variant.price) else product.price
        quantity = int(metadata.get("quantity", 1))
        total_amount = unit_price * quantity

        # Calculate commission
        commission_info = calculate_commission(product, total_amount)

        # Attribution - check affiliate code
        attributed_influencer_id = None
        affiliate_link_id = None

        if metadata.get("affiliate_code"):
            affiliate_link = db.query(AffiliateLink).filter(
                AffiliateLink.affiliate_code == metadata.get("affiliate_code"),
                AffiliateLink.product_id == product.id
            ).first()

            if affiliate_link:
                attributed_influencer_id = affiliate_link.influencer_id
                affiliate_link_id = affiliate_link.id

        # Generate order number
        order_number = generate_order_number()

        # Digital products are auto-fulfilled
        initial_status = "fulfilled" if product.is_digital else "pending"
        now = datetime.utcnow()

        # Create order
        new_order = Order(
            id=generate_uuid(),
            order_number=order_number,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            quantity=quantity,
            brand_profile_id=product.brand_profile_id,
            attributed_influencer_id=attributed_influencer_id,
            affiliate_code=metadata.get("affiliate_code"),
            affiliate_link_id=affiliate_link_id,
            customer_name=metadata.get("customer_name"),
            customer_email=data.get("customer", {}).get("email"),
            customer_phone=metadata.get("customer_phone"),
            customer_notes=metadata.get("customer_notes"),
            unit_price=unit_price,
            total_amount=total_amount,
            currency=product.currency,
            payment_status="paid",
            payment_reference=reference,
            payment_method="paystack",
            paid_at=now,
            **commission_info,
            status=initial_status,
            fulfilled_at=now if product.is_digital else None,
        )

        db.add(new_order)

        # Create commission record (pending for physical, paid for digital)
        if attributed_influencer_id:
            commission = AffiliateCommission(
                id=generate_uuid(),
                order_id=new_order.id,
                influencer_id=attributed_influencer_id,
                product_id=product.id,
                gross_commission=commission_info["commission_amount"],
                platform_fee=commission_info["platform_fee_amount"],
                net_commission=commission_info["net_commission"],
                status="pending",
                commission_type=commission_info["commission_type"],
                commission_rate=commission_info["commission_rate"]
            )
            db.add(commission)

            # Update affiliate link stats
            if affiliate_link_id:
                affiliate_link = db.query(AffiliateLink).filter(
                    AffiliateLink.id == affiliate_link_id
                ).first()
                if affiliate_link:
                    affiliate_link.orders += 1

            # Mark click as converted
            recent_click = db.query(AffiliateClick).filter(
                AffiliateClick.affiliate_link_id == affiliate_link_id,
                AffiliateClick.converted == False
            ).order_by(AffiliateClick.clicked_at.desc()).first()

            if recent_click:
                recent_click.converted = True
                recent_click.order_id = new_order.id

        # Update product stats
        product.total_orders += 1

        # Deduct inventory if tracking
        if product.track_inventory:
            if variant:
                variant.stock_quantity -= quantity
                if variant.stock_quantity <= 0:
                    variant.status = "out_of_stock"
            else:
                product.stock_quantity -= quantity
                if product.stock_quantity <= 0:
                    product.in_stock = False

        # For digital products: auto-pay commission immediately
        if product.is_digital and attributed_influencer_id:
            try:
                commission = db.query(AffiliateCommission).filter(
                    AffiliateCommission.order_id == new_order.id,
                    AffiliateCommission.status == "pending"
                ).first()

                if commission:
                    influencer = db.query(InfluencerProfile).filter(
                        InfluencerProfile.id == commission.influencer_id
                    ).first()

                    if influencer:
                        wallet = db.query(Wallet).filter(
                            Wallet.user_id == influencer.user_id
                        ).first()

                        if not wallet:
                            wallet = Wallet(
                                id=generate_uuid(),
                                user_id=influencer.user_id,
                                balance=0,
                                hold_balance=0,
                                total_earned=0,
                                total_spent=0
                            )
                            db.add(wallet)
                            db.flush()

                        commission_cents = int(commission.net_commission * 100)
                        wallet_tx = WalletTransaction(
                            id=generate_uuid(),
                            to_wallet_id=wallet.id,
                            amount=commission_cents,
                            fee=int(commission.platform_fee * 100),
                            net_amount=commission_cents,
                            transaction_type="affiliate_commission",
                            status="completed",
                            payment_method="affiliate_commission",
                            description=f"Commission from digital order #{new_order.order_number}",
                            completed_at=now,
                        )
                        db.add(wallet_tx)
                        db.flush()

                        wallet.balance += commission_cents
                        wallet.total_earned = (wallet.total_earned or 0) + commission_cents

                        commission.status = "paid"
                        commission.paid_at = now
                        commission.wallet_transaction_id = wallet_tx.id
            except Exception:
                # Don't fail the order if commission payout has an issue
                pass

        db.commit()
        db.refresh(new_order)

        # Prepare response
        response_data = {
            "status": "success",
            "reference": reference,
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "KES"),
            "order_id": new_order.id,
            "order_number": new_order.order_number,
            "message": "Payment successful, order created"
        }

        # For digital products: include presigned download URL
        if product.is_digital and product.digital_file_key:
            try:
                response_data["download_url"] = generate_download_url(product.digital_file_key)
                response_data["download_file_name"] = product.digital_file_name
            except Exception:
                pass

        # For physical products: include brand contact info
        if not product.is_digital:
            brand_profile = db.query(BrandProfile).filter(
                BrandProfile.id == product.brand_profile_id
            ).first()

            if brand_profile:
                response_data["brand_contact"] = {
                    "whatsapp_number": brand_profile.whatsapp_number,
                    "business_location": brand_profile.business_location,
                    "business_hours": brand_profile.business_hours,
                    "preferred_contact_method": brand_profile.preferred_contact_method,
                    "phone_number": brand_profile.phone_number,
                    "business_email": brand_profile.business_email,
                    "website_url": brand_profile.website_url,
                    "instagram_handle": brand_profile.instagram_handle,
                    "facebook_page": brand_profile.facebook_page
                }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )


# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

@router.get("/my-orders", response_model=List[OrderResponse])
async def get_my_orders_as_customer(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Get orders by customer email (public endpoint).
    Customer can track their orders.
    """
    orders = db.query(Order).filter(
        Order.customer_email == email
    ).order_by(Order.created_at.desc()).all()

    return orders


@router.get("/brand/orders", response_model=List[OrderResponse])
async def get_brand_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all orders for brand's products."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        return []

    query = db.query(Order).filter(
        Order.brand_profile_id == brand_profile.id
    )

    if status:
        query = query.filter(Order.status == status)

    return query.order_by(Order.created_at.desc()).all()


@router.get("/influencer/orders", response_model=List[OrderResponse])
async def get_influencer_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all orders attributed to influencer."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        return []

    query = db.query(Order).filter(
        Order.attributed_influencer_id == influencer.id
    )

    if status:
        query = query.filter(Order.status == status)

    return query.order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get order details. Only brand or attributed influencer can view."""
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check authorization
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    is_brand = brand_profile and order.brand_profile_id == brand_profile.id
    is_influencer = influencer and order.attributed_influencer_id == influencer.id

    if not (is_brand or is_influencer or current_user.role == UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )

    return order


# ============================================================================
# ORDER STATUS UPDATES & COMMISSION PAYOUT
# ============================================================================

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update order status.
    Only brand can update.
    When marked as 'fulfilled', commission is paid immediately.
    """
    # Verify brand ownership
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Brand profile required."
        )

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.brand_profile_id == brand_profile.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or not authorized"
        )

    old_status = order.status

    # Update status
    order.status = status_update.status
    order.brand_notes = status_update.brand_notes or order.brand_notes

    if status_update.status == "contacted":
        order.contacted_at = datetime.utcnow()
    elif status_update.status == "fulfilled":
        order.fulfilled_at = datetime.utcnow()
    elif status_update.status == "cancelled":
        order.cancelled_at = datetime.utcnow()
        order.cancellation_reason = status_update.cancellation_reason

    # COMMISSION PAYOUT - Immediately when fulfilled
    if status_update.status == "fulfilled" and old_status != "fulfilled":
        commission = db.query(AffiliateCommission).filter(
            AffiliateCommission.order_id == order_id,
            AffiliateCommission.status == "pending"
        ).first()

        if commission:
            try:
                # Get influencer's wallet
                influencer = db.query(InfluencerProfile).filter(
                    InfluencerProfile.id == commission.influencer_id
                ).first()

                wallet = db.query(Wallet).filter(
                    Wallet.user_id == influencer.user_id
                ).first()

                if not wallet:
                    # Create wallet if doesn't exist
                    wallet = Wallet(
                        id=generate_uuid(),
                        user_id=influencer.user_id,
                        balance=0,
                        hold_balance=0,
                        total_earned=0,
                        total_spent=0
                    )
                    db.add(wallet)
                    db.flush()

                # Create wallet transaction
                wallet_transaction = WalletTransaction(
                    id=generate_uuid(),
                    to_wallet_id=wallet.id,
                    amount=int(commission.net_commission * 100),  # Convert to cents
                    fee=int(commission.platform_fee * 100),
                    net_amount=int(commission.net_commission * 100),
                    transaction_type="affiliate_commission",
                    status="completed",
                    payment_method="affiliate_commission",
                    description=f"Commission from order #{order.order_number}",
                    completed_at=datetime.utcnow()
                )
                db.add(wallet_transaction)
                db.flush()

                # Update wallet balance
                wallet.balance += int(commission.net_commission * 100)
                wallet.total_earned += int(commission.net_commission * 100)

                # Update commission record
                commission.status = "paid"
                commission.paid_at = datetime.utcnow()
                commission.wallet_transaction_id = wallet_transaction.id

                # Update affiliate link stats
                if order.affiliate_link_id:
                    affiliate_link = db.query(AffiliateLink).filter(
                        AffiliateLink.id == order.affiliate_link_id
                    ).first()
                    if affiliate_link:
                        affiliate_link.total_sales_amount += order.total_amount
                        affiliate_link.total_commission_earned += commission.net_commission

                # Update product stats
                product = db.query(Product).filter(
                    Product.id == order.product_id
                ).first()
                if product:
                    product.total_sales_amount += order.total_amount

            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process commission: {str(e)}"
                )

    # Handle cancellation - cancel commission
    if status_update.status == "cancelled" and old_status != "cancelled":
        commission = db.query(AffiliateCommission).filter(
            AffiliateCommission.order_id == order_id
        ).first()

        if commission and commission.status == "pending":
            commission.status = "cancelled"

    try:
        db.commit()
        db.refresh(order)
        return order
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {str(e)}"
        )


@router.delete("/{order_id}", response_model=SuccessResponse)
async def delete_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete order. Only for pending orders."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.brand_profile_id == brand_profile.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete pending orders"
        )

    db.delete(order)
    db.commit()

    return SuccessResponse(
        success=True,
        message="Order deleted successfully"
    )
