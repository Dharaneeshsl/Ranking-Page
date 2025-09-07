from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import json

from ..database import authenticate_user, get_user_by_email
from ..middleware.auth_middleware import APIError, require_auth, require_role
from ..models.user import UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

@router.post("/login")
async def login(request: Request, response: Response, login_data: LoginRequest):
    """
    User login with email and password
    """
    # Authenticate user
    user = await authenticate_user(login_data.email, login_data.password)
    if not user:
        raise APIError(status_code=401, message="Invalid email or password")

    # Store user info in request.session (fastapi_session)
    request.session["user"] = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.name
    }

    # Set session cookie (fastapi_session handles this automatically)
    response.set_cookie(
        key="session_id",
        value=request.cookies.get("session_id", ""),
        httponly=True,
        max_age=86400 if login_data.remember_me else None,  # 24 hours if remember me
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )

    return {
        "status": "success",
        "message": "Login successful",
        "user": UserResponse(**user.dict()).dict()
    }

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Log out the current user"""
    if "user" in request.session:
        del request.session["user"]

    # Clear session cookie
    response.delete_cookie("session_id")

    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(user: dict = Depends(require_auth())):
    """Get current user information"""
    db_user = await get_user_by_email(user["email"])
    if not db_user:
        raise APIError(status_code=404, message="User not found")
    return UserResponse(**db_user.dict())

@router.get("/check")
async def check_auth_status(user: dict = Depends(require_auth())):
    """Check if user is authenticated"""
    return {
        "status": "success",
        "authenticated": True,
        "user": user
    }
