# Digital Products Router
# Manages digital files and download access for downloadable products

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from database.models import User
from database.affiliate_models import (
    Product,
    BrandProfile,
    DigitalFile,
    DigitalPurchase
)
from schemas.affiliate import (
    DigitalFileCreate,
    DigitalFileResponse,
    DigitalPurchaseResponse,
    SuccessResponse
)
from database.config import get_db
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/digital-products", tags=["Digital Products"])


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


# ============================================================================
# FILE MANAGEMENT (Brand only)
# ============================================================================

@router.post("/{product_id}/files", response_model=DigitalFileResponse, status_code=status.HTTP_201_CREATED)
async def add_digital_file(
    product_id: str,
    file_data: DigitalFileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a file to a digital product. Brand owner only."""
    # Verify product ownership
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile or product.brand_profile_id != brand_profile.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not product.is_digital:
        raise HTTPException(status_code=400, detail="Product is not a digital product")

    new_file = DigitalFile(
        id=generate_uuid(),
        product_id=product_id,
        file_name=file_data.file_name,
        file_url=file_data.file_url,
        file_size=file_data.file_size,
        file_type=file_data.file_type,
        version=file_data.version,
        is_preview=file_data.is_preview
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return new_file


@router.get("/{product_id}/files", response_model=List[DigitalFileResponse])
async def get_digital_files(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all files for a digital product. Brand owner only."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile or product.brand_profile_id != brand_profile.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    files = db.query(DigitalFile).filter(
        DigitalFile.product_id == product_id
    ).order_by(DigitalFile.created_at.desc()).all()

    return files


@router.delete("/files/{file_id}", response_model=SuccessResponse)
async def delete_digital_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a digital file. Brand owner only."""
    digital_file = db.query(DigitalFile).filter(DigitalFile.id == file_id).first()
    if not digital_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Verify ownership
    product = db.query(Product).filter(Product.id == digital_file.product_id).first()
    brand_profile = db.query(BrandProfile).filter(
        BrandProfile.user_id == current_user.id
    ).first()

    if not brand_profile or product.brand_profile_id != brand_profile.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(digital_file)
    db.commit()

    return SuccessResponse(success=True, message="File deleted successfully")


# ============================================================================
# PUBLIC ENDPOINTS - Preview & Download
# ============================================================================

@router.get("/{product_id}/preview")
async def get_preview_file(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get free preview file for a digital product. Public endpoint."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_digital == True,
        Product.status == "active"
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Digital product not found")

    preview_file = db.query(DigitalFile).filter(
        DigitalFile.product_id == product_id,
        DigitalFile.is_preview == True
    ).first()

    if not preview_file:
        raise HTTPException(status_code=404, detail="No preview file available")

    return {
        "file_name": preview_file.file_name,
        "file_url": preview_file.file_url,
        "file_size": preview_file.file_size,
        "file_type": preview_file.file_type
    }


@router.get("/download/{access_token}")
async def download_file(
    access_token: str,
    db: Session = Depends(get_db)
):
    """
    Download digital product using access token.
    Public endpoint - token is the authentication.
    Redirects to the actual file URL.
    """
    purchase = db.query(DigitalPurchase).filter(
        DigitalPurchase.access_token == access_token
    ).first()

    if not purchase:
        raise HTTPException(status_code=404, detail="Invalid download link")

    if purchase.status == "refunded":
        raise HTTPException(status_code=403, detail="Purchase has been refunded")

    if purchase.download_count >= purchase.max_downloads:
        raise HTTPException(status_code=403, detail="Download limit reached")

    if purchase.expires_at and purchase.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Download link has expired")

    # Get the main (non-preview) file
    digital_file = db.query(DigitalFile).filter(
        DigitalFile.product_id == purchase.product_id,
        DigitalFile.is_preview == False
    ).first()

    if not digital_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Increment download counts
    purchase.download_count += 1
    purchase.last_downloaded_at = datetime.utcnow()
    digital_file.download_count += 1

    db.commit()

    # Redirect to the actual file
    return RedirectResponse(url=digital_file.file_url, status_code=302)


@router.get("/download/{access_token}/files")
async def list_downloadable_files(
    access_token: str,
    db: Session = Depends(get_db)
):
    """
    List all downloadable files for a purchase.
    Returns file info without incrementing download count.
    """
    purchase = db.query(DigitalPurchase).filter(
        DigitalPurchase.access_token == access_token
    ).first()

    if not purchase:
        raise HTTPException(status_code=404, detail="Invalid download link")

    if purchase.status == "refunded":
        raise HTTPException(status_code=403, detail="Purchase has been refunded")

    files = db.query(DigitalFile).filter(
        DigitalFile.product_id == purchase.product_id,
        DigitalFile.is_preview == False
    ).all()

    product = db.query(Product).filter(Product.id == purchase.product_id).first()

    return {
        "product_name": product.name if product else "Unknown",
        "downloads_remaining": max(0, purchase.max_downloads - purchase.download_count),
        "expires_at": purchase.expires_at,
        "files": [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_url": f.file_url,
                "file_size": f.file_size,
                "file_type": f.file_type,
                "version": f.version
            }
            for f in files
        ]
    }


# ============================================================================
# CUSTOMER PURCHASE LOOKUP
# ============================================================================

@router.get("/my-purchases")
async def get_my_purchases(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Look up digital purchases by customer email.
    Public endpoint for customers to find their downloads.
    """
    purchases = db.query(DigitalPurchase).filter(
        DigitalPurchase.customer_email == email
    ).order_by(DigitalPurchase.created_at.desc()).all()

    result = []
    for purchase in purchases:
        product = db.query(Product).filter(Product.id == purchase.product_id).first()
        result.append({
            "id": purchase.id,
            "product_name": product.name if product else "Unknown",
            "product_thumbnail": product.thumbnail if product else None,
            "access_token": purchase.access_token,
            "download_count": purchase.download_count,
            "max_downloads": purchase.max_downloads,
            "downloads_remaining": max(0, purchase.max_downloads - purchase.download_count),
            "expires_at": purchase.expires_at,
            "status": purchase.status,
            "created_at": purchase.created_at,
            "last_downloaded_at": purchase.last_downloaded_at
        })

    return result
