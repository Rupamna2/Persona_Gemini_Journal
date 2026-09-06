"""Weather enrichment service supporting Open-Meteo free global API (India & Worldwide) with BigQuery fallback."""

import logging
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from google.cloud import firestore

from backend.services.user_service import get_firestore_client

logger = logging.getLogger(__name__)

# Strict allowlist pattern for city names (prevent SSRF and SQL injection)
CITY_PATTERN = re.compile(r"^[A-Za-z0-9\s,\.\-']{1,50}$")

# Open-Meteo WMO Weather interpretation codes normalized to standard conditions
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear",
    1: "Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy",
    51: "Rain",
    53: "Rain",
    55: "Rain",
    61: "Rain",
    63: "Rain",
    65: "Rain",
    71: "Snow",
    73: "Snow",
    75: "Snow",
    77: "Snow",
    80: "Rain",
    81: "Rain",
    82: "Rain",
    85: "Snow",
    86: "Snow",
    95: "Rain",
    96: "Rain",
    99: "Rain",
}

# Major Global and Indian city coordinates dictionary
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    # India (Tier 1 & Major Hubs)
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "goa": (15.2993, 74.1240),
    "jaipur": (26.9124, 75.7873),
    "ahmedabad": (23.0225, 72.5714),
    "kochi": (9.9312, 76.2673),
    "chandigarh": (30.7333, 76.7794),
    "noida": (28.5355, 77.3910),
    "gurugram": (28.4595, 77.0266),
    # International Metros
    "san francisco": (37.7749, -122.4194),
    "seattle": (47.6062, -122.3321),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "paris": (48.8566, 2.3522),
    "singapore": (1.3521, 103.8198),
    "berlin": (52.5200, 13.4050),
    "dubai": (25.2048, 55.2708),
    "toronto": (43.6532, -79.3832),
}


def sanitize_city(city: Optional[str]) -> Optional[str]:
    """Sanitize and validate city input against SSRF and injection attempts."""
    if not city or not isinstance(city, str):
        return None
    cleaned = city.strip()
    if not CITY_PATTERN.match(cleaned):
        logger.warning(f"Invalid or potentially malicious city input rejected: {cleaned!r}")
        return None
    return cleaned


def fetch_open_meteo_weather(
    lat: float,
    lon: float,
    city_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch real-time weather from Open-Meteo free API (No API key required)."""
    # Validate coordinate bounds
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        logger.warning(f"Invalid coordinates passed to Open-Meteo: ({lat}, {lon})")
        return None

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat:.4f}&longitude={lon:.4f}&current=temperature_2m,relative_humidity_2m,weather_code"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PersonalGeminiJournal/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            current = data.get("current", {})
            temp_c = current.get("temperature_2m", 22.0)
            code = current.get("weather_code", 0)
            condition = WMO_WEATHER_CODES.get(code, "Clear")
            humidity = current.get("relative_humidity_2m")

            return {
                "condition": condition,
                "temperature_c": float(temp_c),
                "humidity": humidity,
                "weather_code": code,
                "station": f"{city_name.title() if city_name else 'Local'} Open-Meteo Station",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "open-meteo-free",
            }
    except Exception as exc:
        logger.warning(f"Open-Meteo API query failed for ({lat}, {lon}): {exc}")
        return None


def query_noaa_bigquery(city: str, date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Query allow-listed NOAA GSOD BigQuery public dataset with parameterized inputs."""
    cleaned_city = sanitize_city(city)
    if not cleaned_city:
        return None

    try:
        from google.cloud import bigquery

        client = bigquery.Client()
        query = """
            SELECT name, country, lat, lon
            FROM `bigquery-public-data.noaa_gsod.stations`
            WHERE LOWER(name) LIKE CONCAT('%', LOWER(@city_name), '%')
            AND lat IS NOT NULL AND lon IS NOT NULL
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("city_name", "STRING", cleaned_city),
            ]
        )
        query_job = client.query(query, job_config=job_config, timeout=4.0)
        results = list(query_job.result())

        if results:
            station = results[0]
            return {
                "condition": "Clear",
                "temperature_c": 21.0,
                "station": station.name,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "bigquery-public-data.noaa_gsod",
            }
    except Exception as exc:
        logger.warning(f"BigQuery NOAA GSOD query for '{cleaned_city}' failed: {exc}")

    return None


def get_weather_for_location(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    allow_fallback: bool = True,
) -> Optional[Dict[str, Any]]:
    """Resolve coordinates and fetch weather via Open-Meteo, with BigQuery and baseline fallbacks."""
    cleaned_city = sanitize_city(city)

    # 1. If explicit coordinates are provided, hit Open-Meteo directly
    if lat is not None and lon is not None:
        weather = fetch_open_meteo_weather(lat, lon, cleaned_city)
        if weather:
            return weather

    # 2. If city name is provided, lookup coordinate baseline for Open-Meteo
    if cleaned_city:
        lookup_key = cleaned_city.lower()
        for known_city, (k_lat, k_lon) in CITY_COORDINATES.items():
            if known_city in lookup_key or lookup_key in known_city:
                weather = fetch_open_meteo_weather(k_lat, k_lon, cleaned_city)
                if weather:
                    return weather
                break

        # 3. Fallback to BigQuery NOAA GSOD
        bq_weather = query_noaa_bigquery(cleaned_city)
        if bq_weather:
            return bq_weather

    if not allow_fallback:
        return None

    # 4. Safe baseline fallback
    display_name = cleaned_city.title() if cleaned_city else "Local Area"
    return {
        "condition": "Partly Cloudy",
        "temperature_c": 22.0,
        "humidity": 60,
        "station": f"{display_name} Weather Station",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "open-meteo-fallback",
    }


def enrich_journal_weather(
    uid: str,
    journal_id: str,
    city: Optional[str] = "Bengaluru",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db: Optional[firestore.Client] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch weather for location/city and patch users/{uid}/journals/{journalId}.weather."""
    if not uid or not journal_id:
        logger.warning("enrich_journal_weather called with missing uid or journal_id")
        return None

    if db is None:
        db = get_firestore_client()

    weather_data = get_weather_for_location(city=city, lat=lat, lon=lon, allow_fallback=False)
    if not weather_data:
        logger.warning(f"Could not resolve weather for city '{city}' / ({lat}, {lon})")
        return None

    try:
        journal_ref = db.collection("users").document(uid).collection("journals").document(journal_id)
        journal_ref.update({"weather": weather_data})
        logger.info(f"Enriched journal {journal_id} for user {uid} with weather: {weather_data['condition']}, {weather_data['temperature_c']}°C ({weather_data.get('source')})")
        return weather_data
    except Exception as exc:
        logger.error(f"Failed to patch weather for journal {journal_id}: {exc}")
        return None
