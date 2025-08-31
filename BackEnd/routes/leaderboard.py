from fastapi import APIRouter, HTTPException, status
from database import members_collection
from utils import compute_level, get_badges
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/leaderboard")
async def get_leaderboard(time_frame: str = "all", start_date: str = None, end_date: str = None, limit: int = 100):
    try:
        now = datetime.utcnow()
        date_filter = {}

        if time_frame == "week":
            start = now - timedelta(weeks=1)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "month":
            start = now - timedelta(days=30)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "year":
            start = now - timedelta(days=365)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "custom":
            if not start_date or not end_date:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both start_date and end_date are required")
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            date_filter = {"contributions.timestamp": {"$gte": start, "$lte": end}}

        members = []
        async for member in members_collection.find():
            contributions = member.get("contributions", [])
            if date_filter:
                start = date_filter["contributions.timestamp"].get("$gte", datetime.min)
                end = date_filter["contributions.timestamp"].get("$lte", datetime.max)
                contributions = [c for c in contributions if start <= c.get("timestamp", datetime.min) <= end]

            points = sum(c.get("points", 0) for c in contributions)
            if points > 0:
                members.append({
                    "id": str(member["_id"]),
                    "name": member["name"],
                    "points": points,
                    "level": compute_level(points),
                    "badges": get_badges(points, contributions)
                })

        members.sort(key=lambda x: x["points"], reverse=True)
        for i, member in enumerate(members[:limit], 1):
            member["rank"] = i

        return {"status": "success", "data": {"leaderboard": members, "time_frame": time_frame, "total_members": len(members)}}

    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
