from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class ActionType(str, Enum):
    ATTEND_EVENT = "attend_event"
    VOLUNTEER_TASK = "volunteer_task"
    LEAD_EVENT = "lead_event"
    UPLOAD_DOCS = "upload_docs"
    BRING_SPONSORSHIP = "bring_sponsorship"

class BadgeType(str, Enum):
    BRONZE = "Bronze Member"
    SILVER = "Silver Member"
    GOLD = "Gold Member"
    PLATINUM = "Platinum Member"
    TOP_CONTRIBUTOR = "Top Contributor"
    EVENT_ORGANIZER = "Event Organizer"
    SPONSORSHIP_CHAMPION = "Sponsorship Champion"

class ContributionBase(BaseModel):
    action: ActionType
    points: int
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    description: Optional[str] = None
    event_name: Optional[str] = None

class MemberBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    points: int = 0
    level: str = BadgeType.BRONZE.value
    join_date: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    contributions: List[Dict[str, Any]] = []
    badges: List[str] = Field(default_factory=lambda: [BadgeType.BRONZE.value])

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }

class MemberResponse(MemberBase):
    id: str
    rank: Optional[int] = None
    next_level_points: Optional[int] = None
    progress: Optional[float] = None

    class Config(MemberBase.Config):
        from_attributes = True
        json_encoders = {
            **MemberBase.Config.json_encoders,
            "_id": str,
            ObjectId: str
        }
