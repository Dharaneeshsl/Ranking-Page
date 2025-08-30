from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gamified Ranking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.club_db
members_collection = db.members

# Create indexes
async def create_indexes():
    await members_collection.create_index([("points", -1)])  # For leaderboard/ranking
    await members_collection.create_index([("email", 1)], unique=True, sparse=True)
    await members_collection.create_index([("name", 1), ("email", 1)], unique=True, sparse=True)

# Run on startup
@app.on_event("startup")
async def startup_db_client():
    await create_indexes()

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
    BadgeType.TOP_CONTRIBUTOR: 500,
    BadgeType.EVENT_ORGANIZER: 5,   
    BadgeType.SPONSORSHIP_CHAMPION: 3
}

def compute_level(points: int) -> str:
    """Calculate member level based on points"""
    if points >= BADGE_THRESHOLDS[BadgeType.PLATINUM]:
        return BadgeType.PLATINUM.value
    if points >= BADGE_THRESHOLDS[BadgeType.GOLD]:
        return BadgeType.GOLD.value
    if points >= BADGE_THRESHOLDS[BadgeType.SILVER]:
        return BadgeType.SILVER.value
    return BadgeType.BRONZE.value

def get_badges(points: int, contributions: List[Dict[str, Any]]) -> List[str]:
    """Calculate badges based on points and contributions"""
    badges = [compute_level(points)]  # Level badge based on points
    
    # Add special badges based on contributions
    if contributions:
        event_lead_count = sum(1 for c in contributions if c.get("action") == ActionType.LEAD_EVENT)
        sponsorship_count = sum(1 for c in contributions if c.get("action") == ActionType.BRING_SPONSORSHIP)
        
        if event_lead_count >= BADGE_THRESHOLDS[BadgeType.EVENT_ORGANIZER]:
            badges.append(BadgeType.EVENT_ORGANIZER.value)
        if sponsorship_count >= BADGE_THRESHOLDS[BadgeType.SPONSORSHIP_CHAMPION]:
            badges.append(BadgeType.SPONSORSHIP_CHAMPION.value)
    
    # Ensure unique badges while preserving order
    seen = set()
    return [badge for badge in badges if not (badge in seen or seen.add(badge))]

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

# Removed MemberCreate and MemberUpdate to prevent member manipulation

class MemberResponse(MemberBase):
    id: str
    rank: Optional[int] = None
    next_level_points: Optional[int] = None
    progress: Optional[float] = None
    
    class Config(MemberBase.Config):
        from_attributes = True
        json_encoders = {
            **MemberBase.Config.json_encoders,
            "_id": str,  # Ensure ObjectId is converted to string in response
            ObjectId: str  # For direct ObjectId serialization
        }

@app.post("/api/members/", response_model=MemberResponse)
async def create_member(member: MemberCreate):
    """
    Create a new member with the given details
    """
    try:
        member_data = member.dict()
        member_data["join_date"] = datetime.utcnow()
        member_data["last_active"] = datetime.utcnow()
        member_data["contributions"] = []
        member_data["level"] = BadgeType.BRONZE.value
        member_data["badges"] = [BadgeType.BRONZE.value]
        
        result = await members_collection.insert_one(member_data)
        created_member = await members_collection.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string for JSON serialization
        created_member["id"] = str(created_member["_id"])
        del created_member["_id"]
        
        return created_member
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating member: {str(e)}"
        )

async def get_member_rank(points: int):
    """Get member's current rank based on points"""
    try:
        # Count how many members have more points than the given points
        count = await members_collection.count_documents({"points": {"$gt": points}})
        return count + 1  # Rank is count + 1 (1-based)
    except Exception as e:
        logger.error(f"Error getting member rank: {str(e)}")
        return 1

def calculate_next_level_points(current_level: str) -> int:
    """Calculate points needed for next level"""
    level_map = {
        BadgeType.BRONZE: BADGE_THRESHOLDS[BadgeType.SILVER],
        BadgeType.SILVER: BADGE_THRESHOLDS[BadgeType.GOLD],
        BadgeType.GOLD: BADGE_THRESHOLDS[BadgeType.PLATINUM],
        BadgeType.PLATINUM: None
    }
    return level_map.get(BadgeType(current_level), None)

@app.get("/api/leaderboard")
async def get_leaderboard(
    time_frame: str = "all", 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """
    Get leaderboard with optional time-based filtering
    
    Args:
        time_frame: One of 'all', 'week', 'month', 'year', or 'custom'
        start_date: Required if time_frame is 'custom', format: YYYY-MM-DD
        end_date: Required if time_frame is 'custom', format: YYYY-MM-DD
        limit: Maximum number of members to return (default: 100)
    """
    try:
        # Set date range based on time_frame
        now = datetime.utcnow()
        date_filter = {}
        
        if time_frame == "week":
            start = now - timedelta(weeks=1)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "month":
            start = now - timedelta(days=30)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "year":
            start = now - timedelta(days=365)
            date_filter = {"contributions.timestamp": {"$gte": start}}
        elif time_frame == "custom":
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Both start_date and end_date are required for custom time frame"
                )
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include full end day
                date_filter = {"contributions.timestamp": {"$gte": start, "$lte": end}}
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        # Get all members
        members = []
        async for member in members_collection.find():
            # Filter contributions by date if needed
            contributions = member.get("contributions", [])
            if date_filter:
                start = date_filter["contributions.timestamp"].get("$gte", datetime.min)
                end = date_filter["contributions.timestamp"].get("$lte", datetime.max)
                contributions = [
                    c for c in contributions 
                    if start <= c.get("timestamp", datetime.min) <= end
                ]
            
            # Calculate total points for the filtered contributions
            points = sum(c.get("points", 0) for c in contributions)
            
            # Only include members with points in the selected time frame
            if points > 0:
                members.append({
                    "id": str(member["_id"]),
                    "name": member["name"],
                    "points": points,
                    "level": compute_level(points),  # Recompute level based on filtered points
                    "badges": get_badges(points, contributions)  # Recompute badges based on filtered contributions
                })
        
        # Sort by points descending and limit results
        members.sort(key=lambda x: x["points"], reverse=True)
        
        # Calculate top 5% for Top Contributor badge
        if members:
            total_points = sum(m["points"] for m in members)
            if total_points > 0:
                top_5_percent_index = max(1, len(members) // 20)  # Top 5% or at least 1
                top_5_percent_points = members[top_5_percent_index - 1]["points"]
                
                # Update badges for top contributors
                for member in members:
                    if member["points"] >= top_5_percent_points and \
                       BadgeType.TOP_CONTRIBUTOR.value not in member["badges"]:
                        member["badges"].append(BadgeType.TOP_CONTRIBUTOR.value)
                    elif member["points"] < top_5_percent_points and \
                         BadgeType.TOP_CONTRIBUTOR.value in member["badges"]:
                        member["badges"].remove(BadgeType.TOP_CONTRIBUTOR.value)
        
        # Limit results after all processing
        members = members[:limit]
        
        # Calculate ranks
        for i, member in enumerate(members, 1):
            member["rank"] = i
        
        return {
            "status": "success",
            "data": {
                "leaderboard": members,
                "time_frame": time_frame,
                "start_date": start_date if time_frame == "custom" else None,
                "end_date": end_date if time_frame == "custom" else None,
                "total_members": len(members)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting leaderboard: {str(e)}"
        )

@app.get("/api/members/{member_id}")
async def get_member_profile(member_id: str):
    """
    Get detailed profile and contribution history for a member
    
    Returns:
        A dictionary containing member details, statistics, and recent contributions
    """
    try:
        # Get member data
        member = await members_collection.find_one({"_id": ObjectId(member_id)})
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
            
        # Get member's rank
        rank = await get_member_rank(member["points"])
        
        # Calculate points needed for next level
        next_level_points = calculate_next_level_points(member["level"])
        progress = 0
        if next_level_points > 0:
            progress = min(100, int((member["points"] / next_level_points) * 100))
        
        # Calculate contribution statistics
        contributions = member.get("contributions", [])
        contributions_by_type = {
            action_type.value: {"count": 0, "total_points": 0}
            for action_type in ActionType
        }
        
        for contrib in contributions:
            action = contrib.get("action")
            # Handle both string and enum action types
            action_str = action.value if isinstance(action, ActionType) else action
            if action_str in contributions_by_type:
                contributions_by_type[action_str]["count"] += 1
                contributions_by_type[action_str]["total_points"] += contrib.get("points", 0)
        
        # Filter out action types with zero contributions
        contributions_by_type = {
            k: v for k, v in contributions_by_type.items() 
            if v["count"] > 0
        }
        
        # Get recent contributions (last 10)
        recent_contributions = sorted(
            contributions,
            key=lambda x: x.get("timestamp", datetime.min),
            reverse=True
        )[:10]
        
        # Convert ObjectId to string for JSON serialization
        for contrib in recent_contributions:
            if "_id" in contrib:
                contrib["id"] = str(contrib.pop("_id"))
        
        return {
            "status": "success",
            "data": {
                "id": str(member["_id"]),
                "name": member["name"],
                "email": member.get("email"),
                "points": member["points"],
                "level": member["level"],
                "badges": member.get("badges", []),
                "rank": rank,
                "next_level_points": next_level_points,
                "progress": progress,
                "join_date": member.get("join_date", datetime.utcnow()),
                "last_active": member.get("last_active", datetime.utcnow()),
                "total_contributions": len(contributions),
                "contributions_by_type": contributions_by_type,
                "recent_contributions": recent_contributions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting member profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting member profile: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)