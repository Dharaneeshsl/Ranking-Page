from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import startup_db_client
from routes import leaderboard, members

app = FastAPI(title="Gamified Ranking API")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB
@app.on_event("startup")
async def startup_event():
    await startup_db_client()

# Register routers
app.include_router(leaderboard.router, prefix="/api")
app.include_router(members.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
