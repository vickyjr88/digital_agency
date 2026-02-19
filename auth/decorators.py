# Authentication and Authorization Decorators for Dexter Platform
# These decorators provide easy-to-use access control for API endpoints

from functools import wraps
from typing import List, Callable, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from database.config import get_db
from database.models import User, UserRole
from auth.roles import UserType, Permission, has_permission, has_any_permission
from auth.dependencies import get_current_user


class AuthError(HTTPException):
    """Custom exception for authentication/authorization errors."""
    
    def __init__(self, detail: str, status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=detail)


def require_user_type(*allowed_types: UserType):
    """
    Dependency that requires the user to be one of the specified types.
    
    Usage:
        @app.get("/influencer/profile")
        async def get_profile(
            user: User = Depends(require_user_type(UserType.INFLUENCER))
        ):
            ...
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_type = _get_user_type(current_user)
        
        # Admin can access everything
        if user_type == UserType.ADMIN:
            return current_user
            
        if user_type not in allowed_types:
            allowed_names = ", ".join(t.value for t in allowed_types)
            raise AuthError(
                detail=f"This endpoint requires user type: {allowed_names}",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        return current_user
    
    return dependency


def require_permission(*permissions: Permission):
    """
    Dependency that requires the user to have specific permissions.
    
    Usage:
        @app.post("/packages")
        async def create_package(
            user: User = Depends(require_permission(Permission.CREATE_PACKAGES))
        ):
            ...
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_type = _get_user_type(current_user)
        
        if not has_any_permission(user_type, list(permissions)):
            raise AuthError(
                detail="You don't have permission to perform this action",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        return current_user
    
    return dependency


def require_admin():
    """
    Dependency that requires the user to be an admin.
    
    Usage:
        @app.get("/admin/stats")
        async def get_stats(user: User = Depends(require_admin())):
            ...
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        # Check both the old role field and new user_type field
        is_admin = False
        
        # Check legacy role field
        if hasattr(current_user, 'role') and current_user.role:
            role_val = str(current_user.role).lower()
            if role_val == "admin":
                is_admin = True
        
        # Check new user_type field
        if not is_admin and hasattr(current_user, 'user_type') and current_user.user_type:
            user_type = current_user.user_type
            if isinstance(user_type, str):
                is_admin = user_type.lower() == "admin"
            elif isinstance(user_type, UserType):
                is_admin = user_type == UserType.ADMIN
        
        if not is_admin:
            raise AuthError(
                detail="Admin access required",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        return current_user
    
    return dependency


def require_verified_influencer():
    """
    Dependency that requires the user to be a verified influencer.
    
    Usage:
        @app.post("/packages")
        async def create_package(
            user: User = Depends(require_verified_influencer())
        ):
            ...
    """
    async def dependency(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        from database.models import InfluencerProfile  # Import here to avoid circular
        
        user_type = _get_user_type(current_user)
        
        if user_type != UserType.INFLUENCER and user_type != UserType.ADMIN:
            raise AuthError(
                detail="Only influencers can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if influencer profile exists and is verified
        profile = db.query(InfluencerProfile).filter(
            InfluencerProfile.user_id == current_user.id
        ).first()
        
        if not profile:
            raise AuthError(
                detail="Please complete your influencer profile first",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return current_user
    
    return dependency


def require_brand_owner(brand_id_param: str = "brand_id"):
    """
    Dependency that requires the user to own the specified brand.
    
    Usage:
        @app.put("/brands/{brand_id}")
        async def update_brand(
            brand_id: str,
            user: User = Depends(require_brand_owner("brand_id"))
        ):
            ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user), 
        db: Session = Depends(get_db),
        **kwargs
    ) -> User:
        from database.models import Brand  # Import here to avoid circular
        
        brand_id = kwargs.get(brand_id_param)
        if not brand_id:
            raise AuthError(
                detail="Brand ID is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Admin can access any brand
        user_type = _get_user_type(current_user)
        if user_type == UserType.ADMIN:
            return current_user
        
        # Check ownership
        brand = db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == current_user.id
        ).first()
        
        if not brand:
            raise AuthError(
                detail="Brand not found or you don't have access",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return current_user
    
    return dependency


def _get_user_type(user: User) -> UserType:
    """Helper to extract UserType from User object with backward compatibility."""
    # Legacy: Check if admin via role field first
    if hasattr(user, 'role') and user.role:
        role_val = str(user.role.value if hasattr(user.role, 'value') else user.role).lower()
        if role_val == "admin":
            return UserType.ADMIN

    if hasattr(user, 'user_type') and user.user_type:
        # Get raw value regardless of whether it's an enum or string
        val = user.user_type.value if hasattr(user.user_type, 'value') else user.user_type
        if val:
            try:
                # Try the value as-is first (handles uppercase DB values), then uppercase
                raw = str(val)
                try:
                    return UserType(raw)
                except ValueError:
                    return UserType(raw.upper())
            except ValueError:
                pass

    # Default to brand for backward compatibility
    return UserType.BRAND
