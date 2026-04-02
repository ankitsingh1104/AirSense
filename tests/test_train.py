"""
Tests for src/train.py
========================
Verifies that trained models are saved to disk and produce predictions
with correct shapes.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_and_split, CONFIG as DATA_CONFIG
from src.feature_engineering import prepare_features

MODELS_DIR = PROJECT_ROOT / "models"


@pytest.fixture(scope="module")
def prepared_data():
    """Load + engineer features for testing."""
    csv_path = DATA_CONFIG["data_dir"] / DATA_CONFIG["csv_filename"]
    if not csv_path.exists():
        pytest.skip("Dataset CSV not found — skipping train tests.")
    df_train, df_val, df_test = load_and_split()
    return prepare_features(df_train, df_val, df_test)


class TestModelFiles:
    """Verify model artefacts exist on disk (requires prior training run)."""

    def test_rf_regressor_exists(self):
        path = MODELS_DIR / "rf_regressor.joblib"
        if not path.exists():
            pytest.skip("Model not trained yet.")
        assert path.stat().st_size > 0

    def test_xgb_regressor_exists(self):
        path = MODELS_DIR / "xgb_regressor.json"
        if not path.exists():
            pytest.skip("Model not trained yet.")
        assert path.stat().st_size > 0

    def test_rf_classifier_exists(self):
        path = MODELS_DIR / "rf_classifier.joblib"
        if not path.exists():
            pytest.skip("Model not trained yet.")
        assert path.stat().st_size > 0

    def test_xgb_classifier_exists(self):
        path = MODELS_DIR / "xgb_classifier.json"
        if not path.exists():
            pytest.skip("Model not trained yet.")
        assert path.stat().st_size > 0


class TestPredictionShapes:
    """Verify predictions have the right shape and dtype."""

    def test_rf_regressor_predictions(self, prepared_data):
        import joblib
        path = MODELS_DIR / "rf_regressor.joblib"
        if not path.exists():
            pytest.skip("RF regressor not trained yet.")
        model = joblib.load(path)
        X_test = prepared_data[2]
        preds = model.predict(X_test)
        assert preds.shape == (X_test.shape[0],)
        assert np.issubdtype(preds.dtype, np.floating)

    def test_xgb_regressor_predictions(self, prepared_data):
        from xgboost import XGBRegressor
        path = MODELS_DIR / "xgb_regressor.json"
        if not path.exists():
            pytest.skip("XGB regressor not trained yet.")
        model = XGBRegressor()
        model.load_model(str(path))
        X_test = prepared_data[2]
        preds = model.predict(X_test)
        assert preds.shape == (X_test.shape[0],)

    def test_rf_classifier_predictions(self, prepared_data):
        import joblib
        path = MODELS_DIR / "rf_classifier.joblib"
        if not path.exists():
            pytest.skip("RF classifier not trained yet.")
        model = joblib.load(path)
        X_test = prepared_data[2]
        preds = model.predict(X_test)
        assert preds.shape == (X_test.shape[0],)

    def test_xgb_classifier_predictions(self, prepared_data):
        from xgboost import XGBClassifier
        path = MODELS_DIR / "xgb_classifier.json"
        if not path.exists():
            pytest.skip("XGB classifier not trained yet.")
        model = XGBClassifier()
        model.load_model(str(path))
        X_test = prepared_data[2]
        preds = model.predict(X_test)
        assert preds.shape == (X_test.shape[0],)
