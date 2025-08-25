from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gamified Ranking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.club_db
members_collection = db.members

# Enums
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

# Points configuration
POINTS_MAP = {
    ActionType.ATTEND_EVENT: 10,
    ActionType.VOLUNTEER_TASK: 20,
    ActionType.LEAD_EVENT: 50,
    ActionType.UPLOAD_DOCS: 15,
    ActionType.BRING_SPONSORSHIP: 100
}

BADGE_THRESHOLDS = {
    BadgeType.BRONZE: 0,
    BadgeType.SILVER: 51,
    BadgeType.GOLD: 151,
    BadgeType.PLATINUM: 300,
    BadgeType.TOP_CONTRIBUTOR: 500,  # Top 5% of contributors
    BadgeType.EVENT_ORGANIZER: 5,    # Organized 5+ events
    BadgeType.SPONSORSHIP_CHAMPION: 3  # Brought 3+ sponsorships
}

def get_badges(points: int, contributions: List[Dict[str, Any]]) -> List[str]:
    """Calculate badges based on points and contributions"""
    badges = []
    
    # Level badges
    if points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        badges.append(BadgeType.PLATINUM.value)
    elif points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        badges.append(BadgeType.GOLD.value)
    elif points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        badges.append(BadgeType.SILVER.value)
    else:
        badges.append(BadgeType.BRONZE.value)
    
    # Special badges
    if contributions:
        event_lead_count = sum(1 for c in contributions if c.get("action") == ActionType.LEAD_EVENT)
        sponsorship_count = sum(1 for c in contributions if c.get("action") == ActionType.BRING_SPONSORSHIP)
        
        if event_lead_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
            badges.append(BadgeType.EVENT_ORGANIZER.value)
        if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
            badges.append(BadgeType.SPONSORSHIP_CHAMPION.value)
    
    return badges

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
    join_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    last_active: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    contributions: List[Dict[str, Any]] = []
    badges: List[str] = Field(default_factory=lambda: [BadgeType.BRONZE.value])

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class MemberResponse(MemberBase):
    id: str
    rank: Optional[int] = None
    next_level_points: Optional[int] = None
    progress: Optional[float] = None

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}

class AddPointsRequest(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    action: ActionType
    description: Optional[str] = None
    event_name: Optional[str] = None
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

async def get_member_rank(points: int) -> int:
    """Get member's current rank based on points"""
    count = await members_collection.count_documents({"points": {"$gt": points}})
    return count + 1

def calculate_next_level_points(current_level: str) -> int:
    """Calculate points needed for next level"""
    level_map = {
        BadgeType.BRONZE: BADGE_THRESHOLDS[BadgeType.SILVER],
        BadgeType.SILVER: BADGE_THRESHOLDS[BadgeType.GOLD],
        BadgeType.GOLD: BADGE_THRESHOLDS[BadgeType.PLATINUM],
        BadgeType.PLATINUM: None
    }
    return level_map.get(BadgeType(current_level), None)

@app.post("/api/points")
async def add_points(request: AddPointsRequest):
    """Add points for a member's contribution"""
    try:
        if not request.name.strip():
            raise HTTPException(status_code=400, detail="Name is required")
        
        points = POINTS_MAP[request.action]
        now = datetime.now().strftime("%Y-%m-%d")
        
        contribution = {
            "action": request.action,
            "points": points,
            "date": request.date or now,
            "description": request.description,
            "event_name": request.event_name
        }
        
        # Find or create member
        member_query = {"name": request.name.strip()}
        if request.email:
            member_query["email"] = request.email
            
        member = await members_collection.find_one(member_query)
        
        if member:
            # Update existing member
            updated_points = member.get("points", 0) + points
            updated_contributions = member.get("contributions", []) + [contribution]
            badges = get_badges(updated_points, updated_contributions)
            
            update_data = {
                "$set": {
                    "points": updated_points,
                    "contributions": updated_contributions,
                    "last_active": now,
                    "badges": badges,
                    "level": max(badges, key=lambda b: BADGE_THRESHOLDS.get(BadgeType(b), 0))
                }
            }
            
            if request.email and not member.get("email"):
                update_data["$set"]["email"] = request.email
            
            await members_collection.update_one(
                {"_id": member["_id"]},
                update_data
            )
            member_id = str(member["_id"])
        else:
            # Create new member
            new_member = {
                "name": request.name.strip(),
                "email": request.email,
                "points": points,
                "level": BadgeType.BRONZE.value,
                "join_date": now,
                "last_active": now,
                "contributions": [contribution],
                "badges": [BadgeType.BRONZE.value]
            }
            result = await members_collection.insert_one(new_member)
            member_id = str(result.inserted_id)
        
        return {
            "status": "success",
            "data": {
                "member_id": member_id,
                "points_added": points,
                "total_points": updated_points if 'updated_points' in locals() else points,
                "badges": badges if 'badges' in locals() else [BadgeType.BRONZE.value]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding points: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add points")

@app.get("/api/leaderboard")
async def get_leaderboard(
    time_frame: str = "all",  # all, week, month, year, custom
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get leaderboard with optional time-based filtering"""
    try:
        # Calculate date range based on time_frame
        now = datetime.now()
        date_filter = {}
        
        if time_frame == "week":
            start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            end = (now + timedelta(days=6-now.weekday())).strftime("%Y-%m-%d")
        elif time_frame == "month":
            start = now.replace(day=1).strftime("%Y-%m-%d")
            next_month = now.replace(day=28) + timedelta(days=4)
            end = (next_month - timedelta(days=next_month.day)).strftime("%Y-%m-%d")
        elif time_frame == "year":
            start = now.replace(month=1, day=1).strftime("%Y-%m-%d")
            end = now.replace(month=12, day=31).strftime("%Y-%m-%d")
        elif time_frame == "custom" and start_date and end_date:
            start, end = start_date, end_date
        else:  # all time
            start, end = "1970-01-01", "2100-12-31"
        
        # Get all members with their contributions
        members = await members_collection.find({}).sort("points", -1).limit(limit).to_list(length=None)
        
        leaderboard = []
        for i, member in enumerate(members, 1):
            # Filter contributions by date range
            contributions = member.get("contributions", [])
            filtered_contributions = [
                c for c in contributions 
                if start <= c.get("date", "") <= end
            ]
            
            period_points = sum(c["points"] for c in filtered_contributions)
            
            leaderboard.append({
                "rank": i,
                "member_id": str(member["_id"]),
                "name": member["name"],
                "email": member.get("email"),
                "period_points": period_points,
                "total_points": member.get("points", 0),
                "level": member.get("level", BadgeType.BRONZE.value),
                "badges": member.get("badges", [BadgeType.BRONZE.value]),
                "join_date": member.get("join_date", ""),
                "last_active": member.get("last_active", "")
            })
        
        # Sort by period points (descending)
        leaderboard.sort(key=lambda x: x["period_points"], reverse=True)
        
        # Update ranks based on sorted order
        for i, entry in enumerate(leaderboard, 1):
            entry["rank"] = i
        
        return {
            "status": "success",
            "data": {
                "leaderboard": leaderboard,
                "time_frame": {
                    "type": time_frame,
                    "start_date": start,
                    "end_date": end
                },
                "total_members": len(leaderboard)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")

@app.get("/api/members/{member_id}")
async def get_member_profile(member_id: str):
    """Get detailed profile and contribution history for a member"""
    try:
        # Validate member_id format
        try:
            member_oid = ObjectId(member_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid member ID format")
        
        # Find member
        member = await members_collection.find_one({"_id": member_oid})
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Get member rank
        rank = await get_member_rank(member.get("points", 0))
        
        # Calculate next level points
        current_level = member.get("level", BadgeType.BRONZE.value)
        next_level_points = calculate_next_level_points(current_level)
        
        # Calculate progress to next level
        progress = 0
        if next_level_points:
            current_points = member.get("points", 0)
            previous_level_points = BADGE_THRESHOLDS.get(BadgeType(current_level), 0)
            points_needed = next_level_points - previous_level_points
            points_earned = current_points - previous_level_points
            progress = min(100, int((points_earned / points_needed) * 100)) if points_needed > 0 else 100
        
        # Prepare response
        response = {
            "member_id": str(member["_id"]),
            "name": member["name"],
            "email": member.get("email"),
            "points": member.get("points", 0),
            "level": current_level,
            "rank": rank,
            "badges": member.get("badges", [BadgeType.BRONZE.value]),
            "join_date": member.get("join_date", ""),
            "last_active": member.get("last_active", ""),
            "next_level_points": next_level_points,
            "progress_to_next_level": progress,
            "total_contributions": len(member.get("contributions", [])),
            "contributions_by_type": {},
            "recent_contributions": []
        }
        
        # Calculate contributions by type
        contributions_by_type = {}
        for action in ActionType:
            contributions_by_type[action.value] = {
                "count": 0,
                "total_points": 0,
                "points_per_action": POINTS_MAP[action]
            }
        
        for contrib in member.get("contributions", []):
            action = contrib.get("action")
            if action in contributions_by_type:
                contributions_by_type[action]["count"] += 1
                contributions_by_type[action]["total_points"] += contrib.get("points", 0)
        
        response["contributions_by_type"] = contributions_by_type
        
        # Get recent contributions (last 10)
        recent_contributions = sorted(
            member.get("contributions", []),
            key=lambda x: x.get("date", ""),
            reverse=True
        )[:10]
        response["recent_contributions"] = recent_contributions
        
        return {"status": "success", "data": response}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching member profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch member profile")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)