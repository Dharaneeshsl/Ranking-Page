import os, logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from .database import init_db
from .routes import router as api_router
from .middleware.auth_middleware import APIError

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
DEBUG = os.getenv("ENV") != "production"
SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24).hex()
ORIGINS = [os.getenv("FRONTEND_URL", "http://localhost:5173")]

# App
app = FastAPI(docs_url="/api/docs" if DEBUG else None, redoc_url=None)

# Middleware
@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"})
    return response

app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="sid")

# Error handling
@app.exception_handler(APIError)
async def handle_error(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail.get("message", "Error"))})

# Startup
@app.on_event("startup")
async def start():
    try:
        await init_db()
        logger.info(f"✅ Server ready in {'dev' if DEBUG else 'prod'} mode")
    except Exception as e:
        logger.critical(f"❌ Startup failed: {e}")
        raise

# Routes
@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=DEBUG)
