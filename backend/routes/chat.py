"""Chat route endpoint handling multi-turn journal conversations."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.cloud import firestore

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client
from backend.agents.root_agent import run_journal_agent_turn, check_grounding_safety
from backend.services.rate_limit import enforce_and_increment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

ChatMode = Literal["FreeWrite", "DecisionMaking", "Gratitude", "GoalSetting", "ProblemSolving"]


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128, description="Unique session identifier")
    mode: ChatMode = Field(default="FreeWrite", description="Journaling conversation mode")
    message: str = Field(..., min_length=1, max_length=10000, description="User turn message content")


class MoodResponse(BaseModel):
    mood_label: str
    mood_score: float
    energy_level: str
    topics: List[str]


class QuotaResponse(BaseModel):
    tier: str
    limit: Optional[int] = None
    remaining: Optional[int] = None
    resets_at: Optional[str] = None


class SupportResourceItem(BaseModel):
    name: str
    contact: str


class SupportResourcePayload(BaseModel):
    title: str
    message: str
    hotlines: List[SupportResourceItem]


class ChatResponse(BaseModel):
    reply: str
    mood: MoodResponse
    quota: Optional[QuotaResponse] = None
    support_prompt: bool = False
    support_resources: Optional[SupportResourcePayload] = None


@router.post("", response_model=ChatResponse)
async def post_chat_message(
    body: ChatRequest,
    current_user: Dict[str, Any] = Depends(verify_token),
) -> ChatResponse:
    """Handle a multi-turn journal chat message.

    Executes root agent turn, persists conversation to Firestore session,
    and returns assistant reply and extracted mood analysis.
    """
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing uid",
        )

    db = get_firestore_client()

    # Atomically enforce rate limit quota BEFORE loading prompts or calling Gemini
    quota_info = enforce_and_increment(db, uid)

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Load user Master Prompt configuration
    master_prompt_data: Optional[Dict[str, Any]] = None
    try:
        mp_ref = db.collection("users").document(uid).collection("config").document("master_prompt")
        mp_doc = mp_ref.get()
        if mp_doc.exists:
            master_prompt_data = mp_doc.to_dict()
    except Exception as exc:
        logger.warning(f"Failed to fetch master prompt for user {uid}: {exc}")

    # 2. Load or initialize session document
    session_ref = db.collection("users").document(uid).collection("sessions").document(body.session_id)
    session_doc = session_ref.get()

    history: List[Dict[str, Any]] = []
    if session_doc.exists:
        session_data = session_doc.to_dict() or {}
        history = session_data.get("messages", [])
    else:
        # Create session skeleton
        session_ref.set({
            "sessionId": body.session_id,
            "mode": body.mode,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "messages": [],
            "status": "active",
        }, merge=True)

    # Format history turns for agent context
    formatted_history = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in history
        if "content" in m
    ]

    # 3. Run Agent Precedence Pipeline
    try:
        agent_result = run_journal_agent_turn(
            user_message=body.message,
            mode=body.mode,
            master_prompt=master_prompt_data,
            conversation_history=formatted_history,
        )
    except Exception as exc:
        logger.error(f"Agent execution error for user {uid}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent reasoning error: {str(exc)}",
        )

    reply_text = agent_result.get("reply", "")
    mood_dict = agent_result.get("mood", {
        "mood_label": "Reflective",
        "mood_score": 7.0,
        "energy_level": "Moderate Energy",
        "topics": ["Journaling"],
    })

    # 4. Grounding Check Safety Net (Non-diagnostic, non-blocking responsible AI check)
    past_mood_scores: List[float] = []
    try:
        past_journals = (
            db.collection("users")
            .document(uid)
            .collection("journals")
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(3)
            .stream()
        )
        for j_doc in past_journals:
            j_data = j_doc.to_dict() or {}
            j_summary = j_data.get("summary", {}) or {}
            m_score = j_summary.get("mood_score")
            if m_score is not None:
                try:
                    past_mood_scores.append(float(m_score))
                except (ValueError, TypeError):
                    pass
    except Exception as exc:
        logger.warning(f"Could not load past mood scores for grounding check: {exc}")

    current_mood_val = float(mood_dict.get("mood_score", 7.0))
    is_support_triggered, support_payload = check_grounding_safety(
        user_message=body.message,
        current_mood_score=current_mood_val,
        past_session_mood_scores=past_mood_scores,
    )

    # 5. Append turn messages to session document
    user_turn_entry = {
        "role": "user",
        "content": body.message,
        "timestamp": now_iso,
    }

    assistant_turn_entry = {
        "role": "assistant",
        "content": reply_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mood": mood_dict,
    }

    try:
        session_ref.update({
            "messages": firestore.ArrayUnion([user_turn_entry, assistant_turn_entry]),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "mode": body.mode,
        })
    except Exception as exc:
        logger.error(f"Failed to update session messages for user {uid}: {exc}")
        # If document set was partial, fall back to setting array directly
        session_ref.set({
            "sessionId": body.session_id,
            "mode": body.mode,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "messages": history + [user_turn_entry, assistant_turn_entry],
        }, merge=True)

    return ChatResponse(
        reply=reply_text,
        mood=MoodResponse(**mood_dict),
        quota=QuotaResponse(**quota_info) if quota_info else None,
        support_prompt=is_support_triggered,
        support_resources=SupportResourcePayload(**support_payload) if support_payload else None,
    )
