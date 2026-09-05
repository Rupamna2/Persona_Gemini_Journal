"""User persistence service for profile management and session status."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from firebase_admin import firestore
from google.cloud.firestore_v1 import Client


def get_firestore_client() -> Client:
    """Return the Firestore client from the initialized Firebase Admin SDK."""
    return firestore.client()


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
