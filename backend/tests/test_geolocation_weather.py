"""Unit tests for Unit 19: Geo-Location Memory & Location-Mood Happiness Predictor with Open-Meteo Weather."""

import pytest
from unittest.mock import patch, MagicMock
from backend.services.weather_enrichment import (
    get_weather_for_location,
    fetch_open_meteo_weather,
    sanitize_city,
    WMO_WEATHER_CODES,
    CITY_COORDINATES,
)
from backend.routes.save import LocationInput
from backend.agents.analytics_agent import aggregate_journal_patterns, generate_pattern_insights


def test_city_coordinates_map():
    """Verify Indian and global metro coordinate coverage in dictionary."""
    assert "bengaluru" in CITY_COORDINATES
    assert CITY_COORDINATES["bengaluru"][0] == pytest.approx(12.9716, rel=1e-2)

    assert "mumbai" in CITY_COORDINATES
    assert CITY_COORDINATES["mumbai"][0] == pytest.approx(19.0760, rel=1e-2)

    assert "delhi" in CITY_COORDINATES
    assert "san francisco" in CITY_COORDINATES
    assert "london" in CITY_COORDINATES


def test_wmo_code_resolution():
    """Verify WMO weather codes match human-readable labels."""
    assert WMO_WEATHER_CODES[0] == "Clear"
    assert WMO_WEATHER_CODES[3] == "Overcast"
    assert WMO_WEATHER_CODES[61] == "Rain"
    assert WMO_WEATHER_CODES[95] == "Rain"


def test_sanitize_city():
    """Verify city name sanitization against injection and bad input."""
    assert sanitize_city("Bengaluru, Karnataka") == "Bengaluru, Karnataka"
    assert sanitize_city("San Francisco") == "San Francisco"
    assert sanitize_city("   Mumbai   ") == "Mumbai"
    assert sanitize_city("<script>alert(1)</script>") is None
    assert sanitize_city("") is None
    assert sanitize_city(None) is None


def test_open_meteo_weather_fetching_mocked():
    """Verify Open-Meteo response structure with mock."""
    mock_payload = {
        "current": {
            "temperature_2m": 26.4,
            "relative_humidity_2m": 65,
            "weather_code": 1,
        }
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = str(mock_payload).replace("'", '"').encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        weather = fetch_open_meteo_weather(lat=12.9716, lon=77.5946, city_name="Bengaluru")
        assert weather is not None
        assert weather["temperature_c"] == 26.4
        assert weather["humidity"] == 65
        assert weather["condition"] == "Clear"
        assert weather["source"] == "open-meteo-free"


def test_weather_fallback_on_api_error():
    """Verify graceful fallback when Open-Meteo request throws or times out."""
    with patch("urllib.request.urlopen", side_effect=Exception("Network timeout")):
        weather = get_weather_for_location(lat=12.9716, lon=77.5946, city="Bengaluru")
        assert weather is not None
        assert "temperature_c" in weather
        assert "condition" in weather


def test_location_input_pydantic_validation():
    """Verify LocationInput Pydantic schema validation."""
    loc = LocationInput(
        latitude=12.9716,
        longitude=77.5946,
        city="Bengaluru",
        state="Karnataka",
        country="India",
        display_name="Bengaluru, Karnataka, India",
    )
    assert loc.latitude == 12.9716
    assert loc.city == "Bengaluru"

    # Optional fields default cleanly
    loc_minimal = LocationInput(city="Mumbai")
    assert loc_minimal.city == "Mumbai"
    assert loc_minimal.latitude is None


def test_analytics_location_mood_aggregation():
    """Verify location-mood aggregation computes averages, deltas, and happiest locations."""
    mock_entries = [
        {
            "id": "e1",
            "createdAt": "2026-09-01T10:00:00Z",
            "summary": {"mood_score": 9.0, "energy_level": "High Energy", "topic": "Coding"},
            "location": {"city": "Bengaluru", "country": "India"},
            "weather": {"condition": "Mainly clear", "temperature_c": 24.0},
        },
        {
            "id": "e2",
            "createdAt": "2026-09-02T10:00:00Z",
            "summary": {"mood_score": 8.0, "energy_level": "Medium Energy", "topic": "Productivity"},
            "location": {"city": "Bengaluru", "country": "India"},
            "weather": {"condition": "Partly cloudy", "temperature_c": 25.0},
        },
        {
            "id": "e3",
            "createdAt": "2026-09-03T10:00:00Z",
            "summary": {"mood_score": 6.0, "energy_level": "Low Energy", "topic": "Stress"},
            "location": {"city": "Mumbai", "country": "India"},
            "weather": {"condition": "Heavy rain", "temperature_c": 29.0},
        },
    ]

    aggregated = aggregate_journal_patterns(mock_entries)
    assert aggregated["has_enough_data"] is True
    assert aggregated["total_entries"] == 3

    # Baseline avg is (9 + 8 + 6) / 3 = 7.67 -> 7.7
    assert aggregated["baseline_avg_mood"] == 7.7

    mood_by_loc = aggregated["mood_by_location"]
    assert len(mood_by_loc) == 2

    # Bengaluru should be happiest (avg 8.5)
    assert mood_by_loc[0]["location"] == "Bengaluru"
    assert mood_by_loc[0]["avgMood"] == 8.5
    assert mood_by_loc[0]["count"] == 2
    assert mood_by_loc[0]["delta_from_baseline"] == 0.8

    # Mumbai (avg 6.0)
    assert mood_by_loc[1]["location"] == "Mumbai"
    assert mood_by_loc[1]["avgMood"] == 6.0
    assert mood_by_loc[1]["delta_from_baseline"] == -1.7


def test_generate_pattern_insights_location_fallback():
    """Verify deterministic grounded insight card generation with location data."""
    aggregated = {
        "has_enough_data": True,
        "total_entries": 3,
        "baseline_avg_mood": 7.7,
        "mood_by_location": [
            {"location": "Bengaluru", "avgMood": 8.5, "count": 2, "delta_from_baseline": 0.8},
            {"location": "Mumbai", "avgMood": 6.0, "count": 1, "delta_from_baseline": -1.7},
        ],
        "mood_vs_weather": [
            {"condition": "Clear / Sunny", "avgMood": 8.5, "count": 2},
        ],
        "topics": [{"name": "Coding", "value": 67, "count": 2, "color": "#3B82F6"}],
    }

    insights = generate_pattern_insights(aggregated)
    assert len(insights) >= 2
    loc_insight = next((i for i in insights if i.get("type") == "location"), None)
    assert loc_insight is not None
    assert "Bengaluru" in loc_insight["title"] or "Bengaluru" in loc_insight["description"]
