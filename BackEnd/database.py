"""
MongoDB connection, bootstrap and helpers.

The client is created lazily by connect() so the module can be imported in any
environment. Tests swap the collections with an in-memory mock (mongomock).
"""

from __future__ import annotations

import logging
import ssl
from datetime import datetime
from typing import Optional

import bcrypt

import config
from models.user import UserInDB

logger = logging.getLogger(__name__)


class DatabaseConfigError(RuntimeError):
    """Raised when the database cannot be initialized."""


# ---------------------------------------------------------------------------
# Module-level handles (populated by connect())
# ---------------------------------------------------------------------------
client = None
db = None
users_collection = None
members_collection = None
sessions_collection = None


def _build_motor_client():
    """Create a real motor client with production-sane options."""
    kwargs = dict(
        maxPoolSize=config.DB_MAX_POOL_SIZE,
        minPoolSize=config.DB_MIN_POOL_SIZE,
        maxIdleTimeMS=30000,
        connectTimeoutMS=10000,
        serverSelectionTimeoutMS=10000,
        socketTimeoutMS=45000,
        retryWrites=True,
        retryReads=True,
    )
    if config.MONGODB_TLS_CA:
        # Verify the CA bundle is loadable before handing it to the driver.
        ssl.create_default_context(cafile=config.MONGODB_TLS_CA)
        kwargs.update(ssl=True, tlsCAFile=config.MONGODB_TLS_CA)
    from motor.motor_asyncio import AsyncIOMotorClient

    return AsyncIOMotorClient(config.MONGODB_URI, **kwargs)


def _build_mock_client():
    """In-memory MongoDB (dev/demo only)."""
    try:
        from mongomock_motor import AsyncMongoMockClient
    except ImportError as exc:  # pragma: no cover
        raise DatabaseConfigError(
            "MOCK_DB=1 requires mongomock-motor: pip install -r requirements-dev.txt"
        ) from exc
    logger.warning("MOCK_DB=1 -> using in-memory MongoDB (development/demo only!)")
    return AsyncMongoMockClient()


def connect():
    """Create the client and bind the database + collections."""
    global client, db, users_collection, members_collection, sessions_collection
    if client is None:
        client = _build_mock_client() if config.MOCK_DB else _build_motor_client()
    db = client.get_database(config.DATABASE_NAME)
    users_collection = db.users
    members_collection = db.members
    sessions_collection = db.sessions
    return db


async def close_db() -> None:
    global client
    if client is not None:
        try:
            await client.close()
        except Exception:  # pragma: no cover
            pass
        client = None


async def init_db():
    """Connect, verify, create indexes and seed the admin user."""
    connect()
    try:
        await client.admin.command("ping")
        logger.info("Connected to MongoDB (%s)", config.DATABASE_NAME)
    except Exception as exc:  # mock clients may not implement ping
        if config.MOCK_DB:
            logger.debug("Mock database ping skipped: %s", exc)
        else:
            raise DatabaseConfigError(f"MongoDB ping failed: {exc}") from exc

    # --- Indexes -----------------------------------------------------------
    try:
        await users_collection.create_index("email", unique=True)
        await members_collection.create_index("name")
        await members_collection.create_index("points", -1)
        await members_collection.create_index("last_active", -1)
        await members_collection.create_index(
            [("contributions.timestamp", -1), ("_id", -1)]
        )
        # TTL index keeps the sessions table self-cleaning (real MongoDB only).
        await sessions_collection.create_index(
            "expires_at", expireAfterSeconds=0
        )
    except Exception as exc:
        if config.MOCK_DB:
            logger.debug("Index creation simulated on mock DB: %s", exc)
        else:
            raise DatabaseConfigError(f"Failed to create indexes: {exc}") from exc

    logger.info("Database indexes created/verified")

    # --- Admin bootstrap account ------------------------------------------
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD:
        existing = await users_collection.find_one(
            {"email": config.ADMIN_EMAIL.strip().lower(), "role": "admin"}
        )
        if not existing:
            hashed = bcrypt.hashpw(
                config.ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            now = datetime.utcnow().isoformat()
            await users_collection.insert_one(
                {
                    "email": config.ADMIN_EMAIL.strip().lower(),
                    "name": config.ADMIN_NAME.strip(),
                    "hashed_password": hashed,
                    "role": "admin",
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            logger.info("Seeded admin user: %s", config.ADMIN_EMAIL)
        else:
            logger.info("Admin user already exists")
    else:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set -> no admin account seeded")

    return True


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------
async def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Return an active user by email, or None."""
    if not email:
        return None
    try:
        doc = await users_collection.find_one(
            {"email": email.strip().lower(), "is_active": True}
        )
    except Exception as exc:  # pragma: no cover
        logger.error("Error fetching user by email: %s", exc)
        return None
    if not doc:
        return None
    return UserInDB(**doc, id=str(doc["_id"]))


async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """Validate credentials; returns the user on success, None otherwise."""
    user = await get_user_by_email(email)
    if not user:
        logger.warning("Login failed (unknown email): %s", email)
        return None
    try:
        ok = bcrypt.checkpw(
            password.encode("utf-8"), user.hashed_password.encode("utf-8")
        )
    except ValueError:
        ok = False
    if not ok:
        logger.warning("Login failed (bad password): %s", email)
        return None
    await users_collection.update_one(
        {"email": user.email},
        {"$set": {"last_login": datetime.utcnow().isoformat()}},
    )
    return user
