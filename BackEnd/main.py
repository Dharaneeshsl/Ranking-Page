from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
import logging

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

POINTS_MAP = {
    "attend_event": 10,
    "volunteer_task": 20,
    "lead_event": 50,
    "upload_docs": 15,
    "bring_sponsorship": 100
}

def get_badge(points: int) -> str:
    if points >= 300: return "Platinum Member"
    elif points >= 151: return "Gold Member"
    elif points >= 51: return "Silver Member"
    else: return "Bronze Member"

class Contribution(BaseModel):
    action: str
    points: int
    date: str

class Member(BaseModel):
    name: str
    points: int = 0
    contributions: list = []

class AddPointsRequest(BaseModel):
    name: str
    action: str
    date: str = datetime.now().strftime("%Y-%m-%d")

@app.post("/add_points")
async def add_points(req: AddPointsRequest):
    try:
        if req.action not in POINTS_MAP or not req.name.strip():
            return {"status": "error", "message": "Invalid input"}
        
        points = POINTS_MAP[req.action]
        member = await members_collection.find_one({"name": req.name.strip()})
        
        if not member:
            new_member = {"name": req.name.strip(), "points": points, "contributions": [{"action": req.action, "points": points, "date": req.date}]}
            await members_collection.insert_one(new_member)
        else:
            updated_contributions = member["contributions"] + [{"action": req.action, "points": points, "date": req.date}]
            updated_points = member["points"] + points
            await members_collection.update_one({"name": req.name.strip()}, {"$set": {"points": updated_points, "contributions": updated_contributions}})
        
        return {"status": "success", "message": "Points added"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"status": "error", "message": "Server issue"}

@app.get("/leaderboard")
async def get_leaderboard(start_date: str = "2025-01-01", end_date: str = "2025-12-31"):
    try:
        members = await members_collection.find().to_list(length=None)
        leaderboard = [
            {
                "name": m["name"],
                "period_points": sum(c["points"] for c in m["contributions"] if start_date <= c["date"] <= end_date),
                "total_points": m["points"],
                "badge": get_badge(m["points"])
            }
            for m in members if m.get("contributions")
        ]
        leaderboard.sort(key=lambda x: x.get("period_points", 0), reverse=True)
        return {"status": "success", "data": leaderboard}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"status": "error", "data": [], "message": "Fetch failed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5173, reload=True)