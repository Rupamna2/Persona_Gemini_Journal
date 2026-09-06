import os
import subprocess
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from google.cloud.firestore_v1 import Client
from google.cloud import firestore as google_firestore
from google.oauth2.credentials import Credentials as OAuthCredentials

logger = logging.getLogger(__name__)

_cached_firestore_client = None


def get_firestore_client() -> Client:
    """Return the Firestore client with robust credential resolution (gcloud auth local fallback & Cloud Run)."""
    global _cached_firestore_client
    if _cached_firestore_client is not None:
        return _cached_firestore_client

    project_id = (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("FIREBASE_PROJECT_ID")
        or "personal-gemini-journal-507113"
    )

    # 1. If explicit service account key is provided via GOOGLE_APPLICATION_CREDENTIALS
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
        try:
            client = google_firestore.Client(project=project_id)
            _cached_firestore_client = client
            return _cached_firestore_client
        except Exception as exc:
            logger.debug(f"GOOGLE_APPLICATION_CREDENTIALS client init error: {exc}")

    # 2. Local development fallback: obtain active access token from gcloud CLI
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True, timeout=4).strip()
        if token and not token.startswith("ERROR") and not token.startswith("WARNING"):
            creds = OAuthCredentials(token)
            client = google_firestore.Client(project=project_id, credentials=creds)
            _cached_firestore_client = client
            return _cached_firestore_client
    except Exception as exc:
        logger.debug(f"gcloud access-token resolution encountered: {exc}")

    # 3. Default Firestore client (Cloud Run IAM metadata service or ADC)
    try:
        client = google_firestore.Client(project=project_id)
        _cached_firestore_client = client
        return _cached_firestore_client
    except Exception:
        from firebase_admin import firestore
        _cached_firestore_client = firestore.client()
        return _cached_firestore_client


def sync_user_profile(
    uid: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    photo_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update the user document in Firestore upon Google Sign-In.

    On first sign-in, creates users/{uid} with createdAt and lastLoginAt.
    On subsequent sign-ins, updates only lastLoginAt and any updated profile fields.
    Checks whether users/{uid}/config/master_prompt exists to determine onboarding status.
    """
    db = get_firestore_client()
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()
    now_iso = datetime.now(timezone.utc).isoformat()

    is_new_user = not doc.exists

    if is_new_user:
        profile_data = {
            "displayName": display_name or "",
            "email": email or "",
            "photoURL": photo_url or "",
            "createdAt": now_iso,
            "lastLoginAt": now_iso,
        }
        user_ref.set(profile_data)
    else:
        update_data = {
            "lastLoginAt": now_iso,
        }
        if display_name is not None:
            update_data["displayName"] = display_name
        if photo_url is not None:
            update_data["photoURL"] = photo_url
        if email is not None:
            update_data["email"] = email
        user_ref.update(update_data)

    # Check if master prompt config exists to inform frontend routing (Onboarding vs Dashboard)
    master_prompt_ref = user_ref.collection("config").document("master_prompt")
    has_master_prompt = master_prompt_ref.get().exists

    return {
        "uid": uid,
        "isNewUser": is_new_user,
        "hasMasterPrompt": has_master_prompt,
        "lastLoginAt": now_iso,
    }
