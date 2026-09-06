"""Analytics route endpoint providing life pattern metrics and AI insights for Recharts."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client
from backend.agents.analytics_agent import aggregate_journal_patterns, generate_pattern_insights

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/patterns")
async def get_life_pattern_analytics(
    current_user: Any = Depends(verify_token),
) -> Dict[str, Any]:
    """Retrieve mood trends, weather correlations, topic breakdowns, and AI insight cards."""
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    db = get_firestore_client()

    try:
        journals_ref = db.collection("users").document(uid).collection("journals")
        query = journals_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(50)
        docs = list(query.stream())
    except Exception as exc:
        logger.error(f"Failed to fetch journals for analytics (uid: {uid}): {exc}")
        docs = []

    entries = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["journalId"] = data.get("journalId", doc.id)
        entries.append(data)

    aggregated = aggregate_journal_patterns(entries)

    insights = []
    if aggregated.get("has_enough_data"):
        insights = generate_pattern_insights(aggregated)

    aggregated["insights"] = insights
    return aggregated
