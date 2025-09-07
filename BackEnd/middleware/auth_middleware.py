from typing import Dict, Any, List, Optional
from fastapi import Request, Depends, HTTPException, status
import os
import logging
import secrets
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection

from ..database import db

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "SECRET_KEY",
    "MONGODB_URI",
    "DATABASE_NAME",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
]

# Set default values for development environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT == "development":
    os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production")
    os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
    os.environ.setdefault("DATABASE_NAME", "ranking_page_dev")
    os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "admin123")

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise RuntimeError(error_msg)

# MongoDB collection for sessions
sessions_collection: AsyncIOMotorCollection = db.sessions

SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))  # 24 hours default

class APIError(HTTPException):
    """Base API Error"""
    def __init__(self, status_code: int, message: str, **kwargs):
        super().__init__(
            status_code=status_code,
            detail={"message": message, **kwargs}
        )

class AuthError(APIError):
    """Authentication error (401)"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, message)

class ForbiddenError(APIError):
    """Authorization error (403)"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(status.HTTP_403_FORBIDDEN, message)

class SessionManager:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.expire_minutes = SESSION_EXPIRE_MINUTES

    async def create_session(self, user_data: Dict[str, Any]) -> str:
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.expire_minutes)
        session_doc = {
            "_id": session_id,
            "user": user_data,
            "created_at": now,
            "expires_at": expires_at,
        }
        await self.collection.insert_one(session_doc)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        session_doc = await self.collection.find_one({"_id": session_id})
        if not session_doc:
            return None
        if session_doc["expires_at"] < datetime.utcnow():
            await self.delete_session(session_id)
            return None
        return session_doc["user"]

    async def delete_session(self, session_id: str) -> bool:
        result = await self.collection.delete_one({"_id": session_id})
        return result.deleted_count > 0

    async def cleanup_expired_sessions(self) -> int:
        result = await self.collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
        return result.deleted_count

session_manager = SessionManager(sessions_collection)

async def get_current_user(request: Request) -> Dict[str, Any]:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise AuthError("No session found")
    user = await session_manager.get_session(session_id)
    if not user:
        raise AuthError("Session expired or invalid")
    return user

def require_auth(roles: List[str] = None):
    """
    Dependency to require authentication (and optionally specific roles)
    
    Args:
        roles: List of allowed roles (None means any authenticated user)
    """
    async def dependency(user: Dict[str, Any] = Depends(get_current_user)):
        if not user:
            raise AuthError()
            
        if roles and user.get("role") not in roles:
            raise ForbiddenError("Insufficient permissions")
            
        return user
        
    return dependency

# Alias for role-based access control
require_role = require_auth
