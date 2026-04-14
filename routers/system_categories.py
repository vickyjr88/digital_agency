from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from database.config import get_db
from database.models import User
from database.affiliate_models import SystemCategory, CategoryType
from auth.dependencies import get_current_user

router = APIRouter(prefix="/categories", tags=["System Categories"])

# Schemas
class SystemCategoryBase(BaseModel):
    name: str
    type: CategoryType

class SystemCategoryCreate(SystemCategoryBase):
    pass

class SystemCategoryResponse(SystemCategoryBase):
    id: str
    slug: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Helper string -> slug
def create_slug(name: str) -> str:
    import re
    slug = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug

@router.get("/", response_model=List[SystemCategoryResponse])
def get_categories(
    type: Optional[CategoryType] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get all categories (public/all users)"""
    query = db.query(SystemCategory)
    if not include_inactive:
        query = query.filter(SystemCategory.is_active == True)
    if type:
        query = query.filter(SystemCategory.type == type)
    
    # Order alphabetically
    return query.order_by(SystemCategory.name).all()

@router.post("/", response_model=SystemCategoryResponse)
def create_category(
    category_in: SystemCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new category (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage categories")
    
    slug = create_slug(category_in.name)
    
    # Check if exists
    existing = db.query(SystemCategory).filter(
        SystemCategory.slug == slug, 
        SystemCategory.type == category_in.type
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
        
    db_cat = SystemCategory(
        name=category_in.name,
        slug=slug,
        type=category_in.type
    )
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete or deactivate a category (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage categories")
        
    db_cat = db.query(SystemCategory).filter(SystemCategory.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    db.delete(db_cat)
    db.commit()
    return {"message": "Category deleted"}
