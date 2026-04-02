import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.api.db import get_history

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/history/{country_code}")
async def get_aqi_history(
    country_code: str,
    days: int = Query(7, ge=1, le=30)
):
    """Retrieves AQI time-series history for a country from our DB."""
    try:
        data = await get_history(country_code.upper(), days)
        if not data:
            # Fallback empty or 404
            return []
        
        # Clean data for response
        return data
    except Exception as e:
        logger.error("DB History query failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
