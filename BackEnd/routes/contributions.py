"""Contribution endpoints: list, add (admin), delete (admin)."""

from __future__ import annotations

import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

import database
from middleware.auth_middleware import require_auth
from models import ACTION_POINTS, ContributionCreate, action_label
from utils import make_contribution, recalc_member

router = APIRouter()
logger = logging.getLogger(__name__)


def _valid_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
        )


@router.get("/members/{member_id}/contributions")
async def list_contributions(member_id: str, limit: int = 50, offset: int = 0):
    """Public contribution history for a member (newest first)."""
    oid = _valid_id(member_id)
    member = await database.members_collection.find_one({"_id": oid})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    items = member.get("contributions", []) or []
    items = sorted(
        items, key=lambda c: c.get("timestamp", datetime.min), reverse=True
    )
    page = items[offset : offset + limit]

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

    return {
        "status": "success",
        "data": {
            "member_id": member_id,
            "member_name": member["name"],
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "contributions": [_fmt(c) for c in page],
        },
    }


@router.post("/members/{member_id}/contributions")
async def add_contribution(
    member_id: str,
    body: ContributionCreate,
    user: dict = Depends(require_auth()),
):
    """Add a contribution to an existing member (admin). Points are server-side."""
    oid = _valid_id(member_id)
    member = await database.members_collection.find_one({"_id": oid})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    points = ACTION_POINTS[body.action]
    contribution = make_contribution(
        body.action.value, points, body.description, user.get("email")
    )
    contributions = member.get("contributions", []) or []
    contributions.append(contribution)

    old_badges = set(member.get("badges", []))
    new_total = int(member.get("points", 0)) + points
    await database.members_collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "contributions": contributions,
                "points": new_total,
                "level": _level_for(new_total),
                "badges": _badges_for(new_total, contributions),
                "last_active": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    new_badges = set(_badges_for(new_total, contributions))
    return {
        "status": "success",
        "message": "Contribution recorded",
        "data": {
            "member_id": member_id,
            "member_name": member["name"],
            "contribution": contribution,
            "points_added": points,
            "total_points": new_total,
            "badges_earned": sorted(new_badges - old_badges),
            "badges": sorted(new_badges),
        },
    }


def _level_for(points: int) -> str:
    from utils import compute_level

    return compute_level(points)


def _badges_for(points: int, contributions) -> list:
    from utils import get_badges

    return get_badges(points, contributions)


@router.delete("/members/{member_id}/contributions/{contribution_id}")
async def delete_contribution(
    member_id: str, contribution_id: str, user: dict = Depends(require_auth())
):
    """Remove one contribution from the ledger and recompute totals (admin)."""
    oid = _valid_id(member_id)
    member = await database.members_collection.find_one({"_id": oid})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    contributions = member.get("contributions", []) or []
    target = next(
        (c for c in contributions if str(c.get("_id", "")) == contribution_id),
        None,
    )
    if not target:
        # Contribution docs created before IDs existed fall back to index match
        raise HTTPException(
            status_code=404, detail="Contribution not found"
        )

    contributions = [c for c in contributions if str(c.get("_id", "")) != contribution_id]
    # Persist the trimmed ledger first, then recompute totals from it.
    await database.members_collection.update_one(
        {"_id": oid}, {"$set": {"contributions": contributions}}
    )
    updated = await recalc_member(member_id, user.get("email"))
    return {
        "status": "success",
        "message": "Contribution removed and totals recalculated",
        "data": {
            "member_id": member_id,
            "removed_points": int(target.get("points", 0)),
            "total_points": updated["points"],
            "level": updated["level"],
            "badges": updated["badges"],
        },
    }
