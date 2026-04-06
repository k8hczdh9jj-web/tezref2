# handlers/__init__.py
from .start import router as start_router
from .promo import router as promo_router
from .referral import router as referral_router
from .daily_bonus import router as daily_bonus_router
from .stats import stats_router
from .withdraw import router as withdraw_router
from .rating import rating_router
from .admin_broadcast import admin_broadcast_router
from .admin_ads_router import admin_ads_router

# Hammasini eksport qilish
__all__ = [
    "start_router",
    "promo_router",
    "referral_router",
    "daily_bonus_router",
    "stats_router",
    "withdraw_router",
    "rating_router",
    "admin_broadcast_router",
    "admin_ads_router",
]