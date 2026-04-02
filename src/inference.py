"""
Inference API Module
====================
FastAPI application with two prediction endpoints and a health check.

Endpoints
---------
- ``POST /predict/regression``  → RF & XGB AQI value predictions + ensemble
- ``POST /predict/classification`` → RF & XGB AQI category predictions + confidence
- ``GET  /health``              → Service health check

Models and scaler are loaded once at startup.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from scipy.stats import skew, kurtosis
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CONFIG = {
    "models_dir": Path(__file__).resolve().parent.parent / "models",
    "aqi_category_map_inv": {
        0: "Good",
        1: "Moderate",
        2: "Unhealthy for Sensitive Groups",
        3: "Unhealthy",
        4: "Very Unhealthy",
        5: "Hazardous",
    },
    "pollutant_cols": [
        "co_aqi_value",
        "ozone_aqi_value",
        "no2_aqi_value",
        "pm2.5_aqi_value",
    ],
}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PYDANTIC MODELS
# ---------------------------------------------------------------------------

class PredictionInput(BaseModel):
    """Input schema for prediction endpoints."""
    co_aqi_value: float = Field(..., description="CO AQI value")
    ozone_aqi_value: float = Field(..., description="Ozone AQI value")
    no2_aqi_value: float = Field(..., description="NO₂ AQI value")
    pm2_5_aqi_value: float = Field(..., alias="pm2.5_aqi_value", description="PM2.5 AQI value")
    country_name: str = Field(..., description="Country name for geo-clustering")

    class Config:
        populate_by_name = True


class RegressionResponse(BaseModel):
    """Response schema for regression endpoint."""
    rf_prediction: float
    xgb_prediction: float
    ensemble_average: float


class ClassificationResponse(BaseModel):
    """Response schema for classification endpoint."""
    rf_category: str
    xgb_category: str
    rf_confidence: float
    xgb_confidence: float


class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    models_loaded: bool


# ---------------------------------------------------------------------------
# APP STATE (populated at startup)
# ---------------------------------------------------------------------------
_state: dict = {}


# ---------------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Air Pollution AQI Prediction API",
    description="Predict AQI values and categories using RF + XGBoost ensemble.",
    version="1.0.0",
)


@app.on_event("startup")
async def load_models():
    """Load all models and the scaler once at startup."""
    models_dir = CONFIG["models_dir"]
    try:
        _state["rf_reg"] = joblib.load(models_dir / "rf_regressor.joblib")
        _state["rf_clf"] = joblib.load(models_dir / "rf_classifier.joblib")

        xgb_reg = XGBRegressor()
        xgb_reg.load_model(str(models_dir / "xgb_regressor.json"))
        _state["xgb_reg"] = xgb_reg

        xgb_clf = XGBClassifier()
        xgb_clf.load_model(str(models_dir / "xgb_classifier.json"))
        _state["xgb_clf"] = xgb_clf

        _state["scaler"] = joblib.load(models_dir / "scaler.joblib")
        _state["feature_names"] = joblib.load(models_dir / "feature_names.joblib")
        _state["models_loaded"] = True
        logger.info("All models loaded successfully.")
    except Exception as exc:
        logger.error("Failed to load models: %s", exc)
        _state["models_loaded"] = False


# ---------------------------------------------------------------------------
# FEATURE ENGINEERING FOR SINGLE SAMPLE
# ---------------------------------------------------------------------------
# Import the static country-coords lookup from the feature_engineering module
from src.feature_engineering import _COUNTRY_COORDS  # noqa: E402


def _build_features(inp: PredictionInput) -> np.ndarray:
    """
    Apply the same feature-engineering pipeline used during training
    to a single input sample.

    Parameters
    ----------
    inp : PredictionInput
        Validated user input.

    Returns
    -------
    np.ndarray
        1-D scaled feature vector matching training feature order.
    """
    pcols = CONFIG["pollutant_cols"]
    vals = [inp.co_aqi_value, inp.ozone_aqi_value, inp.no2_aqi_value, inp.pm2_5_aqi_value]

    features: dict = {}

    # Raw pollutant values
    for col, v in zip(pcols, vals):
        features[col] = v

    # A — Pollutant std
    features["pollutant_std"] = float(np.std(vals, ddof=1))

    # B — Dominance ratio
    p_max = max(vals)
    features["pollutant_max"] = p_max
    features["dominance_ratio"] = p_max / (sum(vals) + 1e-6)

    # Dominant pollutant (label-encoded: co=0, no2=1, ozone=2, pm2.5=3 — approx)
    names = ["co", "ozone", "no2", "pm2.5"]
    dominant_idx = int(np.argmax(vals))
    # Simple label encoding (same order used in training LabelEncoder)
    dominant_name = names[dominant_idx]
    le_map = {"co": 0, "no2": 1, "ozone": 2, "pm2.5": 3}
    features["dominant_pollutant"] = le_map.get(dominant_name, 0)

    # C — Interactions
    features["co_no2_interaction"] = inp.co_aqi_value * inp.no2_aqi_value
    features["pm_ozone_interaction"] = inp.pm2_5_aqi_value * inp.ozone_aqi_value

    # D — Skew & kurtosis
    features["pollutant_skew"] = float(skew(vals))
    features["pollutant_kurtosis"] = float(kurtosis(vals))

    # E — Geo cluster (load persisted KMeans to get correct cluster)
    try:
        kmeans = joblib.load(
            Path(__file__).resolve().parent.parent / "models" / "geo_kmeans.joblib"
        )
        coords = _COUNTRY_COORDS.get(inp.country_name)
        if coords:
            geo_cluster = int(kmeans.predict([[coords[0], coords[1]]])[0])
        else:
            geo_cluster = 0
    except Exception:
        # Fallback: use known cluster assignments for major countries
        KNOWN_CLUSTERS = {
            "India": 3, "China": 2, "Pakistan": 3, "Bangladesh": 3,
            "Nepal": 3, "Vietnam": 2, "Thailand": 2, "Indonesia": 2,
            "United States": 1, "Canada": 1, "Mexico": 1,
            "Brazil": 3, "Argentina": 3, "Colombia": 1, "Peru": 3,
            "Germany": 0, "France": 0, "United Kingdom": 0, "Italy": 0,
            "Russia": 0, "Poland": 0, "Spain": 0, "Netherlands": 0,
            "Nigeria": 5, "Egypt": 5, "South Africa": 4, "Kenya": 4,
            "Saudi Arabia": 3, "Iran": 3, "Iraq": 3, "Turkey": 0,
            "Japan": 2, "South Korea": 2, "Australia": 4,
        }
        geo_cluster = KNOWN_CLUSTERS.get(inp.country_name, 0)

    # One-hot encode matching EXACT training column names (drop_first=True drops cluster 0)
    # Training used: geo_cluster_0 dropped, geo_cluster_1 through geo_cluster_5 kept
    for i in range(0, 6):
        col_name = f"geo_cluster_{i}"
        features[col_name] = 1 if geo_cluster == i else 0

    # Ensure feature order matches training
    feature_names = _state.get("feature_names", [])
    row = []
    for fn in feature_names:
        row.append(features.get(fn, 0.0))

    scaler = _state["scaler"]
    scaled = scaler.transform([row])
    return scaled


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/predict/regression", response_model=RegressionResponse)
async def predict_regression(inp: PredictionInput):
    """
    Predict continuous AQI value using RF and XGBoost regressors.

    Returns RF prediction, XGB prediction, and their average.
    """
    if not _state.get("models_loaded"):
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        X = _build_features(inp)
        rf_pred = float(_state["rf_reg"].predict(X)[0])
        xgb_pred = float(_state["xgb_reg"].predict(X)[0])
        return RegressionResponse(
            rf_prediction=round(rf_pred, 2),
            xgb_prediction=round(xgb_pred, 2),
            ensemble_average=round((rf_pred + xgb_pred) / 2, 2),
        )
    except Exception as exc:
        logger.error("Regression prediction error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/predict/classification", response_model=ClassificationResponse)
async def predict_classification(inp: PredictionInput):
    """
    Predict AQI category using RF and XGBoost classifiers.

    Returns predicted categories and confidence scores.
    """
    if not _state.get("models_loaded"):
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        X = _build_features(inp)
        cat_map = CONFIG["aqi_category_map_inv"]

        rf_pred = int(_state["rf_clf"].predict(X)[0])
        rf_proba = _state["rf_clf"].predict_proba(X)[0]
        rf_conf = float(np.max(rf_proba))

        xgb_pred = int(_state["xgb_clf"].predict(X)[0])
        xgb_proba = _state["xgb_clf"].predict_proba(X)[0]
        xgb_conf = float(np.max(xgb_proba))

        return ClassificationResponse(
            rf_category=cat_map.get(rf_pred, "Unknown"),
            xgb_category=cat_map.get(xgb_pred, "Unknown"),
            rf_confidence=round(rf_conf, 4),
            xgb_confidence=round(xgb_conf, 4),
        )
    except Exception as exc:
        logger.error("Classification prediction error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health", response_model=HealthResponse)
async def health():
    """Service health check."""
    return HealthResponse(
        status="ok",
        models_loaded=_state.get("models_loaded", False),
    )
