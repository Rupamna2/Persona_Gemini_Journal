"""Firebase Authentication module for backend route protection."""

import os
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import auth as firebase_auth
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Initialize default Firebase Admin SDK app if not already initialized
if not firebase_admin._apps:
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "avid-pentameter-mr6mz")
    try:
        firebase_admin.initialize_app(options={"projectId": project_id})
    except Exception:
        firebase_admin.initialize_app()

# HTTPBearer security scheme (auto_error=False so we return explicit 401 on missing token)
security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """FastAPI dependency to verify Firebase ID tokens on protected routes.

    Extracts Bearer token, verifies via Firebase Admin SDK, and returns authenticated uid.
    Rejects missing, expired, or malformed tokens with HTTP 401.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        # verify_id_token validates token signature, expiration (1hr), audience, and issuer
        decoded_token: Dict[str, Any] = firebase_auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed: missing uid claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return uid
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
