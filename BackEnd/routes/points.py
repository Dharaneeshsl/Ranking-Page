"""
Points route - handles adding points by name (creates member if doesn't exist)
"""
from fastapi import APIRouter, HTTPException, status
from ..database import members_collection
from ..models import ActionType, ACTION_POINTS, ContributionBase
from ..utils import compute_level, get_badges
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class PointsRequest(BaseModel):
    name: str
    action: str

@router.post("/points")
async def add_points(request: PointsRequest):
    """
    Add points to a member by name. Creates member if they don't exist.
    This is the endpoint the frontend uses for the simple "Add Points" form.
    """
    try:
        # Validate action type
        try:
            action_type = ActionType(request.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type. Must be one of: {[e.value for e in ActionType]}"
            )
        
        # Get points for this action
        points = ACTION_POINTS[action_type]
        
        # Find or create member
        member = await members_collection.find_one({"name": request.name.strip()})
        
        if not member:
            # Create new member
            new_points = points
            new_level = compute_level(new_points)
            contribution = ContributionBase(
                action=action_type,
                points=points,
                timestamp=datetime.utcnow()
            ).dict()
            
            new_member = {
                "name": request.name.strip(),
                "points": new_points,
                "level": new_level,
                "contributions": [contribution],
                "badges": get_badges(new_points, [contribution]),
                "created_at": datetime.utcnow(),
                "last_active": datetime.utcnow()
            }
            
            result = await members_collection.insert_one(new_member)
            member_id = str(result.inserted_id)
            
            return {
                "status": "success",
                "message": f"Created new member and added {points} points",
                "data": {
                    "member_id": member_id,
                    "name": request.name.strip(),
                    "points_added": points,
                    "total_points": new_points,
                    "level": new_level
                }
            }
        else:
            # Update existing member
            member_id = str(member["_id"])
            current_points = member.get("points", 0)
            new_points = current_points + points
            new_level = compute_level(new_points)
            
            contribution = ContributionBase(
                action=action_type,
                points=points,
                timestamp=datetime.utcnow()
            ).dict()
            
            contributions = member.get("contributions", [])
            contributions.append(contribution)
            
            # Update badges
            new_badges = get_badges(new_points, contributions)
            
            await members_collection.update_one(
                {"_id": ObjectId(member_id)},
                {"$set": {
                    "points": new_points,
                    "level": new_level,
                    "contributions": contributions,
                    "badges": new_badges,
                    "last_active": datetime.utcnow()
                }}
            )
            
            return {
                "status": "success",
                "message": f"Added {points} points to member",
                "data": {
                    "member_id": member_id,
                    "name": request.name.strip(),
                    "points_added": points,
                    "total_points": new_points,
                    "level": new_level
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding points: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

