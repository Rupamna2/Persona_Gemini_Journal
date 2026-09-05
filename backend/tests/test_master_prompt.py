"""Unit and integration tests for Master Prompt endpoints and validation."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_master_prompt_unauthorized_returns_401():
    """Verify that unauthenticated GET requests are rejected with 401."""
    response = client.get("/api/master-prompt")
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()["detail"]


def test_get_master_prompt_new_user_returns_defaults():
    """Verify that GET returns sensible empty defaults when no config doc exists yet."""
    mock_uid = "user-new-001"
    with patch("firebase_admin.auth.verify_id_token", return_value={"uid": mock_uid}), \
         patch("backend.routes.master_prompt.get_firestore_client") as mock_get_db:

        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/master-prompt",
            headers={"Authorization": "Bearer mock_valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["aboutMe"] == ""
        assert data["tone"] == "Empathetic"
        assert data["goals"] == []
        assert data["frameworks"] == []
        assert data["thingsToAvoid"] == ""
        assert data["customInstructions"] == ""
        assert data["updatedAt"] is None


def test_get_master_prompt_existing_user_returns_saved_data():
    """Verify that GET returns saved document for returning user."""
    mock_uid = "user-returning-002"
    with patch("firebase_admin.auth.verify_id_token", return_value={"uid": mock_uid}), \
         patch("backend.routes.master_prompt.get_firestore_client") as mock_get_db:

        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "aboutMe": "Engineering leader",
            "tone": "Direct",
            "goals": [{"id": "g1", "text": "Run 10km", "createdAt": "2026-08-30T10:00:00Z", "completed": False}],
            "frameworks": ["5-Why", "First-Principles"],
            "thingsToAvoid": "Fluff and generic advice",
            "customInstructions": "Challenge my assumptions",
            "updatedAt": "2026-08-30T12:00:00Z",
        }
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/master-prompt",
            headers={"Authorization": "Bearer mock_valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["aboutMe"] == "Engineering leader"
        assert data["tone"] == "Direct"
        assert len(data["goals"]) == 1
        assert data["goals"][0]["text"] == "Run 10km"
        assert data["frameworks"] == ["5-Why", "First-Principles"]
        assert data["updatedAt"] == "2026-08-30T12:00:00Z"


def test_post_master_prompt_invalid_tone_returns_400():
    """Verify that POST rejects malformed body with invalid tone (422/400 validation error)."""
    mock_uid = "user-test-003"
    with patch("firebase_admin.auth.verify_id_token", return_value={"uid": mock_uid}):
        response = client.post(
            "/api/master-prompt",
            headers={"Authorization": "Bearer mock_valid_token"},
            json={
                "aboutMe": "Some text",
                "tone": "Aggressive",  # Invalid tone not in Literal
                "goals": [],
                "frameworks": [],
            },
        )
        assert response.status_code == 422  # Pydantic validation rejection


def test_post_master_prompt_persists_correctly():
    """Verify that POST validates, persists with server-generated updatedAt, and writes to users/{uid}/config/master_prompt."""
    mock_uid = "user-test-004"
    with patch("firebase_admin.auth.verify_id_token", return_value={"uid": mock_uid}), \
         patch("backend.routes.master_prompt.get_firestore_client") as mock_get_db:

        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref
        mock_get_db.return_value = mock_db

        payload = {
            "aboutMe": "Product manager building AI tools",
            "tone": "Logical",
            "goals": [
                {"id": "goal-1", "text": "Ship v1 by end of month", "createdAt": "2026-08-30T10:00:00Z", "completed": False}
            ],
            "frameworks": ["Decision Matrix", "SWOT"],
            "thingsToAvoid": "Never suggest procrastinating",
            "customInstructions": "Keep responses structured with bullets",
        }

        response = client.post(
            "/api/master-prompt",
            headers={"Authorization": "Bearer mock_valid_token"},
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["aboutMe"] == payload["aboutMe"]
        assert data["tone"] == "Logical"
        assert data["updatedAt"] is not None

        # Verify Firestore set called with server-side timestamp
        mock_doc_ref.set.assert_called_once()
        saved_data = mock_doc_ref.set.call_args[0][0]
        assert saved_data["aboutMe"] == payload["aboutMe"]
        assert saved_data["tone"] == "Logical"
        assert saved_data["updatedAt"] is not None
