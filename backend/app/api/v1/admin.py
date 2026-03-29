"""Admin endpoints for policy publishing and management."""

from fastapi import APIRouter

from .admin_routes import policies, privacy

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(policies.router)
router.include_router(privacy.router)
