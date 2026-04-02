"""
Tests for src/data_loader.py
=============================
Verifies output shapes, dtypes, no nulls/duplicates after cleaning, and
correct stratified split ratios.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import load_and_split, CONFIG


@pytest.fixture(scope="module")
def splits():
    """Load and split the dataset once for all tests."""
    csv_path = CONFIG["data_dir"] / CONFIG["csv_filename"]
    if not csv_path.exists():
        pytest.skip("Dataset CSV not found — skipping data_loader tests.")
    return load_and_split()


class TestLoadAndSplit:
    """Test suite for load_and_split()."""

    def test_returns_three_dataframes(self, splits):
        """Output should be a tuple of three DataFrames."""
        assert len(splits) == 3
        for df in splits:
            assert isinstance(df, pd.DataFrame)

    def test_no_nulls(self, splits):
        """All splits should be free of null values."""
        for df in splits:
            assert df.isnull().sum().sum() == 0, "Found null values in a split."

    def test_no_duplicates(self, splits):
        """No exact duplicate rows should remain."""
        for df in splits:
            assert df.duplicated().sum() == 0, "Found duplicate rows in a split."

    def test_split_ratios(self, splits):
        """Train ≈70%, val ≈15%, test ≈15%."""
        total = sum(len(df) for df in splits)
        train_ratio = len(splits[0]) / total
        val_ratio = len(splits[1]) / total
        test_ratio = len(splits[2]) / total

        assert 0.65 <= train_ratio <= 0.75, f"Train ratio {train_ratio:.2f} out of range"
        assert 0.12 <= val_ratio <= 0.18, f"Val ratio {val_ratio:.2f} out of range"
        assert 0.12 <= test_ratio <= 0.18, f"Test ratio {test_ratio:.2f} out of range"

    def test_expected_columns(self, splits):
        """All splits should contain the known dataset columns."""
        required = {"aqi_value", "aqi_category", "country_name", "city_name"}
        for df in splits:
            assert required.issubset(set(df.columns)), (
                f"Missing columns: {required - set(df.columns)}"
            )

    def test_dtypes(self, splits):
        """aqi_value should be numeric."""
        for df in splits:
            assert pd.api.types.is_numeric_dtype(df["aqi_value"])
