"""Subscription status API route endpoint."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client
from backend.services.rate_limit import get_subscription_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


class SubscriptionStatusResponse(BaseModel):
    tier: str
    limit: Optional[int] = None
    remaining: Optional[int] = None
    messages_used_this_period: int = 0
    resets_at: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status_endpoint(
    current_user: Any = Depends(verify_token),
) -> SubscriptionStatusResponse:
    """Retrieve current subscription tier and quota status without incrementing usage."""
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    db = get_firestore_client()
    status_info = get_subscription_status(db, uid)
    return SubscriptionStatusResponse(**status_info)
