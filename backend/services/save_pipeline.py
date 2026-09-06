"""Atomic Firestore transactional save pipeline for journal entries, streaks, and geolocation."""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from google.cloud import firestore

from backend.services.user_service import get_firestore_client
from backend.services.weather_enrichment import get_weather_for_location

logger = logging.getLogger(__name__)


def calculate_updated_streaks(
    current_stats: Optional[Dict[str, Any]],
    today_date: date,
) -> Dict[str, Any]:
    """Compute updated streak metrics for a new journal entry."""
    today_str = today_date.isoformat()
    yesterday_str = (today_date - timedelta(days=1)).isoformat()

    current_streak = 0
    longest_streak = 0
    last_journal_date = None

    if current_stats:
        current_streak = current_stats.get("currentStreak", 0)
        longest_streak = current_stats.get("longestStreak", 0)
        last_journal_date = current_stats.get("lastJournalDate")

    if last_journal_date == today_str:
        # Already journaled today; streak count remains unchanged
        pass
    elif last_journal_date == yesterday_str:
        # Consecutive day; increment streak
        current_streak += 1
    else:
        # Broken streak or first journal ever; reset to 1
        current_streak = 1

    longest_streak = max(longest_streak, current_streak)

    return {
        "currentStreak": current_streak,
        "longestStreak": longest_streak,
        "lastJournalDate": today_str,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def execute_atomic_session_save(
    uid: str,
    session_id: str,
    mode: str,
    messages: List[Dict[str, Any]],
    summary: Dict[str, Any],
    embedding: List[float],
    location: Optional[Dict[str, Any]] = None,
    city: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Execute atomic transaction saving journal doc, updating streak stats, and ending session.

    Returns (journal_id, updated_streak_stats).
    """
    db = get_firestore_client()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()
    today_date = now_utc.date()
    journal_id = f"jnl_{int(now_utc.timestamp())}_{session_id[:8]}"

    # Resolve real-time weather using Open-Meteo free API
    lat = location.get("latitude") if location else None
    lon = location.get("longitude") if location else None
    resolved_city = (location.get("city") if location and location.get("city") else city) or "Bengaluru"
    weather_data = get_weather_for_location(city=resolved_city, lat=lat, lon=lon)

    journal_ref = db.collection("users").document(uid).collection("journals").document(journal_id)
    streaks_ref = db.collection("users").document(uid).collection("stats").document("streaks")
    session_ref = db.collection("users").document(uid).collection("sessions").document(session_id)

    @firestore.transactional
    def _save_transaction(transaction: firestore.Transaction) -> Dict[str, Any]:
        # 1. Read current streaks doc
        streaks_doc = streaks_ref.get(transaction=transaction)
        current_stats = streaks_doc.to_dict() if streaks_doc.exists else None

        # 2. Calculate updated streak metrics
        updated_streak_stats = calculate_updated_streaks(current_stats, today_date)

        # 3. Prepare journal doc payload
        journal_payload = {
            "journalId": journal_id,
            "sessionId": session_id,
            "mode": mode,
            "createdAt": now_iso,
            "date": today_date.isoformat(),
            "title": summary.get("title", "Reflective Journal"),
            "messages": messages,
            "summary": summary,
            "embedding": embedding,
            "location": location,
            "weather": weather_data,
        }

        # 4. Write journal doc
        transaction.set(journal_ref, journal_payload)

        # 5. Write streak stats doc
        transaction.set(streaks_ref, updated_streak_stats, merge=True)

        # 6. Update session status to ended
        transaction.set(
            session_ref,
            {
                "status": "ended",
                "endedAt": now_iso,
                "journalId": journal_id,
            },
            merge=True,
        )

        return updated_streak_stats

    transaction = db.transaction()
    updated_streaks = _save_transaction(transaction)

    return journal_id, updated_streaks
