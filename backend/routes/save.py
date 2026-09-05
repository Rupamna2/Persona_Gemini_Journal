"""Save session route endpoint executing summary generation, embedding, and atomic Firestore persistence."""

import json
import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import verify_token
from backend.services.user_service import get_firestore_client
from backend.agents.summary_agent import generate_session_summary
from backend.services.embeddings import generate_embedding
from backend.services.save_pipeline import execute_atomic_session_save

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/save", tags=["save"])

PUBSUB_TOPIC_NAME = "journal-created"


class SaveSessionRequest(BaseModel):
    session_id: str = Field(..., description="The ID of the session to summarize and persist")
    city: Optional[str] = Field(default="San Francisco", description="City for async weather enrichment")


class SaveSessionResponse(BaseModel):
    journal_id: str
    summary: Dict[str, Any]
    streak: Dict[str, Any]


def publish_journal_created_event(uid: str, journal_id: str, city: str):
    """Publish journal-created event to Cloud Pub/Sub asynchronously (non-blocking)."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "avid-pentameter-mr6mz")
    payload = {
        "uid": uid,
        "journalId": journal_id,
        "city": city or "San Francisco",
    }

    try:
        from google.cloud import pubsub_v1
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, PUBSUB_TOPIC_NAME)
        data_bytes = json.dumps(payload).encode("utf-8")
        publisher.publish(topic_path, data=data_bytes)
        logger.info(f"Published journal-created event to {topic_path} for journal {journal_id}")
    except Exception as exc:
        # Pub/Sub failure must NEVER fail the already-successful database save (Invariant)
        logger.warning(f"Async Pub/Sub publish to {PUBSUB_TOPIC_NAME} skipped/failed: {exc}")


@router.post("", response_model=SaveSessionResponse)
async def save_session_endpoint(
    body: SaveSessionRequest,
    current_user: Dict[str, Any] = Depends(verify_token),
) -> SaveSessionResponse:
    """End and persist a journal session into a permanent journal entry with embeddings and streaks."""
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    db = get_firestore_client()
    session_ref = db.collection("users").document(uid).collection("sessions").document(body.session_id)
    session_doc = session_ref.get()

    if not session_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {body.session_id} not found for this account",
        )

    session_data = session_doc.to_dict() or {}
    messages = session_data.get("messages", [])
    mode = session_data.get("mode", "FreeWrite")

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot save an empty session with no messages",
        )

    # 1. Generate Structured Summary
    try:
        summary = generate_session_summary(messages)
    except Exception as exc:
        logger.error(f"Summary generation error for session {body.session_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(exc)}",
        )

    # 2. Generate 768-dim Embedding
    summary_text_for_embedding = (
        f"{summary.get('title', '')}. {summary.get('topic', '')}. "
        f"Insights: {'; '.join(summary.get('key_insights', []))}. "
        f"Actions: {'; '.join(summary.get('action_items', []))}."
    )
    embedding = generate_embedding(summary_text_for_embedding)

    # 3. Execute Atomic Transaction (Journal + Streak + Session-Ended)
    try:
        journal_id, streak_stats = execute_atomic_session_save(
            uid=uid,
            session_id=body.session_id,
            mode=mode,
            messages=messages,
            summary=summary,
            embedding=embedding,
        )
    except Exception as exc:
        logger.error(f"Atomic session save transaction failed for user {uid}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist journal entry transaction: {str(exc)}",
        )

    # 4. Trigger Async Pub/Sub Weather Enrichment (Non-blocking)
    publish_journal_created_event(uid=uid, journal_id=journal_id, city=body.city or "San Francisco")

    return SaveSessionResponse(
        journal_id=journal_id,
        summary=summary,
        streak=streak_stats,
    )
