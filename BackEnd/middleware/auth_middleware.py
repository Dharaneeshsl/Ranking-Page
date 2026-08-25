"""
Session authentication: MongoDB-backed sessions, CSRF protection and
role-based access control dependencies.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status

import config
import database

logger = logging.getLogger(__name__)


class APIError(HTTPException):
    """Base API error with a clean JSON payload."""

    def __init__(self, status_code: int, message: str, **kwargs):
        super().__init__(
            status_code=status_code,
            detail={"message": message, **kwargs},
        )


class AuthError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, message)


class ForbiddenError(APIError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(status.HTTP_403_FORBIDDEN, message)


class SessionManager:
    """CRUD for server-side sessions. Collection resolved lazily for testability."""

    @property
    def collection(self):
        return database.sessions_collection

    async def create_session(
        self, user: Dict[str, Any], remember: bool = False, request: Request = None
    ) -> tuple[str, str]:
        """Return (session_id, csrf_token)."""
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(24)
        now = datetime.utcnow()
        minutes = (
            config.SESSION_REMEMBER_MINUTES
            if remember
            else config.SESSION_EXPIRE_MINUTES
        )
        doc = {
            "_id": session_id,
            "user": user,
            "csrf_token": csrf_token,
            "created_at": now,
            "expires_at": now + timedelta(minutes=minutes),
            "remember": bool(remember),
        }
        if request is not None:
            doc["ip"] = request.client.host if request.client else "unknown"
            doc["user_agent"] = request.headers.get("user-agent", "")[:255]
        await self.collection.insert_one(doc)
        return session_id, csrf_token

    async def get_session_doc(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        try:
            doc = await self.collection.find_one({"_id": session_id})
        except Exception:  # pragma: no cover
            return None
        if not doc:
            return None
        if doc.get("expires_at") and doc["expires_at"] < datetime.utcnow():
            await self.delete_session(session_id)
            return None
        return doc

    async def delete_session(self, session_id: str) -> bool:
        result = await self.collection.delete_one({"_id": session_id})
        return result.deleted_count > 0

    async def cleanup_expired_sessions(self) -> int:
        result = await self.collection.delete_many(
            {"expires_at": {"$lt": datetime.utcnow()}}
        )
        return result.deleted_count or 0


session_manager = SessionManager()


async def get_current_session(request: Request) -> Dict[str, Any]:
    """Resolve the session document from the cookie (raises AuthError)."""
    session_id = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not session_id:
        raise AuthError("Not authenticated")
    doc = await session_manager.get_session_doc(session_id)
    if not doc:
        raise AuthError("Session expired or invalid")
    return doc


def require_auth(roles: Optional[List[str]] = None):
    """
    Dependency factory.

    - Rejects unauthenticated requests (401).
    - Enforces role allow-list when provided (403).
    - Enforces CSRF token on mutating methods (POST/PUT/PATCH/DELETE) when the
      request is authenticated with a cookie (403).
    """

    async def dependency(request: Request):
        doc = await get_current_session(request)
        user = doc.get("user") or {}
        if roles and user.get("role") not in roles:
            raise ForbiddenError(
                f"Requires role: {', '.join(roles)}"
            )
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            token = request.headers.get("X-CSRF-Token") or request.headers.get(
                "X-CSRF-TOKEN"
            )
            expected = doc.get("csrf_token")
            if not expected or not token or not secrets.compare_digest(token, expected):
                raise ForbiddenError("Invalid or missing CSRF token")
        return user

    return dependency


# Convenience aliases
require_admin = require_auth(roles=["admin"])
require_user = require_auth()


def set_session_cookie(response, session_id: str, remember: bool = False) -> None:
    """Attach the session cookie to a response."""
    max_age = (
        config.SESSION_REMEMBER_MINUTES * 60
        if remember
        else config.SESSION_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")


def public_user_dict(user_in_db) -> Dict[str, Any]:
    return {
        "id": user_in_db.id,
        "email": user_in_db.email,
        "name": user_in_db.name,
        "role": user_in_db.role,
        "created_at": user_in_db.created_at,
        "updated_at": user_in_db.updated_at,
        "is_active": user_in_db.is_active,
    }
