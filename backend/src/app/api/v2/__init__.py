from fastapi import APIRouter

from app.api.v2.auth import router as auth_router
from app.api.v2.health import router as health_router
from app.api.v2.identity import router as identity_router

router = APIRouter(prefix="/api/v2")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(identity_router)

