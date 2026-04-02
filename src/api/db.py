import os
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default database path
DB_PATH = os.getenv("DB_PATH", "./data/aqi_history.db")

async def init_db():
    """Initializes the SQLite database and creates the necessary tables."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS aqi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT NOT NULL,
                country_name TEXT,
                city TEXT,
                timestamp TEXT NOT NULL,
                aqi_value REAL,
                aqi_category TEXT,
                co_aqi REAL,
                ozone_aqi REAL,
                no2_aqi REAL,
                pm25_aqi REAL,
                predicted_aqi REAL,
                dominant_pollutant TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_country_time 
            ON aqi_history(country_code, timestamp)
        """)
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)

async def log_aqi_reading(data: Dict[str, Any]):
    """Logs a single AQI reading to history."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO aqi_history (
                country_code, country_name, city, timestamp, aqi_value,
                aqi_category, co_aqi, ozone_aqi, no2_aqi, pm25_aqi,
                predicted_aqi, dominant_pollutant
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("country_code"),
            data.get("country_name"),
            data.get("city"),
            data.get("timestamp", datetime.now().isoformat()),
            data.get("aqi_value"),
            data.get("aqi_category"),
            data.get("co_aqi"),
            data.get("ozone_aqi"),
            data.get("no2_aqi"),
            data.get("pm2.5_aqi"),
            data.get("predicted_aqi"),
            data.get("dominant_pollutant")
        ))
        await db.commit()

async def get_history(country_code: str, days: int = 7) -> List[Dict[str, Any]]:
    """Retrieves aqi history for a country over N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM aqi_history 
            WHERE country_code = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (country_code, cutoff)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
