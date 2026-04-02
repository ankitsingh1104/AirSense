#!/usr/bin/env python
"""Test model predictions on variety of AQI inputs."""

import joblib
import numpy as np
from scipy.stats import skew, kurtosis
from xgboost import XGBRegressor

# Country coordinates for geo-clustering (simplified)
COUNTRY_COORDS = {
    'India': (20.5937, 78.9629),
    'United States': (37.0902, -95.7129),
    'China': (35.8617, 104.1954),
}

# Load models and preprocessing objects
rf = joblib.load('models/rf_regressor.joblib')
xgb = XGBRegressor()
xgb.load_model('models/xgb_regressor.json')
scaler = joblib.load('models/scaler.joblib')
feature_names = joblib.load('models/feature_names.joblib')

# Test cases
tests = [
    {'label': 'India  (live=72)', 'co': 5, 'o3': 40, 'no2': 20, 'pm25': 72, 'country': 'India'},
    {'label': 'USA    (live=41)', 'co': 1, 'o3': 41, 'no2': 10, 'pm25': 20, 'country': 'United States'},
    {'label': 'China  (live=78)', 'co': 3, 'o3': 30, 'no2': 25, 'pm25': 78, 'country': 'China'},
    {'label': 'High AQI (152)', 'co': 8, 'o3': 42, 'no2': 35, 'pm25': 152, 'country': 'India'},
    {'label': 'Extreme (300)', 'co': 20, 'o3': 80, 'no2': 60, 'pm25': 300, 'country': 'China'},
]

def build_features(co, o3, no2, pm25, country):
    """Build feature vector for single sample (matching inference.py _build_features)."""
    vals = [co, o3, no2, pm25]
    
    features = {}
    # Raw pollutant values
    features['co_aqi_value'] = co
    features['ozone_aqi_value'] = o3
    features['no2_aqi_value'] = no2
    features['pm2.5_aqi_value'] = pm25
    
    # Derived features
    features['pollutant_std'] = float(np.std(vals, ddof=1))
    
    p_max = max(vals)
    features['pollutant_max'] = p_max
    features['dominance_ratio'] = p_max / (sum(vals) + 1e-6)
    
    # Dominant pollutant (label-encoded: co=0, no2=1, ozone=2, pm2.5=3)
    names = ['co', 'ozone', 'no2', 'pm2.5']
    values = [co, o3, no2, pm25]
    dominant_idx = int(np.argmax(values))
    dominant_name = names[dominant_idx]
    le_map = {'co': 0, 'no2': 1, 'ozone': 2, 'pm2.5': 3}
    features['dominant_pollutant'] = le_map.get(dominant_name, 0)
    
    # Interactions
    features['co_no2_interaction'] = co * no2
    features['pm_ozone_interaction'] = pm25 * o3
    
    # Statistical features
    features['pollutant_skew'] = float(skew(vals))
    features['pollutant_kurtosis'] = float(kurtosis(vals))
    
    # Geo cluster (simplified: default to 0 for inference)
    for i in range(0, 6):
        features[f'geo_cluster_{i}'] = 0  # All clusters off (equivalent to drop_first=True with cluster 0)
    features['geo_cluster_0'] = 0  # Explicitly keep geo_cluster_0 since we don't drop it here
    
    # But feature_names expects geo_cluster_1 through geo_cluster_5 (drop_first=True)
    for i in range(1, 6):
        features[f'geo_cluster_{i}'] = 0
    
    # Build row in feature_names order
    row = []
    for fn in feature_names:
        row.append(features.get(fn, 0.0))
    
    return np.array([row])

print(f"{'Label':<25} {'RF':>8} {'XGB':>8} {'Avg':>8} {'Live':>8} {'Diff':>8}")
print('-' * 70)

for t in tests:
    # Build features
    X = build_features(t['co'], t['o3'], t['no2'], t['pm25'], t['country'])
    
    # Scale
    X_scaled = scaler.transform(X)
    
    # Predict
    rf_p = rf.predict(X_scaled)[0]
    xgb_p = xgb.predict(X_scaled)[0]
    avg = (rf_p + xgb_p) / 2
    live = t['pm25']
    
    print(f"{t['label']:<25} {rf_p:>8.1f} {xgb_p:>8.1f} {avg:>8.1f} {live:>8.1f} {avg-live:>+8.1f}")
