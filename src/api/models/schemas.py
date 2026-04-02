from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PollutantInput(BaseModel):
    """Input directly from user or WAQI API."""
    co_aqi_value: float = Field(..., description="CO AQI value")
    ozone_aqi_value: float = Field(..., description="Ozone AQI value")
    no2_aqi_value: float = Field(..., description="NO2 AQI value")
    pm25_aqi_value: float = Field(..., alias="pm2.5_aqi_value", description="PM2.5 AQI value")
    country_name: str = Field(..., description="Full country name (e.g. 'India')")
    city_name: Optional[str] = Field("", description="City name (optional)")

    class Config:
        populate_by_name = True

class SHAPContribution(BaseModel):
    feature: str
    value: float
    contribution: float

class PredictionResponse(BaseModel):
    """Result of our ensemble model (RF + XGB)."""
    aqi_value: float
    aqi_category: str
    rf_prediction: float
    xgb_prediction: float
    ensemble_prediction: float
    shap_values: List[SHAPContribution]
    confidence: float

class PollutantDetail(BaseModel):
    aqi_value: float
    aqi_category: str

class RealtimeCountryResponse(BaseModel):
    """Merged response: Live WAQI data + ML Prediction."""
    country_code: str
    country_name: str
    city: str
    live_aqi: float
    predicted_aqi: float
    aqi_category: str
    pollutants: Dict[str, PollutantDetail]
    dominant_pollutant: str
    shap_values: List[SHAPContribution]
    rf_prediction: Optional[float] = None
    xgb_prediction: Optional[float] = None
    source: str = "waqi"
    fetched_at: datetime = Field(default_factory=datetime.now)

class GlobeSnapshotItem(BaseModel):
    """Summarized record for the 3D globe."""
    country_code: str
    country_name: str
    lat: float
    lon: float
    aqi_value: float
    aqi_category: str
    dominant_pollutant: str
    last_updated: datetime
