# External API Router for Dexter Platform
# Allows other apps to interact with Dexter using Access Keys

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from database.config import get_db
from database.models import ExternalService
from database.affiliate_models import Product
from core.minio_service import generate_download_url

router = APIRouter(prefix="/api/external", tags=["External API"])

async def verify_access_key(
    x_access_key: str = Header(..., description="Access key for external application"),
    db: Session = Depends(get_db)
) -> ExternalService:
    """Dependency to verify the access key in the request header."""
    service = db.query(ExternalService).filter(
        ExternalService.api_key == x_access_key,
        ExternalService.is_active == True
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive access key"
        )
    
    return service

@router.get("/download/{product_id}")
async def external_download_product(
    product_id: str,
    db: Session = Depends(get_db),
    service: ExternalService = Depends(verify_access_key)
):
    """
    Generate a download URL for a digital product.
    Accessible by external apps with a valid access key.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_digital or not product.digital_file_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product does not have a digital file associated with it"
        )
    
    # Generate presigned URL (24 hour expiry by default)
    download_url = generate_download_url(product.digital_file_key)
    
    return {
        "success": True,
        "product_name": product.name,
        "file_name": product.digital_file_name,
        "download_url": download_url,
        "expires_in": "24 hours"
    }

@router.get("/", status_code=status.HTTP_200_OK)
async def list_external_services(
    db: Session = Depends(get_db)
):
    """
    List all external applications registered in the system.
    Note: In a real scenario, this should be restricted to admins.
    """
    services = db.query(ExternalService).order_by(ExternalService.created_at.desc()).all()
    return services

@router.delete("/{service_id}", status_code=status.HTTP_200_OK)
async def delete_external_service(
    service_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an external application registration.
    """
    service = db.query(ExternalService).filter(ExternalService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    db.delete(service)
    db.commit()
    return {"success": True, "message": "Service deleted successfully"}

@router.post("/register-app", status_code=status.HTTP_201_CREATED)
async def register_external_app(
    name: str,
    db: Session = Depends(get_db)
):
    """
    Register a new external application and generate an access key.
    Note: In a real scenario, this should be restricted to admins.
    """
    # Check if app already exists
    existing = db.query(ExternalService).filter(ExternalService.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application with name '{name}' already registered"
        )
    
    # Generate a secure random access key
    api_key = f"dex_{secrets.token_urlsafe(32)}"
    
    new_service = ExternalService(
        name=name,
        api_key=api_key
    )
    
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return {
        "success": True,
        "message": "External application registered successfully",
        "app_name": new_service.name,
        "access_key": api_key,
        "note": "Save this key securely. It will not be shown again."
    }
