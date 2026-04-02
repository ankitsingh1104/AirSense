import httpx
import logging
from typing import Optional, Dict, Any
import pycountry

logger = logging.getLogger(__name__)

WAQI_BASE = "https://api.waqi.info"

# Mapping for 50+ major countries to their capital city (for feed endpoint)
COUNTRY_CAPITALS = {
    "AF": "Kabul", "AL": "Tirana", "DZ": "Algiers", "AR": "Buenos Aires",
    "AU": "Canberra", "AT": "Vienna", "BD": "Dhaka", "BE": "Brussels",
    "BR": "Brasilia", "CA": "Ottawa", "CL": "Santiago", "CN": "Beijing",
    "CO": "Bogota", "EG": "Cairo", "FI": "Helsinki", "FR": "Paris",
    "DE": "Berlin", "GR": "Athens", "HU": "Budapest", "IS": "Reykjavik",
    "IN": "New Delhi", "ID": "Jakarta", "IR": "Tehran", "IQ": "Baghdad",
    "IE": "Dublin", "IL": "Jerusalem", "IT": "Rome", "JP": "Tokyo",
    "KZ": "Astana", "KE": "Nairobi", "KW": "Kuwait City", "MY": "Kuala Lumpur",
    "MX": "Mexico City", "MA": "Rabat", "NL": "Amsterdam", "NZ": "Wellington",
    "NG": "Abuja", "NO": "Oslo", "PK": "Islamabad", "PE": "Lima",
    "PH": "Manila", "PL": "Warsaw", "PT": "Lisbon", "QA": "Doha",
    "RO": "Bucharest", "RU": "Moscow", "SA": "Riyadh", "SG": "Singapore",
    "ZA": "Pretoria", "KR": "Seoul", "ES": "Madrid", "LK": "Colombo",
    "SE": "Stockholm", "CH": "Bern", "TW": "Taipei", "TH": "Bangkok",
    "TR": "Ankara", "UA": "Kyiv", "AE": "Abu Dhabi", "GB": "London",
    "US": "Washington", "VN": "Hanoi"
}

# Mapping for common country codes to full names (for predictions & UI)
COUNTRY_NAMES = {
    "IN": "India", "CN": "China", "US": "United States", "GB": "United Kingdom",
    "FR": "France", "DE": "Germany", "JP": "Japan", "PK": "Pakistan",
    "BR": "Brazil", "BD": "Bangladesh", "RU": "Russia", "ID": "Indonesia",
    "EG": "Egypt", "NG": "Nigeria"
}

async def fetch_city_aqi(city: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Fetch realtime AQI for a city from WAQI."""
    url = f"{WAQI_BASE}/feed/{city}/?token={api_key}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            if data.get("status") == "ok":
                return _normalize_waqi_data(data["data"])
            logger.warning("WAQI fetch failed for %s: %s", city, data.get("data"))
            return None
        except Exception as e:
            logger.error("WAQI API Error for %s: %s", city, str(e))
            return None

async def fetch_country_aqi(country_code: str, api_key: str) -> Optional[Dict[str, Any]]:
    code = country_code.upper()
    city = COUNTRY_CAPITALS.get(code)
    country_name = _country_name_from_iso(code)

    async with httpx.AsyncClient(timeout=10.0) as client:
        raw = None

        if city:
            url = f"{WAQI_BASE}/feed/{city}/?token={api_key}"
            try:
                resp = await client.get(url)
                raw = resp.json()
            except Exception as e:
                logger.warning("WAQI fetch error for %s via capital '%s': %s", code, city, e)

        # Fallback path: search stations by country name and resolve via station uid.
        if not raw or raw.get("status") != "ok":
            query = country_name or city or code
            search_url = f"{WAQI_BASE}/search/?token={api_key}&keyword={query}"
            try:
                search_resp = await client.get(search_url)
                search_raw = search_resp.json()
                stations = search_raw.get("data", []) if isinstance(search_raw, dict) else []
                if stations:
                    uid = stations[0].get("uid")
                    station_name = stations[0].get("station", {}).get("name")
                    if uid:
                        feed_url = f"{WAQI_BASE}/feed/@{uid}/?token={api_key}"
                        feed_resp = await client.get(feed_url)
                        raw = feed_resp.json()
                        if station_name:
                            raw.setdefault("data", {}).setdefault("city", {}).setdefault("name", station_name)
            except Exception as e:
                logger.warning("WAQI search fallback failed for %s (%s): %s", code, query, e)

    if raw.get("status") != "ok":
        logger.warning("WAQI bad status for %s: %s", code, raw.get("status") if raw else "no_response")
        return None

    data = raw.get("data", {})
    live_aqi = data.get("aqi")
    if live_aqi is None or live_aqi == "-":
        return None

    iaqi = data.get("iaqi", {})
    # WAQI iaqi values are already AQI sub-indices (0-500), not raw concentrations
    return {
        "country_code": code,
        "country_name": COUNTRY_NAMES.get(code, country_name or code),
        "live_aqi": float(live_aqi),
        "city": data.get("city", {}).get("name", city or country_name or code),
        "co_aqi": float(iaqi.get("co", {}).get("v", 0) or 0),
        "ozone_aqi": float(iaqi.get("o3", {}).get("v", 0) or 0),
        "no2_aqi": float(iaqi.get("no2", {}).get("v", 0) or 0),
        "pm25_aqi": float(iaqi.get("pm25", {}).get("v", 0) or 0),
        "dominant": data.get("dominentpol", "pm25"),
    }


def _country_name_from_iso(country_code: str) -> Optional[str]:
    if country_code in COUNTRY_NAMES:
        return COUNTRY_NAMES[country_code]
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            return country.name
    except Exception:
        return None
    return None

def _normalize_waqi_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Processes WAQI raw response into our standard model input format."""
    # WAQI iaqi values are already AQI sub-indices (0-500 scale)
    iaqi = raw.get("iaqi", {})
    
    return {
        "city": raw.get("city", {}).get("name", "Unknown"),
        "aqi_value": float(raw.get("aqi", 0)),
        "dominant_pollutant": raw.get("dominentpol", "unknown"),
        "pollutants": {
            "co": float(iaqi.get("co", {}).get("v", 0) or 0),
            "ozone": float(iaqi.get("o3", {}).get("v", 0) or 0),
            "no2": float(iaqi.get("no2", {}).get("v", 0) or 0),
            "pm2.5": float(iaqi.get("pm25", {}).get("v", 0) or 0)
        },
        "last_updated": raw.get("time", {}).get("s", "unknown")
    }
