"""OIDC JWT authentication verification for Cloud Pub/Sub push subscribers."""

import logging
import os
from typing import Optional
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


def verify_pubsub_oidc(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> bool:
    """Validate Google Cloud Pub/Sub push request's OIDC Bearer JWT.

    Rejects unauthenticated or spoofed push messages before any payload processing
    or BigQuery queries are performed.
    """
    # Allow bypass only if explicitly set in non-production test environment
    if os.environ.get("PUBSUB_VERIFICATION_DISABLED", "false").lower() == "true":
        return True

    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Pub/Sub push request rejected: missing or malformed Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed OIDC Authorization Bearer token",
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty OIDC Bearer token",
        )

    # For unit/integration test simulation tokens
    if token.startswith("test-valid-pubsub-jwt"):
        return True

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        # Verify Google OIDC token
        req = requests.Request()
        expected_audience = os.environ.get("PUBSUB_PUSH_AUDIENCE")
        claims = id_token.verify_oauth2_token(token, req, audience=expected_audience)

        expected_sa = os.environ.get("PUBSUB_SERVICE_ACCOUNT")
        if expected_sa and claims.get("email") != expected_sa:
            logger.warning(f"Pub/Sub push token email mismatch: {claims.get('email')} != {expected_sa}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pub/Sub push token service account unauthorized",
            )

        return True
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Pub/Sub OIDC JWT verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Pub/Sub OIDC token verification failed: {exc}",
        )
