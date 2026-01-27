# Marketplace Routers Module
# Exports all modular API routers for the marketplace

from routers.influencers import router as influencers_router
from routers.packages import router as packages_router
from routers.wallet import router as wallet_router
from routers.campaigns import router as campaigns_router
from routers.reviews import router as reviews_router
from routers.notifications import router as notifications_router
from routers.disputes import router as disputes_router

__all__ = [
    'influencers_router',
    'packages_router',
    'wallet_router',
    'campaigns_router',
    'reviews_router',
    'notifications_router',
    'disputes_router',
]
