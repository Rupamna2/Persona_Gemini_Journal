"""Tests for Memory Vault Semantic Vector Search and Grounded Recall (Unit 12)."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.agents.memory_agent import compute_cosine_similarity

client = TestClient(app)

TEST_UID = "test-memory-user-456"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "memoryuser@example.com",
        "name": "Memory User",
    }


def test_cosine_similarity_helper():
    """Verify dot product cosine similarity logic."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert compute_cosine_similarity(vec1, vec2) == 1.0

    vec3 = [0.0, 1.0, 0.0]
    assert compute_cosine_similarity(vec1, vec3) == 0.0


def test_memory_search_unauthorized_returns_401():
    """Unauthenticated GET /api/memory/search returns 401."""
    res = client.get("/api/memory/search?q=What+did+I+write+about+goals?")
    assert res.status_code == 401


def test_memory_search_empty_query_returns_400():
    """Empty query string returns 400 Bad Request."""
    app.dependency_overrides[verify_token] = override_verify_token_valid
    try:
        res = client.get("/api/memory/search?q=   ")
        assert res.status_code == 400
        assert "cannot be empty" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_memory_search_oversized_query_returns_400():
    """Query exceeding 500 characters returns 400 Bad Request before embedding call."""
    app.dependency_overrides[verify_token] = override_verify_token_valid
    with patch("backend.agents.memory_agent.generate_embedding") as mock_embed:
        try:
            long_query = "a" * 501
            res = client.get(f"/api/memory/search?q={long_query}")
            assert res.status_code == 400
            assert "exceeds 500 characters limit" in res.json()["detail"]
            # Assert embedding generator was NEVER called
            assert not mock_embed.called
        finally:
            app.dependency_overrides.clear()


def test_memory_search_returns_grounded_answer_and_citations():
    """Search retrieves user's journals and generates answer citing dates and topics."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()

    # Create mock journal docs with 768-dim mock vectors
    vec_a = [0.9] + [0.0] * 767
    vec_b = [0.1] + [0.0] * 767

    mock_doc1 = MagicMock()
    mock_doc1.id = "j-alpha"
    mock_doc1.to_dict.return_value = {
        "journalId": "j-alpha",
        "date": "2026-08-15",
        "title": "Promotion Decision Reflection",
        "mode": "DecisionMaking",
        "summary": {
            "mood_score": 8.0,
            "key_insights": ["Weighed leadership autonomy against extra commute time"],
            "action_items": ["Accept team lead role"],
        },
        "embedding": vec_a,
        "createdAt": "2026-08-15T10:00:00Z",
    }

    mock_doc2 = MagicMock()
    mock_doc2.id = "j-beta"
    mock_doc2.to_dict.return_value = {
        "journalId": "j-beta",
        "date": "2026-08-20",
        "title": "Weekend Hiking Recharge",
        "mode": "Gratitude",
        "summary": {
            "mood_score": 9.5,
            "key_insights": ["Nature walks significantly lowered work anxiety"],
        },
        "embedding": vec_b,
        "createdAt": "2026-08-20T17:00:00Z",
    }

    mock_query = MagicMock()
    mock_query.limit.return_value.stream.return_value = [mock_doc1, mock_doc2]

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value = mock_query

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value = mock_journals_coll
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.memory.get_firestore_client", return_value=mock_db), \
         patch("backend.agents.memory_agent.generate_embedding", return_value=vec_a), \
         patch("backend.agents.memory_agent.generate_content_with_fallback") as mock_gemini:

        mock_gemini.return_value = (
            "On August 15, 2026 ('Promotion Decision Reflection'), you evaluated taking the team lead "
            "role, focusing on autonomy versus commute time, and decided to accept the promotion."
        )

        try:
            res = client.get("/api/memory/search?q=What+did+I+decide+about+the+promotion?")
            assert res.status_code == 200
            data = res.json()

            assert data["query"] == "What did I decide about the promotion?"
            assert "Promotion Decision Reflection" in data["answer"]
            assert len(data["citations"]) == 2
            assert data["citations"][0]["journalId"] == "j-alpha"
            assert data["citations"][0]["date"] == "2026-08-15"
            assert data["citations"][0]["title"] == "Promotion Decision Reflection"

            # Verify Firestore collection call was strictly scoped to authenticated uid
            mock_db.collection.assert_called_with("users")
            mock_db.collection("users").document.assert_called_with(TEST_UID)
            mock_user_doc.collection.assert_called_with("journals")

        finally:
            app.dependency_overrides.clear()


def test_memory_search_empty_vault():
    """User with no saved journals receives clean informational message."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.limit.return_value.stream.return_value = []

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value = mock_query

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value = mock_journals_coll
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.memory.get_firestore_client", return_value=mock_db), \
         patch("backend.agents.memory_agent.generate_embedding", return_value=[0.0]*768):

        try:
            res = client.get("/api/memory/search?q=Tell+me+about+my+week")
            assert res.status_code == 200
            data = res.json()
            assert "haven't recorded any journal entries yet" in data["answer"]
            assert data["citations"] == []
        finally:
            app.dependency_overrides.clear()
