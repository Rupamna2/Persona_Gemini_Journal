"""Tests for Journal Chat Agents Backend (Unit 07)."""

import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import verify_token
from backend.agents.root_agent import (
    FIXED_SECURITY_PREAMBLE,
    format_master_prompt_context,
    run_journal_agent_turn,
)
from backend.agents.model_utils import generate_content_with_fallback, DEFAULT_FALLBACK_LADDER
from backend.agents.mood_analyzer import analyze_turn_mood, MoodExtraction

client = TestClient(app)

TEST_UID = "test-chat-user-123"


def override_verify_token_valid():
    return {
        "uid": TEST_UID,
        "email": "chatuser@example.com",
        "name": "Chat User",
    }


def test_post_chat_unauthorized_returns_401():
    """Unauthenticated POST /api/chat must return 401."""
    res = client.post(
        "/api/chat",
        json={"session_id": "sess-1", "mode": "FreeWrite", "message": "Hello"},
    )
    assert res.status_code == 401


def test_post_chat_invalid_mode_returns_422():
    """Invalid mode must be rejected with 422 Unprocessable Entity."""
    app.dependency_overrides[verify_token] = override_verify_token_valid
    try:
        res = client.post(
            "/api/chat",
            json={"session_id": "sess-1", "mode": "InvalidNonExistentMode", "message": "Hello"},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_instruction_stack_precedence_and_preamble():
    """Verify FIXED_SECURITY_PREAMBLE is strictly first and master prompt is in <user_master_prompt> tags."""
    sample_master_prompt = {
        "aboutMe": "Software Engineer working on distributed systems",
        "tone": "Direct",
        "goals": [{"id": "g-1", "text": "Launch personal journal"}],
        "frameworks": ["5-Why", "First-Principles"],
        "thingsToAvoid": "Overly casual tone",
        "customInstructions": "Remind me to reflect on trade-offs",
    }

    xml_context = format_master_prompt_context(sample_master_prompt)
    assert "<user_master_prompt>" in xml_context
    assert "</user_master_prompt>" in xml_context
    assert "Software Engineer" in xml_context
    assert "Direct" in xml_context
    assert "5-Why" in xml_context

    with patch("backend.agents.root_agent.generate_content_with_fallback") as mock_gen, \
         patch("backend.agents.root_agent.analyze_turn_mood") as mock_mood:

        mock_gen.return_value = "What is the primary architectural trade-off here?"
        mock_mood.return_value = {
            "mood_label": "Analytical",
            "mood_score": 8.0,
            "energy_level": "High Energy",
            "topics": ["Architecture", "Trade-offs"],
        }

        result = run_journal_agent_turn(
            user_message="I'm deciding between REST and gRPC.",
            mode="DecisionMaking",
            master_prompt=sample_master_prompt,
            conversation_history=[{"role": "user", "content": "Starting my session"}],
        )

        assert mock_gen.called
        call_kwargs = mock_gen.call_args.kwargs
        sys_instruction = call_kwargs["system_instruction"]

        # Precedence check: FIXED_SECURITY_PREAMBLE appears BEFORE <user_master_prompt>
        preamble_pos = sys_instruction.find("FIXED_SECURITY_PREAMBLE")
        if preamble_pos == -1:
            preamble_pos = sys_instruction.find("You are the personal AI journaling companion")
        prompt_tag_pos = sys_instruction.find("<user_master_prompt>")
        mode_pos = sys_instruction.find("Decision Making")

        assert preamble_pos != -1
        assert prompt_tag_pos != -1
        assert preamble_pos < prompt_tag_pos < mode_pos, "Preamble must precede Master Prompt, which must precede mode instruction"

        assert result["reply"] == "What is the primary architectural trade-off here?"
        assert result["mood"]["mood_label"] == "Analytical"


def test_resilient_fallback_ladder_recovers_on_503():
    """Primary model failure with 503 should transparently fall through to fallback model."""
    mock_client = MagicMock()

    # First call (gemini-3.7-flash) fails with 503 Service Unavailable
    # Second call (gemini-3.6-flash) succeeds
    mock_response = MagicMock()
    mock_response.text = "Recovered fallback response"

    mock_client.models.generate_content.side_effect = [
        Exception("503 Service Unavailable: High load"),
        mock_response,
    ]

    with patch("backend.agents.model_utils.get_genai_client", return_value=mock_client):
        output = generate_content_with_fallback(
            contents="Test prompt",
            system_instruction="Test system",
            models=["gemini-3.7-flash", "gemini-3.6-flash"],
            max_retries_per_model=0,
        )

        assert output == "Recovered fallback response"
        assert mock_client.models.generate_content.call_count == 2


def test_mood_analyzer_structured_extraction():
    """Verify structured mood extraction returns valid schema data."""
    mock_json_reply = json.dumps({
        "mood_label": "Grateful",
        "mood_score": 9.2,
        "energy_level": "High Energy",
        "topics": ["Teamwork", "Productivity"],
    })

    with patch("backend.agents.mood_analyzer.generate_content_with_fallback", return_value=mock_json_reply):
        mood = analyze_turn_mood(
            user_message="Grateful for a great sprint with the team!",
            assistant_reply="It sounds like you had strong momentum today.",
        )

        assert mood["mood_label"] == "Grateful"
        assert mood["mood_score"] == 9.2
        assert mood["energy_level"] == "High Energy"
        assert "Teamwork" in mood["topics"]


def test_post_chat_persists_session_and_accumulates_turns():
    """POST /api/chat runs agent turn, returns reply + mood, and persists to Firestore session."""
    app.dependency_overrides[verify_token] = override_verify_token_valid

    mock_db = MagicMock()
    mock_mp_doc = MagicMock()
    mock_mp_doc.exists = True
    mock_mp_doc.to_dict.return_value = {
        "aboutMe": "Designer",
        "tone": "Empathetic",
        "goals": [{"id": "1", "text": "Write daily"}],
    }

    mock_session_doc = MagicMock()
    mock_session_doc.exists = True
    mock_session_doc.to_dict.return_value = {
        "sessionId": "sess-alpha",
        "mode": "Gratitude",
        "messages": [
            {"role": "user", "content": "Hello", "timestamp": "2026-08-30T12:00:00Z"},
            {"role": "assistant", "content": "Welcome!", "timestamp": "2026-08-30T12:00:01Z"},
        ],
    }

    mock_session_ref = MagicMock()
    mock_session_ref.get.return_value = mock_session_doc

    mock_mp_ref = MagicMock()
    mock_mp_ref.get.return_value = mock_mp_doc

    mock_status_doc = MagicMock()
    mock_status_doc.exists = True
    mock_status_doc.to_dict.return_value = {
        "tier": "free_trial",
        "period_start": "2026-08-01T00:00:00+00:00",
        "period_end": "2026-08-31T00:00:00+00:00",
        "messages_used_this_period": 2,
    }
    mock_status_ref = MagicMock()
    mock_status_ref.get.return_value = mock_status_doc

    # Setup Firestore mock paths
    def mock_collection(name):
        user_coll = MagicMock()
        def mock_user_doc(uid):
            user_doc = MagicMock()
            def mock_subcoll(subname):
                sub_coll = MagicMock()
                if subname == "config":
                    sub_coll.document.return_value = mock_mp_ref
                elif subname == "sessions":
                    sub_coll.document.return_value = mock_session_ref
                elif subname == "subscription":
                    sub_coll.document.return_value = mock_status_ref
                return sub_coll
            user_doc.collection.side_effect = mock_subcoll
            return user_doc
        user_coll.document.side_effect = mock_user_doc
        return user_coll

    mock_db.collection.side_effect = mock_collection

    with patch("backend.routes.chat.get_firestore_client", return_value=mock_db), \
         patch("backend.routes.chat.run_journal_agent_turn") as mock_agent:

        mock_agent.return_value = {
            "reply": "I'm glad to hear you are feeling grateful today.",
            "mood": {
                "mood_label": "Joyful",
                "mood_score": 9.0,
                "energy_level": "High Energy",
                "topics": ["Gratitude", "Family"],
            },
        }

        try:
            res = client.post(
                "/api/chat",
                json={
                    "session_id": "sess-alpha",
                    "mode": "Gratitude",
                    "message": "Today was a peaceful day with my family.",
                },
            )

            assert res.status_code == 200
            data = res.json()
            assert data["reply"] == "I'm glad to hear you are feeling grateful today."
            assert data["mood"]["mood_label"] == "Joyful"
            assert data["mood"]["mood_score"] == 9.0

            # Verify Firestore session update was called
            assert mock_session_ref.update.called or mock_session_ref.set.called

        finally:
            app.dependency_overrides.clear()
