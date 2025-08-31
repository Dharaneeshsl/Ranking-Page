from fastapi import APIRouter, HTTPException, status
from database import members_collection
from utils import get_member_rank, calculate_next_level_points
from models import ActionType
from bson import ObjectId
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/members/{member_id}")
async def get_member_profile(member_id: str):
    try:
        member = await members_collection.find_one({"_id": ObjectId(member_id)})
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        rank = await get_member_rank(member["points"])
        next_level_points = calculate_next_level_points(member["level"])
        progress = int((member["points"] / next_level_points) * 100) if next_level_points else 100

        contributions = member.get("contributions", [])
        contributions_by_type = {a.value: {"count": 0, "total_points": 0} for a in ActionType}
        for contrib in contributions:
            action = contrib.get("action")
            action_str = action.value if isinstance(action, ActionType) else action
            if action_str in contributions_by_type:
                contributions_by_type[action_str]["count"] += 1
                contributions_by_type[action_str]["total_points"] += contrib.get("points", 0)

        contributions_by_type = {k: v for k, v in contributions_by_type.items() if v["count"] > 0}
        recent_contributions = sorted(contributions, key=lambda x: x.get("timestamp", datetime.min), reverse=True)[:10]

        return {
            "status": "success",
            "data": {
                "id": str(member["_id"]),
                "name": member["name"],
                "points": member["points"],
                "level": member["level"],
                "badges": member.get("badges", []),
                "rank": rank,
                "next_level_points": next_level_points,
                "progress": progress,
                "total_contributions": len(contributions),
                "contributions_by_type": contributions_by_type,
                "recent_contributions": recent_contributions,
            }
        }

    except Exception as e:
        logger.error(f"Error getting member profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
