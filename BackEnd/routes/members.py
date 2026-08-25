"""Member management endpoints (public reads, admin-only writes)."""

from __future__ import annotations

import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

import database
from middleware.auth_middleware import require_admin, require_auth
from models import ManualPointsUpdate, MemberCreate, action_label
from utils import (
    compute_level,
    compute_member_stats,
    find_member_by_name,
    get_member_rank,
    make_contribution,
    progress_for,
    serialize_member_dict,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _valid_id(member_id: str) -> ObjectId:
    try:
        return ObjectId(member_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid member ID format"
        )


@router.get("/members")
async def get_all_members():
    """List all members (public)."""
    members = []
    async for doc in database.members_collection.find({}).sort("points", -1):
        members.append(serialize_member_dict(doc))
    return {"status": "success", "data": {"members": members, "total": len(members)}}


@router.post("/members")
async def create_member(body: MemberCreate, user: dict = Depends(require_admin)):
    """Create a member directly with optional starting points (admin)."""
    existing = await find_member_by_name(body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this name already exists",
        )
    contributions = []
    if body.initial_points > 0:
        contributions.append(
            make_contribution(
                "manual_adjustment",
                body.initial_points,
                "Initial balance",
                user.get("email"),
            )
        )
    stats = compute_member_stats(contributions)
    now = datetime.utcnow()
    doc = {
        "name": body.name,
        "email": body.email,
        "points": stats["points"],
        "level": stats["level"],
        "badges": stats["badges"],
        "contributions": contributions,
        "created_at": now,
        "updated_at": now,
        "last_active": now if contributions else None,
    }
    result = await database.members_collection.insert_one(doc)
    return {
        "status": "success",
        "message": "Member created",
        "data": serialize_member_dict({**doc, "_id": result.inserted_id}),
    }


@router.get("/members/{member_id}")
async def get_member_profile(member_id: str):
    """Full member profile with rank, progress and contribution history (public)."""
    oid = _valid_id(member_id)
    member = await database.members_collection.find_one({"_id": oid})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    point_stats = member.get("points", 0)
    rank = await get_member_rank(point_stats)
    level = member.get("level", compute_level(point_stats))
    progress = progress_for(point_stats, level)

    contributions = member.get("contributions", []) or []
    by_type: dict[str, dict] = {}
    for c in contributions:
        key = str(c.get("action", "unknown"))
        entry = by_type.setdefault(
            key, {"label": action_label(key), "count": 0, "total_points": 0}
        )
        entry["count"] += 1
        entry["total_points"] += int(c.get("points", 0))

    def _fmt(c: dict) -> dict:
        return {
            "id": str(c.get("_id", "")),
            "action": str(c.get("action", "")),
            "label": action_label(str(c.get("action", ""))),
            "points": int(c.get("points", 0)),
            "description": c.get("description"),
            "timestamp": c.get("timestamp"),
            "created_by": c.get("created_by"),
        }

    recent = sorted(
        contributions, key=lambda c: c.get("timestamp", datetime.min), reverse=True
    )[:10]

    return {
        "status": "success",
        "data": {
            "id": str(member["_id"]),
            "name": member["name"],
            "email": member.get("email"),
            "points": point_stats,
            "level": level,
            "badges": member.get("badges", []),
            "rank": rank,
            "total_contributions": len(contributions),
            "total_points_contributions": sum(
                int(c.get("points", 0)) for c in contributions
            ),
            "next_level_points": progress["next_level_points"],
            "points_to_next": progress["points_to_next"],
            "progress": progress["progress"],
            "maxed": progress["maxed"],
            "contributions_by_type": by_type,
            "recent_contributions": [_fmt(c) for c in recent],
            "created_at": member.get("created_at"),
            "last_active": member.get("last_active"),
        },
    }


@router.put("/members/{member_id}")
async def update_member_points(
    member_id: str, body: ManualPointsUpdate, user: dict = Depends(require_auth())
):
    """
    Admin override: set the member's absolute total points.
    The delta is recorded in the ledger as a manual adjustment so history and
    date-filtered rankings stay consistent.
    """
    oid = _valid_id(member_id)
    member = await database.members_collection.find_one({"_id": oid})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    current = int(member.get("points", 0))
    contributions = member.get("contributions", []) or []
    delta = body.points - current
    if delta != 0:
        contributions.append(
            make_contribution(
                "manual_adjustment",
                delta,
                body.reason or f"Adjusted total to {body.points}",
                user.get("email"),
            )
        )
    stats = compute_member_stats(contributions)  # == body.points by construction
    now = datetime.utcnow()
    await database.members_collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "points": stats["points"],
                "level": stats["level"],
                "badges": stats["badges"],
                "contributions": contributions,
                "last_active": now,
                "updated_at": now,
            }
        },
    )
    return {
        "status": "success",
        "message": "Member points updated",
        "data": {
            "id": member_id,
            "name": member["name"],
            "points": stats["points"],
            "level": stats["level"],
            "badges": stats["badges"],
            "delta": delta,
            **progress_for(stats["points"], stats["level"]),
        },
    }


@router.delete("/members/{member_id}")
async def delete_member(member_id: str, user: dict = Depends(require_admin)):
    """Permanently delete a member (admin)."""
    oid = _valid_id(member_id)
    result = await database.members_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "success", "message": "Member deleted successfully"}
