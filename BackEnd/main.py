from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi_session import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import secrets
import uvicorn
import os
from datetime import datetime, timedelta
from typing import Optional

from .database import init_db
from .routes import auth as auth_router
from .middleware.auth_middleware import APIError, require_auth, require_role

# Configuration
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Initialize FastAPI app
app = FastAPI(
    title="Ranking Page API",
    debug=DEBUG,
    docs_url="/api/docs" if DEBUG else None,
    redoc_url="/api/redoc" if DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session_id",
    same_site="lax",
    https_only=not DEBUG,
    max_age=86400,  # 24 hours
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
