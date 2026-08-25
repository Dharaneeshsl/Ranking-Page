"""Points, members, contributions and leaderboard flows."""


def _award(client, admin, name, action):
    return client.post(
        "/api/points",
        json={"name": name, "action": action},
        cookies=admin["cookies"],
        headers=admin["headers"],
    )


def test_add_points_creates_member_and_updates(client, admin):
    r = _award(client, admin, "Alice", "attend_event")
    assert r.status_code == 200
    assert r.json()["data"]["total_points"] == 10

    r = _award(client, admin, "Alice", "bring_sponsorship")
    assert r.status_code == 200
    assert r.json()["data"]["total_points"] == 110
    assert r.json()["data"]["level"] == "Silver"  # 110 >= 51
    assert "Silver Member" in r.json()["data"]["badges"]


def test_leaderboard_ordering_and_profile(client, admin):
    _award(client, admin, "Alice", "attend_event")  # 10
    _award(client, admin, "Bob", "bring_sponsorship")  # 100
    _award(client, admin, "Bob", "volunteer_task")  # +20 = 120

    lb = client.get("/api/leaderboard").json()["data"]["leaderboard"]
    assert [m["name"] for m in lb] == ["Bob", "Alice"]
    assert lb[0]["total_points"] == 120
    assert lb[0]["rank"] == 1
    assert lb[0]["progress"] is not None

    profile = client.get(f"/api/members/{lb[0]['member_id']}").json()["data"]
    assert profile["rank"] == 1
    assert profile["total_contributions"] == 2
    assert "volunteer_task" in profile["contributions_by_type"]


async def test_date_filter_leaderboard(client, admin):
    import datetime

    from database import members_collection

    _award(client, admin, "Old", "attend_event")
    _award(client, admin, "New", "attend_event")

    old = await members_collection.find_one({"name": "Old"})
    old["contributions"][0]["timestamp"] = datetime.datetime(1999, 12, 31)
    await members_collection.update_one(
        {"_id": old["_id"]}, {"$set": {"contributions": old["contributions"]}}
    )

    r = client.get(
        "/api/leaderboard",
        params={"start_date": "2000-01-01", "end_date": "2000-01-02"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["total_members"] == 0  # Old outside range, New is 2026


def test_reject_invalid_action(client, admin):
    r = client.post(
        "/api/points",
        json={"name": "X", "action": "fly_to_mars"},
        cookies=admin["cookies"],
        headers=admin["headers"],
    )
    assert r.status_code == 422


def test_manual_adjust_and_delete_contribution(client, admin):
    r = _award(client, admin, "Carol", "attend_event")  # 10
    mid = r.json()["data"]["member_id"]

    r = client.put(
        f"/api/members/{mid}",
        json={"points": 500, "reason": "campaign bonus"},
        cookies=admin["cookies"],
        headers=admin["headers"],
    )
    assert r.status_code == 200
    assert r.json()["data"]["points"] == 500
    assert r.json()["data"]["level"] == "Platinum"

    contribs = client.get(f"/api/members/{mid}/contributions").json()["data"]
    assert contribs["total"] == 2

    # delete the manual adjustment (490): total should return to 10
    manual = next(c for c in contribs["contributions"] if c["action"] == "manual_adjustment")
    r = client.delete(
        f"/api/members/{mid}/contributions/{manual['id']}",
        cookies=admin["cookies"],
        headers=admin["headers"],
    )
    assert r.status_code == 200
    assert r.json()["data"]["total_points"] == 10

    profile = client.get(f"/api/members/{mid}").json()["data"]
    assert profile["points"] == 10
    assert profile["total_contributions"] == 1


def test_stats_endpoint(client, admin):
    _award(client, admin, "Alice", "bring_sponsorship")
    _award(client, admin, "Bob", "attend_event")
    stats = client.get("/api/stats").json()["data"]
    assert stats["total_members"] == 2
    assert stats["total_points"] == 110
    assert stats["top_member"]["name"] == "Alice"


def test_csv_export(client, admin):
    _award(client, admin, "Alice", "attend_event")
    r = client.get("/api/leaderboard/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "Alice" in r.text
