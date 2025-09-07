from fastapi import APIRouter

from .auth import router as auth_router
from .leaderboard import router as leaderboard_router
from .members import router as members_router
from .contributions import router as contributions_router

router = APIRouter()
router.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
router.include_router(leaderboard_router, prefix="/api", tags=["Leaderboard"])
router.include_router(members_router, prefix="/api", tags=["Members"])
router.include_router(contributions_router, prefix="/api", tags=["Contributions"])
