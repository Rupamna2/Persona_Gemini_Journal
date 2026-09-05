"""Tests for Life Pattern Analytics Agent and Routes (Unit 16)."""

import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.agents.analytics_agent import aggregate_journal_patterns, generate_pattern_insights

client = TestClient(app)

TEST_UID = "test-analytics-user-888"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "analyticsuser@example.com",
        "name": "Analytics User",
    }


def test_analytics_unauthorized_returns_401():
    """Unauthenticated GET /api/analytics/patterns returns 401."""
    res = client.get("/api/analytics/patterns")
    assert res.status_code == 401


def test_analytics_sparse_data_returns_honest_zero_state():
    """Sparse-data user (<2 entries) returns has_enough_data: False and no insights."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_query = MagicMock()
    # 0 entries
    mock_query.stream.return_value = []

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value.limit.return_value = mock_query

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value = mock_journals_coll
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.analytics.get_firestore_client", return_value=mock_db):
        try:
            res = client.get("/api/analytics/patterns")
            assert res.status_code == 200
            data = res.json()
            assert data["has_enough_data"] is False
            assert data["total_entries"] == 0
            assert data["insights"] == []
            assert data["mood_trend"] == []
            assert data["mood_vs_weather"] == []
            assert data["topics"] == []
        finally:
            app.dependency_overrides.clear()


def test_analytics_rich_data_returns_aggregated_metrics_and_insights():
    """Rich-data user returns calculated mood trend, mood vs weather, and AI insight cards."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_doc1 = MagicMock()
    mock_doc1.id = "j-a1"
    mock_doc1.to_dict.return_value = {
        "journalId": "j-a1",
        "date": "2026-08-28",
        "mode": "DecisionMaking",
        "summary": {
            "mood_score": 9.0,
            "energy_level": "High Energy",
            "topic": "Architecture",
        },
        "weather": {
            "condition": "Clear",
            "temperature_c": 21.5,
        },
        "createdAt": "2026-08-28T10:00:00Z",
    }

    mock_doc2 = MagicMock()
    mock_doc2.id = "j-a2"
    mock_doc2.to_dict.return_value = {
        "journalId": "j-a2",
        "date": "2026-08-29",
        "mode": "Gratitude",
        "summary": {
            "mood_score": 7.0,
            "energy_level": "Medium Energy",
            "topic": "Wellbeing",
        },
        "weather": {
            "condition": "Overcast",
            "temperature_c": 16.0,
        },
        "createdAt": "2026-08-29T10:00:00Z",
    }

    mock_doc3 = MagicMock()
    mock_doc3.id = "j-a3"
    mock_doc3.to_dict.return_value = {
        "journalId": "j-a3",
        "date": "2026-08-30",
        "mode": "GoalSetting",
        "summary": {
            "mood_score": 8.5,
            "energy_level": "High Energy",
            "topic": "Architecture",
        },
        "weather": {
            "condition": "Clear",
            "temperature_c": 22.0,
        },
        "createdAt": "2026-08-30T10:00:00Z",
    }

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.stream.return_value = [mock_doc1, mock_doc2, mock_doc3]

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value.limit.return_value = mock_query

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value = mock_journals_coll
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.analytics.get_firestore_client", return_value=mock_db), \
         patch("backend.agents.analytics_agent.generate_content_with_fallback") as mock_gemini:

        mock_gemini.return_value = json.dumps({
            "insights": [
                {
                    "title": "Clear Sky Momentum",
                    "description": "Your mood score averages 8.8/10 during clear weather conditions.",
                    "type": "weather",
                },
                {
                    "title": "Strategic Focus",
                    "description": "Architecture represents 67% of your core reflection topics.",
                    "type": "general",
                },
            ]
        })

        try:
            res = client.get("/api/analytics/patterns")
            assert res.status_code == 200
            data = res.json()
            assert data["has_enough_data"] is True
            assert data["total_entries"] == 3
            assert len(data["mood_trend"]) == 3
            assert len(data["mood_vs_weather"]) >= 2
            assert len(data["topics"]) >= 2
            assert len(data["insights"]) == 2
            assert data["insights"][0]["title"] == "Clear Sky Momentum"

            # Tenant isolation assertion
            mock_db.collection.assert_called_with("users")
            mock_db.collection("users").document.assert_called_with(TEST_UID)
            mock_user_doc.collection.assert_called_with("journals")
        finally:
            app.dependency_overrides.clear()


def test_aggregate_journal_patterns_handles_mixed_and_null_weather():
    """Aggregation cleanly groups conditions, handles null weather gracefully, and normalizes."""
    entries = [
        {
            "createdAt": "2026-08-25T10:00:00Z",
            "summary": {"mood_score": 8.0, "energy_level": "High Energy", "topic": "Coding"},
            "weather": {"condition": "Rain / Storm", "temperature_c": 12.0},
        },
        {
            "createdAt": "2026-08-26T10:00:00Z",
            "summary": {"mood_score": 6.5, "energy_level": "Low Energy", "topic": "Coding"},
            "weather": None,  # un-enriched
        },
        {
            "createdAt": "2026-08-27T10:00:00Z",
            "summary": {"mood_score": 9.5, "energy_level": "High Energy", "topic": "Health"},
            "weather": {"condition": "Partly Cloudy", "temperature_c": 20.0},
        },
    ]

    res = aggregate_journal_patterns(entries)
    assert res["has_enough_data"] is True
    assert res["total_entries"] == 3
    assert res["weather_enriched_entries"] == 2

    # Check topic breakdown percentage sum
    assert sum(t["value"] for t in res["topics"]) == 100
