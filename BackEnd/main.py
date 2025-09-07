import os
import logging
from fastapi import FastAPI, Request, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi_session import SessionMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timedelta
from typing import Optional, List

from .database import init_db, DatabaseConfigError
from .routes import auth as auth_router
from .routes import leaderboard_router, members_router, contributions_router
from .middleware.auth_middleware import APIError, require_auth, require_role

# Configure logging
import logging
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

# Session configuration
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session_id")
SESSION_LIFETIME = os.getenv("SESSION_LIFETIME", "86400")
SESSION_SAME_SITE = os.getenv("SESSION_SAME_SITE", "lax")
SESSION_DOMAIN = os.getenv("SESSION_DOMAIN")

# Validate required configurations
required_env_vars = {
    "SECRET_KEY": SECRET_KEY,
}

missing_vars = [var for var, val in required_env_vars.items() if not val]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise ValueError(error_msg)

# Validate session configuration
try:
    session_lifetime_int = int(SESSION_LIFETIME)
    if session_lifetime_int <= 0:
        raise ValueError("SESSION_LIFETIME must be a positive integer")
except ValueError as e:
    logger.critical(f"Invalid SESSION_LIFETIME value: {SESSION_LIFETIME}")
    raise ValueError(f"SESSION_LIFETIME must be a positive integer, got: {SESSION_LIFETIME}")

# Validate CORS configuration
if not FRONTEND_URL.startswith(('http://', 'https://')):
    logger.warning(f"FRONTEND_URL should start with http:// or https://, got: {FRONTEND_URL}")

logger.info("✅ Environment variable validation completed")

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
    session_cookie=SESSION_COOKIE_NAME,
    session_lifetime=session_lifetime_int,  # 24 hours
    same_site=SESSION_SAME_SITE,
    https_only=ENVIRONMENT == "production",  # Only send over HTTPS in production
    domain=SESSION_DOMAIN,
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
    try:
        logger.info("🚀 Starting database initialization...")
        await init_db()
        logger.info("✅ Database initialized successfully")

        print("\n=== Server started successfully ===")
        print(f"Environment: {'Development' if DEBUG else 'Production'}")
        print(f"Frontend URL: {FRONTEND_URL}")
        print("================================\n")

    except DatabaseConfigError as e:
        logger.critical(f"❌ Database configuration error: {str(e)}")
        print("\n❌ CRITICAL ERROR: Database configuration is invalid")
        print(f"Details: {str(e)}")
        print("Please check your environment variables and try again.")
        print("Required: MONGODB_URI, DATABASE_NAME, ADMIN_EMAIL, ADMIN_PASSWORD")
        # Exit the application on configuration errors
        import sys
        sys.exit(1)

    except Exception as e:
        logger.critical(f"❌ Database initialization failed: {str(e)}")
        print("\n❌ CRITICAL ERROR: Failed to initialize database")
        print(f"Details: {str(e)}")
        print("Please check your database connection and try again.")
        # Exit the application on database connection errors
        import sys
        sys.exit(1)

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
app.include_router(leaderboard_router, prefix="/api", tags=["Leaderboard"])
app.include_router(members_router, prefix="/api", tags=["Members"])
app.include_router(contributions_router, prefix="/api", tags=["Contributions"])

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
