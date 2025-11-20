# handlers/__init__.py
from .start import router as start_router
from .promo import router as promo_router
from .referral import router as referral_router
from .stats import stats_router
from .team import team_router
from .withdraw import router as withdraw_router
from .rating import rating_router
from .contact_admin import router as contact_admin_router
from .admin_broadcast import admin_broadcast_router

# Hammasini eksport qilish
__all__ = [
    "start_router",
    "promo_router",
    "referral_router",
    "stats_router",
    "team_router",
    "withdraw_router",
    "rating_router",
    "contact_admin_router",
    "admin_broadcast_router",
]