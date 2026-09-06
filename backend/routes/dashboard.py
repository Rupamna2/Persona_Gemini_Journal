"""Dashboard aggregation route returning streaks, mood trends, recent journals, and subscription quota."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from google.cloud import firestore

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client
from backend.services.rate_limit import get_subscription_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class StreakData(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    last_journal_date: Optional[str] = None


class RecentEntry(BaseModel):
    id: str
    date: str
    mode: str
    title: str
    mood_emoji: str
    mood_score: float
    summary: str


class MoodPoint(BaseModel):
    day: str
    score: float
    label: str


class SubscriptionBadge(BaseModel):
    tier: str
    limit: Optional[int] = None
    remaining: Optional[int] = None
    messages_used_this_period: int = 0
    resets_at: Optional[str] = None


class DashboardDataResponse(BaseModel):
    streaks: StreakData
    subscription: SubscriptionBadge
    recent_entries: List[RecentEntry]
    mood_trend: List[MoodPoint]
    average_mood: float
    total_journals: int


def mood_score_to_emoji(score: float) -> str:
    """Map mood score 1.0 - 10.0 to representative emoji."""
    if score >= 9.0:
        return "✨"
    elif score >= 8.0:
        return "💡"
    elif score >= 7.0:
        return "🌱"
    elif score >= 5.5:
        return "⚖️"
    elif score >= 4.0:
        return "🌧️"
    return "⚡"


@router.get("", response_model=DashboardDataResponse)
async def get_dashboard_metrics(
    current_user: Any = Depends(verify_token),
) -> DashboardDataResponse:
    """Fetch live aggregated dashboard metrics for the authenticated user."""
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    db = get_firestore_client()

    # 1. Fetch Streaks Stats
    current_streak = 0
    longest_streak = 0
    last_journal_date = None

    try:
        streaks_ref = db.collection("users").document(uid).collection("stats").document("streaks")
        streaks_doc = streaks_ref.get()
        if streaks_doc.exists:
            sdata = streaks_doc.to_dict() or {}
            current_streak = sdata.get("currentStreak", 0)
            longest_streak = sdata.get("longestStreak", 0)
            last_journal_date = sdata.get("lastJournalDate")
    except Exception as exc:
        logger.warning(f"Failed to fetch streaks for {uid}: {exc}")

    # 2. Fetch Subscription Status
    sub_info = get_subscription_status(db, uid)
    subscription_badge = SubscriptionBadge(
        tier=sub_info.get("tier", "free_trial"),
        limit=sub_info.get("limit"),
        remaining=sub_info.get("remaining"),
        messages_used_this_period=sub_info.get("messages_used_this_period", 0),
        resets_at=sub_info.get("resets_at"),
    )

    # 3. Fetch Recent Journals
    recent_entries: List[RecentEntry] = []
    mood_trend: List[MoodPoint] = []
    total_score = 0.0
    valid_score_count = 0
    total_journals = 0

    try:
        journals_ref = db.collection("users").document(uid).collection("journals")
        # Order by createdAt desc, limit 30
        query = journals_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(30)
        docs = list(query.stream())
        total_journals = len(docs)

        for i, doc in enumerate(docs):
            jdata = doc.to_dict() or {}
            j_id = jdata.get("journalId", doc.id)
            j_mode = jdata.get("mode", "FreeWrite")
            j_date = jdata.get("date", "Recent")
            j_title = jdata.get("title", "Journal Reflection")
            summary_dict = jdata.get("summary", {}) or {}
            score = summary_dict.get("mood_score", 7.5)
            insights = summary_dict.get("key_insights", [])
            summary_text = insights[0] if insights else summary_dict.get("topic", "Reflective session completed.")

            if i < 5:
                recent_entries.append(RecentEntry(
                    id=j_id,
                    date=j_date,
                    mode=j_mode,
                    title=j_title,
                    mood_emoji=mood_score_to_emoji(score),
                    mood_score=float(score),
                    summary=str(summary_text),
                ))

            mood_trend.append(MoodPoint(
                day=f"Entry {len(docs) - i}",
                score=float(score),
                label=j_date,
            ))
            total_score += score
            valid_score_count += 1

        # Reverse mood_trend so it flows chronologically left to right
        mood_trend.reverse()

    except Exception as exc:
        logger.warning(f"Failed to query journals collection for {uid}: {exc}")

    # If no journals yet, provide clean starting trendline
    if not mood_trend:
        mood_trend = [
            MoodPoint(day="Start", score=7.0, label="Day 1"),
            MoodPoint(day="Now", score=7.5, label="Today"),
        ]

    avg_mood = round(total_score / valid_score_count, 1) if valid_score_count > 0 else 7.5

    return DashboardDataResponse(
        streaks=StreakData(
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_journal_date=last_journal_date,
        ),
        subscription=subscription_badge,
        recent_entries=recent_entries,
        mood_trend=mood_trend,
        average_mood=avg_mood,
        total_journals=total_journals,
    )
