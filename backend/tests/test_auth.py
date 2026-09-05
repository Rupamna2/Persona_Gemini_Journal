"""Tests for authentication and token verification."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.user_service import sync_user_profile

client = TestClient(app)


def test_protected_route_missing_token_returns_401():
    """Verify that requests without Authorization header are rejected with 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()["detail"]


def test_protected_route_invalid_token_returns_401():
    """Verify that requests with invalid/expired tokens are rejected with 401."""
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.side_effect = Exception("Firebase ID token has expired")
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_or_expired_token_123"},
        )
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]


def test_protected_route_valid_token_resolves_uid():
    """Verify that a valid Firebase ID token resolves to the correct uid in /api/auth/me."""
    mock_uid = "user-abc-789"
    with patch("firebase_admin.auth.verify_id_token") as mock_verify, \
         patch("backend.routes.auth_routes.get_firestore_client") as mock_get_db:

        mock_verify.return_value = {"uid": mock_uid}

        # Mock Firestore user doc and master prompt doc
        mock_db = MagicMock()
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "displayName": "Alice Smith",
            "email": "alice@gmail.com",
            "photoURL": "https://lh3.googleusercontent.com/a/alice.jpg",
            "createdAt": "2026-08-30T10:00:00Z",
            "lastLoginAt": "2026-08-30T15:00:00Z",
        }

        mock_config_doc = MagicMock()
        mock_config_doc.exists = True

        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_config_doc
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid_id_token_xyz"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == mock_uid
        assert data["displayName"] == "Alice Smith"
        assert data["email"] == "alice@gmail.com"
        assert data["hasMasterPrompt"] is True


def test_sync_user_profile_first_time_and_returning():
    """Verify user profile sync logic with valid token."""
    mock_uid = "test-user-google-12345"

    with patch("firebase_admin.auth.verify_id_token") as mock_verify, \
         patch("backend.routes.auth_routes.sync_user_profile") as mock_sync:

        mock_verify.return_value = {"uid": mock_uid}
        mock_sync.return_value = {
            "uid": mock_uid,
            "isNewUser": True,
            "hasMasterPrompt": False,
            "lastLoginAt": "2026-08-30T15:00:00Z",
        }

        # Test sync route
        response = client.post(
            "/api/auth/sync",
            headers={"Authorization": "Bearer mock_valid_jwt_token"},
            json={
                "displayName": "Test Journaler",
                "email": "test@example.com",
                "photoURL": "https://example.com/photo.jpg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == mock_uid
        assert data["isNewUser"] is True
        assert data["hasMasterPrompt"] is False
        mock_sync.assert_called_once_with(
            uid=mock_uid,
            email="test@example.com",
            display_name="Test Journaler",
            photo_url="https://example.com/photo.jpg",
        )


def test_user_service_profile_creation_and_update():
    """Unit test for sync_user_profile Firestore interaction."""
    mock_uid = "uid-first-login"
    mock_db = MagicMock()
    mock_user_ref = MagicMock()
    mock_doc = MagicMock()

    # Simulate first login (doc does not exist)
    mock_doc.exists = False
    mock_user_ref.get.return_value = mock_doc
    mock_master_prompt_doc = MagicMock()
    mock_master_prompt_doc.exists = False
    mock_user_ref.collection.return_value.document.return_value.get.return_value = mock_master_prompt_doc

    mock_db.collection.return_value.document.return_value = mock_user_ref

    with patch("backend.services.user_service.get_firestore_client", return_value=mock_db):
        res = sync_user_profile(
            uid=mock_uid,
            email="user@gmail.com",
            display_name="User One",
            photo_url="https://photo.url",
        )
        assert res["isNewUser"] is True
        assert res["hasMasterPrompt"] is False
        mock_user_ref.set.assert_called_once()
        set_args = mock_user_ref.set.call_args[0][0]
        assert set_args["displayName"] == "User One"
        assert set_args["email"] == "user@gmail.com"
        assert "createdAt" in set_args
        assert "lastLoginAt" in set_args


def test_no_password_auth_routes_exist():
    """Verify that no password login/reset endpoints exist in the application router."""
    paths = []
    for route in app.routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        elif hasattr(route, "routes"):
            paths.extend([r.path for r in route.routes if hasattr(r, "path")])
    for path in paths:
        assert "password" not in path.lower()
        assert "reset" not in path.lower()
        assert "signup-email" not in path.lower()
