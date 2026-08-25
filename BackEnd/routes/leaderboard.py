"""Leaderboard, stats and CSV export endpoints."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

import database
from utils import compute_level, get_badges, progress_for

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_LIMIT = 500


def _parse_date(value, field: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}. Use YYYY-MM-DD.",
        )


def _date_filter(time_frame: str, start_date: str, end_date: str) -> dict:
    """Build the contributions.timestamp filter (inclusive end-of-day)."""
    now = datetime.utcnow()
    if start_date and end_date:
        start = _parse_date(start_date, "start_date")
        end = _parse_date(end_date, "end_date") + timedelta(days=1)
        return {"contributions.timestamp": {"$gte": start, "$lt": end}}
    if time_frame == "week":
        return {"contributions.timestamp": {"$gte": now - timedelta(days=7)}}
    if time_frame == "month":
        return {"contributions.timestamp": {"$gte": now - timedelta(days=30)}}
    if time_frame == "year":
        return {"contributions.timestamp": {"$gte": now - timedelta(days=365)}}
    if time_frame == "custom":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail="Both start_date and end_date are required for custom time frame",
            )
        return _date_filter("", start_date, end_date)
    return {}


async def fetch_leaderboard(time_frame="all", start_date=None, end_date=None, limit=100):
    """Return ranked member entries for the given period."""
    limit = max(1, min(limit, MAX_LIMIT))
    date_filter = _date_filter(time_frame, start_date, end_date)

    if not date_filter:
        entries: List[dict] = []
        async for doc in database.members_collection.find({}).sort("points", -1).limit(limit):
            points = int(doc.get("points", 0))
            contributions = doc.get("contributions", []) or []
            entries.append(
                {
                    "member_id": str(doc["_id"]),
                    "id": str(doc["_id"]),
                    "name": doc.get("name", ""),
                    "total_points": points,
                    "points": points,
                    "level": doc.get("level", compute_level(points)),
                    "badges": doc.get("badges", get_badges(points, contributions)),
                    "total_contributions": len(contributions),
                    "last_active": doc.get("last_active"),
                }
            )
    else:
        pipeline = [
            {"$unwind": "$contributions"},
            {"$match": date_filter},
            {
                "$group": {
                    "_id": "$_id",
                    "name": {"$first": "$name"},
                    "contributions": {"$push": "$contributions"},
                    "points": {"$sum": "$contributions.points"},
                }
            },
            {"$sort": {"points": -1}},
            {"$limit": limit},
        ]
        entries = []
        async for doc in database.members_collection.aggregate(pipeline):
            points = int(doc.get("points", 0))
            if points <= 0:
                continue
            entries.append(
                {
                    "member_id": str(doc["_id"]),
                    "id": str(doc["_id"]),
                    "name": doc.get("name", ""),
                    "total_points": points,
                    "points": points,
                    "level": compute_level(points),
                    "badges": get_badges(points, doc.get("contributions", [])),
                    "total_contributions": len(doc.get("contributions", [])),
                    "last_active": None,
                }
            )

    for i, entry in enumerate(entries, 1):
        entry["rank"] = i
        entry.update(progress_for(entry["points"], entry["level"]))
    return entries


@router.get("/leaderboard")
async def get_leaderboard(
    time_frame: str = Query("all", pattern="^(all|week|month|year|custom)$"),
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(100, ge=1, le=MAX_LIMIT),
):
    """Ranked leaderboard for a period (public)."""
    try:
        members = await fetch_leaderboard(time_frame, start_date, end_date, limit)
        return {
            "status": "success",
            "data": {
                "leaderboard": members,
                "time_frame": time_frame,
                "total_members": len(members),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_leaderboard failed")
        raise HTTPException(
            status_code=500, detail="Internal server error while getting leaderboard"
        ) from exc


@router.get("/leaderboard/export")
async def export_leaderboard(
    time_frame: str = Query("all", pattern="^(all|week|month|year|custom)$"),
    start_date: str = None,
    end_date: str = None,
):
    """CSV export of the current leaderboard (public read)."""
    try:
        members = await fetch_leaderboard(time_frame, start_date, end_date, MAX_LIMIT)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["Rank", "Name", "Points", "Level", "Level Progress (%)", "Contributions", "Last Active"]
        )
        for m in members:
            writer.writerow(
                [
                    m["rank"],
                    m["name"],
                    m["total_points"],
                    m["level"],
                    m["progress"],
                    m["total_contributions"],
                    m.get("last_active") or "",
                ]
            )
        buf.seek(0)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="leaderboard_{stamp}.csv"'},
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.exception("export failed")
        raise HTTPException(status_code=500, detail="CSV export failed") from exc


@router.get("/stats")
async def get_stats():
    """Aggregate platform statistics (public)."""
    try:
        total_members = await database.members_collection.count_documents({})
        members: List[dict] = []
        async for doc in database.members_collection.find({}):
            members.append(doc)

        total_points = sum(int(d.get("points", 0) or 0) for d in members)
        active_cutoff = datetime.utcnow() - timedelta(days=7)
        # last_active may be datetime or iso-string from legacy docs
        active_week = [d for d in members if _is_recent(d.get("last_active"), active_cutoff)]

        level_counts = {"Bronze": 0, "Silver": 0, "Gold": 0, "Platinum": 0}
        for d in members:
            level_counts[d.get("level", compute_level(d.get("points", 0)))] = (
                level_counts.get(d.get("level", ""), 0) + 1
            )

        top = max(members, key=lambda d: d.get("points", 0)) if members else None
        return {
            "status": "success",
            "data": {
                "total_members": total_members,
                "total_points": total_points,
                "average_points": round(total_points / total_members, 1) if total_members else 0,
                "active_last_7_days": len(active_week),
                "top_member": (
                    {
                        "id": str(top["_id"]),
                        "name": top["name"],
                        "points": top.get("points", 0),
                        "level": top.get("level", "Bronze"),
                    }
                    if top
                    else None
                ),
                "levels": level_counts,
            },
        }
    except Exception as exc:
        logger.exception("stats failed")
        raise HTTPException(status_code=500, detail="Failed to compute stats") from exc


def _is_recent(value, cutoff) -> bool:
    if not value:
        return False
    if isinstance(value, datetime):
        return value >= cutoff
    try:
        return datetime.fromisoformat(str(value)) >= cutoff
    except (TypeError, ValueError):
        return False
