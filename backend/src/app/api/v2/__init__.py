from fastapi import APIRouter

from app.api.v2.auth import router as auth_router
from app.api.v2.health import router as health_router
from app.api.v2.identity import router as identity_router
from app.api.v2.profile import router as profile_router
from app.api.v2.market import router as market_router
from app.api.v2.intelligence import router as intelligence_router
from app.api.v2.dashboard import router as dashboard_router
from app.api.v2.agent import router as agent_router
from app.api.v2.applications import router as applications_router
from app.api.v2.calibration import router as calibration_router
from app.api.v2.admin import router as admin_router
from app.api.v2.docs_api import router as docs_router
from app.api.v2.strategy import router as strategy_router

router = APIRouter(prefix="/api/v2")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(identity_router)
router.include_router(profile_router)
router.include_router(market_router)
router.include_router(intelligence_router)
router.include_router(dashboard_router)
router.include_router(agent_router)
router.include_router(applications_router)
router.include_router(calibration_router)
router.include_router(admin_router)
router.include_router(docs_router)
router.include_router(strategy_router)



