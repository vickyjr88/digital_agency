# Product Catalog Endpoints for Affiliate Commerce

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from decimal import Decimal
import re

from database.models import User
from database.affiliate_models import (
    BrandProfile,
    Product,
    ProductVariant,
    AffiliateLink
)
from schemas.affiliate import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListItem,
    ProductVariantCreate,
    ProductVariantResponse,
    SuccessResponse,
    PaginatedResponse
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/products", tags=["Products"])


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from product name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def ensure_unique_slug(db: Session, base_slug: str, product_id: Optional[str] = None) -> str:
    """Ensure slug is unique by appending counter if needed."""
    slug = base_slug
    counter = 1

    while True:
        query = db.query(Product).filter(Product.slug == slug)
        if product_id:
            query = query.filter(Product.id != product_id)

        if not query.first():
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product.
    Requires brand profile to be set up first.
    """
    # Get brand profile
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand profile required. Create one first at /api/brand-profiles/"
        )

    # Generate slug
    base_slug = generate_slug(product_data.name)
    slug = ensure_unique_slug(db, base_slug)

    # Create product
    product_dict = product_data.dict(exclude={'variants'})
    new_product = Product(
        id=generate_uuid(),
        brand_profile_id=brand_profile.id,
        slug=slug,
        **product_dict
    )

    db.add(new_product)
    db.flush()  # Get product ID before adding variants

    # Create variants if provided
    if product_data.has_variants and product_data.variants:
        for variant_data in product_data.variants:
            variant = ProductVariant(
                id=generate_uuid(),
                product_id=new_product.id,
                **variant_data.dict()
            )
            db.add(variant)

    try:
        db.commit()
        db.refresh(new_product)
        return new_product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create product: {str(e)}"
        )


@router.get("/", response_model=List[ProductListItem])
async def list_products(
    category: Optional[str] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None,
    min_commission: Optional[float] = None,
    max_commission: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all products (marketplace view).
    Public endpoint for influencers to browse products.
    """
    query = db.query(Product)

    # Filters
    if status:
        query = query.filter(Product.status == status)

    if category:
        query = query.filter(Product.category == category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )

    if min_commission is not None:
        query = query.filter(
            or_(
                Product.commission_rate >= min_commission,
                Product.fixed_commission >= min_commission
            )
        )

    # Pagination
    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return products


@router.get("/my-products", response_model=List[ProductResponse])
async def list_my_products(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all products belonging to current brand."""
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        return []

    query = db.query(Product).filter(
        Product.brand_profile_id == brand_profile.id
    ).options(joinedload(Product.variants))

    if status:
        query = query.filter(Product.status == status)

    return query.all()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get product details by ID."""
    product = db.query(Product).filter(
        Product.id == product_id
    ).options(joinedload(Product.variants)).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get product details by slug (for customer view)."""
    product = db.query(Product).filter(
        Product.slug == slug
    ).options(joinedload(Product.variants)).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update product. Only brand owner can update."""
    # Get brand profile
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Get product
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.brand_profile_id == brand_profile.id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you don't have permission"
        )

    # Update fields
    update_data = product_data.dict(exclude_unset=True)

    # Update slug if name changed
    if 'name' in update_data:
        base_slug = generate_slug(update_data['name'])
        product.slug = ensure_unique_slug(db, base_slug, product_id)

    for field, value in update_data.items():
        if field != 'name':  # Already handled slug
            setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
        return product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update product: {str(e)}"
        )


@router.delete("/{product_id}", response_model=SuccessResponse)
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete product (soft delete - archives it).
    Only brand owner can delete.
    """
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.brand_profile_id == brand_profile.id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Soft delete - archive instead of deleting
    product.status = "archived"
    db.commit()

    return SuccessResponse(
        success=True,
        message="Product archived successfully"
    )


@router.get("/categories/list", response_model=List[str])
async def list_categories(db: Session = Depends(get_db)):
    """Get list of all product categories."""
    categories = db.query(Product.category).distinct().all()
    return [cat[0] for cat in categories if cat[0]]


@router.post("/{product_id}/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def add_product_variant(
    product_id: str,
    variant_data: ProductVariantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a variant to a product."""
    # Verify ownership
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.brand_profile_id == brand_profile.id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not authorized"
        )

    # Create variant
    variant = ProductVariant(
        id=generate_uuid(),
        product_id=product_id,
        **variant_data.dict()
    )

    product.has_variants = True

    try:
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return variant
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add variant: {str(e)}"
        )


@router.get("/{product_id}/affiliates-count", response_model=dict)
async def get_product_affiliates_count(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get count of active affiliates promoting this product."""
    count = db.query(AffiliateLink).filter(
        AffiliateLink.product_id == product_id
    ).count()

    return {"product_id": product_id, "affiliates_count": count}
