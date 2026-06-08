from fastapi import APIRouter

from app.api.v2.health import router as health_router

router = APIRouter(prefix="/api/v2")
router.include_router(health_router)
