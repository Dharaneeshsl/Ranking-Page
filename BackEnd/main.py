from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ValidationError
from datetime import datetime
from typing import List
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Club Ranking API", description="API for managing club member rankings and contributions.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
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
    if points >= 300: return "Platinum Member 🏆"
    elif points >= 151: return "Gold Member ⭐"
    elif points >= 51: return "Silver Member 🥈"
    else: return "Bronze Member 🥉"

class Contribution(BaseModel):
    action: str
    points: int
    date: str

class Member(BaseModel):
    name: str
    points: int = 0
    contributions: List[Contribution] = []

class AddPointsRequest(BaseModel):
    name: str
    action: str
    date: str = datetime.now().strftime("%Y-%m-%d")

class ConnectionManager:
    def __init__(self): self.active_connections = []
    async def connect(self, websocket): await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket): self.active_connections.remove(websocket)
    async def broadcast(self, message): 
        for connection in self.active_connections: 
            await connection.send_json(message)

manager = ConnectionManager()

@app.post("/add_points")
async def add_points(req: AddPointsRequest):
    try:
        if req.action not in POINTS_MAP:
            logger.error(f"Invalid action attempted: {req.action}")
            return {"error": "Invalid action"}
        if not req.name.strip():
            logger.error("Empty member name attempted")
            return {"error": "Member name is required"}
        
        points = POINTS_MAP[req.action]
        member = await members_collection.find_one({"name": req.name.strip()})
        
        if not member:
            new_member = Member(name=req.name.strip(), points=points, contributions=[Contribution(action=req.action, points=points, date=req.date)])
            await members_collection.insert_one(new_member.dict())
            logger.info(f"New member added: {req.name} with {points} points")
        else:
            updated_contributions = member["contributions"] + [Contribution(action=req.action, points=points, date=req.date).dict()]
            updated_points = member["points"] + points
            await members_collection.update_one(
                {"name": req.name.strip()},
                {"$set": {"points": updated_points, "contributions": updated_contributions}}
            )
            logger.info(f"Points updated for {req.name}: +{points}")
        
        await manager.broadcast({"type": "update_leaderboard"})
        return {"message": "Points added successfully"}
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return {"error": f"Server error: {str(e)}"}

@app.get("/leaderboard")
async def get_leaderboard(start_date: str = "2025-01-01", end_date: str = "2025-12-31"):
    try:
        cursor = members_collection.find()
        members_list = await cursor.to_list(length=None)
        
        leaderboard = []
        for m in members_list:
            period_points = sum(c["points"] for c in m["contributions"] if start_date <= c["date"] <= end_date)
            total_points = m["points"]
            leaderboard.append({
                "name": m["name"],
                "period_points": period_points,
                "total_points": total_points,
                "badge": get_badge(total_points)
            })
        
        leaderboard.sort(key=lambda x: x["period_points"], reverse=True)
        logger.info(f"Leaderboard fetched for period {start_date} to {end_date}")
        return leaderboard
    except Exception as e:
        logger.error(f"Failed to fetch leaderboard: {str(e)}")
        return {"error": f"Failed to fetch leaderboard: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed")