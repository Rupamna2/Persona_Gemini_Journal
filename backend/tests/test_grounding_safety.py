"""Tests for Grounding Check Safety Net (Unit 17)."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.agents.root_agent import check_grounding_safety

client = TestClient(app)

TEST_UID = "test-grounding-user-555"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "groundinguser@example.com",
        "name": "Grounding User",
    }


def test_check_grounding_safety_crisis_phrases():
    """Direct crisis keyword phrases return support_prompt: True with resources."""
    triggered, resources = check_grounding_safety(
        user_message="I feel completely broken and want to end it all.",
        current_mood_score=4.0,
    )
    assert triggered is True
    assert resources is not None
    assert "Gentle Support Reminder" in resources["title"]
    assert len(resources["hotlines"]) >= 2


def test_check_grounding_safety_sustained_low_mood():
    """3 consecutive low mood scores (<= 2.0) trigger support_prompt: True."""
    # 1. Single low score alone with healthy past -> False
    triggered, _ = check_grounding_safety(
        user_message="Tough day today.",
        current_mood_score=1.8,
        past_session_mood_scores=[7.5, 8.0],
    )
    assert triggered is False

    # 2. Low score with 2 consecutive past low scores -> True
    triggered, resources = check_grounding_safety(
        user_message="Tough day today again.",
        current_mood_score=1.5,
        past_session_mood_scores=[1.8, 2.0],
    )
    assert triggered is True
    assert resources is not None


def test_check_grounding_safety_normal_reflection():
    """Standard reflections return support_prompt: False and resources: None."""
    triggered, resources = check_grounding_safety(
        user_message="I drafted the product roadmap and met with my team.",
        current_mood_score=8.5,
        past_session_mood_scores=[7.0, 8.0],
    )
    assert triggered is False
    assert resources is None


def test_chat_route_returns_support_prompt_on_crisis_without_blocking_reply():
    """When crisis language is sent, POST /api/chat returns normal reply + support_resources."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_session_ref = MagicMock()
    mock_session_doc = MagicMock()
    mock_session_doc.exists = True
    mock_session_doc.to_dict.return_value = {"messages": []}
    mock_session_ref.get.return_value = mock_session_doc

    mock_journals_coll = MagicMock()
    mock_journals_coll.order_by.return_value.limit.return_value.stream.return_value = []

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value.document.return_value = mock_session_ref
    mock_user_doc.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = []
    mock_db.collection.return_value.document.return_value = mock_user_doc

    with patch("backend.routes.chat.get_firestore_client", return_value=mock_db), \
         patch("backend.routes.chat.enforce_and_increment", return_value={"tier": "free_trial", "limit": 10, "remaining": 9}), \
         patch("backend.routes.chat.run_journal_agent_turn") as mock_agent_turn:

        mock_agent_turn.return_value = {
            "reply": "I hear how much pain you are experiencing right now. Let's take things one step at a time.",
            "mood": {
                "mood_label": "Overwhelmed",
                "mood_score": 1.5,
                "energy_level": "Low Energy",
                "topics": ["Emotional Health"],
            },
        }

        try:
            res = client.post(
                "/api/chat",
                json={
                    "session_id": "sess-safety-1",
                    "mode": "FreeWrite",
                    "message": "I feel hopeless and I want to die.",
                },
            )

            assert res.status_code == 200
            data = res.json()
            # 1. Normal reply is preserved and returned
            assert "pain you are experiencing" in data["reply"]
            # 2. Safety support flag and resources are populated
            assert data["support_prompt"] is True
            assert data["support_resources"] is not None
            assert "988" in str(data["support_resources"]["hotlines"])
        finally:
            app.dependency_overrides.clear()
