import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List, Union
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
from functools import wraps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours by default
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.secret_key = SECRET_KEY

    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Create a new session and return session ID"""
        session_id = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        self.sessions[session_id] = {
            "user": user_data,
            "expires": expires.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data if valid"""
        if not session_id or session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        if datetime.fromisoformat(session["expires"]) < datetime.utcnow():
            self.delete_session(session_id)
            return None
            
        # Update last activity
        session["last_activity"] = datetime.utcnow().isoformat()
        return session["user"]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if datetime.fromisoformat(session["expires"]) < current_time
        ]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)

# Initialize session manager
session_manager = SessionManager()

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

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user from session cookie"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise AuthError("No session found")
    
    user = session_manager.get_session(session_id)
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

# Alias for backwards compatibility
require_role = require_auth
