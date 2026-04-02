import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.inference import PredictionInput, _build_features

router = APIRouter()
logger = logging.getLogger(__name__)


class SimulateRequest(BaseModel):
    country_name: str = Field(..., description="Country name used in feature engineering")
    pollutant_values: Dict[str, float] = Field(
        ..., description="Current pollutant values, keys: pm2.5/no2/co/ozone"
    )
    modification_map: Dict[str, float] = Field(
        default_factory=dict,
        description="Percent deltas per pollutant, e.g. {'pm2.5': -0.2}",
    )


class SimulateResponse(BaseModel):
    simulated_aqi: float
    rf_prediction: float
    xgb_prediction: float
    delta_from_live: float
    adjusted_pollutants: Dict[str, float]


def _normalize_key(key: str) -> str:
    k = key.lower().strip()
    if k in {"pm2.5", "pm25", "pm_2_5"}:
        return "pm2.5"
    if k in {"o3", "ozone"}:
        return "ozone"
    if k in {"no2", "no_2"}:
        return "no2"
    if k in {"co"}:
        return "co"
    return k


def _clip_aqi(val: float) -> float:
    return max(0.0, min(500.0, float(val)))


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_aqi(req: SimulateRequest, request: Request) -> SimulateResponse:
    app_state = request.app.state
    if not hasattr(app_state, "rf_reg"):
        raise HTTPException(status_code=503, detail="Models not loaded")

    base = {
        "pm2.5": 0.0,
        "no2": 0.0,
        "co": 0.0,
        "ozone": 0.0,
    }

    for k, v in req.pollutant_values.items():
        nk = _normalize_key(k)
        if nk in base:
            base[nk] = _clip_aqi(v)

    adjusted = dict(base)
    for k, delta in req.modification_map.items():
        nk = _normalize_key(k)
        if nk in adjusted:
            adjusted[nk] = _clip_aqi(adjusted[nk] * (1.0 + float(delta)))

    try:
        inp = PredictionInput(
            country_name=req.country_name,
            co_aqi_value=adjusted["co"],
            ozone_aqi_value=adjusted["ozone"],
            no2_aqi_value=adjusted["no2"],
            **{"pm2.5_aqi_value": adjusted["pm2.5"]},
        )

        X = _build_features(inp)
        rf_pred = float(app_state.rf_reg.predict(X)[0])
        xgb_pred = float(app_state.xgb_reg.predict(X)[0])
        ensemble = (rf_pred + xgb_pred) / 2.0

        # Baseline for delta: ensemble prediction from current pollutant values.
        base_inp = PredictionInput(
            country_name=req.country_name,
            co_aqi_value=base["co"],
            ozone_aqi_value=base["ozone"],
            no2_aqi_value=base["no2"],
            **{"pm2.5_aqi_value": base["pm2.5"]},
        )
        base_X = _build_features(base_inp)
        base_rf = float(app_state.rf_reg.predict(base_X)[0])
        base_xgb = float(app_state.xgb_reg.predict(base_X)[0])
        baseline = (base_rf + base_xgb) / 2.0

        return SimulateResponse(
            simulated_aqi=round(ensemble, 1),
            rf_prediction=round(rf_pred, 2),
            xgb_prediction=round(xgb_pred, 2),
            delta_from_live=round(ensemble - baseline, 1),
            adjusted_pollutants={k: round(v, 2) for k, v in adjusted.items()},
        )
    except Exception as exc:
        logger.error("Simulation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")
