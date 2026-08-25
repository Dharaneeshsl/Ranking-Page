"""
Business logic helpers: levels, badges, member stats recomputation.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import database
from models import ActionType, BadgeType, Contribution, action_label

logger = logging.getLogger(__name__)

# Level thresholds (points required to REACH the level)
LEVEL_THRESHOLDS: dict[str, int] = {
    "Bronze": 0,
    "Silver": 51,
    "Gold": 151,
    "Platinum": 301,
}

LEVEL_ORDER = ["Bronze", "Silver", "Gold", "Platinum"]

BADGE_THRESHOLDS = {
    BadgeType.SILVER: LEVEL_THRESHOLDS["Silver"],
    BadgeType.GOLD: LEVEL_THRESHOLDS["Gold"],
    BadgeType.PLATINUM: LEVEL_THRESHOLDS["Platinum"],
    BadgeType.EVENT_ORGANIZER: 5,   # events led
    BadgeType.SPONSORSHIP_CHAMPION: 3,  # sponsorships brought
    BadgeType.TOP_CONTRIBUTOR: 500,  # 500+ points
}


def compute_level(points: int) -> str:
    """Return the level name for a point total."""
    if points >= LEVEL_THRESHOLDS["Platinum"]:
        return "Platinum"
    if points >= LEVEL_THRESHOLDS["Gold"]:
        return "Gold"
    if points >= LEVEL_THRESHOLDS["Silver"]:
        return "Silver"
    return "Bronze"


def calculate_next_level_points(current_level: str) -> int:
    """Threshold (points) of the next level; same as current for max level."""
    try:
        idx = LEVEL_ORDER.index(current_level)
    except ValueError:
        return LEVEL_THRESHOLDS["Silver"]
    if idx >= len(LEVEL_ORDER) - 1:
        return LEVEL_THRESHOLDS["Platinum"]
    return LEVEL_THRESHOLDS[LEVEL_ORDER[idx + 1]]


def get_badges(points: int, contributions: List[Dict[str, Any]]) -> List[str]:
    """Compute the full badge list for a member."""
    badges: List[str] = []
    if points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        badges.append(BadgeType.PLATINUM.value)
    if points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        badges.append(BadgeType.GOLD.value)
    if points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        badges.append(BadgeType.SILVER.value)

    event_count = sum(
        1
        for c in contributions
        if str(c.get("action", "")) in (ActionType.LEAD_EVENT.value,)
    )
    sponsorship_count = sum(
        1
        for c in contributions
        if str(c.get("action", "")) in (ActionType.BRING_SPONSORSHIP.value,)
    )
    if event_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
        badges.append(BadgeType.EVENT_ORGANIZER.value)
    if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
        badges.append(BadgeType.SPONSORSHIP_CHAMPION.value)
    if points >= BADGE_THRESHOLDS[BadgeType.TOP_CONTRIBUTOR]:
        badges.append(BadgeType.TOP_CONTRIBUTOR.value)
    return badges


def compute_member_stats(contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Derive points/level/badges purely from the contribution ledger.
    Points are always the sum of the ledger, so history stays consistent.
    """
    points = sum(int(c.get("points", 0) or 0) for c in contributions)
    return {
        "points": points,
        "level": compute_level(points),
        "badges": get_badges(points, contributions),
    }


def progress_for(points: int, level: str) -> Dict[str, Any]:
    """Progress info toward the next level: {next_level_points, points_to_next, progress}."""
    next_level_points = calculate_next_level_points(level)
    if level == "Platinum":
        return {
            "next_level_points": next_level_points,
            "points_to_next": 0,
            "progress": 100,
            "maxed": True,
        }
    span = next_level_points - LEVEL_THRESHOLDS[level] if next_level_points > 0 else 1
    within = max(0, points - LEVEL_THRESHOLDS[level])
    progress = min(100, int(round(within * 100 / span)))
    return {
        "next_level_points": next_level_points,
        "points_to_next": max(0, next_level_points - points),
        "progress": progress,
        "maxed": False,
    }


def make_contribution(
    action: str,
    points: int,
    description: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a contribution dict (with _id + datetime timestamp) ready to store."""
    from bson import ObjectId

    doc = Contribution(
        action=action,
        points=points,
        description=description
        or (
            action_label(action)
            if action != "manual_adjustment"
            else None
        ),
        timestamp=datetime.utcnow(),
        created_by=created_by,
    ).model_dump()
    doc["_id"] = ObjectId()
    return doc


async def get_member_rank(points: int) -> int:
    """1-based rank: how many members have strictly more points."""
    count = await database.members_collection.count_documents(
        {"points": {"$gt": points}}
    )
    return count + 1


async def recalc_member(member_id: str, admin_email: Optional[str] = None) -> dict:
    """
    Recompute points/level/badges for a member from its contribution ledger
    and persist the result. Returns a snapshot of the updated member.
    """
    from bson import ObjectId

    member = await database.members_collection.find_one({"_id": ObjectId(member_id)})
    if not member:
        return None
    contributions = member.get("contributions", []) or []
    stats = compute_member_stats(contributions)
    await database.members_collection.update_one(
        {"_id": ObjectId(member_id)},
        {
            "$set": {
                "points": stats["points"],
                "level": stats["level"],
                "badges": stats["badges"],
                "last_active": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    member.update(stats)
    member["last_active"] = datetime.utcnow()
    return member


async def find_member_by_name(name: str) -> Optional[dict]:
    """Case-insensitive exact-name lookup."""
    pattern = re.compile(rf"^{re.escape(name.strip())}$", re.IGNORECASE)
    return await database.members_collection.find_one({"name": pattern})


def serialize_member_dict(doc: dict, with_contributions: bool = False) -> dict:
    """Convert a stored member doc into an API-safe dict."""
    members_collection = database.members_collection  # noqa: F841 (kept for clarity)
    data = {
        "id": str(doc["_id"]),
        "member_id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "email": doc.get("email"),
        "points": doc.get("points", 0),
        "level": doc.get("level", "Bronze"),
        "badges": doc.get("badges", []),
        "total_contributions": len(doc.get("contributions", []) or []),
        "last_active": doc.get("last_active"),
        "created_at": doc.get("created_at"),
    }
    return data
