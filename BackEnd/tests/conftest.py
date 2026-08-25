"""Shared fixtures - swap real MongoDB for an in-memory mock per test."""

import os
import secrets

# Configure BEFORE importing the app so config picks up test settings.
# The test admin password is generated at runtime - never a literal in source.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("MOCK_DB", "1")
os.environ.setdefault("SECRET_KEY", "test" + secrets.token_urlsafe(24))
os.environ.setdefault("DATABASE_NAME", "ranking_test")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "test" + secrets.token_urlsafe(12))
os.environ.setdefault("ADMIN_NAME", "Test Admin")
os.environ.setdefault("FRONTEND_URLS", "http://localhost:5173")
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "10000")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")

import pytest
from mongomock_motor import AsyncMongoMockClient

import database
from main import app


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    db = client.get_database("ranking_test")
    database.client = client
    database.db = db
    database.users_collection = db.users
    database.members_collection = db.members
    database.sessions_collection = db.sessions
    yield db
    database.client = None
    database.db = None
    database.users_collection = None
    database.members_collection = None
    database.sessions_collection = None


@pytest.fixture
def client(mock_db):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(client):
    """Authenticated admin helper returning (cookies, csrf, headers)."""
    r = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": os.environ["ADMIN_PASSWORD"],
        },
    )
    assert r.status_code == 200, r.text
    csrf = r.json()["csrf_token"]
    cookie = r.cookies.get("session_id")
    return {
        "cookies": {"session_id": cookie},
        "csrf": csrf,
        "headers": {"X-CSRF-Token": csrf},
    }
