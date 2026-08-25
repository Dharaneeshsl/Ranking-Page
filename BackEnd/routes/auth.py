"""Authentication endpoints (login / logout / me / check)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response

import database
from middleware.auth_middleware import (
    APIError,
    clear_session_cookie,
    get_current_session,
    set_session_cookie,
    public_user_dict,
    session_manager,
)
from models.user import (
    CheckResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, response: Response, body: LoginRequest):
    """Authenticate with email/password; creates a server-side session."""
    user = await database.authenticate_user(body.email, body.password)
    if not user:
        raise APIError(401, "Invalid email or password")

    session_id, csrf_token = await session_manager.create_session(
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
        },
        remember=body.remember_me,
        request=request,
    )
    set_session_cookie(response, session_id, remember=body.remember_me)
    logger.info("Login success: %s", user.email)
    return LoginResponse(
        status="success",
        message="Login successful",
        user=UserResponse(**public_user_dict(user)),
        csrf_token=csrf_token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session=Depends(get_current_session),
):
    """Invalidate the session and clear the cookie."""
    session_id = request.cookies.get("session_id")
    await session_manager.delete_session(session_id or "")
    clear_session_cookie(response)
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/me", response_model=CheckResponse)
async def me(request: Request, session=Depends(get_current_session)):
    """Current user info plus the CSRF token for this session."""
    user = session.get("user") or {}
    db_user = await database.get_user_by_email(user.get("email", ""))
    if not db_user:
        raise APIError(404, "User not found")
    return CheckResponse(
        status="success",
        authenticated=True,
        user=UserResponse(**public_user_dict(db_user)),
        csrf_token=session.get("csrf_token"),
    )


@router.get("/check", response_model=CheckResponse)
async def check(request: Request):
    """Lightweight auth probe; never raises - reports authenticated true/false."""
    try:
        session = await get_current_session(request)
    except APIError:
        return CheckResponse(status="success", authenticated=False)
    user = session.get("user") or {}
    db_user = await database.get_user_by_email(user.get("email", ""))
    if not db_user:
        return CheckResponse(status="success", authenticated=False)
    return CheckResponse(
        status="success",
        authenticated=True,
        user=UserResponse(**public_user_dict(db_user)),
        csrf_token=session.get("csrf_token"),
    )
