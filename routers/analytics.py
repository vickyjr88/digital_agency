from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import datetime, timedelta

from database.config import get_db
from database.models import User, Transaction, Content, Brand, PaymentStatus
from database.marketplace_models import Campaign, InfluencerProfile
from auth.decorators import require_user_type, AuthError
from auth.roles import UserType as UserTypeRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=dict)
async def get_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Get comprehensive analytics dashboard data.
    """
    # 1. User Stats
    total_users = db.query(User).count()
    new_users_today = db.query(User).filter(
        func.date(User.created_at) == datetime.utcnow().date()
    ).count()
    
    # 2. Revenue (SaaS + Marketplace could be separate, but let's aggregate for now)
    total_revenue = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == PaymentStatus.SUCCESS
    ).scalar() or 0
    
    # Revenue this month
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    revenue_this_month = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == PaymentStatus.SUCCESS,
        extract('month', Transaction.created_at) == current_month,
        extract('year', Transaction.created_at) == current_year
    ).scalar() or 0
    
    # 3. Content Stats
    total_content = db.query(Content).count()
    content_today = db.query(Content).filter(
        func.date(Content.generated_at) == datetime.utcnow().date()
    ).count()
    
    # 4. Marketplace Stats
    total_influencers = db.query(InfluencerProfile).count()
    total_campaigns = db.query(Campaign).count()
    
    return {
        "users": {
            "total": total_users,
            "new_today": new_users_today
        },
        "revenue": {
            "total": total_revenue,
            "this_month": revenue_this_month
        },
        "content": {
            "total": total_content,
            "generated_today": content_today
        },
        "marketplace": {
            "influencers": total_influencers,
            "campaigns": total_campaigns
        }
    }

@router.get("/revenue-chart", response_model=List[dict])
async def get_revenue_chart(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Get revenue over time (daily) for the last N days.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Aggregate daily revenue
    # Using func.date() for SQLite/Postgres compatibility usually works, but specialized for Postgres might be needed if using 'date' cast explicitly.
    # Assuming Postgres per user context.
    
    results = db.query(
        func.date(Transaction.created_at).label("date"),
        func.sum(Transaction.amount).label("amount")
    ).filter(
        Transaction.created_at >= start_date,
        Transaction.status == PaymentStatus.SUCCESS
    ).group_by(
        func.date(Transaction.created_at)
    ).order_by(
        func.date(Transaction.created_at)
    ).all()
    
    # Fill in missing days
    data_map = {str(r.date): r.amount for r in results}
    chart_data = []
    
    for i in range(days):
        d = (start_date + timedelta(days=i)).date()
        d_str = str(d)
        chart_data.append({
            "date": d_str,
            "amount": data_map.get(d_str, 0)
        })
        
    return chart_data

@router.get("/users-chart", response_model=List[dict])
async def get_users_chart(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_type(UserTypeRole.ADMIN))
):
    """
    Get user growth over time (daily) for the last N days.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count")
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by(
        func.date(User.created_at)
    ).all()
    
    data_map = {str(r.date): r.count for r in results}
    chart_data = []
    
    for i in range(days):
        d = (start_date + timedelta(days=i)).date()
        d_str = str(d)
        chart_data.append({
            "date": d_str,
            "count": data_map.get(d_str, 0)
        })
        
    return chart_data
