"""
Evaluation & Explainability Module
====================================
Computes regression/classification metrics, generates 14+ plots
(residuals, SHAP, LIME, calibration, confusion matrices, feature importance),
and prints formatted comparison tables.

Public API
----------
``run_evaluation(models, X_val, X_test, y_reg_val, y_reg_test,
                  y_clf_val, y_clf_test, feature_names)``
"""

import logging
import warnings
from pathlib import Path

import joblib
import lime.lime_tabular
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be before pyplot import
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import shap
from sklearn.calibration import CalibrationDisplay
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from xgboost import XGBClassifier, XGBRegressor

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CONFIG = {
    "plots_dir": Path(__file__).resolve().parent.parent / "plots",
    "models_dir": Path(__file__).resolve().parent.parent / "models",
    "plot_style": "seaborn-v0_8-whitegrid",
    "figsize": (10, 6),
    "dpi": 150,
    "aqi_categories": [
        "Good", "Moderate", "Unhealthy-SG",
        "Unhealthy", "Very Unhealthy", "Hazardous",
    ],
    "shap_sample": 200,
    "random_state": 42,
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def run_evaluation(
    models: dict,
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_reg_val: np.ndarray,
    y_reg_test: np.ndarray,
    y_clf_val: np.ndarray,
    y_clf_test: np.ndarray,
    feature_names: list[str],
) -> None:
    """
    Run the full evaluation pipeline: metrics + all plots.

    Parameters
    ----------
    models : dict
        {"rf_reg", "xgb_reg", "rf_clf", "xgb_clf"} — fitted model objects.
    X_train : np.ndarray
        Scaled training features (used for LIME background).
    X_val, X_test : np.ndarray
        Scaled validation / test features.
    y_reg_val, y_reg_test : np.ndarray
        Continuous AQI targets.
    y_clf_val, y_clf_test : np.ndarray
        Integer-encoded AQI-category targets.
    feature_names : list[str]
        Ordered list of feature names matching X columns.
    """
    CONFIG["plots_dir"].mkdir(parents=True, exist_ok=True)
    plt.style.use(CONFIG["plot_style"])

    rf_reg = models["rf_reg"]
    xgb_reg = models["xgb_reg"]
    rf_clf = models["rf_clf"]
    xgb_clf = models["xgb_clf"]

    # --- A. Regression Metrics ---------------------------------------------
    logger.info("=" * 60)
    logger.info("REGRESSION METRICS")
    logger.info("=" * 60)
    _regression_metrics(rf_reg, xgb_reg, X_val, X_test, y_reg_val, y_reg_test)

    # --- B. Classification Metrics -----------------------------------------
    logger.info("=" * 60)
    logger.info("CLASSIFICATION METRICS")
    logger.info("=" * 60)
    _classification_metrics(rf_clf, xgb_clf, X_val, X_test, y_clf_val, y_clf_test)

    # --- C. Plots ----------------------------------------------------------
    logger.info("Generating plots …")

    # 1–2. Residual scatter plots
    _plot_residual_scatter(rf_reg, X_test, y_reg_test, "RF", "residuals_rf.png")
    _plot_residual_scatter(xgb_reg, X_test, y_reg_test, "XGBoost", "residuals_xgb.png")

    # 3. Residual distribution
    _plot_residual_distribution(rf_reg, xgb_reg, X_test, y_reg_test)

    # 4–5. SHAP summary beeswarm
    _plot_shap_summary(rf_reg, X_test, feature_names, "RF", "shap_rf_summary.png")
    _plot_shap_summary(xgb_reg, X_test, feature_names, "XGBoost", "shap_xgb_summary.png")

    # 6. SHAP waterfall — most polluted predicted city
    _plot_shap_waterfall_most_polluted(rf_reg, X_test, feature_names)

    # 7. Feature importance comparison
    _plot_feature_importance(rf_reg, xgb_reg, feature_names)

    # 8. Calibration curves
    _plot_calibration(rf_clf, X_test, y_clf_test, "RF", "calibration_rf.png")
    _plot_calibration(xgb_clf, X_test, y_clf_test, "XGBoost", "calibration_xgb.png")

    # 9. Confusion matrices
    _plot_confusion_matrix(rf_clf, X_test, y_clf_test, "RF", "confusion_matrix_rf.png")
    _plot_confusion_matrix(xgb_clf, X_test, y_clf_test, "XGBoost", "confusion_matrix_xgb.png")

    # D. SHAP / LIME edge-case comparison
    _edge_case_comparison(rf_reg, X_train, X_test, y_reg_test, feature_names)

    logger.info("All plots saved to %s", CONFIG["plots_dir"])


# ---------------------------------------------------------------------------
# A. REGRESSION METRICS
# ---------------------------------------------------------------------------

def _regression_metrics(rf, xgb, X_val, X_test, y_val, y_test):
    """Print a formatted comparison table of regression metrics."""
    rows = []
    for name, model in [("RF", rf), ("XGB", xgb)]:
        for split_name, X, y in [("Val", X_val, y_val), ("Test", X_test, y_test)]:
            preds = model.predict(X)
            mae = mean_absolute_error(y, preds)
            rmse = np.sqrt(mean_squared_error(y, preds))
            r2 = r2_score(y, preds)
            mape = mean_absolute_percentage_error(y, preds)
            rows.append((name, split_name, mae, rmse, r2, mape))

    header = f"{'Model':<6} {'Split':<6} {'MAE':>8} {'RMSE':>8} {'R²':>8} {'MAPE':>8}"
    logger.info(header)
    logger.info("-" * len(header))
    for name, split, mae, rmse, r2, mape in rows:
        logger.info(
            f"{name:<6} {split:<6} {mae:>8.3f} {rmse:>8.3f} {r2:>8.4f} {mape:>8.4f}"
        )


# ---------------------------------------------------------------------------
# B. CLASSIFICATION METRICS
# ---------------------------------------------------------------------------

def _classification_metrics(rf, xgb, X_val, X_test, y_val, y_test):
    """Print a formatted comparison table of classification metrics."""
    rows = []
    for name, model in [("RF", rf), ("XGB", xgb)]:
        for split_name, X, y in [("Val", X_val, y_val), ("Test", X_test, y_test)]:
            preds = model.predict(X)
            acc = accuracy_score(y, preds)
            f1 = f1_score(y, preds, average="weighted", zero_division=0)
            kappa = cohen_kappa_score(y, preds)
            rows.append((name, split_name, acc, f1, kappa))

    header = f"{'Model':<6} {'Split':<6} {'Acc':>8} {'F1-W':>8} {'Kappa':>8}"
    logger.info(header)
    logger.info("-" * len(header))
    for name, split, acc, f1, kappa in rows:
        logger.info(f"{name:<6} {split:<6} {acc:>8.4f} {f1:>8.4f} {kappa:>8.4f}")


# ---------------------------------------------------------------------------
# C1. RESIDUAL SCATTER
# ---------------------------------------------------------------------------

def _plot_residual_scatter(model, X_test, y_test, label, filename):
    """
    Scatter: Actual vs Predicted AQI coloured by residual magnitude.
    Includes y=x reference line.
    """
    preds = model.predict(X_test)
    residuals = np.abs(y_test - preds)

    fig, ax = plt.subplots(figsize=CONFIG["figsize"])
    sc = ax.scatter(y_test, preds, c=residuals, cmap="RdYlGn_r", alpha=0.7, edgecolors="k", linewidths=0.3, s=20)
    lims = [min(y_test.min(), preds.min()) - 5, max(y_test.max(), preds.max()) + 5]
    ax.plot(lims, lims, "k--", linewidth=1, label="y = x")
    ax.set_xlabel("Actual AQI")
    ax.set_ylabel("Predicted AQI")
    ax.set_title(f"{label} Regressor — Actual vs Predicted AQI")
    ax.legend()
    fig.colorbar(sc, ax=ax, label="Residual Magnitude")
    fig.tight_layout()
    fig.savefig(CONFIG["plots_dir"] / filename, dpi=CONFIG["dpi"])
    plt.close(fig)
    logger.info("Saved %s", filename)


# ---------------------------------------------------------------------------
# C3. RESIDUAL DISTRIBUTION
# ---------------------------------------------------------------------------

def _plot_residual_distribution(rf, xgb, X_test, y_test):
    """Side-by-side histogram of residuals for RF vs XGB."""
    res_rf = y_test - rf.predict(X_test)
    res_xgb = y_test - xgb.predict(X_test)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    for ax, res, name in zip(axes, [res_rf, res_xgb], ["RF", "XGBoost"]):
        ax.hist(res, bins=50, alpha=0.75, edgecolor="k", linewidth=0.5)
        ax.axvline(res.mean(), color="red", linestyle="--", linewidth=1.5)
        ax.set_xlabel("Residual (Actual − Predicted)")
        ax.set_ylabel("Count")
        ax.set_title(f"{name} Residual Distribution")
        ax.legend([
            f"Mean = {res.mean():.2f}\nStd = {res.std():.2f}"
        ])

    fig.tight_layout()
    fig.savefig(CONFIG["plots_dir"] / "residual_distribution.png", dpi=CONFIG["dpi"])
    plt.close(fig)
    logger.info("Saved residual_distribution.png")


# ---------------------------------------------------------------------------
# C4-5. SHAP SUMMARY BEESWARM
# ---------------------------------------------------------------------------

def _plot_shap_summary(model, X_test, feature_names, label, filename):
    """SHAP summary beeswarm plot (sampled for speed)."""
    n = min(CONFIG["shap_sample"], X_test.shape[0])
    rng = np.random.RandomState(CONFIG["random_state"])
    idx = rng.choice(X_test.shape[0], n, replace=False)
    X_sample = X_test[idx]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)

    fig, ax = plt.subplots(figsize=CONFIG["figsize"])
    shap.summary_plot(
        shap_values, X_sample,
        feature_names=feature_names,
        show=False,
    )
    plt.title(f"SHAP Summary — {label} Regressor")
    plt.tight_layout()
    plt.savefig(CONFIG["plots_dir"] / filename, dpi=CONFIG["dpi"], bbox_inches="tight")
    plt.close("all")
    logger.info("Saved %s", filename)


# ---------------------------------------------------------------------------
# C6. SHAP WATERFALL — MOST POLLUTED PREDICTED CITY
# ---------------------------------------------------------------------------

def _plot_shap_waterfall_most_polluted(model, X_test, feature_names):
    """SHAP waterfall for the test sample with the highest predicted AQI."""
    preds = model.predict(X_test)
    idx = int(np.argmax(preds))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        explainer = shap.TreeExplainer(model)
        sv = explainer(X_test[idx : idx + 1])

    fig, ax = plt.subplots(figsize=CONFIG["figsize"])
    shap.plots.waterfall(sv[0], show=False)
    plt.title("SHAP Waterfall — Most Polluted Predicted City (RF)")
    plt.tight_layout()
    plt.savefig(CONFIG["plots_dir"] / "shap_rf_waterfall.png", dpi=CONFIG["dpi"], bbox_inches="tight")
    plt.close("all")
    logger.info("Saved shap_rf_waterfall.png")


# ---------------------------------------------------------------------------
# C7. FEATURE IMPORTANCE COMPARISON
# ---------------------------------------------------------------------------

def _plot_feature_importance(rf, xgb, feature_names):
    """Side-by-side horizontal bar chart of top-12 feature importances."""
    rf_imp = rf.feature_importances_
    xgb_imp = xgb.feature_importances_

    top_k = 12
    rf_idx = np.argsort(rf_imp)[-top_k:]
    xgb_idx = np.argsort(xgb_imp)[-top_k:]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    axes[0].barh(
        [feature_names[i] for i in rf_idx],
        rf_imp[rf_idx],
        color="#4C72B0", edgecolor="k", linewidth=0.5,
    )
    axes[0].set_title("RF — Top 12 Features")
    axes[0].set_xlabel("Importance")

    axes[1].barh(
        [feature_names[i] for i in xgb_idx],
        xgb_imp[xgb_idx],
        color="#DD8452", edgecolor="k", linewidth=0.5,
    )
    axes[1].set_title("XGBoost — Top 12 Features")
    axes[1].set_xlabel("Importance")

    fig.suptitle("Feature Importance Comparison", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(CONFIG["plots_dir"] / "feature_importance_comparison.png", dpi=CONFIG["dpi"])
    plt.close(fig)
    logger.info("Saved feature_importance_comparison.png")


# ---------------------------------------------------------------------------
# C8. CALIBRATION CURVES
# ---------------------------------------------------------------------------

def _plot_calibration(model, X_test, y_test, label, filename):
    """
    Reliability diagram (calibration curve) for a classifier.
    Uses one-vs-rest for the most common class to generate a meaningful curve.
    """
    fig, ax = plt.subplots(figsize=CONFIG["figsize"])

    # Use the most common class for a binary calibration view
    most_common_class = int(np.argmax(np.bincount(y_test.astype(int))))
    y_binary = (y_test == most_common_class).astype(int)

    proba = model.predict_proba(X_test)
    if proba.shape[1] > most_common_class:
        prob_positive = proba[:, most_common_class]
    else:
        prob_positive = proba[:, 0]

    CalibrationDisplay.from_predictions(
        y_binary, prob_positive,
        n_bins=10, ax=ax, name=f"{label} (class={CONFIG['aqi_categories'][most_common_class]})",
    )
    ax.set_title(f"Calibration Curve — {label} Classifier")
    fig.tight_layout()
    fig.savefig(CONFIG["plots_dir"] / filename, dpi=CONFIG["dpi"])
    plt.close(fig)
    logger.info("Saved %s", filename)


# ---------------------------------------------------------------------------
# C9. CONFUSION MATRICES
# ---------------------------------------------------------------------------

def _plot_confusion_matrix(model, X_test, y_test, label, filename):
    """Normalised confusion matrix as a seaborn heatmap."""
    preds = model.predict(X_test)
    present_labels = sorted(set(y_test) | set(preds))
    cm = confusion_matrix(y_test, preds, labels=present_labels, normalize="true")

    cat_labels = [CONFIG["aqi_categories"][int(l)] if int(l) < len(CONFIG["aqi_categories"]) else str(l)
                  for l in present_labels]

    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(
        cm, annot=True, fmt=".2f", cmap="Blues",
        xticklabels=cat_labels, yticklabels=cat_labels, ax=ax,
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"Confusion Matrix — {label} Classifier (Normalised)")
    fig.tight_layout()
    fig.savefig(CONFIG["plots_dir"] / filename, dpi=CONFIG["dpi"])
    plt.close(fig)
    logger.info("Saved %s", filename)


# ---------------------------------------------------------------------------
# D. EDGE-CASE COMPARISON (SHAP vs LIME)
# ---------------------------------------------------------------------------

def _edge_case_comparison(model, X_train, X_test, y_test, feature_names):
    """
    For the 3 test samples with the highest absolute residuals:
      - Generate a SHAP waterfall plot.
      - Generate a LIME explanation plot.
      - Print a summary table of top-3 features flagged by each method.
    """
    preds = model.predict(X_test)
    residuals = np.abs(y_test - preds)
    worst_idx = np.argsort(residuals)[-3:][::-1]  # top-3, descending

    # Build LIME explainer once
    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        X_train,
        feature_names=feature_names,
        mode="regression",
        random_state=CONFIG["random_state"],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree_explainer = shap.TreeExplainer(model)

    summary_rows = []

    for rank, idx in enumerate(worst_idx):
        idx = int(idx)
        sample = X_test[idx : idx + 1]

        # --- SHAP waterfall ---
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sv = tree_explainer(sample)

        fig, ax = plt.subplots(figsize=CONFIG["figsize"])
        shap.plots.waterfall(sv[0], show=False)
        plt.title(f"Edge Case #{rank + 1} — SHAP Waterfall")
        plt.tight_layout()
        plt.savefig(
            CONFIG["plots_dir"] / f"edge_case_{rank + 1}_shap.png",
            dpi=CONFIG["dpi"], bbox_inches="tight",
        )
        plt.close("all")

        shap_vals = np.abs(sv[0].values)
        shap_top3 = [feature_names[i] for i in np.argsort(shap_vals)[-3:][::-1]]

        # --- LIME ---
        lime_exp = lime_explainer.explain_instance(
            X_test[idx], model.predict, num_features=10,
        )
        lime_fig = lime_exp.as_pyplot_figure()
        lime_fig.set_size_inches(*CONFIG["figsize"])
        lime_fig.suptitle(f"Edge Case #{rank + 1} — LIME Explanation")
        lime_fig.tight_layout()
        lime_fig.savefig(
            CONFIG["plots_dir"] / f"edge_case_{rank + 1}_lime.png",
            dpi=CONFIG["dpi"],
        )
        plt.close("all")

        lime_top3 = [feat for feat, _ in lime_exp.as_list()[:3]]

        summary_rows.append({
            "rank": rank + 1,
            "residual": residuals[idx],
            "shap_top3": shap_top3,
            "lime_top3": lime_top3,
        })

        logger.info("Saved edge_case_%d_shap.png & edge_case_%d_lime.png", rank + 1, rank + 1)

    # --- Print summary table -----------------------------------------------
    logger.info("")
    logger.info("EDGE-CASE COMPARISON — Top-3 Features Flagged by SHAP vs LIME")
    logger.info("| Rank | Residual |      SHAP Top-3       |       LIME Top-3       |")
    logger.info("|------|----------|-----------------------|------------------------|")
    for row in summary_rows:
        s = ", ".join(row["shap_top3"])
        l = ", ".join(row["lime_top3"])
        logger.info(
            "| %4d | %8.2f | %-21s | %-22s |",
            row["rank"], row["residual"], s[:21], l[:22],
        )
