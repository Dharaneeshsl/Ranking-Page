"""Aggregate all API routers under a single router (mounted at /api in main)."""

from fastapi import APIRouter

from .auth import router as auth_router
from .contributions import router as contributions_router
from .leaderboard import router as leaderboard_router
from .members import router as members_router
from .points import router as points_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(leaderboard_router, tags=["Leaderboard"])
router.include_router(members_router, tags=["Members"])
router.include_router(contributions_router, tags=["Contributions"])
router.include_router(points_router, tags=["Points"])
