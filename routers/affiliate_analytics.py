# Analytics Endpoints for Affiliate Commerce

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from database.models import User
from database.marketplace_models import InfluencerProfile
from database.affiliate_models import (
    Product,
    BrandProfile,
    Order,
    AffiliateLink,
    AffiliateClick,
    AffiliateCommission
)
from schemas.affiliate import (
    InfluencerDashboardStats,
    BrandDashboardStats,
    TopPerformingProduct,
    TopPerformingAffiliate
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/affiliate-analytics", tags=["Affiliate Analytics"])


# ============================================================================
# INFLUENCER DASHBOARD
# ============================================================================

@router.get("/influencer/dashboard", response_model=InfluencerDashboardStats)
async def get_influencer_dashboard(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get influencer's affiliate performance dashboard."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Influencer profile not found"
        )

    # Date range
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get total clicks
    total_clicks = db.query(func.count(AffiliateClick.id)).filter(
        AffiliateClick.influencer_id == influencer.id,
        AffiliateClick.clicked_at >= start_date
    ).scalar() or 0

    # Get orders
    orders_query = db.query(Order).filter(
        Order.attributed_influencer_id == influencer.id,
        Order.created_at >= start_date
    )

    total_orders = orders_query.count()
    total_orders_fulfilled = orders_query.filter(Order.status == "fulfilled").count()

    # Get sales total
    total_sales = db.query(func.sum(Order.total_amount)).filter(
        Order.attributed_influencer_id == influencer.id,
        Order.status == "fulfilled",
        Order.created_at >= start_date
    ).scalar() or Decimal("0.00")

    # Get commissions
    commissions_query = db.query(AffiliateCommission).filter(
        AffiliateCommission.influencer_id == influencer.id
    )

    total_commissions_earned = db.query(func.sum(AffiliateCommission.net_commission)).filter(
        AffiliateCommission.influencer_id == influencer.id,
        AffiliateCommission.status == "paid"
    ).scalar() or Decimal("0.00")

    pending_commissions = db.query(func.sum(AffiliateCommission.net_commission)).filter(
        AffiliateCommission.influencer_id == influencer.id,
        AffiliateCommission.status == "pending"
    ).scalar() or Decimal("0.00")

    # Get available balance from wallet
    from database.marketplace_models import Wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    available_to_withdraw = Decimal(wallet.balance / 100) if wallet else Decimal("0.00")

    # Calculate metrics
    conversion_rate = (total_orders / total_clicks * 100) if total_clicks > 0 else Decimal("0.00")
    average_order_value = (total_sales / total_orders_fulfilled) if total_orders_fulfilled > 0 else Decimal("0.00")

    return InfluencerDashboardStats(
        total_clicks=total_clicks,
        total_orders=total_orders,
        total_orders_fulfilled=total_orders_fulfilled,
        total_sales=total_sales,
        total_commissions_earned=total_commissions_earned,
        pending_commissions=pending_commissions,
        available_to_withdraw=available_to_withdraw,
        conversion_rate=round(conversion_rate, 2),
        average_order_value=round(average_order_value, 2)
    )


@router.get("/influencer/top-products", response_model=list[TopPerformingProduct])
async def get_influencer_top_products(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get influencer's top performing products."""
    influencer = db.query(InfluencerProfile).filter(
        InfluencerProfile.user_id == current_user.id
    ).first()

    if not influencer:
        return []

    # Aggregate by product
    results = db.query(
        Order.product_id,
        Product.name,
        func.count(Order.id).label('sales_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.sum(AffiliateCommission.net_commission).label('commission_earned')
    ).join(
        Product, Order.product_id == Product.id
    ).outerjoin(
        AffiliateCommission, Order.id == AffiliateCommission.order_id
    ).filter(
        Order.attributed_influencer_id == influencer.id,
        Order.status == "fulfilled"
    ).group_by(
        Order.product_id, Product.name
    ).order_by(
        func.count(Order.id).desc()
    ).limit(limit).all()

    return [
        TopPerformingProduct(
            product_id=r[0],
            product_name=r[1],
            sales_count=r[2] or 0,
            total_sales=r[3] or Decimal("0.00"),
            commission_earned=r[4] or Decimal("0.00")
        )
        for r in results
    ]


# ============================================================================
# BRAND DASHBOARD
# ============================================================================

@router.get("/brand/dashboard", response_model=BrandDashboardStats)
async def get_brand_dashboard(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get brand's affiliate program performance dashboard."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found"
        )

    # Date range
    start_date = datetime.utcnow() - timedelta(days=days)

    # Products stats
    total_products = db.query(func.count(Product.id)).filter(
        Product.brand_profile_id == brand_profile.id
    ).scalar() or 0

    active_products = db.query(func.count(Product.id)).filter(
        Product.brand_profile_id == brand_profile.id,
        Product.status == "active"
    ).scalar() or 0

    # Affiliates
    total_affiliates = db.query(func.count(func.distinct(AffiliateLink.influencer_id))).filter(
        AffiliateLink.product_id.in_(
            db.query(Product.id).filter(Product.brand_profile_id == brand_profile.id)
        )
    ).scalar() or 0

    # Active affiliates (made at least one sale)
    active_affiliates = db.query(func.count(func.distinct(Order.attributed_influencer_id))).filter(
        Order.brand_profile_id == brand_profile.id,
        Order.attributed_influencer_id.isnot(None),
        Order.created_at >= start_date
    ).scalar() or 0

    # Clicks
    total_clicks = db.query(func.count(AffiliateClick.id)).filter(
        AffiliateClick.product_id.in_(
            db.query(Product.id).filter(Product.brand_profile_id == brand_profile.id)
        ),
        AffiliateClick.clicked_at >= start_date
    ).scalar() or 0

    # Orders
    orders_query = db.query(Order).filter(
        Order.brand_profile_id == brand_profile.id,
        Order.created_at >= start_date
    )

    total_orders = orders_query.count()
    total_orders_fulfilled = orders_query.filter(Order.status == "fulfilled").count()

    # Sales
    total_sales = db.query(func.sum(Order.total_amount)).filter(
        Order.brand_profile_id == brand_profile.id,
        Order.status == "fulfilled",
        Order.created_at >= start_date
    ).scalar() or Decimal("0.00")

    # Commissions paid
    total_commissions_paid = db.query(func.sum(AffiliateCommission.net_commission)).filter(
        AffiliateCommission.product_id.in_(
            db.query(Product.id).filter(Product.brand_profile_id == brand_profile.id)
        ),
        AffiliateCommission.status == "paid"
    ).scalar() or Decimal("0.00")

    # Platform fees
    total_platform_fees = db.query(func.sum(AffiliateCommission.platform_fee)).filter(
        AffiliateCommission.product_id.in_(
            db.query(Product.id).filter(Product.brand_profile_id == brand_profile.id)
        ),
        AffiliateCommission.status == "paid"
    ).scalar() or Decimal("0.00")

    # Conversion rate
    conversion_rate = (total_orders / total_clicks * 100) if total_clicks > 0 else Decimal("0.00")

    return BrandDashboardStats(
        total_products=total_products,
        active_products=active_products,
        total_affiliates=total_affiliates,
        active_affiliates=active_affiliates,
        total_clicks=total_clicks,
        total_orders=total_orders,
        total_orders_fulfilled=total_orders_fulfilled,
        total_sales=total_sales,
        total_commissions_paid=total_commissions_paid,
        total_platform_fees=total_platform_fees,
        conversion_rate=round(conversion_rate, 2)
    )


@router.get("/brand/top-affiliates", response_model=list[TopPerformingAffiliate])
async def get_brand_top_affiliates(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get brand's top performing affiliates."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        return []

    # Aggregate by influencer
    results = db.query(
        Order.attributed_influencer_id,
        InfluencerProfile.display_name,
        func.count(Order.id).label('sales_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.sum(AffiliateCommission.net_commission).label('commission_earned')
    ).join(
        InfluencerProfile, Order.attributed_influencer_id == InfluencerProfile.id
    ).outerjoin(
        AffiliateCommission, Order.id == AffiliateCommission.order_id
    ).filter(
        Order.brand_profile_id == brand_profile.id,
        Order.attributed_influencer_id.isnot(None),
        Order.status == "fulfilled"
    ).group_by(
        Order.attributed_influencer_id, InfluencerProfile.display_name
    ).order_by(
        func.count(Order.id).desc()
    ).limit(limit).all()

    return [
        TopPerformingAffiliate(
            influencer_id=r[0],
            display_name=r[1],
            sales_count=r[2] or 0,
            total_sales=r[3] or Decimal("0.00"),
            commission_earned=r[4] or Decimal("0.00")
        )
        for r in results
    ]


@router.get("/brand/top-products", response_model=list[TopPerformingProduct])
async def get_brand_top_products(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get brand's top performing products."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        return []

    results = db.query(
        Product.id,
        Product.name,
        func.count(Order.id).label('sales_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.sum(AffiliateCommission.gross_commission).label('total_commission')
    ).outerjoin(
        Order, and_(
            Order.product_id == Product.id,
            Order.status == "fulfilled"
        )
    ).outerjoin(
        AffiliateCommission, Order.id == AffiliateCommission.order_id
    ).filter(
        Product.brand_profile_id == brand_profile.id
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.count(Order.id).desc()
    ).limit(limit).all()

    return [
        TopPerformingProduct(
            product_id=r[0],
            product_name=r[1],
            sales_count=r[2] or 0,
            total_sales=r[3] or Decimal("0.00"),
            commission_earned=r[4] or Decimal("0.00")
        )
        for r in results
    ]
