"""
Master Runner
=============
Orchestrates the full Air Pollution ML pipeline.

Usage
-----
    python main.py --mode train      # Steps 1-3
    python main.py --mode evaluate   # Step 4 (loads saved models)
    python main.py --mode serve      # Start FastAPI server
    python main.py --mode all        # Steps 1-4 then serve
"""

import argparse
import logging
import sys
from pathlib import Path

import joblib

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG = {
    "log_dir": PROJECT_ROOT / "logs",
    "models_dir": PROJECT_ROOT / "models",
    "host": "0.0.0.0",
    "port": 8000,
}


def _setup_logging() -> None:
    """Configure logging to console + file."""
    CONFIG["log_dir"].mkdir(parents=True, exist_ok=True)
    log_file = CONFIG["log_dir"] / "pipeline.log"

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


# ---------------------------------------------------------------------------
# PIPELINE STAGES
# ---------------------------------------------------------------------------

def run_train() -> tuple:
    """
    Execute Steps 1-3: load data → engineer features → train models.

    Returns
    -------
    tuple
        (models_dict, X_train, X_val, X_test,
         y_reg_val, y_reg_test, y_clf_val, y_clf_test, feature_names)
    """
    logger = logging.getLogger("main.train")

    # --- Step 1: Data Loading -----------------------------------------------
    logger.info("=" * 70)
    logger.info("STEP 1 — DATA LOADING")
    logger.info("=" * 70)
    from src.data_loader import load_and_split
    df_train, df_val, df_test = load_and_split()

    # --- Step 2: Feature Engineering ----------------------------------------
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 2 — FEATURE ENGINEERING")
    logger.info("=" * 70)
    from src.feature_engineering import prepare_features
    (
        X_train, X_val, X_test,
        y_reg_train, y_reg_val, y_reg_test,
        y_clf_train, y_clf_val, y_clf_test,
        scaler, feature_names,
    ) = prepare_features(df_train, df_val, df_test)

    # Persist scaler + feature names for the inference API
    CONFIG["models_dir"].mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, CONFIG["models_dir"] / "scaler.joblib")
    joblib.dump(feature_names, CONFIG["models_dir"] / "feature_names.joblib")
    logger.info("Saved scaler and feature_names to %s", CONFIG["models_dir"])

    # --- Step 3: Model Training ---------------------------------------------
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 3 — MODEL TRAINING")
    logger.info("=" * 70)
    from src.train import train_all
    models = train_all(X_train, y_reg_train, y_clf_train)

    return (
        models, X_train, X_val, X_test,
        y_reg_val, y_reg_test,
        y_clf_val, y_clf_test,
        feature_names,
    )


def run_evaluate(
    models=None,
    X_train=None, X_val=None, X_test=None,
    y_reg_val=None, y_reg_test=None,
    y_clf_val=None, y_clf_test=None,
    feature_names=None,
) -> None:
    """
    Execute Step 4: evaluation & explainability.

    If models/data are not supplied (standalone mode), they are
    reconstructed from saved artefacts + re-running data/feature steps.
    """
    logger = logging.getLogger("main.evaluate")

    if models is None:
        logger.info("Loading saved models and re-running data + feature pipeline …")

        from src.data_loader import load_and_split
        from src.feature_engineering import prepare_features

        df_train, df_val, df_test = load_and_split()
        (
            X_train, X_val, X_test,
            y_reg_train, y_reg_val, y_reg_test,
            y_clf_train, y_clf_val, y_clf_test,
            scaler, feature_names,
        ) = prepare_features(df_train, df_val, df_test)

        models = _load_models()

    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 4 — EVALUATION & EXPLAINABILITY")
    logger.info("=" * 70)

    from src.evaluate import run_evaluation
    run_evaluation(
        models,
        X_train, X_val, X_test,
        y_reg_val, y_reg_test,
        y_clf_val, y_clf_test,
        feature_names,
    )


def run_serve() -> None:
    """Start the FastAPI server (Step 5)."""
    logger = logging.getLogger("main.serve")
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 5 — STARTING FASTAPI SERVER")
    logger.info("=" * 70)

    import uvicorn
    uvicorn.run(
        "src.inference:app",
        host=CONFIG["host"],
        port=CONFIG["port"],
        reload=False,
    )


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _load_models() -> dict:
    """Load all four models from disk."""
    from xgboost import XGBClassifier, XGBRegressor

    md = CONFIG["models_dir"]
    rf_reg = joblib.load(md / "rf_regressor.joblib")
    rf_clf = joblib.load(md / "rf_classifier.joblib")

    xgb_reg = XGBRegressor()
    xgb_reg.load_model(str(md / "xgb_regressor.json"))

    xgb_clf = XGBClassifier()
    xgb_clf.load_model(str(md / "xgb_classifier.json"))

    return {"rf_reg": rf_reg, "xgb_reg": xgb_reg, "rf_clf": rf_clf, "xgb_clf": xgb_clf}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Parse arguments and dispatch to the appropriate pipeline stage."""
    parser = argparse.ArgumentParser(
        description="Global Air Pollution Analysis & AQI Prediction Pipeline",
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["train", "evaluate", "serve", "all"],
        help="Pipeline mode: train | evaluate | serve | all",
    )
    args = parser.parse_args()

    _setup_logging()
    logger = logging.getLogger("main")
    logger.info("Pipeline started — mode=%s", args.mode)

    if args.mode == "train":
        run_train()

    elif args.mode == "evaluate":
        run_evaluate()

    elif args.mode == "serve":
        run_serve()

    elif args.mode == "all":
        (
            models, X_train, X_val, X_test,
            y_reg_val, y_reg_test,
            y_clf_val, y_clf_test,
            feature_names,
        ) = run_train()

        run_evaluate(
            models, X_train, X_val, X_test,
            y_reg_val, y_reg_test,
            y_clf_val, y_clf_test,
            feature_names,
        )

        run_serve()

    logger.info("Pipeline finished.")


if __name__ == "__main__":
    main()
