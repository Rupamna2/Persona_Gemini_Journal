"""Tests for Weather Enrichment Subscriber (Unit 15)."""

import base64
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.subscriber.main import app as subscriber_app
from backend.services.weather_enrichment import sanitize_city, query_noaa_bigquery, enrich_journal_weather

client = TestClient(subscriber_app)

TEST_UID = "test-weather-user-777"
TEST_JOURNAL_ID = "j-weather-777"


def test_subscriber_rejects_unauthenticated_spoofed_request():
    """Pub/Sub push request with missing or invalid OIDC token returns 401."""
    # 1. No Authorization header
    res = client.post("/pubsub/push", json={"message": {"data": "eyJ1aWQiOiJ1MSJ9"}})
    assert res.status_code == 401

    # 2. Malformed / non-Bearer header
    res = client.post(
        "/pubsub/push",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
        json={"message": {"data": "eyJ1aWQiOiJ1MSJ9"}},
    )
    assert res.status_code == 401


def test_subscriber_processes_valid_message_and_patches_firestore():
    """Valid Pub/Sub push message decodes data and patches journal weather in Firestore."""
    payload = {
        "uid": TEST_UID,
        "journalId": TEST_JOURNAL_ID,
        "city": "Seattle",
    }
    encoded_data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    mock_db = MagicMock()
    mock_journal_ref = MagicMock()
    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_journal_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.services.weather_enrichment.get_firestore_client", return_value=mock_db):
        res = client.post(
            "/pubsub/push",
            headers={"Authorization": "Bearer test-valid-pubsub-jwt-123"},
            json={"message": {"data": encoded_data}},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "processed"
        assert data["journal_id"] == TEST_JOURNAL_ID
        assert data["weather_enriched"] is True

        # Assert direct field update was called
        mock_journal_ref.update.assert_called_once()
        update_args = mock_journal_ref.update.call_args[0][0]
        assert "weather" in update_args
        assert update_args["weather"]["condition"] in ("Rain", "Partly Cloudy", "Clear")
        assert "temperature_c" in update_args["weather"]
        assert "fetched_at" in update_args["weather"]


def test_subscriber_handles_lookup_failure_gracefully_leaving_weather_null():
    """When weather query fails, subscriber logs warning and returns 200 without crashing."""
    payload = {
        "uid": TEST_UID,
        "journalId": TEST_JOURNAL_ID,
        "city": "UnknownCityXYZ",
    }
    encoded_data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    mock_db = MagicMock()

    with patch("backend.services.weather_enrichment.query_noaa_bigquery", return_value=None), \
         patch("backend.services.weather_enrichment.get_firestore_client", return_value=mock_db):

        res = client.post(
            "/pubsub/push",
            headers={"Authorization": "Bearer test-valid-pubsub-jwt-123"},
            json={"message": {"data": encoded_data}},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "processed"
        assert data["weather_enriched"] is False


def test_sanitize_city_blocks_ssrf_and_sql_injection():
    """Sanitizer blocks SQL injection, URLs, and malicious character sets."""
    assert sanitize_city("San Francisco") == "San Francisco"
    assert sanitize_city("New York, NY") == "New York, NY"
    assert sanitize_city("St. John's") == "St. John's"

    # Malicious injection payloads must return None
    assert sanitize_city("'; DROP TABLE journals;--") is None
    assert sanitize_city("http://169.254.169.254/latest/meta-data/") is None
    assert sanitize_city("<script>alert(1)</script>") is None
    assert sanitize_city("A" * 60) is None  # Exceeds max length
    assert sanitize_city("") is None
    assert sanitize_city(None) is None


def test_subscriber_health_endpoint():
    """Subscriber health endpoint returns 200."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["service"] == "weather-enrichment-subscriber"
