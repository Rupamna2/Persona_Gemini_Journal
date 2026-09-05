"""Tests for Dashboard Aggregation Route (Unit 11)."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token

client = TestClient(app)

TEST_UID = "test-dash-user-123"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "dashuser@example.com",
        "name": "Dashboard User",
    }


def test_dashboard_unauthorized_returns_401():
    """Unauthenticated GET /api/dashboard returns 401."""
    res = client.get("/api/dashboard")
    assert res.status_code == 401


def test_dashboard_returns_aggregated_metrics():
    """GET /api/dashboard returns streaks, subscription, recent entries, and mood trend."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()

    # Mock streaks
    mock_streak_doc = MagicMock()
    mock_streak_doc.exists = True
    mock_streak_doc.to_dict.return_value = {
        "currentStreak": 5,
        "longestStreak": 12,
        "lastJournalDate": "2026-08-30",
    }
    mock_streak_ref = MagicMock()
    mock_streak_ref.get.return_value = mock_streak_doc

    # Mock subscription status
    mock_sub_doc = MagicMock()
    mock_sub_doc.exists = True
    mock_sub_doc.to_dict.return_value = {
        "tier": "free_trial",
        "period_start": "2026-08-01T00:00:00+00:00",
        "period_end": "2026-09-30T00:00:00+00:00",
        "messages_used_this_period": 3,
    }
    mock_sub_ref = MagicMock()
    mock_sub_ref.get.return_value = mock_sub_doc

    # Mock journals stream
    mock_journal_doc_1 = MagicMock()
    mock_journal_doc_1.id = "j-101"
    mock_journal_doc_1.to_dict.return_value = {
        "journalId": "j-101",
        "date": "2026-08-30",
        "mode": "Gratitude",
        "title": "Family Dinner & Great Conversation",
        "summary": {
            "mood_score": 8.5,
            "key_insights": ["Spending quality time rejuvenates energy"],
        },
        "createdAt": "2026-08-30T19:00:00Z",
    }

    mock_journal_doc_2 = MagicMock()
    mock_journal_doc_2.id = "j-102"
    mock_journal_doc_2.to_dict.return_value = {
        "journalId": "j-102",
        "date": "2026-08-29",
        "mode": "ProblemSolving",
        "title": "Sprint Planning Resolution",
        "summary": {
            "mood_score": 7.0,
            "key_insights": ["Clarifying expectations reduced blocker"],
        },
        "createdAt": "2026-08-29T18:00:00Z",
    }

    mock_journals_query = MagicMock()
    mock_journals_query.limit.return_value.stream.return_value = [mock_journal_doc_1, mock_journal_doc_2]

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value = mock_journals_query

    # Assemble user subcollections
    def mock_collection(name):
        user_coll = MagicMock()
        def mock_user_doc(uid):
            user_doc = MagicMock()
            def mock_subcoll(subname):
                if subname == "stats":
                    stats_coll = MagicMock()
                    stats_coll.document.return_value = mock_streak_ref
                    return stats_coll
                elif subname == "subscription":
                    sub_coll = MagicMock()
                    sub_coll.document.return_value = mock_sub_ref
                    return sub_coll
                elif subname == "journals":
                    return mock_journals_coll
                return MagicMock()
            user_doc.collection.side_effect = mock_subcoll
            return user_doc
        user_coll.document.side_effect = mock_user_doc
        return user_coll

    mock_db.collection.side_effect = mock_collection

    with patch("backend.routes.dashboard.get_firestore_client", return_value=mock_db), \
         patch("backend.services.rate_limit.get_subscription_status") as mock_get_sub:

        mock_get_sub.return_value = {
            "tier": "free_trial",
            "limit": 10,
            "remaining": 7,
            "messages_used_this_period": 3,
            "resets_at": "2026-08-31T00:00:00+00:00",
        }

        try:
            res = client.get("/api/dashboard")
            assert res.status_code == 200
            data = res.json()

            # Verify streaks
            assert data["streaks"]["current_streak"] == 5
            assert data["streaks"]["longest_streak"] == 12
            assert data["streaks"]["last_journal_date"] == "2026-08-30"

            # Verify subscription badge
            assert data["subscription"]["tier"] == "free_trial"
            assert data["subscription"]["remaining"] == 7
            assert data["subscription"]["messages_used_this_period"] == 3

            # Verify recent entries
            assert len(data["recent_entries"]) == 2
            assert data["recent_entries"][0]["title"] == "Family Dinner & Great Conversation"
            assert data["recent_entries"][0]["mood_score"] == 8.5
            assert data["recent_entries"][0]["mood_emoji"] == "💡"

            # Verify mood sparkline trend
            assert len(data["mood_trend"]) == 2
            assert data["average_mood"] == 7.8
            assert data["total_journals"] == 2
        finally:
            app.dependency_overrides.clear()
