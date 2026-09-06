"""Mood and emotional extraction agent using structured JSON output."""

import re
import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from backend.agents.model_utils import generate_content_with_fallback, CLASSIFIER_FALLBACK_LADDER

logger = logging.getLogger(__name__)


class MoodExtraction(BaseModel):
    mood_label: str = Field(description="Short mood descriptor e.g. Focused, Reflective, Hopeful, Frustrated")
    mood_score: float = Field(description="Mood score on a scale from 1.0 (very low) to 10.0 (ecstatic)", ge=1.0, le=10.0)
    energy_level: str = Field(description="Energy level e.g. High Energy, Moderate Energy, Low Energy, Calm")
    topics: List[str] = Field(description="List of 2 to 5 relevant topics/themes discussed in this turn")


DEFAULT_FALLBACK_MOOD: Dict[str, Any] = {
    "mood_label": "Reflective",
    "mood_score": 7.0,
    "energy_level": "Moderate Energy",
    "topics": ["Journaling", "Reflection"],
}


def clean_json_str(raw: str) -> str:
    """Extract clean JSON substring from model output, stripping markdown fences if present."""
    if not raw:
        return ""
    cleaned = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        return match.group(1).strip()
    return cleaned


def analyze_turn_mood(user_message: str, assistant_reply: str) -> Dict[str, Any]:
    """Analyze a single conversation turn and return structured emotional metadata."""
    prompt = (
        f"Analyze the emotional tone, energy level, mood score (1.0 to 10.0), and key topics of this journal exchange.\n\n"
        f"USER MESSAGE:\n{user_message}\n\n"
        f"ASSISTANT REPLY:\n{assistant_reply}\n\n"
        f"Respond in pure JSON matching the schema:\n"
        f'{{"mood_label": string, "mood_score": float, "energy_level": string, "topics": [string]}}'
    )

    try:
        raw_output = generate_content_with_fallback(
            contents=prompt,
            system_instruction="You are an expert psychological sentiment analyzer. Extract structured mood metadata from journal interactions in pure JSON.",
            response_mime_type="application/json",
            models=CLASSIFIER_FALLBACK_LADDER,
            temperature=0.2,
        )

        cleaned_json = clean_json_str(raw_output)
        parsed = json.loads(cleaned_json)
        # Validate through Pydantic
        validated = MoodExtraction(**parsed)
        return validated.model_dump()
    except Exception as exc:
        logger.warning(f"Structured mood extraction failed: {exc}. Falling back to default mood.")
        return DEFAULT_FALLBACK_MOOD
