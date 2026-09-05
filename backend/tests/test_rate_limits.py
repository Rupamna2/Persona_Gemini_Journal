"""Tests for Rate Limit and Subscription Service (Unit 10)."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.services.rate_limit import (
    FREE_TRIAL_MESSAGE_LIMIT,
    RateLimitExceeded,
    get_subscription_status,
    enforce_and_increment,
)

client = TestClient(app)

TEST_UID = "test-rate-user-789"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "rateuser@example.com",
        "name": "Rate Limit User",
    }


def test_subscription_status_unauthorized_returns_401():
    """Unauthenticated GET /api/subscription/status returns 401."""
    res = client.get("/api/subscription/status")
    assert res.status_code == 401


def test_subscription_status_reads_without_incrementing():
    """GET /api/subscription/status returns current tier and usage without incrementing."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    now_utc = datetime.now(timezone.utc)
    mock_db = MagicMock()
    mock_status_doc = MagicMock()
    mock_status_doc.exists = True
    mock_status_doc.to_dict.return_value = {
        "tier": "free_trial",
        "period_start": (now_utc - timedelta(days=5)).isoformat(),
        "period_end": (now_utc + timedelta(days=25)).isoformat(),
        "messages_used_this_period": 4,
    }

    mock_status_ref = MagicMock()
    mock_status_ref.get.return_value = mock_status_doc

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_status_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.subscription.get_firestore_client", return_value=mock_db):
        try:
            res = client.get("/api/subscription/status")
            assert res.status_code == 200
            data = res.json()
            assert data["tier"] == "free_trial"
            assert data["limit"] == 10
            assert data["remaining"] == 6
            assert data["messages_used_this_period"] == 4

            # Ensure get did NOT call transaction or write
            assert not mock_status_ref.set.called
            assert not mock_status_ref.update.called
        finally:
            app.dependency_overrides.clear()


def test_free_trial_10_messages_and_11th_blocked():
    """First 10 messages succeed, and 11th triggers RateLimitExceeded (HTTP 429)."""
    now_utc = datetime.now(timezone.utc)
    mock_db = MagicMock()
    mock_status_ref = MagicMock()

    # Track usage in closure
    doc_state = {
        "tier": "free_trial",
        "period_start": (now_utc - timedelta(days=2)).isoformat(),
        "period_end": (now_utc + timedelta(days=28)).isoformat(),
        "messages_used_this_period": 0,
    }

    def mock_get(transaction=None):
        doc = MagicMock()
        doc.exists = True
        doc.to_dict.return_value = dict(doc_state)
        return doc

    def mock_set(ref, data, merge=True):
        doc_state.update(data)

    mock_status_ref.get.side_effect = mock_get

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_status_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    mock_transaction = MagicMock()
    mock_transaction.set.side_effect = mock_set
    mock_db.transaction.return_value = mock_transaction

    # 1. Calls 1 through 10
    for i in range(1, 11):
        quota = enforce_and_increment(mock_db, TEST_UID)
        assert quota["tier"] == "free_trial"
        assert quota["remaining"] == (10 - i)
        assert doc_state["messages_used_this_period"] == i

    # 2. 11th call raises RateLimitExceeded
    with pytest.raises(RateLimitExceeded) as exc_info:
        enforce_and_increment(mock_db, TEST_UID)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"] == "RATE_LIMIT_EXCEEDED"
    assert exc_info.value.detail["tier"] == "free_trial"
    assert exc_info.value.detail["limit"] == 10


def test_lazy_period_rollover_resets_quota():
    """When period_end has passed, next chat turn resets usage count to 1."""
    now_utc = datetime.now(timezone.utc)
    mock_db = MagicMock()
    mock_status_ref = MagicMock()

    # Expired period (from last month)
    expired_doc_state = {
        "tier": "free_trial",
        "period_start": (now_utc - timedelta(days=60)).isoformat(),
        "period_end": (now_utc - timedelta(days=30)).isoformat(),
        "messages_used_this_period": 10,  # was at cap
    }

    def mock_get(transaction=None):
        doc = MagicMock()
        doc.exists = True
        doc.to_dict.return_value = dict(expired_doc_state)
        return doc

    def mock_set(ref, data, merge=True):
        expired_doc_state.update(data)

    mock_status_ref.get.side_effect = mock_get

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_status_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    mock_transaction = MagicMock()
    mock_transaction.set.side_effect = mock_set
    mock_db.transaction.return_value = mock_transaction

    # Execute turn after period expiry
    quota = enforce_and_increment(mock_db, TEST_UID)
    assert quota["tier"] == "free_trial"
    assert quota["remaining"] == 9  # reset from 10 used -> 1 used -> 9 remaining
    assert expired_doc_state["messages_used_this_period"] == 1


def test_pro_tier_is_never_blocked():
    """Pro tier increments usage count but is never blocked even after 50 messages."""
    now_utc = datetime.now(timezone.utc)
    mock_db = MagicMock()
    mock_status_ref = MagicMock()

    pro_doc_state = {
        "tier": "pro",
        "period_start": (now_utc - timedelta(days=5)).isoformat(),
        "period_end": (now_utc + timedelta(days=25)).isoformat(),
        "messages_used_this_period": 100,
    }

    def mock_get(transaction=None):
        doc = MagicMock()
        doc.exists = True
        doc.to_dict.return_value = dict(pro_doc_state)
        return doc

    def mock_set(ref, data, merge=True):
        pro_doc_state.update(data)

    mock_status_ref.get.side_effect = mock_get

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_status_ref
    mock_db.collection.return_value.document.return_value = mock_user_doc

    mock_transaction = MagicMock()
    mock_transaction.set.side_effect = mock_set
    mock_db.transaction.return_value = mock_transaction

    quota = enforce_and_increment(mock_db, TEST_UID)
    assert quota["tier"] == "pro"
    assert quota["limit"] is None
    assert quota["remaining"] is None
    assert pro_doc_state["messages_used_this_period"] == 101


def test_chat_route_blocks_and_avoids_agent_when_rate_limited():
    """When user is rate limited, POST /api/chat returns 429 and root_agent is NOT called."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    with patch("backend.routes.chat.enforce_and_increment") as mock_rate_limit, \
         patch("backend.routes.chat.run_journal_agent_turn") as mock_agent:

        mock_rate_limit.side_effect = RateLimitExceeded(
            tier="free_trial",
            limit=10,
            resets_at="2026-09-29T00:00:00+00:00",
        )

        try:
            res = client.post(
                "/api/chat",
                json={
                    "session_id": "sess-limit",
                    "mode": "FreeWrite",
                    "message": "Hello when rate limited",
                },
            )

            assert res.status_code == 429
            data = res.json()
            assert data["detail"]["error"] == "RATE_LIMIT_EXCEEDED"

            # Critical: Root agent MUST NOT be called when rate limited (protects Gemini quota)
            assert not mock_agent.called

        finally:
            app.dependency_overrides.clear()
