"""
Feature Engineering Module
===========================
Creates advanced pollutant features, geo-cluster labels, encodes categoricals,
and scales all numeric features.

Public API
----------
``prepare_features(df_train, df_val, df_test)``
    Returns processed X/y arrays plus the fitted scaler and feature names.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CONFIG = {
    "pollutant_cols": [
        "co_aqi_value",
        "ozone_aqi_value",
        "no2_aqi_value",
        "pm2.5_aqi_value",
    ],
    "aqi_category_map": {
        "Good": 0,
        "Moderate": 1,
        "Unhealthy for Sensitive Groups": 2,
        "Unhealthy": 3,
        "Very Unhealthy": 4,
        "Hazardous": 5,
    },
    "kmeans_k": 6,
    "random_state": 42,
    "drop_string_cols": [
        "country_name",
        "city_name",
        "aqi_category",
        "co_aqi_category",
        "ozone_aqi_category",
        "no2_aqi_category",
        "pm2.5_aqi_category",
    ],
}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# STATIC COUNTRY → (LAT, LON) LOOKUP
# Used instead of live geocoding for speed and reliability.
# Covers ~200 countries/territories. Missing entries get geo_cluster = -1.
# ---------------------------------------------------------------------------
_COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "Afghanistan": (33.93, 67.71), "Albania": (41.15, 20.17),
    "Algeria": (28.03, 1.66), "Andorra": (42.55, 1.60),
    "Angola": (-11.20, 17.87), "Antigua and Barbuda": (17.06, -61.80),
    "Argentina": (-38.42, -63.62), "Armenia": (40.07, 45.04),
    "Australia": (-25.27, 133.78), "Austria": (47.52, 14.55),
    "Azerbaijan": (40.14, 47.58), "Bahamas": (25.03, -77.40),
    "Bahrain": (26.07, 50.56), "Bangladesh": (23.68, 90.36),
    "Barbados": (13.19, -59.54), "Belarus": (53.71, 27.95),
    "Belgium": (50.50, 4.47), "Belize": (17.19, -88.50),
    "Benin": (9.31, 2.32), "Bhutan": (27.51, 90.43),
    "Bolivia": (-16.29, -63.59), "Bosnia and Herzegovina": (43.92, 17.68),
    "Botswana": (-22.33, 24.68), "Brazil": (-14.24, -51.93),
    "Brunei": (4.54, 114.73), "Bulgaria": (42.73, 25.49),
    "Burkina Faso": (12.24, -1.56), "Burundi": (-3.37, 29.92),
    "Cabo Verde": (16.00, -24.01), "Cambodia": (12.57, 104.99),
    "Cameroon": (7.37, 12.35), "Canada": (56.13, -106.35),
    "Central African Republic": (6.61, 20.94), "Chad": (15.45, 18.73),
    "Chile": (-35.68, -71.54), "China": (35.86, 104.20),
    "Colombia": (4.57, -74.30), "Comoros": (-11.88, 43.87),
    "Congo": (-0.23, 15.83),
    "Democratic Republic of the Congo": (-4.04, 21.76),
    "Costa Rica": (9.75, -83.75), "Croatia": (45.10, 15.20),
    "Cuba": (21.52, -77.78), "Cyprus": (35.13, 33.43),
    "Czech Republic": (49.82, 15.47), "Czechia": (49.82, 15.47),
    "Denmark": (56.26, 9.50), "Djibouti": (11.83, 42.59),
    "Dominican Republic": (18.74, -70.16),
    "Ecuador": (-1.83, -78.18), "Egypt": (26.82, 30.80),
    "El Salvador": (13.79, -88.90), "Equatorial Guinea": (1.65, 10.27),
    "Eritrea": (15.18, 39.78), "Estonia": (58.60, 25.01),
    "Eswatini": (-26.52, 31.47), "Ethiopia": (9.15, 40.49),
    "Fiji": (-17.71, 178.07), "Finland": (61.92, 25.75),
    "France": (46.23, 2.21), "Gabon": (-0.80, 11.61),
    "Gambia": (13.44, -15.31), "Georgia": (42.32, 43.36),
    "Germany": (51.17, 10.45), "Ghana": (7.95, -1.02),
    "Greece": (39.07, 21.82), "Guatemala": (15.78, -90.23),
    "Guinea": (9.95, -9.70), "Haiti": (18.97, -72.29),
    "Honduras": (15.20, -86.24), "Hungary": (47.16, 19.50),
    "Iceland": (64.96, -19.02), "India": (20.59, 78.96),
    "Indonesia": (-0.79, 113.92), "Iran": (32.43, 53.69),
    "Iraq": (33.22, 43.68), "Ireland": (53.14, -7.69),
    "Israel": (31.05, 34.85), "Italy": (41.87, 12.57),
    "Ivory Coast": (7.54, -5.55), "Jamaica": (18.11, -77.30),
    "Japan": (36.20, 138.25), "Jordan": (30.59, 36.24),
    "Kazakhstan": (48.02, 66.92), "Kenya": (-0.02, 37.91),
    "Kosovo": (42.60, 20.90), "Kuwait": (29.31, 47.48),
    "Kyrgyzstan": (41.20, 74.77), "Laos": (19.86, 102.50),
    "Latvia": (56.88, 24.60), "Lebanon": (33.85, 35.86),
    "Lesotho": (-29.61, 28.23), "Liberia": (6.43, -9.43),
    "Libya": (26.34, 17.23), "Lithuania": (55.17, 23.88),
    "Luxembourg": (49.82, 6.13), "Madagascar": (-18.77, 46.87),
    "Malawi": (-13.25, 34.30), "Malaysia": (4.21, 101.98),
    "Maldives": (3.20, 73.22), "Mali": (17.57, -4.00),
    "Malta": (35.94, 14.38), "Mauritania": (21.01, -10.94),
    "Mauritius": (-20.35, 57.55), "Mexico": (23.63, -102.55),
    "Moldova": (47.41, 28.37), "Mongolia": (46.86, 103.85),
    "Montenegro": (42.71, 19.37), "Morocco": (31.79, -7.09),
    "Mozambique": (-18.67, 35.53), "Myanmar": (21.91, 95.96),
    "Namibia": (-22.96, 18.49), "Nepal": (28.39, 84.12),
    "Netherlands": (52.13, 5.29), "New Zealand": (-40.90, 174.89),
    "Nicaragua": (12.87, -85.21), "Niger": (17.61, 8.08),
    "Nigeria": (9.08, 8.68), "North Korea": (40.34, 127.51),
    "North Macedonia": (41.51, 21.75), "Norway": (60.47, 8.47),
    "Oman": (21.47, 55.98), "Pakistan": (30.38, 69.35),
    "Palestine": (31.95, 35.23), "Panama": (8.54, -80.78),
    "Papua New Guinea": (-6.31, 143.96), "Paraguay": (-23.44, -58.44),
    "Peru": (-9.19, -75.02), "Philippines": (12.88, 121.77),
    "Poland": (51.92, 19.15), "Portugal": (39.40, -8.22),
    "Qatar": (25.35, 51.18), "Romania": (45.94, 24.97),
    "Russia": (61.52, 105.32), "Rwanda": (-1.94, 29.87),
    "Saudi Arabia": (23.89, 45.08), "Senegal": (14.50, -14.45),
    "Serbia": (44.02, 21.01), "Sierra Leone": (8.46, -11.78),
    "Singapore": (1.35, 103.82), "Slovakia": (48.67, 19.70),
    "Slovenia": (46.15, 14.99), "Somalia": (5.15, 46.20),
    "South Africa": (-30.56, 22.94), "South Korea": (35.91, 127.77),
    "South Sudan": (6.88, 31.31), "Spain": (40.46, -3.75),
    "Sri Lanka": (7.87, 80.77), "Sudan": (12.86, 30.22),
    "Suriname": (3.92, -56.03), "Sweden": (60.13, 18.64),
    "Switzerland": (46.82, 8.23), "Syria": (34.80, 38.00),
    "Taiwan": (23.70, 120.96), "Tajikistan": (38.86, 71.28),
    "Tanzania": (-6.37, 34.89), "Thailand": (15.87, 100.99),
    "Togo": (8.62, 1.21), "Trinidad and Tobago": (10.69, -61.22),
    "Tunisia": (33.89, 9.54), "Turkey": (38.96, 35.24),
    "Turkmenistan": (38.97, 59.56), "Uganda": (1.37, 32.29),
    "Ukraine": (48.38, 31.17), "United Arab Emirates": (23.42, 53.85),
    "United Kingdom": (55.38, -3.44), "United States": (37.09, -95.71),
    "United States of America": (37.09, -95.71),
    "Uruguay": (-32.52, -55.77), "Uzbekistan": (41.38, 64.59),
    "Venezuela": (6.42, -66.59), "Vietnam": (14.06, 108.28),
    "Yemen": (15.55, 48.52), "Zambia": (-13.13, 28.64),
    "Zimbabwe": (-19.02, 29.15),
    # Common alternative names
    "Cote d'Ivoire": (7.54, -5.55), "Côte d'Ivoire": (7.54, -5.55),
    "Republic of Korea": (35.91, 127.77), "Korea": (35.91, 127.77),
    "UK": (55.38, -3.44), "USA": (37.09, -95.71),
    "UAE": (23.42, 53.85), "U.S.": (37.09, -95.71),
    "Russian Federation": (61.52, 105.32),
    "The Netherlands": (52.13, 5.29),
    "Puerto Rico": (18.22, -66.59), "Hong Kong": (22.40, 114.11),
    "Macau": (22.20, 113.54), "Taiwan, Province of China": (23.70, 120.96),
}


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def prepare_features(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
) -> tuple:
    """
    Apply all feature-engineering transformations and return processed arrays.

    Parameters
    ----------
    df_train, df_val, df_test : pd.DataFrame
        Raw split DataFrames from the data loader.

    Returns
    -------
    tuple
        (X_train, X_val, X_test,
         y_reg_train, y_reg_val, y_reg_test,
         y_clf_train, y_clf_val, y_clf_test,
         scaler, feature_names)
    """
    pcols = CONFIG["pollutant_cols"]
    cat_map = CONFIG["aqi_category_map"]

    # --- Engineer features for each split ----------------------------------
    logger.info("Engineering features …")
    df_train = engineer_features(df_train.copy())
    df_val = engineer_features(df_val.copy())
    df_test = engineer_features(df_test.copy())

    # --- Extract targets BEFORE dropping string cols -----------------------
    y_reg_train = df_train["aqi_value"].values
    y_reg_val = df_val["aqi_value"].values
    y_reg_test = df_test["aqi_value"].values

    y_clf_train = df_train["aqi_category"].map(cat_map).values
    y_clf_val = df_val["aqi_category"].map(cat_map).values
    y_clf_test = df_test["aqi_category"].map(cat_map).values

    # --- Encode dominant_pollutant (categorical) ---------------------------
    # Using fixed labels to ensure consistency and avoid "previously unseen label" errors.
    pollutant_labels = ["co", "no2", "ozone", "pm2.5"]
    le = LabelEncoder()
    le.fit(pollutant_labels)

    df_train["dominant_pollutant"] = le.transform(df_train["dominant_pollutant"])
    df_val["dominant_pollutant"] = le.transform(df_val["dominant_pollutant"])
    df_test["dominant_pollutant"] = le.transform(df_test["dominant_pollutant"])

    # --- One-hot encode geo_cluster ----------------------------------------
    df_train = pd.get_dummies(df_train, columns=["geo_cluster"], drop_first=True, dtype=int)
    df_val = pd.get_dummies(df_val, columns=["geo_cluster"], drop_first=True, dtype=int)
    df_test = pd.get_dummies(df_test, columns=["geo_cluster"], drop_first=True, dtype=int)

    # Align columns across splits (some clusters may be missing in val/test)
    df_val = df_val.reindex(columns=df_train.columns, fill_value=0)
    df_test = df_test.reindex(columns=df_train.columns, fill_value=0)

    # --- Drop string & target columns --------------------------------------
    cols_to_drop = [
        c for c in CONFIG["drop_string_cols"] if c in df_train.columns
    ]
    cols_to_drop.append("aqi_value")
    df_train = df_train.drop(columns=cols_to_drop, errors="ignore")
    df_val = df_val.drop(columns=cols_to_drop, errors="ignore")
    df_test = df_test.drop(columns=cols_to_drop, errors="ignore")

    feature_names = list(df_train.columns)
    logger.info("Feature count: %d", len(feature_names))
    logger.info("Features: %s", feature_names)

    # --- Scale -------------------------------------------------------------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_train.values)
    X_val = scaler.transform(df_val.values)
    X_test = scaler.transform(df_test.values)

    logger.info("Feature engineering complete.")
    return (
        X_train, X_val, X_test,
        y_reg_train, y_reg_val, y_reg_test,
        y_clf_train, y_clf_val, y_clf_test,
        scaler, feature_names,
    )


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all engineered columns to *df* **in-place** (returns modified df).

    Features Created
    ----------------
    A. pollutant_std
    B. pollutant_max, dominance_ratio, dominant_pollutant
    C. co_no2_interaction, pm_ozone_interaction
    D. pollutant_skew, pollutant_kurtosis
    E. geo_cluster (via static lat/lon lookup + KMeans)
    """
    pcols = CONFIG["pollutant_cols"]
    pollutant_matrix = df[pcols]

    # A — Pollutant Complexity Index
    df["pollutant_std"] = pollutant_matrix.std(axis=1)

    # B — Dominance Ratio
    df["pollutant_max"] = pollutant_matrix.max(axis=1)
    df["dominance_ratio"] = df["pollutant_max"] / (
        pollutant_matrix.sum(axis=1) + 1e-6
    )
    # Dominant pollutant name (argmax returns column label)
    df["dominant_pollutant"] = pollutant_matrix.idxmax(axis=1).apply(
        lambda c: c.replace("_aqi_value", "")
    )

    # C — Interaction Features
    df["co_no2_interaction"] = df["co_aqi_value"] * df["no2_aqi_value"]
    df["pm_ozone_interaction"] = df["pm2.5_aqi_value"] * df["ozone_aqi_value"]

    # D — Statistical Shape Features (row-wise skew & kurtosis)
    df["pollutant_skew"] = pollutant_matrix.apply(
        lambda row: skew(row, nan_policy="omit"), axis=1
    )
    df["pollutant_kurtosis"] = pollutant_matrix.apply(
        lambda row: kurtosis(row, nan_policy="omit"), axis=1
    )

    # E — Geo-cluster via static lookup + KMeans
    df = _add_geo_cluster(df)

    return df


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------

def _add_geo_cluster(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map country_name → (lat, lon) via static lookup, then cluster with KMeans.
    Countries not found get geo_cluster = -1.
    """
    coords = df["country_name"].map(_COUNTRY_COORDS)
    has_coords = coords.notna()

    # Default lat/lon for missing entries
    df["_lat"] = 0.0
    df["_lon"] = 0.0
    df.loc[has_coords, "_lat"] = coords[has_coords].apply(lambda c: c[0])
    df.loc[has_coords, "_lon"] = coords[has_coords].apply(lambda c: c[1])

    # KMeans on (lat, lon)
    km = KMeans(n_clusters=CONFIG["kmeans_k"], random_state=CONFIG["random_state"], n_init=10)
    labels = km.fit_predict(df[["_lat", "_lon"]])
    df["geo_cluster"] = labels

    # Mark unknown countries as -1
    df.loc[~has_coords, "geo_cluster"] = -1

    # Log unknown countries for debugging
    unknown = df.loc[~has_coords, "country_name"].unique()
    if len(unknown) > 0:
        logger.warning("Could not geocode %d country names: %s", len(unknown), unknown[:10])

    df = df.drop(columns=["_lat", "_lon"])
    return df
