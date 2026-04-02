import logging
import numpy as np
import shap
from fastapi import APIRouter, HTTPException, Request
from src.api.models.schemas import PollutantInput, PredictionResponse, SHAPContribution
from src.inference import _build_features

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize SHAP explainer (lazy-loaded)
_explainer = None

def get_explainer(model):
    global _explainer
    if _explainer is None:
        # Use TreeExplainer for Random Forest (fastest for trees)
        _explainer = shap.TreeExplainer(model)
    return _explainer

@router.post("/predict", response_model=PredictionResponse)
async def predict_aqi(inp: PollutantInput, request: Request):
    """
    Manual prediction endpoint using our ensemble (RF + XGB).
    Also returns SHAP feature contributions for the top 5 features.
    """
    app_state = request.app.state
    if not hasattr(app_state, "rf_reg"):
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        # 1. Feature Engineering
        X = _build_features(inp)
        
        # 2. Ensemble Predictions
        rf_pred = float(app_state.rf_reg.predict(X)[0])
        xgb_pred = float(app_state.xgb_reg.predict(X)[0])
        ensemble_pred = (rf_pred + xgb_pred) / 2.0
        
        # 3. Categorization (using RF Classifier)
        rf_clf_pred = int(app_state.rf_clf.predict(X)[0])
        cat_map = {0: "Good", 1: "Moderate", 2: "Unhealthy for Sensitive Groups", 
                   3: "Unhealthy", 4: "Very Unhealthy", 5: "Hazardous"}
        aqi_category = cat_map.get(rf_clf_pred, "Unknown")
        
        # 4. Confidence (std dev of reg predictions)
        # Lower std dev means models agree more -> higher confidence
        confidence = 1.0 / (1.0 + np.abs(rf_pred - xgb_pred))

        # 5. SHAP (Explainability)
        explainer = get_explainer(app_state.rf_reg)
        shap_values = explainer.shap_values(X)
        
        # Handle index for shap_values (multi-output vs single-output)
        if hasattr(shap_values, "__len__") and len(shap_values.shape) > 1:
            # For multi-class (clf) it's a list, for reg it's usually (N, features)
            sv = shap_values[0]
        else:
            sv = shap_values[0]

        feature_names = app_state.feature_names
        contributions = []
        for i, val in enumerate(sv):
            contributions.append(SHAPContribution(
                feature=feature_names[i],
                # Original unscaled value (approx from X input or just logic)
                value=float(X[0][i]), 
                contribution=float(val)
            ))
        
        # Sort by absolute contribution and take top 5
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        top_5_shap = contributions[:5]

        return PredictionResponse(
            aqi_value=round(ensemble_pred, 1),
            aqi_category=aqi_category,
            rf_prediction=round(rf_pred, 2),
            xgb_prediction=round(xgb_pred, 2),
            ensemble_prediction=round(ensemble_pred, 1),
            shap_values=top_5_shap,
            confidence=round(float(confidence), 3)
        )

    except Exception as e:
        logger.error("Prediction error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
