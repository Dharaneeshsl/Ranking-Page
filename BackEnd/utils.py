from datetime import datetime
from typing import List, Dict, Any
from models import BadgeType, ActionType
from database import members_collection
import logging

logger = logging.getLogger(__name__)

BADGE_THRESHOLDS = {
    BadgeType.BRONZE: 0,
    BadgeType.SILVER: 51,
    BadgeType.GOLD: 151,
    BadgeType.PLATINUM: 300,
    BadgeType.TOP_CONTRIBUTOR: 500,
    BadgeType.EVENT_ORGANIZER: 5,
    BadgeType.SPONSORSHIP_CHAMPION: 3
}

def compute_level(points: int) -> str:
    if points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        return BadgeType.PLATINUM.value
    if points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        return BadgeType.GOLD.value
    if points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        return BadgeType.SILVER.value
    return BadgeType.BRONZE.value

def get_badges(points: int, contributions: List[Dict[str, Any]]) -> List[str]:
    badges = [compute_level(points)]
    if contributions:
        event_lead_count = sum(1 for c in contributions if c.get("action") == ActionType.LEAD_EVENT)
        sponsorship_count = sum(1 for c in contributions if c.get("action") == ActionType.BRING_SPONSORSHIP)
        if event_lead_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
            badges.append(BadgeType.EVENT_ORGANIZER.value)
        if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
            badges.append(BadgeType.SPONSORSHIP_CHAMPION.value)
    return list(dict.fromkeys(badges))  # remove duplicates

async def get_member_rank(points: int):
    try:
        count = await members_collection.count_documents({"points": {"$gt": points}})
        return count + 1
    except Exception as e:
        logger.error(f"Error getting member rank: {str(e)}")
        return 1

def calculate_next_level_points(current_level: str) -> int:
    level_map = {
        BadgeType.BRONZE: BADGE_THRESHOLDS[BadgeType.SILVER],
        BadgeType.SILVER: BADGE_THRESHOLDS[BadgeType.GOLD],
        BadgeType.GOLD: BADGE_THRESHOLDS[BadgeType.PLATINUM],
        BadgeType.PLATINUM: None
    }
    return level_map.get(BadgeType(current_level), None)
