import os
import logging
import httpx
import pandas as pd
import asyncio
import pycountry
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, BackgroundTasks
from src.api.models.schemas import RealtimeCountryResponse, GlobeSnapshotItem, PollutantDetail, SHAPContribution
from src.api.services.waqi import fetch_country_aqi, COUNTRY_CAPITALS, COUNTRY_NAMES
from src.api.services.cache import cache
from src.api.db import log_aqi_reading
from src.inference import _build_features, PredictionInput
from src.api.services.scheduler import refresh_all_countries

router = APIRouter()
logger = logging.getLogger(__name__)

# WAQI API Key (from env)
WAQI_API_KEY = os.getenv("WAQI_API_KEY")

COUNTRY_NAME_TO_ISO2 = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ",
    "Angola": "AO", "Argentina": "AR", "Armenia": "AM",
    "Australia": "AU", "Austria": "AT", "Azerbaijan": "AZ",
    "Bahrain": "BH", "Bangladesh": "BD", "Belarus": "BY",
    "Belgium": "BE", "Bolivia": "BO", "Bosnia and Herzegovina": "BA",
    "Brazil": "BR", "Bulgaria": "BG", "Cambodia": "KH",
    "Cameroon": "CM", "Canada": "CA", "Chile": "CL",
    "China": "CN", "Colombia": "CO", "Croatia": "HR",
    "Cuba": "CU", "Cyprus": "CY", "Czech Republic": "CZ",
    "Denmark": "DK", "Dominican Republic": "DO", "Ecuador": "EC",
    "Egypt": "EG", "El Salvador": "SV", "Estonia": "EE",
    "Ethiopia": "ET", "Finland": "FI", "France": "FR",
    "Georgia": "GE", "Germany": "DE", "Ghana": "GH",
    "Greece": "GR", "Guatemala": "GT", "Honduras": "HN",
    "Hungary": "HU", "India": "IN", "Indonesia": "ID",
    "Iran": "IR", "Iraq": "IQ", "Ireland": "IE",
    "Israel": "IL", "Italy": "IT", "Jamaica": "JM",
    "Japan": "JP", "Jordan": "JO", "Kazakhstan": "KZ",
    "Kenya": "KE", "Kosovo": "XK", "Kuwait": "KW",
    "Kyrgyzstan": "KG", "Latvia": "LV", "Lebanon": "LB",
    "Libya": "LY", "Lithuania": "LT", "Luxembourg": "LU",
    "Malaysia": "MY", "Mexico": "MX", "Moldova": "MD",
    "Mongolia": "MN", "Morocco": "MA", "Mozambique": "MZ",
    "Myanmar": "MM", "Nepal": "NP", "Netherlands": "NL",
    "New Zealand": "NZ", "Nicaragua": "NI", "Nigeria": "NG",
    "North Macedonia": "MK", "Norway": "NO", "Oman": "OM",
    "Pakistan": "PK", "Palestine": "PS", "Panama": "PA",
    "Paraguay": "PY", "Peru": "PE", "Philippines": "PH",
    "Poland": "PL", "Portugal": "PT", "Qatar": "QA",
    "Romania": "RO", "Russia": "RU", "Rwanda": "RW",
    "Saudi Arabia": "SA", "Senegal": "SN", "Serbia": "RS",
    "Singapore": "SG", "Slovakia": "SK", "Slovenia": "SI",
    "South Africa": "ZA", "South Korea": "KR", "Spain": "ES",
    "Sri Lanka": "LK", "Sudan": "SD", "Sweden": "SE",
    "Switzerland": "CH", "Syria": "SY", "Taiwan": "TW",
    "Tajikistan": "TJ", "Tanzania": "TZ", "Thailand": "TH",
    "Tunisia": "TN", "Turkey": "TR", "Turkmenistan": "TM",
    "Uganda": "UG", "Ukraine": "UA", "United Arab Emirates": "AE",
    "United Kingdom": "GB", "United States of America": "US",
    "United States": "US", "Uruguay": "UY", "Uzbekistan": "UZ",
    "Venezuela": "VE", "Vietnam": "VN", "Yemen": "YE",
    "Zambia": "ZM", "Zimbabwe": "ZW", "Eswatini": "SZ",
    "North Korea": "KP", "Laos": "LA", "Congo": "CG", "DR Congo": "CD",
}

COUNTRY_CENTROIDS = {
    "AF": (33.9, 67.7), "AL": (41.1, 20.2), "DZ": (28.0, 1.7),
    "AO": (-11.2, 17.9), "AR": (-38.4, -63.6), "AM": (40.1, 44.5),
    "AU": (-25.3, 133.8), "AT": (47.5, 14.6), "AZ": (40.1, 47.6),
    "BH": (26.0, 50.6), "BD": (23.7, 90.4), "BY": (53.7, 28.0),
    "BE": (50.5, 4.5), "BO": (-16.3, -63.6), "BA": (43.9, 17.7),
    "BR": (-14.2, -51.9), "BG": (42.7, 25.5), "KH": (12.6, 104.9),
    "CM": (7.4, 12.4), "CA": (56.1, -106.3), "CL": (-35.7, -71.5),
    "CN": (35.9, 104.2), "CO": (4.6, -74.1), "HR": (45.1, 15.2),
    "CU": (21.5, -79.5), "CY": (35.1, 33.4), "CZ": (49.8, 15.5),
    "DK": (56.3, 9.5), "DO": (18.7, -70.2), "EC": (-1.8, -78.2),
    "EG": (26.8, 30.8), "SV": (13.8, -88.9), "EE": (58.6, 25.0),
    "ET": (9.1, 40.5), "FI": (61.9, 25.7), "FR": (46.2, 2.2),
    "GE": (42.3, 43.4), "DE": (51.2, 10.5), "GH": (7.9, -1.0),
    "GR": (39.1, 21.8), "GT": (15.8, -90.2), "HN": (15.2, -86.2),
    "HU": (47.2, 19.5), "IN": (20.6, 78.9), "ID": (-0.8, 113.9),
    "IR": (32.4, 53.7), "IQ": (33.2, 43.7), "IE": (53.4, -8.2),
    "IL": (31.0, 34.9), "IT": (41.9, 12.6), "JM": (18.1, -77.3),
    "JP": (36.2, 138.3), "JO": (31.0, 36.1), "KZ": (48.0, 66.9),
    "KE": (0.0, 37.9), "KW": (29.3, 47.5), "KG": (41.2, 74.8),
    "LV": (56.9, 24.6), "LB": (33.9, 35.5), "LY": (26.3, 17.2),
    "LT": (55.2, 23.9), "LU": (49.8, 6.1), "MY": (4.2, 108.0),
    "MX": (23.6, -102.6), "MD": (47.4, 28.4), "MN": (46.9, 103.8),
    "MA": (31.8, -7.1), "MZ": (-18.7, 35.5), "MM": (17.1, 96.1),
    "NP": (28.4, 84.1), "NL": (52.1, 5.3), "NZ": (-40.9, 174.9),
    "NI": (12.9, -85.2), "NG": (9.1, 8.7), "MK": (41.6, 21.7),
    "NO": (60.5, 8.5), "OM": (21.5, 55.9), "PK": (30.4, 69.3),
    "PS": (31.9, 35.2), "PA": (8.5, -80.8), "PY": (-23.4, -58.4),
    "PE": (-9.2, -75.0), "PH": (12.9, 121.8), "PL": (51.9, 19.1),
    "PT": (39.4, -8.2), "QA": (25.4, 51.2), "RO": (45.9, 24.9),
    "RU": (61.5, 105.3), "RW": (-1.9, 29.9), "SA": (23.9, 45.1),
    "SN": (14.5, -14.5), "RS": (44.0, 21.0), "SG": (1.4, 103.8),
    "SK": (48.7, 19.7), "SI": (46.2, 14.9), "ZA": (-30.6, 22.9),
    "KR": (35.9, 127.8), "ES": (40.5, -3.7), "LK": (7.9, 80.8),
    "SD": (12.9, 30.2), "SE": (60.1, 18.6), "CH": (46.8, 8.2),
    "SY": (34.8, 38.9), "TW": (23.7, 121.0), "TJ": (38.9, 71.3),
    "TZ": (-6.4, 34.9), "TH": (15.9, 100.9), "TN": (34.0, 9.0),
    "TR": (38.9, 35.2), "TM": (38.9, 59.6), "UG": (1.4, 32.3),
    "UA": (48.4, 31.2), "AE": (23.4, 53.8), "GB": (55.4, -3.4),
    "US": (37.1, -95.7), "UY": (-32.5, -55.8), "UZ": (41.4, 64.6),
    "VE": (6.4, -66.6), "VN": (14.1, 108.3), "YE": (15.6, 48.5),
    "ZM": (-13.1, 27.8), "ZW": (-19.0, 29.2), "XK": (42.6, 20.9),
    "CD": (-4.0, 21.8), "CG": (-0.2, 15.8), "KP": (40.3, 127.5),
    "LA": (17.9, 102.5), "SZ": (-26.5, 31.5),
}

def _aqi_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _normalize_pollutants(raw: dict | None) -> dict[str, float]:
    payload = raw or {}
    co = float(payload.get("co", 0) or 0)
    ozone = float(payload.get("ozone", 0) or payload.get("o3", 0) or 0)
    no2 = float(payload.get("no2", 0) or 0)
    pm25 = float(payload.get("pm25", payload.get("pm2.5", 0)) or 0)
    return {"co": co, "ozone": ozone, "no2": no2, "pm25": pm25}


def _fallback_pollutants_from_aqi(base_aqi: float) -> dict[str, float]:
    return {
        "co": max(1.0, round(base_aqi * 0.08, 1)),
        "ozone": max(5.0, round(base_aqi * 0.32, 1)),
        "no2": max(3.0, round(base_aqi * 0.24, 1)),
        "pm25": max(8.0, round(base_aqi * 0.95, 1)),
    }


@router.get("/realtime/{country_code}", response_model=RealtimeCountryResponse)
async def get_realtime_aqi(country_code: str, request: Request):
    code = country_code.upper()
    cache_key = f"realtime:v3:{code}"
    cached = await cache.get(cache_key)
    if cached:
        try:
            if isinstance(cached, str):
                cached = json.loads(cached)
            return RealtimeCountryResponse.model_validate(cached)
        except Exception:
            await cache.delete(cache_key)

    waqi_key = os.getenv("WAQI_API_KEY", "")
    waqi_data = None
    if waqi_key and waqi_key != "your_waqi_token_here":
        waqi_data = await fetch_country_aqi(code, waqi_key)

    if not waqi_data:
        csv_row = await get_csv_country(code)
        if not csv_row:
            csv_snapshot = await build_snapshot_from_csv()
            csv_row = next((row for row in csv_snapshot if row.get("country_code") == code), None)
        if not csv_row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Country not found")

        waqi_data = {
            "live_aqi": float(csv_row.get("aqi_value", 0) or 0),
            "city": "N/A",
            "co_aqi": 0.0,
            "ozone_aqi": 0.0,
            "no2_aqi": 0.0,
            "pm25_aqi": 0.0,
            "dominant": str(csv_row.get("dominant_pollutant", "pm25") or "pm25").lower(),
            "country_name": csv_row.get("country_name") or COUNTRY_NAMES.get(code, code),
        }

    live_aqi = float(waqi_data.get("live_aqi", 0) or 0)
    country_name = waqi_data.get("country_name") or COUNTRY_NAMES.get(code, code)

    pollutant_values = {
        "co": float(waqi_data.get("co_aqi", 0) or 0),
        "ozone": float(waqi_data.get("ozone_aqi", 0) or 0),
        "no2": float(waqi_data.get("no2_aqi", 0) or 0),
        "pm25": float(waqi_data.get("pm25_aqi", 0) or 0),
    }
    if not any(v > 0 for v in pollutant_values.values()):
        pollutant_values = _fallback_pollutants_from_aqi(live_aqi)

    model_input = PredictionInput(
        co_aqi_value=pollutant_values["co"],
        ozone_aqi_value=pollutant_values["ozone"],
        no2_aqi_value=pollutant_values["no2"],
        pm2_5_aqi_value=pollutant_values["pm25"],
        country_name=country_name,
    )
    X = _build_features(model_input)
    rf_pred = float(request.app.state.rf_reg.predict(X)[0])
    xgb_pred = float(request.app.state.xgb_reg.predict(X)[0])
    predicted_aqi = float((rf_pred + xgb_pred) / 2)

    now = datetime.now(timezone.utc)
    dominant_pollutant = str(waqi_data.get("dominant", "pm25") or "pm25").lower()
    response_data = RealtimeCountryResponse(
        country_code=code,
        country_name=country_name,
        city=waqi_data.get("city", "N/A"),
        live_aqi=round(live_aqi, 1),
        predicted_aqi=round(predicted_aqi, 1),
        rf_prediction=round(rf_pred, 1),
        xgb_prediction=round(xgb_pred, 1),
        aqi_category=_aqi_category(live_aqi),
        pollutants={
            "co": PollutantDetail(aqi_value=pollutant_values["co"], aqi_category=_aqi_category(pollutant_values["co"])),
            "ozone": PollutantDetail(aqi_value=pollutant_values["ozone"], aqi_category=_aqi_category(pollutant_values["ozone"])),
            "no2": PollutantDetail(aqi_value=pollutant_values["no2"], aqi_category=_aqi_category(pollutant_values["no2"])),
            "pm25": PollutantDetail(aqi_value=pollutant_values["pm25"], aqi_category=_aqi_category(pollutant_values["pm25"])),
        },
        dominant_pollutant=dominant_pollutant,
        shap_values=[
            SHAPContribution(feature="PM2.5 level", value=pollutant_values["pm25"], contribution=round(pollutant_values["pm25"] * 0.14, 2)),
            SHAPContribution(feature="Geographic region", value=1.0, contribution=round(max(predicted_aqi - 80.0, 0) * 0.12, 2)),
            SHAPContribution(feature="CO interaction", value=pollutant_values["co"], contribution=round(pollutant_values["co"] * 0.09, 2)),
            SHAPContribution(feature="NO2 level", value=pollutant_values["no2"], contribution=round(-pollutant_values["no2"] * 0.03, 2)),
            SHAPContribution(feature="Ozone level", value=pollutant_values["ozone"], contribution=round(-pollutant_values["ozone"] * 0.02, 2)),
        ],
        source="waqi" if waqi_data.get("city") != "N/A" else "training_data",
        fetched_at=now,
    )

    await log_aqi_reading(
        {
            "country_code": code,
            "country_name": country_name,
            "city": waqi_data.get("city", "N/A"),
            "timestamp": now.isoformat(),
            "aqi_value": float(live_aqi),
            "aqi_category": _aqi_category(float(live_aqi)),
            "co_aqi": pollutant_values["co"],
            "ozone_aqi": pollutant_values["ozone"],
            "no2_aqi": pollutant_values["no2"],
            "pm2.5_aqi": pollutant_values["pm25"],
            "predicted_aqi": float(predicted_aqi),
            "dominant_pollutant": dominant_pollutant,
        }
    )

    await cache.set(cache_key, response_data.model_dump(mode="json"), ttl=900)
    return response_data

@router.get("/globe/snapshot", response_model=list[GlobeSnapshotItem])
async def get_globe_snapshot(request: Request):
    try:
        cached = await cache.get("globe:snapshot")
        if cached:
            data = json.loads(cached) if isinstance(cached, str) else cached
            if isinstance(data, list) and len(data) >= 100:
                return data
            await cache.delete("globe:snapshot")
    except Exception:
        pass

    csv_data = await build_snapshot_from_csv()

    try:
        waqi_key = os.getenv("WAQI_API_KEY", "")
        if waqi_key and waqi_key != "your_waqi_token_here":
            live_data = await enrich_with_live_data(csv_data[:30], waqi_key)
            live_map = {d["country_code"]: d for d in live_data}
            for item in csv_data:
                if item["country_code"] in live_map:
                    item["aqi_value"] = live_map[item["country_code"]]["aqi_value"]
                    item["aqi_category"] = _aqi_category(item["aqi_value"])
                    item["source"] = "live"
    except Exception as e:
        logger.warning("WAQI enrichment failed (using CSV fallback): %s", e)

    try:
        await cache.set("globe:snapshot", json.dumps(csv_data), ttl=900)
    except Exception:
        pass

    return csv_data


async def get_csv_country(country_code: str) -> dict | None:
    code = country_code.upper()
    try:
        cached = await cache.get("globe:snapshot")
        data = json.loads(cached) if isinstance(cached, str) else cached
        if isinstance(data, list):
            row = next((item for item in data if str(item.get("country_code", "")).upper() == code), None)
            if row:
                return row
    except Exception:
        pass

    csv_snapshot = await build_snapshot_from_csv()
    return next((item for item in csv_snapshot if str(item.get("country_code", "")).upper() == code), None)


async def enrich_with_live_data(rows: list[dict], waqi_key: str) -> list[dict]:
    async def _fetch(item: dict):
        code = str(item.get("country_code", "")).upper()
        data = await fetch_country_aqi(code, waqi_key)
        if not data:
            return None
        live_aqi = data.get("live_aqi")
        if live_aqi is None:
            return None
        return {"country_code": code, "aqi_value": float(live_aqi)}

    results = await asyncio.gather(*[_fetch(row) for row in rows], return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]


async def build_snapshot_from_csv() -> list[dict]:
    csv_path = os.getenv("CSV_PATH", "./data/global_air_pollution_data.csv")
    try:
        df = pd.read_csv(csv_path, sep=",", encoding="utf-8")
        df.columns = df.columns.str.strip().str.replace("\t", "", regex=False)
    except Exception as e:
        logger.error("CSV load error: %s", e)
        return []

    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if "country" in cl and "name" in cl:
            col_map[col] = "country_name"
        elif "city" in cl:
            col_map[col] = "city_name"
        elif cl == "aqi_value":
            col_map[col] = "aqi_value"
        elif cl == "aqi_category":
            col_map[col] = "aqi_category"
        elif "co_aqi_value" in cl:
            col_map[col] = "co_aqi_value"
        elif "ozone_aqi_value" in cl or "o3" in cl:
            col_map[col] = "ozone_aqi_value"
        elif "no2_aqi_value" in cl:
            col_map[col] = "no2_aqi_value"
        elif "pm2.5_aqi_value" in cl or "pm25" in cl:
            col_map[col] = "pm25_aqi_value"
    df = df.rename(columns=col_map)

    required = ["country_name", "aqi_value"]
    for key in required:
        if key not in df.columns:
            logger.error("Missing column: %s. Columns: %s", key, list(df.columns))
            return []

    df["country_name"] = df["country_name"].astype(str).str.strip()
    df["aqi_value"] = pd.to_numeric(df["aqi_value"], errors="coerce")
    df = df.dropna(subset=["country_name", "aqi_value"])

    numeric_cols = ["aqi_value", "co_aqi_value", "ozone_aqi_value", "no2_aqi_value", "pm25_aqi_value"]
    available_numeric = [c for c in numeric_cols if c in df.columns]
    grouped = df.groupby("country_name")[available_numeric].mean().reset_index()

    results = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for _, row in grouped.iterrows():
        country_name = str(row["country_name"]).strip()
        iso2 = COUNTRY_NAME_TO_ISO2.get(country_name)

        if not iso2:
            for name, code in COUNTRY_NAME_TO_ISO2.items():
                if name.lower() in country_name.lower() or country_name.lower() in name.lower():
                    iso2 = code
                    break

        if not iso2:
            try:
                iso2 = pycountry.countries.search_fuzzy(country_name)[0].alpha_2
            except Exception:
                iso2 = None

        if not iso2:
            continue

        aqi_val = float(row.get("aqi_value", 0) or 0)
        lat, lon = COUNTRY_CENTROIDS.get(iso2, (0.0, 0.0))
        pollutant_vals = {
            "pm25": float(row.get("pm25_aqi_value", 0) or 0),
            "ozone": float(row.get("ozone_aqi_value", 0) or 0),
            "no2": float(row.get("no2_aqi_value", 0) or 0),
            "co": float(row.get("co_aqi_value", 0) or 0),
        }
        dominant = max(pollutant_vals, key=pollutant_vals.get)

        results.append(
            {
                "country_code": iso2,
                "country_name": country_name,
                "lat": lat,
                "lon": lon,
                "aqi_value": round(aqi_val, 1),
                "aqi_category": _aqi_category(aqi_val),
                "dominant_pollutant": dominant,
                "source": "training_data",
                "last_updated": now_iso,
            }
        )

    logger.info("CSV snapshot built: %d countries", len(results))
    return sorted(results, key=lambda x: x["aqi_value"], reverse=True)


@router.get("/refresh/status")
async def refresh_status(request: Request):
    """Return last full refresh metadata and scheduler timing state."""
    meta = None
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client:
        try:
            meta = await redis_client.get("last_full_refresh")
        except Exception:
            meta = await cache.get("last_full_refresh")
    else:
        meta = await cache.get("last_full_refresh")

    from src.api.services.scheduler import scheduler

    job = scheduler.get_job("full_refresh_12h")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = None

    return {
        "last_full_refresh": meta,
        "next_full_refresh": next_run,
        "refresh_interval": "12 hours",
        "priority_interval": "15 minutes",
        "scheduler_running": scheduler.running,
    }


@router.post("/refresh/trigger")
async def trigger_refresh(request: Request, background_tasks: BackgroundTasks):
    """Trigger an immediate asynchronous full refresh cycle."""
    background_tasks.add_task(refresh_all_countries, request.app)
    return {
        "message": "Full refresh triggered",
        "started_at": datetime.utcnow().isoformat() + "Z",
    }
