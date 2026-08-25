"""Authentication + authorization flow."""


def test_health_and_ready(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/ready").status_code == 200


def test_login_wrong_password(client):
    import os

    r = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": os.environ["ADMIN_PASSWORD"] + "-wrong",
        },
    )
    assert r.status_code == 401
    assert "Invalid" in r.json()["error"]


def test_login_ok_and_me(client, admin):
    r = client.get("/api/auth/me", cookies=admin["cookies"])
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == "admin@example.com"
    assert body["csrf_token"] == admin["csrf"]


def test_check_unauthenticated(client):
    r = client.get("/api/auth/check")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_logout_invalidates_session(client, admin):
    r = client.post("/api/auth/logout", cookies=admin["cookies"], headers=admin["headers"])
    assert r.status_code == 200
    assert client.get("/api/auth/me", cookies=admin["cookies"]).status_code == 401


def test_mutation_without_csrf_rejected(client, admin):
    r = client.post(
        "/api/points",
        json={"name": "Alice", "action": "attend_event"},
        cookies=admin["cookies"],
    )
    assert r.status_code == 403


def test_reads_are_public(client, admin):
    assert client.get("/api/leaderboard").status_code == 200
    assert client.get("/api/members").status_code == 200
    assert client.get("/api/stats").status_code == 200


def test_members_write_requires_auth(client):
    assert client.put("/api/members/000000000000000000000000", json={"points": 5}).status_code == 401
    assert client.delete("/api/members/000000000000000000000000").status_code == 401
