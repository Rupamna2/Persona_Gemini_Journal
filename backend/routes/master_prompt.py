"""Master Prompt configuration routes and validation schemas."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from backend.auth import verify_token
from backend.services.user_service import get_firestore_client

router = APIRouter(prefix="/api/master-prompt", tags=["master-prompt"])

ToneType = Literal["Logical", "Empathetic", "Direct", "Playful", "ToughLove"]


class GoalItem(BaseModel):
    """Schema for individual goal in Master Prompt."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = Field(min_length=1, max_length=500)
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed: bool = Field(default=False)


class MasterPromptRequest(BaseModel):
    """Pydantic schema for creating or updating Master Prompt."""
    aboutMe: str = Field(default="", max_length=5000)
    tone: ToneType = Field(default="Empathetic")
    goals: List[GoalItem] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    thingsToAvoid: str = Field(default="", max_length=5000)
    customInstructions: str = Field(default="", max_length=5000)


class MasterPromptResponse(MasterPromptRequest):
    """Pydantic response schema including server-generated updatedAt."""
    updatedAt: Optional[str] = None


@router.get("", response_model=MasterPromptResponse)
async def get_master_prompt(
    uid: str = Depends(verify_token),
) -> MasterPromptResponse:
    """Retrieve the Master Prompt for the authenticated user.

    Returns saved document or sensible defaults if not yet configured.
    """
    db = get_firestore_client()
    doc_ref = db.collection("users").document(uid).collection("config").document("master_prompt")
    doc = doc_ref.get()

    if not doc.exists:
        return MasterPromptResponse(
            aboutMe="",
            tone="Empathetic",
            goals=[],
            frameworks=[],
            thingsToAvoid="",
            customInstructions="",
            updatedAt=None,
        )

    data = doc.to_dict() or {}
    return MasterPromptResponse(
        aboutMe=data.get("aboutMe", ""),
        tone=data.get("tone", "Empathetic"),
        goals=[GoalItem(**g) if isinstance(g, dict) else GoalItem(text=str(g)) for g in data.get("goals", [])],
        frameworks=data.get("frameworks", []),
        thingsToAvoid=data.get("thingsToAvoid", ""),
        customInstructions=data.get("customInstructions", ""),
        updatedAt=data.get("updatedAt"),
    )


@router.post("", response_model=MasterPromptResponse)
async def save_master_prompt(
    body: MasterPromptRequest,
    uid: str = Depends(verify_token),
) -> MasterPromptResponse:
    """Validate and persist Master Prompt personalization profile.

    Server-side sets updatedAt timestamp and saves to users/{uid}/config/master_prompt.
    """
    db = get_firestore_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "aboutMe": body.aboutMe,
        "tone": body.tone,
        "goals": [g.model_dump() for g in body.goals],
        "frameworks": body.frameworks,
        "thingsToAvoid": body.thingsToAvoid,
        "customInstructions": body.customInstructions,
        "updatedAt": now_iso,
    }

    doc_ref = db.collection("users").document(uid).collection("config").document("master_prompt")
    doc_ref.set(doc_data)

    return MasterPromptResponse(
        aboutMe=doc_data["aboutMe"],
        tone=doc_data["tone"],
        goals=body.goals,
        frameworks=doc_data["frameworks"],
        thingsToAvoid=doc_data["thingsToAvoid"],
        customInstructions=doc_data["customInstructions"],
        updatedAt=now_iso,
    )
