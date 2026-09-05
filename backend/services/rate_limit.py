"""Rate limiting and subscription service enforcing server-side message quotas."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from google.cloud import firestore

logger = logging.getLogger(__name__)

FREE_TRIAL_MESSAGE_LIMIT: int = 10
TRIAL_PERIOD_DAYS: int = 30


class RateLimitExceeded(HTTPException):
    """Exception raised when a user exceeds their tier's message quota."""

    def __init__(self, tier: str, limit: int, resets_at: str):
        detail = {
            "error": "RATE_LIMIT_EXCEEDED",
            "tier": tier,
            "limit": limit,
            "resets_at": resets_at,
            "message": f"You have reached your {limit} messages limit for this {TRIAL_PERIOD_DAYS}-day period. Please wait until {resets_at} or upgrade to Pro.",
        }
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_subscription_status(db: firestore.Client, uid: str) -> Dict[str, Any]:
    """Read subscription status and quota metrics without incrementing usage."""
    now_utc = datetime.now(timezone.utc)
    status_ref = db.collection("users").document(uid).collection("subscription").document("status")
    status_doc = status_ref.get()

    if not status_doc.exists:
        period_start = now_utc.isoformat()
        period_end = (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat()
        return {
            "tier": "free_trial",
            "limit": FREE_TRIAL_MESSAGE_LIMIT,
            "remaining": FREE_TRIAL_MESSAGE_LIMIT,
            "messages_used_this_period": 0,
            "resets_at": period_end,
            "period_start": period_start,
            "period_end": period_end,
        }

    data = status_doc.to_dict() or {}
    tier = data.get("tier", "free_trial")
    period_end_dt = _parse_iso_datetime(data.get("period_end"))
    period_start = data.get("period_start", now_utc.isoformat())
    period_end = data.get("period_end", (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat())
    messages_used = data.get("messages_used_this_period", 0)

    # Check for lazy period expiry
    if period_end_dt and now_utc >= period_end_dt:
        messages_used = 0
        period_start = now_utc.isoformat()
        period_end = (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat()
    else:
        raw_used = data.get("messages_used_this_period", 0)
        try:
            messages_used = int(raw_used) if raw_used is not None else 0
        except (TypeError, ValueError):
            messages_used = 0

    if tier == "pro":
        return {
            "tier": "pro",
            "limit": None,
            "remaining": None,
            "messages_used_this_period": messages_used,
            "resets_at": period_end,
            "period_start": period_start,
            "period_end": period_end,
        }

    remaining = max(0, FREE_TRIAL_MESSAGE_LIMIT - messages_used)
    return {
        "tier": "free_trial",
        "limit": FREE_TRIAL_MESSAGE_LIMIT,
        "remaining": remaining,
        "messages_used_this_period": messages_used,
        "resets_at": period_end,
        "period_start": period_start,
        "period_end": period_end,
    }


def enforce_and_increment(db: firestore.Client, uid: str) -> Dict[str, Any]:
    """Atomically check and increment the user's message quota before executing an agent turn.

    Raises RateLimitExceeded (HTTP 429) if quota is exhausted on free trial.
    """
    now_utc = datetime.now(timezone.utc)
    status_ref = db.collection("users").document(uid).collection("subscription").document("status")

    @firestore.transactional
    def _check_and_increment(transaction: firestore.Transaction) -> Dict[str, Any]:
        status_doc = status_ref.get(transaction=transaction)

        if not status_doc.exists:
            tier = "free_trial"
            period_start = now_utc.isoformat()
            period_end = (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat()
            messages_used = 0
        else:
            data = status_doc.to_dict() or {}
            tier = data.get("tier", "free_trial")
            period_end_dt = _parse_iso_datetime(data.get("period_end"))
            period_start = data.get("period_start", now_utc.isoformat())
            period_end = data.get("period_end", (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat())

            # Lazy rolling period reset
            if period_end_dt and now_utc >= period_end_dt:
                logger.info(f"User {uid} 30-day period expired on {period_end}; resetting quota.")
                period_start = now_utc.isoformat()
                period_end = (now_utc + timedelta(days=TRIAL_PERIOD_DAYS)).isoformat()
                messages_used = 0
            else:
                raw_used = data.get("messages_used_this_period", 0)
                try:
                    messages_used = int(raw_used) if raw_used is not None else 0
                except (TypeError, ValueError):
                    messages_used = 0

        # Enforce tier limits
        if tier == "pro":
            messages_used += 1
            transaction.set(
                status_ref,
                {
                    "tier": "pro",
                    "period_start": period_start,
                    "period_end": period_end,
                    "messages_used_this_period": messages_used,
                    "updatedAt": now_utc.isoformat(),
                },
                merge=True,
            )
            return {
                "tier": "pro",
                "limit": None,
                "remaining": None,
                "resets_at": period_end,
            }

        # Free trial enforcement
        if messages_used >= FREE_TRIAL_MESSAGE_LIMIT:
            logger.warning(
                f"Rate limit exceeded for user {uid}: {messages_used}/{FREE_TRIAL_MESSAGE_LIMIT} used. Resets at {period_end}."
            )
            raise RateLimitExceeded(
                tier="free_trial",
                limit=FREE_TRIAL_MESSAGE_LIMIT,
                resets_at=period_end,
            )

        messages_used += 1
        remaining = FREE_TRIAL_MESSAGE_LIMIT - messages_used

        transaction.set(
            status_ref,
            {
                "tier": "free_trial",
                "period_start": period_start,
                "period_end": period_end,
                "messages_used_this_period": messages_used,
                "updatedAt": now_utc.isoformat(),
            },
            merge=True,
        )

        return {
            "tier": "free_trial",
            "limit": FREE_TRIAL_MESSAGE_LIMIT,
            "remaining": remaining,
            "resets_at": period_end,
        }

    transaction = db.transaction()
    return _check_and_increment(transaction)
