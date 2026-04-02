"""
Model Training Module
=====================
Trains four models via RandomizedSearchCV:
  1. Random Forest Regressor  → models/rf_regressor.joblib
  2. XGBoost Regressor        → models/xgb_regressor.json
  3. Random Forest Classifier  → models/rf_classifier.joblib
  4. XGBoost Classifier        → models/xgb_classifier.json

Public API
----------
``train_all(X_train, y_reg_train, y_clf_train)``
    Trains all four models and saves them to disk.
    Returns a dict of fitted model objects.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBClassifier, XGBRegressor

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CONFIG = {
    "models_dir": Path(__file__).resolve().parent.parent / "models",
    "random_state": 42,
    "n_iter": 20,
    "cv": 5,
    "rf_param_grid": {
        "n_estimators": [100, 200, 300],
        "max_depth": [None, 10, 20, 30],
        "min_samples_split": [2, 5, 10],
        "max_features": ["sqrt", "log2"],
    },
    "xgb_param_grid": {
        "n_estimators": [100, 300, 500],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.7, 0.8, 1.0],
        "colsample_bytree": [0.7, 0.8, 1.0],
    },
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def train_all(
    X_train: np.ndarray,
    y_reg_train: np.ndarray,
    y_clf_train: np.ndarray,
) -> dict:
    """
    Train all four models and persist to disk.

    Parameters
    ----------
    X_train : np.ndarray
        Scaled training features.
    y_reg_train : np.ndarray
        Continuous AQI values (regression target).
    y_clf_train : np.ndarray
        Integer-encoded AQI categories (classification target).

    Returns
    -------
    dict
        {"rf_reg": model, "xgb_reg": model, "rf_clf": model, "xgb_clf": model}
    """
    CONFIG["models_dir"].mkdir(parents=True, exist_ok=True)
    models = {}

    # A — Random Forest Regressor
    models["rf_reg"] = _train_rf_regressor(X_train, y_reg_train)

    # B — XGBoost Regressor
    models["xgb_reg"] = _train_xgb_regressor(X_train, y_reg_train)

    # C — Random Forest Classifier
    models["rf_clf"] = _train_rf_classifier(X_train, y_clf_train)

    # D — XGBoost Classifier
    models["xgb_clf"] = _train_xgb_classifier(X_train, y_clf_train)

    logger.info("All models trained and saved successfully.")
    return models


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _train_rf_regressor(X: np.ndarray, y: np.ndarray):
    """
    Train Random Forest Regressor with RandomizedSearchCV.

    Scoring : neg_mean_absolute_error
    Saves   : models/rf_regressor.joblib
    """
    logger.info("=" * 60)
    logger.info("Training Random Forest Regressor …")
    logger.info("=" * 60)

    base = RandomForestRegressor(random_state=CONFIG["random_state"])
    search = RandomizedSearchCV(
        base,
        param_distributions=CONFIG["rf_param_grid"],
        n_iter=CONFIG["n_iter"],
        cv=CONFIG["cv"],
        scoring="neg_mean_absolute_error",
        random_state=CONFIG["random_state"],
        n_jobs=1,
        verbose=1,
    )
    search.fit(X, y)

    best = search.best_estimator_
    logger.info("Best RF Regressor params: %s", search.best_params_)
    logger.info("Best CV MAE: %.4f", -search.best_score_)

    path = CONFIG["models_dir"] / "rf_regressor.joblib"
    joblib.dump(best, path)
    logger.info("Saved → %s", path)
    return best


def _train_xgb_regressor(X: np.ndarray, y: np.ndarray):
    """
    Train XGBoost Regressor with RandomizedSearchCV.

    Scoring : neg_mean_absolute_error
    Saves   : models/xgb_regressor.json
    """
    logger.info("=" * 60)
    logger.info("Training XGBoost Regressor …")
    logger.info("=" * 60)

    base = XGBRegressor(
        random_state=CONFIG["random_state"],
        verbosity=0,
    )
    search = RandomizedSearchCV(
        base,
        param_distributions=CONFIG["xgb_param_grid"],
        n_iter=CONFIG["n_iter"],
        cv=CONFIG["cv"],
        scoring="neg_mean_absolute_error",
        random_state=CONFIG["random_state"],
        n_jobs=1,
        verbose=1,
    )
    search.fit(X, y)

    best = search.best_estimator_
    logger.info("Best XGB Regressor params: %s", search.best_params_)
    logger.info("Best CV MAE: %.4f", -search.best_score_)

    path = CONFIG["models_dir"] / "xgb_regressor.json"
    best.save_model(str(path))
    logger.info("Saved → %s", path)
    return best


def _train_rf_classifier(X: np.ndarray, y: np.ndarray):
    """
    Train Random Forest Classifier with RandomizedSearchCV.

    Scoring : f1_weighted
    Saves   : models/rf_classifier.joblib
    """
    logger.info("=" * 60)
    logger.info("Training Random Forest Classifier …")
    logger.info("=" * 60)

    base = RandomForestClassifier(random_state=CONFIG["random_state"])
    search = RandomizedSearchCV(
        base,
        param_distributions=CONFIG["rf_param_grid"],
        n_iter=CONFIG["n_iter"],
        cv=CONFIG["cv"],
        scoring="f1_weighted",
        random_state=CONFIG["random_state"],
        n_jobs=1,
        verbose=1,
    )
    search.fit(X, y)

    best = search.best_estimator_
    logger.info("Best RF Classifier params: %s", search.best_params_)
    logger.info("Best CV F1: %.4f", search.best_score_)

    path = CONFIG["models_dir"] / "rf_classifier.joblib"
    joblib.dump(best, path)
    logger.info("Saved → %s", path)
    return best


def _train_xgb_classifier(X: np.ndarray, y: np.ndarray):
    """
    Train XGBoost Classifier with RandomizedSearchCV.

    Scoring : f1_weighted
    Saves   : models/xgb_classifier.json
    """
    logger.info("=" * 60)
    logger.info("Training XGBoost Classifier …")
    logger.info("=" * 60)

    n_classes = len(np.unique(y))
    base = XGBClassifier(
        random_state=CONFIG["random_state"],
        eval_metric="mlogloss",
        use_label_encoder=False,
        num_class=n_classes if n_classes > 2 else None,
        verbosity=0,
    )
    search = RandomizedSearchCV(
        base,
        param_distributions=CONFIG["xgb_param_grid"],
        n_iter=CONFIG["n_iter"],
        cv=CONFIG["cv"],
        scoring="f1_weighted",
        random_state=CONFIG["random_state"],
        n_jobs=1,
        verbose=1,
    )
    search.fit(X, y)

    best = search.best_estimator_
    logger.info("Best XGB Classifier params: %s", search.best_params_)
    logger.info("Best CV F1: %.4f", search.best_score_)

    path = CONFIG["models_dir"] / "xgb_classifier.json"
    best.save_model(str(path))
    logger.info("Saved → %s", path)
    return best
