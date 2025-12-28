"""
Models for the ranking system.
"""
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    """Types of contributions/actions"""
    ATTEND_EVENT = "attend_event"
    VOLUNTEER_TASK = "volunteer_task"
    LEAD_EVENT = "lead_event"
    UPLOAD_DOCS = "upload_docs"
    BRING_SPONSORSHIP = "bring_sponsorship"

class BadgeType(str, Enum):
    """Types of badges"""
    BRONZE = "Bronze Member"
    SILVER = "Silver Member"
    GOLD = "Gold Member"
    PLATINUM = "Platinum Member"
    EVENT_ORGANIZER = "Event Organizer"
    SPONSORSHIP_CHAMPION = "Sponsorship Champion"
    TOP_CONTRIBUTOR = "Top Contributor"

# Points for each action type
ACTION_POINTS = {
    ActionType.ATTEND_EVENT: 10,
    ActionType.VOLUNTEER_TASK: 20,
    ActionType.LEAD_EVENT: 50,
    ActionType.UPLOAD_DOCS: 15,
    ActionType.BRING_SPONSORSHIP: 100
}

class ContributionBase(BaseModel):
    """Base model for contributions"""
    action: ActionType
    points: int = Field(..., ge=0)
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class MemberBase(BaseModel):
    """Base model for members"""
    name: str
    email: Optional[str] = None
    points: int = 0
    level: str = "Bronze"
    badges: list[str] = []
    contributions: list[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None

# Export all
__all__ = [
    "ActionType",
    "BadgeType",
    "ACTION_POINTS",
    "ContributionBase",
    "MemberBase"
]

