"""Authentication and profile sync API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from backend.auth import verify_token
from backend.services.user_service import sync_user_profile, get_firestore_client

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserSyncRequest(BaseModel):
    """Pydantic model for user profile synchronization upon sign-in."""
    displayName: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    photoURL: Optional[str] = Field(default=None, max_length=1000)


class UserSyncResponse(BaseModel):
    """Response model for auth sync."""
    uid: str
    isNewUser: bool
    hasMasterPrompt: bool
    lastLoginAt: str


class UserMeResponse(BaseModel):
    """Response model for authenticated user profile."""
    uid: str
    displayName: str
    email: str
    photoURL: str
    createdAt: str
    lastLoginAt: str
    hasMasterPrompt: bool


@router.post("/sync", response_model=UserSyncResponse)
async def sync_auth_user(
    body: UserSyncRequest,
    uid: str = Depends(verify_token),
) -> UserSyncResponse:
    """Sync user document in Firestore on Google Sign-In.

    Ensures users/{uid} is created or updated with latest login timestamp.
    Returns whether user is new and whether master prompt is configured.
    """
    result = sync_user_profile(
        uid=uid,
        email=body.email,
        display_name=body.displayName,
        photo_url=body.photoURL,
    )
    return UserSyncResponse(**result)


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_profile(
    uid: str = Depends(verify_token),
) -> UserMeResponse:
    """Fetch profile document for the authenticated user."""
    db = get_firestore_client()
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please sync first.",
        )
    data = doc.to_dict() or {}
    master_prompt_ref = user_ref.collection("config").document("master_prompt")
    has_master_prompt = master_prompt_ref.get().exists

    return UserMeResponse(
        uid=uid,
        displayName=data.get("displayName", ""),
        email=data.get("email", ""),
        photoURL=data.get("photoURL", ""),
        createdAt=data.get("createdAt", ""),
        lastLoginAt=data.get("lastLoginAt", ""),
        hasMasterPrompt=has_master_prompt,
    )
