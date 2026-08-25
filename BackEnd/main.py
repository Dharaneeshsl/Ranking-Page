"""
Gamified Ranking System - FastAPI application entrypoint.

Run in development:      uvicorn main:app --reload        (from BackEnd/)
Run in production:       uvicorn main:app --workers 2     (or via Dockerfile)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

import config
import database
from middleware.auth_middleware import APIError
from middleware.system import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from routes import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

config.log_summary()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on unsafe production configuration.
    config.validate_production_config()
    await database.init_db()
    logger.info("✅ %s v%s ready (env=%s)", config.APP_NAME, config.APP_VERSION, config.ENVIRONMENT)
    try:
        yield
    finally:
        await database.close_db()
        logger.info("Shutdown complete")


app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Member contribution tracking, gamification and live rankings.",
    docs_url="/api/docs" if not config.IS_PRODUCTION else None,
    redoc_url="/api/redoc" if not config.IS_PRODUCTION else None,
    openapi_url="/api/openapi.json" if not config.IS_PRODUCTION else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware (added in reverse order of execution; CORS ends up outermost)
# ---------------------------------------------------------------------------
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if config.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.TRUSTED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ---------------------------------------------------------------------------
# Exception handlers (clean JSON, no stack leakage)
# ---------------------------------------------------------------------------
@app.exception_handler(APIError)
async def handle_api_error(request: Request, exc: APIError):
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail.get("message", "Error")},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def handle_http_error(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", detail)
    else:
        message = detail
    return JSONResponse(
        status_code=exc.status_code, content={"error": message}, headers=exc.headers
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"error": "Internal server error. Please try again."}
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api")
async def root():
    return {
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "environment": config.ENVIRONMENT,
    }


@app.get("/api/health")
async def health():
    """Liveness probe - no DB access."""
    from datetime import datetime

    return {"status": "ok", "service": config.APP_NAME, "time": datetime.utcnow().isoformat()}


@app.get("/api/ready")
async def ready():
    """Readiness probe - verifies the database connection."""
    try:
        await database.client.admin.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as exc:  # pragma: no cover
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "database": str(exc)}
        )


app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(__import__("os").getenv("PORT", "8000")),
        reload=not config.IS_PRODUCTION,
        proxy_headers=config.IS_PRODUCTION,
    )
