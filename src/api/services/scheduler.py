import os
import json
import asyncio
import logging
from datetime import datetime, timezone

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.api.services.cache import cache
from src.api.services.waqi import fetch_country_aqi, COUNTRY_NAMES
from src.api.routes.websocket import broadcast_update
from src.inference import PredictionInput, _build_features

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")

PRIORITY_COUNTRIES = [
    "IN", "PK", "BD", "NP", "MM", "KH", "VN", "ID", "PH", "TH",
    "IQ", "IR", "KW", "SA", "AE", "KZ", "UZ", "TJ", "MN", "AF",
    "NG", "GH", "ET", "EG", "SD", "KE", "CM", "SN", "ZW", "ZM",
]


def _aqi_to_category(aqi: float) -> str:
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _redis_set(app, key: str, value: dict | list, ttl: int | None = None):
    redis_client = getattr(app.state, "redis", None)
    payload = json.dumps(value, default=str)
    if redis_client:
        try:
            if ttl:
                await redis_client.set(key, payload, ex=ttl)
            else:
                await redis_client.set(key, payload)
            return
        except Exception as exc:
            logger.warning("Redis set failed for %s, fallback to cache: %s", key, exc)
    await cache.set(key, value, ttl=ttl or 900)


async def _redis_get(app, key: str):
    redis_client = getattr(app.state, "redis", None)
    if redis_client:
        try:
            return await redis_client.get(key)
        except Exception:
            return await cache.get(key)
    return await cache.get(key)


async def _load_country_codes() -> list[str]:
    # Derive all countries from the CSV-backed snapshot builder (176+ coverage).
    from src.api.routes.realtime import build_snapshot_from_csv

    rows = await build_snapshot_from_csv()
    codes = [str(row.get("country_code", "")).upper() for row in rows if row.get("country_code")]
    return sorted(set(codes))


def init_scheduler(app):
    """Call from FastAPI startup to register and start background refresh jobs."""
    scheduler.add_job(
        func=refresh_all_countries,
        trigger=CronTrigger(hour="0,12", minute=0, timezone="UTC"),
        id="full_refresh_12h",
        name="12-hour full country refresh",
        replace_existing=True,
        args=[app],
        misfire_grace_time=300,
        coalesce=True,
    )

    scheduler.add_job(
        func=refresh_priority_countries,
        trigger=IntervalTrigger(minutes=15),
        id="priority_refresh_15m",
        name="15-min priority country refresh",
        replace_existing=True,
        args=[app],
        misfire_grace_time=60,
    )

    scheduler.add_job(
        func=refresh_all_countries,
        trigger="date",
        id="startup_refresh",
        name="Startup refresh",
        args=[app],
        misfire_grace_time=600,
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler started: 12h full refresh + 15m priority refresh")


async def refresh_all_countries(app):
    """12h job: refresh all countries, cache snapshot, persist history, broadcast updates."""
    start_time = datetime.utcnow()
    logger.info("[%s] Starting 12h full refresh...", start_time.isoformat() + "Z")

    waqi_key = os.getenv("WAQI_API_KEY", "")
    results: list[dict] = []
    errors: list[str] = []

    countries = await _load_country_codes()
    batch_size = 10
    for i in range(0, len(countries), batch_size):
        batch = countries[i : i + batch_size]
        tasks = [refresh_single_country(app, code, waqi_key) for code in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for code, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                errors.append(code)
                logger.warning("Failed %s: %s", code, result)
            elif result:
                results.append(result)
            else:
                errors.append(code)

        await asyncio.sleep(1.0)

    if results:
        snapshot = await build_globe_snapshot(results)
        await _redis_set(app, "globe:snapshot", snapshot, ttl=43200)
        await broadcast_update(app, snapshot)

    end_time = datetime.utcnow()
    duration = int((end_time - start_time).total_seconds())
    logger.info(
        "12h refresh complete: %d updated, %d failed, took %ss",
        len(results),
        len(errors),
        duration,
    )

    await _redis_set(
        app,
        "last_full_refresh",
        {
            "timestamp": end_time.isoformat() + "Z",
            "countries_ok": len(results),
            "countries_fail": len(errors),
            "duration_sec": duration,
            "failed_codes": errors,
        },
    )


async def refresh_priority_countries(app):
    """15m job: refresh the most pollution-sensitive country subset."""
    waqi_key = os.getenv("WAQI_API_KEY", "")
    results: list[dict] = []

    tasks = [refresh_single_country(app, code, waqi_key) for code in PRIORITY_COUNTRIES]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for code, result in zip(PRIORITY_COUNTRIES, batch_results):
        if result and not isinstance(result, Exception):
            results.append(result)
            await _redis_set(app, f"realtime:v3:{code}", result, ttl=900)

    if results:
        await broadcast_update(app, results)
        logger.info("15m priority refresh: %d/30 updated", len(results))


async def refresh_single_country(app, country_code: str, waqi_key: str):
    """Fetch live AQI + run RF/XGB prediction for a single country code."""
    waqi_data = await fetch_country_aqi(country_code, waqi_key)
    if not waqi_data:
        return None

    inp = PredictionInput(
        co_aqi_value=float(waqi_data.get("co_aqi", 0) or 0),
        ozone_aqi_value=float(waqi_data.get("ozone_aqi", 0) or 0),
        no2_aqi_value=float(waqi_data.get("no2_aqi", 0) or 0),
        **{"pm2.5_aqi_value": float(waqi_data.get("pm25_aqi", 0) or 0)},
        country_name=get_country_name(country_code),
    )

    X = _build_features(inp)
    rf_pred = float(app.state.rf_reg.predict(X)[0])
    xgb_pred = float(app.state.xgb_reg.predict(X)[0])
    predicted = (rf_pred + xgb_pred) / 2

    result = {
        "country_code": country_code,
        "country_name": get_country_name(country_code),
        "city": waqi_data.get("city", "N/A"),
        "live_aqi": round(float(waqi_data.get("live_aqi", 0) or 0), 1),
        "predicted_aqi": round(predicted, 1),
        "rf_prediction": round(rf_pred, 1),
        "xgb_prediction": round(xgb_pred, 1),
        "aqi_category": _aqi_to_category(float(waqi_data.get("live_aqi", 0) or 0)),
        "dominant_pollutant": waqi_data.get("dominant", "pm25"),
        "source": "waqi",
        "fetched_at": _now_iso(),
    }

    await _redis_set(app, f"realtime:v3:{country_code}", result, ttl=900)
    await save_to_history(result, waqi_data)
    return result


async def build_globe_snapshot(updated_rows: list[dict]) -> list[dict]:
    """Merge latest realtime updates into full CSV snapshot for complete globe coverage."""
    from src.api.routes.realtime import build_snapshot_from_csv

    base = await build_snapshot_from_csv()
    updates = {row.get("country_code"): row for row in updated_rows if row.get("country_code")}
    for row in base:
        code = row.get("country_code")
        upd = updates.get(code)
        if not upd:
            continue
        row["aqi_value"] = upd.get("live_aqi", row.get("aqi_value"))
        row["aqi_category"] = upd.get("aqi_category", row.get("aqi_category"))
        row["dominant_pollutant"] = upd.get("dominant_pollutant", row.get("dominant_pollutant"))
        row["source"] = "live"
        row["last_updated"] = upd.get("fetched_at", _now_iso())
    return base


def get_country_name(country_code: str) -> str:
    return COUNTRY_NAMES.get(country_code.upper(), country_code.upper())


async def save_to_history(result: dict, waqi_data: dict):
    """Store each country refresh sample in SQLite for trend tracking."""
    db_path = os.getenv("DB_PATH", "./data/aqi_history.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO aqi_history
            (country_code, country_name, city, timestamp,
             aqi_value, aqi_category, co_aqi, ozone_aqi,
             no2_aqi, pm25_aqi, predicted_aqi, dominant_pollutant)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                result["country_code"],
                result["country_name"],
                result["city"],
                result["fetched_at"],
                result["live_aqi"],
                result["aqi_category"],
                float(waqi_data.get("co_aqi", 0) or 0),
                float(waqi_data.get("ozone_aqi", 0) or 0),
                float(waqi_data.get("no2_aqi", 0) or 0),
                float(waqi_data.get("pm25_aqi", 0) or 0),
                result["predicted_aqi"],
                result["dominant_pollutant"],
            ),
        )
        await db.commit()
