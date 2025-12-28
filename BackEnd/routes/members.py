from fastapi import APIRouter, HTTPException, status, Depends
from ..database import members_collection
from ..utils import get_member_rank, calculate_next_level_points, compute_level, get_badges
from ..models import ActionType, ACTION_POINTS
from ..middleware.auth_middleware import require_auth
from bson import ObjectId
from datetime import datetime
from typing import List
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/members")
async def get_all_members():
    """Get all members"""
    try:
        members = []
        async for member in members_collection.find({}):
            members.append({
                "id": str(member["_id"]),
                "name": member.get("name", ""),
                "points": member.get("points", 0),
                "level": member.get("level", "Bronze"),
                "badges": member.get("badges", [])
            })
        return {"status": "success", "data": {"members": members, "total": len(members)}}
    except Exception as e:
        logger.error(f"Error getting all members: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/members/{member_id}")
async def update_member_points(member_id: str, data: dict):
    """Update member's total points"""
    try:
        try:
            ObjectId(member_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid member ID format")
        
        member = await members_collection.find_one({"_id": ObjectId(member_id)})
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
        new_points = int(data.get("points", member.get("points", 0)))
        new_level = compute_level(new_points)
        
        # Recalculate badges based on new points and contributions
        contributions = member.get("contributions", [])
        new_badges = get_badges(new_points, contributions)
        
        await members_collection.update_one(
            {"_id": ObjectId(member_id)},
            {"$set": {
                "points": new_points,
                "level": new_level,
                "badges": new_badges,
                "last_active": datetime.utcnow()
            }}
        )
        
        return {
            "status": "success",
            "message": "Member points updated successfully",
            "data": {
                "id": member_id,
                "points": new_points,
                "level": new_level,
                "badges": new_badges
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member points: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/members/{member_id}")
async def delete_member(member_id: str):
    """Delete a member"""
    try:
        try:
            ObjectId(member_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid member ID format")
        
        result = await members_collection.delete_one({"_id": ObjectId(member_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
        return {"status": "success", "message": "Member deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting member: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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
