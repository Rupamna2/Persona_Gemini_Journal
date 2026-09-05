"""Cloud Run push subscriber service for asynchronous weather enrichment via Pub/Sub."""

import base64
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.subscriber.auth_oidc import verify_pubsub_oidc
from backend.services.weather_enrichment import enrich_journal_weather

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subscriber"])


class PubSubMessage(BaseModel):
    data: str = Field(..., description="Base64-encoded message payload")
    messageId: Optional[str] = Field(None, description="Unique Pub/Sub message ID")
    publishTime: Optional[str] = Field(None, description="Publish timestamp")


class PubSubPushEnvelope(BaseModel):
    message: PubSubMessage
    subscription: Optional[str] = Field(None, description="Resource name of push subscription")


@router.post("/pubsub/push", status_code=status.HTTP_200_OK)
@router.post("/", status_code=status.HTTP_200_OK)
async def handle_pubsub_push_message(
    envelope: PubSubPushEnvelope,
    is_authenticated: bool = Depends(verify_pubsub_oidc),
) -> Dict[str, Any]:
    """Handle incoming Pub/Sub push notification for journal-created event.

    1. OIDC Token validated before processing payload (blocks spoofing).
    2. Decodes base64 message data {uid, journalId, city}.
    3. Patches users/{uid}/journals/{journalId}.weather with NOAA observation.
    4. Acknowledges message with HTTP 200.
    """
    try:
        raw_data = base64.b64decode(envelope.message.data).decode("utf-8")
        payload = json.loads(raw_data)
    except Exception as exc:
        logger.warning(f"Failed to decode Pub/Sub message data: {exc}")
        # Return 200 to ack corrupted message so Pub/Sub doesn't retry forever
        return {"status": "ignored", "reason": "corrupted_payload"}

    uid = payload.get("uid")
    journal_id = payload.get("journalId") or payload.get("journal_id")
    city = payload.get("city") or "San Francisco"

    if not uid or not journal_id:
        logger.warning(f"Missing required fields in Pub/Sub payload: uid={uid}, journal_id={journal_id}")
        return {"status": "ignored", "reason": "missing_fields"}

    logger.info(f"Received weather enrichment job for user {uid}, journal {journal_id}, city {city}")

    # Enrich journal with weather observation
    result = enrich_journal_weather(uid=uid, journal_id=journal_id, city=city)

    return {
        "status": "processed",
        "journal_id": journal_id,
        "weather_enriched": result is not None,
    }


# Standalone FastAPI App for Cloud Run Subscriber Deployment
app = FastAPI(
    title="Weather Enrichment Subscriber",
    description="Asynchronous Cloud Run microservice consuming journal-created Pub/Sub events.",
    version="1.0.0",
)

app.include_router(router)


@app.get("/health")
async def subscriber_health() -> Dict[str, str]:
    """Subscriber health check."""
    return {
        "status": "healthy",
        "service": "weather-enrichment-subscriber",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.subscriber.main:app", host="0.0.0.0", port=8080, reload=True)
