import os
import logging
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi_session import SessionMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timedelta
from typing import Optional, List

from .database import init_db, DatabaseConfigError
from .routes import auth as auth_router
from .middleware.auth_middleware import APIError, require_auth, require_role

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
DEBUG = ENVIRONMENT != "production"
SECRET_KEY = os.getenv("SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()] or [FRONTEND_URL]

# Validate required configurations
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in environment variables")

# Initialize FastAPI app
app = FastAPI(
    title="Ranking Page API",
    description="Production-ready API for Ranking Page Application",
    version="1.0.0",
    debug=DEBUG,
    docs_url="/api/docs" if DEBUG else None,
    redoc_url="/api/redoc" if DEBUG else None,
    openapi_url="/api/openapi.json" if DEBUG else None,
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Add CORS middleware with production-ready settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["Content-Range", "X-Total-Count"],
    max_age=600,  # 10 minutes
)

# Add session middleware with secure settings
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie=os.getenv("SESSION_COOKIE_NAME", "session_id"),
    session_lifetime=int(os.getenv("SESSION_LIFETIME", "86400")),  # 24 hours
    same_site=os.getenv("SESSION_SAME_SITE", "lax"),
    https_only=ENVIRONMENT == "production",  # Only send over HTTPS in production
    domain=os.getenv("SESSION_DOMAIN"),
    secure_cookies=ENVIRONMENT == "production",  # Only send cookies over HTTPS
    http_only=True,  # Prevent JavaScript access to session cookie
)

# Error handler
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail["message"]},
    )

# Startup event
@app.on_event("startup")
async def startup():
    await init_db()
    print("\n=== Server started successfully ===")
    print(f"Environment: {'Development' if DEBUG else 'Production'}")
    print(f"Frontend URL: {FRONTEND_URL}")
    print("================================\n")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "debug": DEBUG,
    }

# Include routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])

# Example protected route
@app.get("/api/protected")
async def protected_route(user: dict = Depends(require_auth())):
    return {
        "status": "success",
        "message": "You are authenticated",
        "user": user,
        "timestamp": datetime.utcnow().isoformat(),
    }

# Admin-only route example
@app.get("/api/admin-only")
async def admin_route(user: dict = Depends(require_role(["admin"]))):
    return {
        "status": "success",
        "message": "Admin access granted",
        "user": user,
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
