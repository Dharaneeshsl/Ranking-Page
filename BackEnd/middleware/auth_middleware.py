from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import json
from datetime import datetime, timedelta
import secrets

class APIError(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(
            status_code=status_code,
            detail={"status": "error", "message": message}
        )

class SessionManager:
    def __init__(self, secret_key: str, session_lifetime: int = 86400):
        self.secret_key = secret_key
        self.session_lifetime = session_lifetime

    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Create a new session for the user"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "user_id": str(user_data.get("id")),
            "email": user_data.get("email"),
            "role": user_data.get("role"),
            "expires_at": (datetime.utcnow() + timedelta(seconds=self.session_lifetime)).isoformat()
        }
        return session_id, session_data

    def verify_session(self, session_data: Dict[str, Any]) -> bool:
        """Verify if session is valid"""
        if not session_data or "expires_at" not in session_data:
            return False
        return datetime.utcnow() < datetime.fromisoformat(session_data["expires_at"])

# Initialize session manager with secret key
session_manager = SessionManager(secret_key=secrets.token_hex(32))

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency to get current user from session"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise APIError(status_code=401, message="Not authenticated")
    
    session_data = request.session.get(session_id)
    if not session_data or not session_manager.verify_session(session_data):
        # Clean up expired session
        if session_id in request.session:
            del request.session[session_id]
        raise APIError(status_code=401, message="Session expired or invalid")
    
    return session_data

def require_auth():
    """Dependency to require authentication"""
    async def _require_auth(user: Dict[str, Any] = Depends(get_current_user)):
        return user
    return _require_auth

def require_role(roles: list):
    """Dependency to require specific role"""
    async def _require_role(user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise APIError(status_code=403, message="Insufficient permissions")
        return user
    return _require_role
