from fastapi import APIRouter, HTTPException, status, Depends

from datetime import datetime
from typing import Dict, Any
import logging
from bson import ObjectId

from ..database import members_collection
from ..models import ActionType, ContributionBase, BadgeType
from ..utils import get_badges, compute_level, BADGE_THRESHOLDS
from ..middleware.auth_middleware import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)
async def update_member_points(member_id: str, contribution: Dict[str, Any]):
    """Update member's points, level, and badges based on new contribution"""
    # Get current member data
    member = await members_collection.find_one({"_id": ObjectId(member_id)})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Update points and contributions
    new_points = member.get('points', 0) + contribution['points']
    new_level = compute_level(new_points)
    
    # Update contributions
    contributions = member.get('contributions', [])
    contributions.append(contribution)
    
    # Update badges
    current_badges = set(member.get('badges', []))

    # Level-based badges (award all deserved badges)
    if new_points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        current_badges.add(BadgeType.PLATINUM.value)
    if new_points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        current_badges.add(BadgeType.GOLD.value)
    if new_points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        current_badges.add(BadgeType.SILVER.value)
    
    # Special badges
    event_lead_count = sum(1 for c in contributions if c.get("action") == ActionType.LEAD_EVENT.value or c.get("action") == ActionType.LEAD_EVENT)
    sponsorship_count = sum(1 for c in contributions if c.get("action") == ActionType.BRING_SPONSORSHIP.value or c.get("action") == ActionType.BRING_SPONSORSHIP)
    
    if event_lead_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
        current_badges.add(BadgeType.EVENT_ORGANIZER.value)
    if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
        current_badges.add(BadgeType.SPONSORSHIP_CHAMPION.value)
    if new_points >= BADGE_THRESHOLDS[BadgeType.TOP_CONTRIBUTOR]:
        current_badges.add(BadgeType.TOP_CONTRIBUTOR.value)
    
    # Update member in database
    update_data = {
        "$set": {
            "points": new_points,
            "level": new_level,
            "contributions": contributions,
            "badges": list(current_badges),
            "last_active": datetime.utcnow()
        }
    }
    
    await members_collection.update_one(
        {"_id": ObjectId(member_id)},
        update_data
    )
    
    return {
        "member_id": str(member_id),
        "points_added": contribution['points'],
        "new_total_points": new_points,
        "new_level": new_level,
        "badges_earned": list(current_badges - set(member.get('badges', [])))
    }

@router.post("/members/{member_id}/contributions")
async def add_contribution(
    member_id: str,
    contribution_data: Dict[str, Any],
    user: dict = Depends(require_auth())
):
    try:
        # Validate MongoDB ObjectId
        try:
            ObjectId(member_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid member ID format"
            )

        # Validate action type
        try:
            action = ActionType(contribution_data['action'])
            contribution_data['action'] = action
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type. Must be one of: {[e.value for e in ActionType]}"
            )

        # Ensure points are provided and valid
        if 'points' not in contribution_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Points must be provided in contribution data"
            )

        if not isinstance(contribution_data['points'], (int, float)) or contribution_data['points'] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Points must be a non-negative number"
            )

        # Create contribution with validated data
        contribution = ContributionBase(**contribution_data).dict()

        # Update member points and get result
        result = await update_member_points(member_id, contribution)

        return {
            "status": "success",
            "data": {
                "contribution": contribution,
                **result
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding contribution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while adding contribution"
        )
