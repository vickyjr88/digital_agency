# Auth module for Dexter Platform
# Provides role-based access control and authentication decorators

from auth.roles import (
    UserType,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
    has_any_permission,
    has_all_permissions,
)

from auth.decorators import (
    AuthError,
    require_user_type,
    require_permission,
    require_admin,
    require_verified_influencer,
    require_brand_owner,
)

__all__ = [
    # Roles
    "UserType",
    "Permission",
    "ROLE_PERMISSIONS",
    "get_permissions_for_role",
    "has_permission",
    "has_any_permission",
    "has_all_permissions",
    
    # Decorators
    "AuthError",
    "require_user_type",
    "require_permission",
    "require_admin",
    "require_verified_influencer",
    "require_brand_owner",
]
