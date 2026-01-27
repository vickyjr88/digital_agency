# Role-Based Access Control for Dexter Platform
# This module defines user roles and permissions for the marketplace

from enum import Enum
from typing import List, Set


class UserType(str, Enum):
    """User types in the marketplace."""
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"


class Permission(str, Enum):
    """Fine-grained permissions for the platform."""
    
    # Brand permissions
    CREATE_BRAND = "create_brand"
    VIEW_OWN_BRANDS = "view_own_brands"
    EDIT_OWN_BRANDS = "edit_own_brands"
    DELETE_OWN_BRANDS = "delete_own_brands"
    GENERATE_CONTENT = "generate_content"
    PURCHASE_PACKAGES = "purchase_packages"
    VIEW_CAMPAIGNS = "view_campaigns"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    DEPOSIT_FUNDS = "deposit_funds"
    VIEW_MARKETPLACE = "view_marketplace"
    LEAVE_REVIEWS = "leave_reviews"
    RAISE_DISPUTES = "raise_disputes"
    
    # Influencer permissions
    CREATE_INFLUENCER_PROFILE = "create_influencer_profile"
    EDIT_INFLUENCER_PROFILE = "edit_influencer_profile"
    CREATE_PACKAGES = "create_packages"
    EDIT_OWN_PACKAGES = "edit_own_packages"
    DELETE_OWN_PACKAGES = "delete_own_packages"
    ACCEPT_ORDERS = "accept_orders"
    SUBMIT_DELIVERABLES = "submit_deliverables"
    WITHDRAW_FUNDS = "withdraw_funds"
    
    # Common permissions
    VIEW_OWN_WALLET = "view_own_wallet"
    VIEW_OWN_TRANSACTIONS = "view_own_transactions"
    VIEW_NOTIFICATIONS = "view_notifications"
    UPDATE_PROFILE = "update_profile"
    VIEW_TRENDS = "view_trends"
    
    # Admin permissions
    VIEW_ALL_USERS = "view_all_users"
    MANAGE_USERS = "manage_users"
    VIEW_ALL_BRANDS = "view_all_brands"
    VIEW_ALL_CAMPAIGNS = "view_all_campaigns"
    RESOLVE_DISPUTES = "resolve_disputes"
    VIEW_ADMIN_STATS = "view_admin_stats"
    MANAGE_PLATFORM = "manage_platform"
    VERIFY_INFLUENCERS = "verify_influencers"
    MANAGE_ESCROW = "manage_escrow"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserType, Set[Permission]] = {
    UserType.BRAND: {
        # Brand-specific
        Permission.CREATE_BRAND,
        Permission.VIEW_OWN_BRANDS,
        Permission.EDIT_OWN_BRANDS,
        Permission.DELETE_OWN_BRANDS,
        Permission.GENERATE_CONTENT,
        Permission.PURCHASE_PACKAGES,
        Permission.VIEW_CAMPAIGNS,
        Permission.MANAGE_CAMPAIGNS,
        Permission.DEPOSIT_FUNDS,
        Permission.VIEW_MARKETPLACE,
        Permission.LEAVE_REVIEWS,
        Permission.RAISE_DISPUTES,
        # Common
        Permission.VIEW_OWN_WALLET,
        Permission.VIEW_OWN_TRANSACTIONS,
        Permission.VIEW_NOTIFICATIONS,
        Permission.UPDATE_PROFILE,
        Permission.VIEW_TRENDS,
    },
    
    UserType.INFLUENCER: {
        # Influencer-specific
        Permission.CREATE_INFLUENCER_PROFILE,
        Permission.EDIT_INFLUENCER_PROFILE,
        Permission.CREATE_PACKAGES,
        Permission.EDIT_OWN_PACKAGES,
        Permission.DELETE_OWN_PACKAGES,
        Permission.ACCEPT_ORDERS,
        Permission.SUBMIT_DELIVERABLES,
        Permission.WITHDRAW_FUNDS,
        Permission.VIEW_CAMPAIGNS,
        Permission.LEAVE_REVIEWS,
        Permission.RAISE_DISPUTES,
        # Common
        Permission.VIEW_OWN_WALLET,
        Permission.VIEW_OWN_TRANSACTIONS,
        Permission.VIEW_NOTIFICATIONS,
        Permission.UPDATE_PROFILE,
        Permission.VIEW_TRENDS,
    },
    
    UserType.ADMIN: {
        # Admin has ALL permissions
        *Permission.__members__.values()
    },
}


def get_permissions_for_role(user_type: UserType) -> Set[Permission]:
    """Get all permissions for a given user type."""
    return ROLE_PERMISSIONS.get(user_type, set())


def has_permission(user_type: UserType, permission: Permission) -> bool:
    """Check if a user type has a specific permission."""
    return permission in get_permissions_for_role(user_type)


def has_any_permission(user_type: UserType, permissions: List[Permission]) -> bool:
    """Check if a user type has any of the given permissions."""
    user_permissions = get_permissions_for_role(user_type)
    return any(p in user_permissions for p in permissions)


def has_all_permissions(user_type: UserType, permissions: List[Permission]) -> bool:
    """Check if a user type has all of the given permissions."""
    user_permissions = get_permissions_for_role(user_type)
    return all(p in user_permissions for p in permissions)
