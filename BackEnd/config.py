"""
Centralized application configuration.

Loads environment variables (with a .env file if present) and exposes a single
typed settings object. Development gets safe defaults; production is strictly
validated at startup so misconfiguration fails fast instead of silently.
"""

from __future__ import annotations

import logging
import os
from typing import List

from dotenv import load_dotenv

# Load .env from BackEnd/ (or cwd) early so every module reads the same config.
load_dotenv()

logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_TEST = ENVIRONMENT == "test" or os.getenv("TESTING", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Core settings
# ---------------------------------------------------------------------------
APP_NAME = os.getenv("APP_NAME", "Gamified Ranking System")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# SECRET_KEY: used to sign cookies / derive session secrets. Never kept in
# source. Production REQUIRES it from the environment (fails fast below);
# development falls back to a random per-process key.
_env_secret = os.getenv("SECRET_KEY")
SECRET_KEY = _env_secret or (os.urandom(24).hex() if not IS_PRODUCTION else "")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ranking_page_dev")

# Optional TLS CA bundle for managed MongoDB (Atlas etc.)
MONGODB_TLS_CA = os.getenv("MONGODB_TLS_CA") or None

# In-memory MongoDB (mongomock-motor) for zero-dependency local demos/tests.
MOCK_DB = os.getenv("MOCK_DB", "0").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Admin bootstrap account (seeded by init_db() when present)
# ---------------------------------------------------------------------------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin User")

# ---------------------------------------------------------------------------
# Web / cookies / sessions
# ---------------------------------------------------------------------------
FRONTEND_URLS = [
    u.strip().rstrip("/")
    for u in os.getenv("FRONTEND_URLS", "http://localhost:5173").split(",")
    if u.strip()
]
CORS_ORIGINS: List[str] = FRONTEND_URLS or ["http://localhost:5173"]

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session_id")
SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))  # 24h
SESSION_REMEMBER_MINUTES = int(os.getenv("SESSION_REMEMBER_MINUTES", "43200"))  # 30d
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE", "1" if IS_PRODUCTION else "0"
).lower() in ("1", "true", "yes")

TRUSTED_HOSTS = [
    h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()
]

# ---------------------------------------------------------------------------
# Rate limiting (in-memory sliding window; see middleware/system.py)
# ---------------------------------------------------------------------------
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "300"))
RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))

# ---------------------------------------------------------------------------
# MongoDB pool tuning
# ---------------------------------------------------------------------------
DB_MAX_POOL_SIZE = int(os.getenv("DB_MAX_POOL_SIZE", "100"))
DB_MIN_POOL_SIZE = int(os.getenv("DB_MIN_POOL_SIZE", "5"))


def validate_production_config() -> None:
    """Raise RuntimeError if production configuration is unsafe/incomplete."""
    problems: List[str] = []

    if IS_PRODUCTION:
        if len(SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be a strong random value (min 32 chars)")
        if not MONGODB_URI or MONGODB_URI == "mongodb://localhost:27017":
            problems.append("MONGODB_URI must point to your managed MongoDB")
        if not DATABASE_NAME:
            problems.append("DATABASE_NAME is required")
        if not ADMIN_EMAIL:
            problems.append("ADMIN_EMAIL is required")
        if not ADMIN_PASSWORD or len(ADMIN_PASSWORD) < 12:
            problems.append("ADMIN_PASSWORD is required (min 12 characters)")

    if problems:
        raise RuntimeError(
            "Invalid production configuration:\n  - " + "\n  - ".join(problems)
        )


def log_summary() -> None:
    logger.info(
        "Config loaded | env=%s | db=%s(%s) | mock=%s | origins=%s",
        ENVIRONMENT,
        DATABASE_NAME,
        "mock" if MOCK_DB else MONGODB_URI.replace("@", ":***@"),
        MOCK_DB,
        ", ".join(CORS_ORIGINS),
    )
