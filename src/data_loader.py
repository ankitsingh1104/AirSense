"""
Data Loader Module
==================
Downloads the Global Air Pollution dataset from Kaggle (if not already present),
performs data quality reporting, cleaning (duplicates + nulls), and returns a
stratified 70/15/15 train/val/test split.

Returns
-------
tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    (df_train, df_val, df_test)
"""

import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CONFIG = {
    "data_dir": Path(__file__).resolve().parent.parent / "data",
    "csv_filename": "global_air_pollution_data.csv",
    "kaggle_dataset": "sazidthe1/global-air-pollution-data",
    "test_size": 0.15,
    "val_size": 0.15,
    "random_state": 42,
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def load_and_split() -> tuple:
    """
    Master function: download → load → clean → split.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (df_train, df_val, df_test) with stratification on ``aqi_category``.
    """
    csv_path = CONFIG["data_dir"] / CONFIG["csv_filename"]

    # --- Download if missing ------------------------------------------------
    if not csv_path.exists():
        logger.info("Dataset not found at %s — attempting Kaggle download…", csv_path)
        _download_dataset()

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. "
            "Please place 'global_air_pollution_data.csv' in the data/ folder "
            "or configure your Kaggle API credentials."
        )

    # --- Load ---------------------------------------------------------------
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    logger.info("Loaded dataset: %s", csv_path)

    # --- Data quality report ------------------------------------------------
    _print_quality_report(df)

    # --- Clean --------------------------------------------------------------
    df = _clean(df)

    # --- Stratified split ---------------------------------------------------
    df_train, df_val, df_test = _stratified_split(df)

    logger.info(
        "Split sizes — train: %d, val: %d, test: %d",
        len(df_train), len(df_val), len(df_test),
    )
    return df_train, df_val, df_test


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _download_dataset() -> None:
    """Download dataset via the Kaggle CLI. Requires ``kaggle`` to be installed
    and ``~/.kaggle/kaggle.json`` to exist."""
    CONFIG["data_dir"].mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "kaggle",
        "datasets", "download",
        "-d", CONFIG["kaggle_dataset"],
        "-p", str(CONFIG["data_dir"]),
        "--unzip",
    ]
    try:
        logger.info("Running: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Download complete.")
    except subprocess.CalledProcessError as exc:
        logger.warning("Kaggle download failed: %s", exc.stderr)
        logger.warning(
            "Fallback: please manually download the dataset from "
            "https://www.kaggle.com/datasets/sazidthe1/global-air-pollution-data "
            "and place the CSV in %s",
            CONFIG["data_dir"],
        )


def _print_quality_report(df: pd.DataFrame) -> None:
    """Log a concise data-quality summary."""
    logger.info("=" * 60)
    logger.info("DATA QUALITY REPORT")
    logger.info("=" * 60)
    logger.info("Shape: %s", df.shape)
    logger.info("Dtypes:\n%s", df.dtypes.to_string())
    logger.info("Null counts:\n%s", df.isnull().sum().to_string())
    logger.info("Duplicate rows: %d", df.duplicated().sum())
    logger.info("=" * 60)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates and handle missing values.

    Strategy
    --------
    1. Drop exact-duplicate rows.
    2. For numeric columns, fill NaNs with the column **median**
       (robust to outliers, which AQI data commonly contains).
    3. For remaining categorical NaNs, drop the rows (very few expected).
    """
    before = len(df)
    df = df.drop_duplicates()
    logger.info("Dropped %d duplicate rows.", before - len(df))

    # Fill numeric nulls with median
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            logger.info("Filled %s nulls with median (%.2f).", col, median_val)

    # Drop rows still containing nulls (categorical cols)
    remaining_nulls = df.isnull().sum().sum()
    if remaining_nulls > 0:
        df = df.dropna()
        logger.info("Dropped %d rows with remaining categorical nulls.", remaining_nulls)

    df = df.reset_index(drop=True)
    return df


def _stratified_split(df: pd.DataFrame) -> tuple:
    """
    70 / 15 / 15 stratified split on ``aqi_category``.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    """
    rs = CONFIG["random_state"]
    test_frac = CONFIG["test_size"]
    val_frac = CONFIG["val_size"]

    # First split: 70 % train+val  |  15 % test
    # (val_frac relative to the whole dataset = val_frac / (1 - test_frac) of remainder)
    df_train_val, df_test = train_test_split(
        df,
        test_size=test_frac,
        random_state=rs,
        stratify=df["aqi_category"],
    )

    relative_val = val_frac / (1 - test_frac)
    df_train, df_val = train_test_split(
        df_train_val,
        test_size=relative_val,
        random_state=rs,
        stratify=df_train_val["aqi_category"],
    )

    return (
        df_train.reset_index(drop=True),
        df_val.reset_index(drop=True),
        df_test.reset_index(drop=True),
    )
