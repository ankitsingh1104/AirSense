import os
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import predict, realtime, history, websocket, forecast, simulate, snapshot
from src.api.services.cache import cache
from src.api.db import init_db
from src.api.services.scheduler import init_scheduler, scheduler
from src.inference import load_models, _state

# Config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Global Air Pollution API",
    description="Real-time AQI tracking and ensemble ML predictions.",
    version="2.0.0"
)

# Shared CORS from frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup & Shutdown Events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up AQI API...")
    
    # 1. Load ML Models once into app state
    await load_models()
    app.state.rf_reg = _state.get("rf_reg")
    app.state.rf_clf = _state.get("rf_clf")
    app.state.xgb_reg = _state.get("xgb_reg")
    app.state.xgb_clf = _state.get("xgb_clf")
    app.state.scaler = _state.get("scaler")
    app.state.feature_names = _state.get("feature_names")
    logger.info("ML Models and Scalers synced to app state.")

    # 2. Initialize Database (SQLite)
    await init_db()
    
    # 3. Connect to Cache (Redis)
    await cache.connect()
    app.state.redis = cache.redis

    # 4. Start Scheduler (includes immediate startup refresh job)
    init_scheduler(app)
    logger.info("Background scheduler initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await cache.disconnect()

# Include Routers
app.include_router(predict.router, prefix="/api", tags=["prediction"])
app.include_router(realtime.router, prefix="/api", tags=["realtime"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(forecast.router, prefix="/api", tags=["forecast"])
app.include_router(simulate.router, prefix="/api", tags=["simulation"])
app.include_router(snapshot.router, prefix="/api", tags=["snapshot"])
app.include_router(websocket.router, tags=["websocket"])

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_loaded": hasattr(app.state, "rf_reg"),
        "cache": "connected" if cache.redis else "fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
