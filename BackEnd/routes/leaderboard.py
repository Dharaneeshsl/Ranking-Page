from fastapi import APIRouter, HTTPException, status
from ..database import members_collection
from ..utils import compute_level, get_badges
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/leaderboard")
async def get_leaderboard(time_frame: str = "all", start_date: str = None, end_date: str = None, limit: int = 100):
    try:
        now = datetime.utcnow()
        date_filter = {}
        
        # Handle date filtering - if start_date/end_date provided, use them regardless of time_frame
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                date_filter = {"contributions.timestamp": {"$gte": start, "$lte": end}}
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
        elif time_frame == "week":
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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both start_date and end_date are required for custom time frame")
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
            date_filter = {"contributions.timestamp": {"$gte": start, "$lte": end}}

        # If no date filter, just get all members with their total points
        if not date_filter:
            members = []
            async for member in members_collection.find({}).sort("points", -1).limit(limit):
                points = member.get("points", 0)
                contributions = member.get("contributions", [])
                members.append({
                    "member_id": str(member["_id"]),
                    "id": str(member["_id"]),
                    "name": member.get("name", ""),
                    "total_points": points,
                    "points": points,
                    "level": member.get("level", compute_level(points)),
                    "badges": member.get("badges", get_badges(points, contributions))
                })
        else:
            # Use MongoDB aggregation pipeline for filtering and sorting
            pipeline = [
                {"$unwind": "$contributions"},
                {"$match": date_filter},
                {"$group": {
                    "_id": "$_id",
                    "name": {"$first": "$name"},
                    "contributions": {"$push": "$contributions"},
                    "points": {"$sum": "$contributions.points"}
                }},
                {"$sort": {"points": -1}},
                {"$limit": limit}
            ]

            members = []
            async for member in members_collection.aggregate(pipeline):
                points = member.get("points", 0)
                if points > 0:
                    members.append({
                        "member_id": str(member["_id"]),
                        "id": str(member["_id"]),
                        "name": member["name"],
                        "total_points": points,
                        "points": points,
                        "level": compute_level(points),
                        "badges": get_badges(points, member.get("contributions", []))
                    })

        for i, member in enumerate(members, 1):
            member["rank"] = i

        return {"status": "success", "data": {"leaderboard": members, "time_frame": time_frame, "total_members": len(members)}}

    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while getting leaderboard")
