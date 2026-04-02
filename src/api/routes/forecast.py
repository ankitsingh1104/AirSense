import logging
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from src.api.services.cache import cache
from src.api.db import get_history
from src.api.forecasting import get_forecast

router = APIRouter()
logger = logging.getLogger(__name__)


class ForecastPoint(BaseModel):
    timestamp: str
    date_label: str
    predicted_aqi: float
    upper_bound: float
    lower_bound: float


class ForecastResponse(BaseModel):
    country_code: str
    forecast: List[ForecastPoint]
    model_used: str
    days_ahead: int
    trend: str
    fetched_at: str
    error: Optional[str] = None


@router.get("/forecast/{country_code}", response_model=ForecastResponse)
async def get_country_forecast(
    country_code: str,
    days: int = 14,
    refresh: bool = False,
) -> ForecastResponse:
    """
    Get 7-14 day AQI forecast for a country
    
    Query Parameters:
        - days: Number of days to forecast (default 14, max 30)
    
    Returns:
        ForecastResponse with forecast points, confidence intervals, model used
    """
    country_code = country_code.upper()
    days = min(max(days, 7), 30)  # Clamp between 7-30
    
    cache_key = f"forecast:v2:{country_code}:{days}"
    if not refresh:
        cached = await cache.get(cache_key)
        if cached:
            values = [item.get("predicted_aqi") for item in cached.get("forecast", [])]
            if len(set(values)) <= 2:
                await cache.delete(cache_key)
            else:
                logger.info("Forecast cache hit for %s", country_code)
                return ForecastResponse(**cached)
    
    try:
        # Get historical data
        history = await get_history(country_code, days=60)  # Get 60 days of history for training
        
        if not history or len(history) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for {country_code}"
            )
        
        # Convert to DataFrame
        df = pd.DataFrame(history)
        
        forecast_result = await run_in_threadpool(
            get_forecast,
            df,
            days,
            country_code,
        )
        
        if forecast_result.get("error") and not forecast_result.get("forecast"):
            raise HTTPException(
                status_code=500,
                detail=f"Forecast generation failed: {forecast_result.get('error')}"
            )
        
        # Format response
        forecast_points = [
            ForecastPoint(**point) for point in forecast_result.get("forecast", [])
        ]
        
        response = ForecastResponse(
            country_code=country_code,
            forecast=forecast_points,
            model_used=forecast_result.get("model", "unknown"),
            days_ahead=len(forecast_points),
            trend=forecast_result.get("trend", "stable"),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            error=forecast_result.get("error")
        )
        
        # Cache for 1 hour (recomputation is expensive)
        await cache.set(cache_key, response.model_dump(), ttl=3600)
        
        logger.info(
            "Forecast generated for %s: %s points using %s",
            country_code,
            len(forecast_points),
            forecast_result.get("model"),
        )
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast error for {country_code}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")


@router.delete("/forecast/cache/all")
async def clear_forecast_cache_all():
    deleted_count = await cache.delete_pattern("forecast:*")
    return {"status": "ok", "deleted": deleted_count}
