"""Points route: add points by member name (auto-creates the member)."""

from __future__ import annotations

import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

import database
from middleware.auth_middleware import require_auth
from models import ACTION_POINTS, PointsRequest
from utils import (
    compute_member_stats,
    find_member_by_name,
    make_contribution,
    progress_for,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/points")
async def add_points(body: PointsRequest, user: dict = Depends(require_auth())):
    """
    Award points for an action to a member (created on the fly).
    Points are always derived server-side from the action type.
    """
    try:
        points = ACTION_POINTS[body.action]
        created_by = user.get("email", "admin")
        member = await find_member_by_name(body.name)

        if not member:
            contribution = make_contribution(
                body.action.value, points, body.description, created_by
            )
            stats = compute_member_stats([contribution])
            now = datetime.utcnow()
            new_member = {
                "name": body.name,
                "email": None,
                "points": stats["points"],
                "level": stats["level"],
                "badges": stats["badges"],
                "contributions": [contribution],
                "created_at": now,
                "updated_at": now,
                "last_active": now,
            }
            result = await database.members_collection.insert_one(new_member)
            member_id = str(result.inserted_id)
            message = f"Created member and awarded {points} points"
        else:
            member_id = str(member["_id"])
            contributions = member.get("contributions", []) or []
            contributions.append(
                make_contribution(body.action.value, points, body.description, created_by)
            )
            stats = compute_member_stats(contributions)
            now = datetime.utcnow()
            await database.members_collection.update_one(
                {"_id": ObjectId(member_id)},
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
            message = f"Awarded {points} points to {member['name']}"

        total = stats["points"]
        return {
            "status": "success",
            "message": message,
            "data": {
                "member_id": member_id,
                "name": body.name,
                "points_added": points,
                "total_points": total,
                "level": stats["level"],
                "badges": stats["badges"],
                **progress_for(total, stats["level"]),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("add_points failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while awarding points",
        ) from exc
