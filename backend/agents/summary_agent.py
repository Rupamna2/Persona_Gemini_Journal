"""Summary agent extracting structured end-of-session synthesis and insights."""

import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from backend.agents.model_utils import generate_content_with_fallback, DEFAULT_FALLBACK_LADDER

logger = logging.getLogger(__name__)


class SessionSummary(BaseModel):
    title: str = Field(description="A concise, meaningful reflective title for this journal entry")
    topic: str = Field(description="Primary topic or subject matter of this conversation")
    mood_start: str = Field(description="Initial emotional state observed at session start")
    mood_end: str = Field(description="Final emotional state observed at session end")
    mood_score: float = Field(description="Composite session mood score on 1.0 - 10.0 scale", ge=1.0, le=10.0)
    energy_level: str = Field(description="Dominant energy level e.g. High Energy, Calm, Low Energy")
    key_insights: List[str] = Field(description="2 to 4 major insights or breakthroughs discovered")
    action_items: List[str] = Field(description="Concrete action items or next steps identified")
    decision_status: str = Field(description="Status of any decision discussed (e.g. Decided, In Progress, Exploring, N/A)")
    emotional_themes: List[str] = Field(description="Underlying emotional themes (e.g. Clarity, Gratitude, Ambition, Anxiety)")
    growth_areas: List[str] = Field(description="Personal development areas highlighted during reflection")


DEFAULT_FALLBACK_SUMMARY: Dict[str, Any] = {
    "title": "Reflective Journal Session",
    "topic": "Personal Reflection",
    "mood_start": "Reflective",
    "mood_end": "Clear",
    "mood_score": 7.5,
    "energy_level": "Moderate Energy",
    "key_insights": ["Reflected on current priorities and progress."],
    "action_items": ["Continue daily reflection and focus."],
    "decision_status": "Exploring",
    "emotional_themes": ["Mindfulness", "Clarity"],
    "growth_areas": ["Self-awareness"],
}


def generate_session_summary(transcript_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate structured end-of-session summary from transcript turns."""
    formatted_transcript = ""
    for msg in transcript_messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        formatted_transcript += f"{role}: {content}\n\n"

    prompt = (
        "Generate a structured, insightful summary of this personal journal session.\n\n"
        "TRANSCRIPT:\n"
        f"{formatted_transcript}\n\n"
        "Provide a JSON response matching the following schema:\n"
        "{\n"
        '  "title": string,\n'
        '  "topic": string,\n'
        '  "mood_start": string,\n'
        '  "mood_end": string,\n'
        '  "mood_score": float (1.0 - 10.0),\n'
        '  "energy_level": string,\n'
        '  "key_insights": [string],\n'
        '  "action_items": [string],\n'
        '  "decision_status": string,\n'
        '  "emotional_themes": [string],\n'
        '  "growth_areas": [string]\n'
        "}"
    )

    try:
        raw_output = generate_content_with_fallback(
            contents=prompt,
            system_instruction="You are an expert executive coach and journal summarizer. Extract clear, honest, structured insights in pure JSON.",
            response_mime_type="application/json",
            models=DEFAULT_FALLBACK_LADDER,
            temperature=0.3,
        )

        parsed = json.loads(raw_output)
        validated = SessionSummary(**parsed)
        return validated.model_dump()
    except Exception as exc:
        logger.warning(f"Failed to generate structured session summary: {exc}. Using fallback summary.")
        return DEFAULT_FALLBACK_SUMMARY
