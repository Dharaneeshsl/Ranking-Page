"""
Utility functions for the ranking system.
"""
from enum import Enum
from typing import List, Dict, Any
from .database import members_collection
from .models import BadgeType

# Level thresholds
LEVEL_THRESHOLDS = {
    "Bronze": 0,
    "Silver": 51,
    "Gold": 151,
    "Platinum": 301
}

# Badge thresholds
BADGE_THRESHOLDS = {
    BadgeType.BRONZE: 0,
    BadgeType.SILVER: 51,
    BadgeType.GOLD: 151,
    BadgeType.PLATINUM: 301,
    BadgeType.EVENT_ORGANIZER: 5,  # 5 events led
    BadgeType.SPONSORSHIP_CHAMPION: 3,  # 3 sponsorships
    BadgeType.TOP_CONTRIBUTOR: 500  # 500+ points
}

def compute_level(points: int) -> str:
    """
    Calculate member level based on points.
    
    Args:
        points: Total points accumulated
        
    Returns:
        Level name (Bronze, Silver, Gold, Platinum)
    """
    if points >= LEVEL_THRESHOLDS["Platinum"]:
        return "Platinum"
    elif points >= LEVEL_THRESHOLDS["Gold"]:
        return "Gold"
    elif points >= LEVEL_THRESHOLDS["Silver"]:
        return "Silver"
    else:
        return "Bronze"

def calculate_next_level_points(current_level: str) -> int:
    """
    Calculate points needed for next level.
    
    Args:
        current_level: Current level name
        
    Returns:
        Points threshold for next level
    """
    level_order = ["Bronze", "Silver", "Gold", "Platinum"]
    try:
        current_index = level_order.index(current_level)
        if current_index < len(level_order) - 1:
            return LEVEL_THRESHOLDS[level_order[current_index + 1]]
        return LEVEL_THRESHOLDS["Platinum"]  # Max level
    except ValueError:
        return LEVEL_THRESHOLDS["Silver"]

def get_badges(points: int, contributions: List[Dict[str, Any]]) -> List[str]:
    """
    Calculate badges earned by a member.
    
    Args:
        points: Total points
        contributions: List of contribution documents
        
    Returns:
        List of badge names
    """
    badges = []
    
    # Level-based badges
    if points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        badges.append(BadgeType.PLATINUM.value)
    if points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        badges.append(BadgeType.GOLD.value)
    if points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        badges.append(BadgeType.SILVER.value)
    
    # Special badges
    from .models import ActionType
    event_lead_count = sum(1 for c in contributions if c.get("action") == ActionType.LEAD_EVENT.value or c.get("action") == ActionType.LEAD_EVENT)
    sponsorship_count = sum(1 for c in contributions if c.get("action") == ActionType.BRING_SPONSORSHIP.value or c.get("action") == ActionType.BRING_SPONSORSHIP)
    
    if event_lead_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
        badges.append(BadgeType.EVENT_ORGANIZER.value)
    if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
        badges.append(BadgeType.SPONSORSHIP_CHAMPION.value)
    if points >= BADGE_THRESHOLDS[BadgeType.TOP_CONTRIBUTOR]:
        badges.append(BadgeType.TOP_CONTRIBUTOR.value)
    
    return badges

async def get_member_rank(points: int) -> int:
    """
    Get rank of a member based on their points.
    
    Args:
        points: Member's total points
        
    Returns:
        Rank (1-based)
    """
    count = await members_collection.count_documents({"points": {"$gt": points}})
    return count + 1

