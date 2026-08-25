"""
Domain models for the ranking system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Types of contributions/actions."""

    ATTEND_EVENT = "attend_event"
    VOLUNTEER_TASK = "volunteer_task"
    LEAD_EVENT = "lead_event"
    UPLOAD_DOCS = "upload_docs"
    BRING_SPONSORSHIP = "bring_sponsorship"


class BadgeType(str, Enum):
    """Names of badges awarded to members."""

    BRONZE = "Bronze Member"
    SILVER = "Silver Member"
    GOLD = "Gold Member"
    PLATINUM = "Platinum Member"
    EVENT_ORGANIZER = "Event Organizer"
    SPONSORSHIP_CHAMPION = "Sponsorship Champion"
    TOP_CONTRIBUTOR = "Top Contributor"


# Points awarded per action (server-side only - clients can never set points).
ACTION_POINTS: dict[ActionType, int] = {
    ActionType.ATTEND_EVENT: 10,
    ActionType.VOLUNTEER_TASK: 20,
    ActionType.LEAD_EVENT: 50,
    ActionType.UPLOAD_DOCS: 15,
    ActionType.BRING_SPONSORSHIP: 100,
}

ACTION_LABELS: dict[str, str] = {
    "attend_event": "Attend Event",
    "volunteer_task": "Volunteer Task",
    "lead_event": "Lead Event",
    "upload_docs": "Upload Docs",
    "bring_sponsorship": "Bring Sponsorship",
    "manual_adjustment": "Manual Adjustment",
}


def action_label(action: str) -> str:
    return ACTION_LABELS.get(action, action.replace("_", " ").title())


class ContributionCreate(BaseModel):
    """A new contribution. Points are derived server-side."""

    action: ActionType
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class Contribution(BaseModel):
    """Stored contribution document."""

    action: str
    points: int = Field(..., ge=0)
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


class PointsRequest(BaseModel):
    """Add points by member name (creates the member if missing)."""

    name: str = Field(..., min_length=1, max_length=120)
    action: ActionType
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        return v

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class MemberCreate(BaseModel):
    """Create a member directly."""

    name: str = Field(..., min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=254)
    initial_points: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        return v

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        return v or None


class ManualPointsUpdate(BaseModel):
    """Admin override of a member's absolute total points."""

    points: int = Field(..., ge=0, le=1_000_000)
    reason: Optional[str] = Field(default=None, max_length=300)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


__all__ = [
    "ActionType",
    "BadgeType",
    "ACTION_POINTS",
    "ACTION_LABELS",
    "action_label",
    "Contribution",
    "ContributionCreate",
    "PointsRequest",
    "MemberCreate",
    "ManualPointsUpdate",
]
