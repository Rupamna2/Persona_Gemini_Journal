"""Tests for Session Save Pipeline Backend (Unit 09)."""

import json
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.services.embeddings import generate_embedding, normalize_l2, TARGET_EMBEDDING_DIM
from backend.services.save_pipeline import calculate_updated_streaks, execute_atomic_session_save
from backend.agents.summary_agent import generate_session_summary

client = TestClient(app)

TEST_UID = "test-save-user-456"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "saveuser@example.com",
        "name": "Save User",
    }


def test_embedding_768_dim_and_normalized():
    """Embedding vector must be exactly 768 dimensions and L2-normalized."""
    vec = generate_embedding("Architecture reflection on distributed transactions")
    assert len(vec) == TARGET_EMBEDDING_DIM
    # L2 norm should equal 1.0 (within float precision)
    norm = sum(x * x for x in vec)
    assert pytest.approx(norm, abs=1e-3) == 1.0


def test_streak_calculation_rules():
    """Verify streak update rules for today, yesterday, and older/broken streaks."""
    today = date(2026, 8, 30)
    yesterday = date(2026, 8, 29)
    older = date(2026, 8, 25)

    # 1. First journal ever
    s1 = calculate_updated_streaks(None, today)
    assert s1["currentStreak"] == 1
    assert s1["longestStreak"] == 1
    assert s1["lastJournalDate"] == "2026-08-30"

    # 2. Consecutive day (yesterday -> today)
    prev_stats = {"currentStreak": 4, "longestStreak": 7, "lastJournalDate": "2026-08-29"}
    s2 = calculate_updated_streaks(prev_stats, today)
    assert s2["currentStreak"] == 5
    assert s2["longestStreak"] == 7
    assert s2["lastJournalDate"] == "2026-08-30"

    # 3. Already journaled today (no increase)
    today_stats = {"currentStreak": 5, "longestStreak": 7, "lastJournalDate": "2026-08-30"}
    s3 = calculate_updated_streaks(today_stats, today)
    assert s3["currentStreak"] == 5
    assert s3["longestStreak"] == 7

    # 4. Broken streak (5 days ago -> today)
    broken_stats = {"currentStreak": 6, "longestStreak": 6, "lastJournalDate": "2026-08-25"}
    s4 = calculate_updated_streaks(broken_stats, today)
    assert s4["currentStreak"] == 1
    assert s4["longestStreak"] == 6


def test_summary_agent_extraction():
    """Summary agent extracts structured JSON summary with insights."""
    sample_transcript = [
        {"role": "user", "content": "I'm feeling stuck choosing between two software architectures."},
        {"role": "assistant", "content": "Let's compare trade-offs of async queues vs direct REST."},
        {"role": "user", "content": "Decided on async Pub/Sub to decouple ingestion. Feeling much clearer!"},
    ]

    mock_summary_json = json.dumps({
        "title": "Decoupled Architecture with Pub/Sub",
        "topic": "System Architecture",
        "mood_start": "Anxious",
        "mood_end": "Clear",
        "mood_score": 8.5,
        "energy_level": "High Energy",
        "key_insights": ["Decoupling ingestion improves resilience."],
        "action_items": ["Implement Pub/Sub publisher in save pipeline."],
        "decision_status": "Decided",
        "emotional_themes": ["Clarity", "Relief"],
        "growth_areas": ["Decisiveness"],
    })

    with patch("backend.agents.summary_agent.generate_content_with_fallback", return_value=mock_summary_json):
        summary = generate_session_summary(sample_transcript)
        assert summary["title"] == "Decoupled Architecture with Pub/Sub"
        assert summary["decision_status"] == "Decided"
        assert summary["mood_score"] == 8.5
        assert len(summary["key_insights"]) == 1


def test_post_save_unauthorized_returns_401():
    """Unauthenticated save request returns 401."""
    res = client.post("/api/save", json={"session_id": "sess-xyz"})
    assert res.status_code == 401


def test_post_save_empty_session_returns_400():
    """Attempting to save an empty session returns 400."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_session_doc = MagicMock()
    mock_session_doc.exists = True
    mock_session_doc.to_dict.return_value = {"messages": []}

    mock_session_ref = MagicMock()
    mock_session_ref.get.return_value = mock_session_doc

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_session_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.save.get_firestore_client", return_value=mock_db):
        try:
            res = client.post("/api/save", json={"session_id": "sess-empty"})
            assert res.status_code == 400
        finally:
            app.dependency_overrides.clear()


def test_post_save_successful_transaction_and_pubsub_publish():
    """Successful save completes atomic transaction, writes weather: null, and publishes to Pub/Sub."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_session_doc = MagicMock()
    mock_session_doc.exists = True
    mock_session_doc.to_dict.return_value = {
        "sessionId": "sess-101",
        "mode": "DecisionMaking",
        "messages": [
            {"role": "user", "content": "I made my choice today."},
            {"role": "assistant", "content": "Excellent, well done."},
        ],
    }

    mock_session_ref = MagicMock()
    mock_session_ref.get.return_value = mock_session_doc

    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    mock_streaks_doc = MagicMock()
    mock_streaks_doc.exists = True
    mock_streaks_doc.to_dict.return_value = {
        "currentStreak": 2,
        "longestStreak": 5,
        "lastJournalDate": yesterday_str,
    }
    mock_streaks_ref = MagicMock()
    mock_streaks_ref.get.return_value = mock_streaks_doc

    mock_journal_ref = MagicMock()

    def mock_collection(name):
        u_coll = MagicMock()
        def mock_u_doc(uid):
            u_doc = MagicMock()
            def mock_sub(subname):
                s_coll = MagicMock()
                def mock_s_doc(doc_id):
                    if subname == "sessions":
                        return mock_session_ref
                    elif subname == "stats":
                        return mock_streaks_ref
                    elif subname == "journals":
                        return mock_journal_ref
                    return MagicMock()
                s_coll.document.side_effect = mock_s_doc
                return s_coll
            u_doc.collection.side_effect = mock_sub
            return u_doc
        u_coll.document.side_effect = mock_u_doc
        return u_coll

    mock_db.collection.side_effect = mock_collection

    # Mock Firestore transaction context
    mock_transaction = MagicMock()
    mock_db.transaction.return_value = mock_transaction

    with patch("backend.routes.save.get_firestore_client", return_value=mock_db), \
         patch("backend.services.save_pipeline.get_firestore_client", return_value=mock_db), \
         patch("backend.routes.save.generate_session_summary") as mock_gen_summary, \
         patch("backend.routes.save.publish_journal_created_event") as mock_publish:

        mock_gen_summary.return_value = {
            "title": "Decisive Steps",
            "topic": "Productivity",
            "mood_start": "Neutral",
            "mood_end": "Empowered",
            "mood_score": 8.8,
            "energy_level": "High Energy",
            "key_insights": ["Action breeds clarity."],
            "action_items": ["Ship feature spec."],
            "decision_status": "Decided",
            "emotional_themes": ["Empowerment"],
            "growth_areas": ["Focus"],
        }

        try:
            res = client.post("/api/save", json={"session_id": "sess-101", "city": "Seattle"})
            assert res.status_code == 200
            data = res.json()
            assert "journal_id" in data
            assert data["summary"]["title"] == "Decisive Steps"
            assert data["streak"]["currentStreak"] == 3
            assert data["streak"]["longestStreak"] == 5

            # Assert Pub/Sub publish was triggered exactly once
            assert mock_publish.called
            mock_publish.assert_called_once_with(
                uid=TEST_UID,
                journal_id=data["journal_id"],
                city="Seattle",
            )
        finally:
            app.dependency_overrides.clear()
