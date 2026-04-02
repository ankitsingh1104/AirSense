"""
Tests for src/feature_engineering.py
======================================
Verifies that all engineered features are created with correct shapes and dtypes.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_and_split, CONFIG as DATA_CONFIG
from src.feature_engineering import engineer_features, prepare_features


@pytest.fixture(scope="module")
def splits():
    """Load raw splits."""
    csv_path = DATA_CONFIG["data_dir"] / DATA_CONFIG["csv_filename"]
    if not csv_path.exists():
        pytest.skip("Dataset CSV not found — skipping feature_engineering tests.")
    return load_and_split()


@pytest.fixture(scope="module")
def engineered(splits):
    """Apply engineer_features to train split."""
    return engineer_features(splits[0].copy())


@pytest.fixture(scope="module")
def prepared(splits):
    """Run full prepare_features pipeline."""
    return prepare_features(splits[0], splits[1], splits[2])


class TestEngineerFeatures:
    """Test the raw feature-engineering function."""

    def test_pollutant_std_created(self, engineered):
        assert "pollutant_std" in engineered.columns

    def test_dominance_ratio_range(self, engineered):
        assert "dominance_ratio" in engineered.columns
        assert engineered["dominance_ratio"].between(0, 1).all()

    def test_dominant_pollutant_values(self, engineered):
        assert "dominant_pollutant" in engineered.columns
        valid = {"co", "ozone", "no2", "pm2.5"}
        assert set(engineered["dominant_pollutant"].unique()).issubset(valid)

    def test_interaction_features(self, engineered):
        assert "co_no2_interaction" in engineered.columns
        assert "pm_ozone_interaction" in engineered.columns

    def test_skew_kurtosis(self, engineered):
        assert "pollutant_skew" in engineered.columns
        assert "pollutant_kurtosis" in engineered.columns

    def test_geo_cluster(self, engineered):
        assert "geo_cluster" in engineered.columns


class TestPrepareFeatures:
    """Test the full pipeline (encoding + scaling)."""

    def test_output_count(self, prepared):
        """Should return 11 items."""
        assert len(prepared) == 11

    def test_X_shapes(self, prepared):
        X_train, X_val, X_test = prepared[0], prepared[1], prepared[2]
        assert X_train.ndim == 2
        assert X_val.ndim == 2
        assert X_test.ndim == 2
        # All should have the same number of features
        assert X_train.shape[1] == X_val.shape[1] == X_test.shape[1]

    def test_y_shapes(self, prepared):
        for i in range(3, 9):  # y_reg and y_clf for train/val/test
            assert prepared[i].ndim == 1

    def test_y_clf_dtype(self, prepared):
        """Classification targets should be integer-like."""
        y_clf_train = prepared[6]
        assert np.issubdtype(y_clf_train.dtype, np.integer) or \
               np.all(y_clf_train == y_clf_train.astype(int))

    def test_feature_names(self, prepared):
        feature_names = prepared[10]
        assert isinstance(feature_names, list)
        assert len(feature_names) > 0
        assert len(feature_names) == prepared[0].shape[1]
