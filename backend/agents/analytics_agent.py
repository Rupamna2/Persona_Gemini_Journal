"""Analytics Agent computing mood-weather correlations, topic breakdowns, and grounded AI insights."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.agents.model_utils import generate_content_with_fallback
from backend.agents.root_agent import FIXED_SECURITY_PREAMBLE

logger = logging.getLogger(__name__)

COLOR_PALETTE = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]


class InsightCard(BaseModel):
    title: str = Field(..., description="Short catchy headline for the behavioral insight")
    description: str = Field(..., description="Grounded natural language finding referencing specific data percentages or scores")
    type: str = Field(default="general", description="Category: 'weather', 'mode', or 'general'")


class PatternAnalysisResult(BaseModel):
    insights: List[InsightCard] = Field(default_factory=list, description="2 to 3 grounded behavioral insights")


def aggregate_journal_patterns(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate raw Firestore journal documents into structured Recharts metrics."""
    if not entries:
        return {
            "mood_trend": [],
            "mood_vs_weather": [],
            "topics": [],
            "has_enough_data": False,
            "total_entries": 0,
        }

    # 1. Mood & Energy Trend (sorted chronologically)
    sorted_entries = sorted(entries, key=lambda e: e.get("createdAt", ""))
    mood_trend = []
    for idx, entry in enumerate(sorted_entries, start=1):
        summary = entry.get("summary", {}) or {}
        mood_score = summary.get("mood_score")
        if mood_score is not None:
            try:
                mood_score = float(mood_score)
            except (ValueError, TypeError):
                mood_score = 7.0
        else:
            mood_score = 7.0

        energy_str = summary.get("energy_level", "Medium Energy")
        energy_val = 8.5 if "High" in str(energy_str) else (5.5 if "Low" in str(energy_str) else 7.0)

        label = f"E{idx}" if len(sorted_entries) > 7 else (entry.get("date", f"E{idx}")[-5:])
        mood_trend.append({
            "week": label,
            "mood": round(mood_score, 1),
            "energy": round(energy_val, 1),
        })

    # 2. Mood vs Weather Aggregation
    weather_groups: Dict[str, List[float]] = {}
    valid_weather_entries = 0

    for entry in entries:
        summary = entry.get("summary", {}) or {}
        mood_score = summary.get("mood_score")
        weather = entry.get("weather")

        if mood_score is not None and weather and isinstance(weather, dict):
            try:
                score = float(mood_score)
                condition = weather.get("condition") or "Clear"
                # Normalize condition
                if "Rain" in condition or "Storm" in condition or "Drizzle" in condition:
                    norm_cond = "Rain / Storm"
                elif "Cloud" in condition or "Partly" in condition:
                    norm_cond = "Partly Cloudy"
                elif "Overcast" in condition or "Fog" in condition:
                    norm_cond = "Overcast"
                else:
                    norm_cond = "Clear / Sunny"

                weather_groups.setdefault(norm_cond, []).append(score)
                valid_weather_entries += 1
            except (ValueError, TypeError):
                continue

    mood_vs_weather = []
    for cond, scores in weather_groups.items():
        avg_mood = sum(scores) / len(scores) if scores else 0.0
        mood_vs_weather.append({
            "condition": cond,
            "avgMood": round(avg_mood, 1),
            "count": len(scores),
        })

    # 3. Topic & Theme Distribution
    topic_counts: Dict[str, int] = {}
    for entry in entries:
        summary = entry.get("summary", {}) or {}
        topic = summary.get("topic")
        if topic and str(topic).strip():
            topic_counts[str(topic).strip()] = topic_counts.get(str(topic).strip(), 0) + 1
        else:
            mode = entry.get("mode", "Reflection")
            topic_counts[mode] = topic_counts.get(mode, 0) + 1

    total_topics = sum(topic_counts.values()) or 1
    topics_list = []
    for idx, (tname, count) in enumerate(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]):
        pct = round((count / total_topics) * 100)
        topics_list.append({
            "name": tname,
            "value": pct if pct > 0 else 1,
            "count": count,
            "color": COLOR_PALETTE[idx % len(COLOR_PALETTE)],
        })

    has_enough = len(entries) >= 2 and valid_weather_entries >= 1

    return {
        "mood_trend": mood_trend,
        "mood_vs_weather": mood_vs_weather,
        "topics": topics_list,
        "has_enough_data": has_enough,
        "total_entries": len(entries),
        "weather_enriched_entries": valid_weather_entries,
    }


def generate_pattern_insights(aggregated_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate 2-3 grounded natural language insight cards via Gemini."""
    if not aggregated_data.get("has_enough_data"):
        return []

    mood_weather_summary = json.dumps(aggregated_data.get("mood_vs_weather", []))
    topics_summary = json.dumps(aggregated_data.get("topics", []))
    total_entries = aggregated_data.get("total_entries", 0)

    prompt = f"""
You are the Life Pattern Analytics agent. Analyze the following aggregated metrics from the user's journal history.
Generate exactly 2 or 3 concise, highly grounded behavioral insight cards.
Every finding MUST directly cite the numbers in the data. Do NOT hallucinate patterns not present in the data.

Metrics Data:
- Total Journal Entries: {total_entries}
- Mood by Weather Condition: {mood_weather_summary}
- Focus Topics Distribution: {topics_summary}

Format each insight card with:
- title: concise, positive, actionable header
- description: 1-2 sentence evidence-grounded summary referencing specific scores/percentages
- type: 'weather', 'mode', or 'general'
"""

    system_instruction = f"""{FIXED_SECURITY_PREAMBLE}
You are an expert behavioural analytics agent. You produce strictly grounded JSON analytics insights based on verified database metrics only."""

    try:
        response_text = generate_content_with_fallback(
            contents=[prompt],
            system_instruction=system_instruction,
            response_schema=PatternAnalysisResult,
            response_mime_type="application/json",
            temperature=0.3,
        )
        data = json.loads(response_text)
        return data.get("insights", [])
    except Exception as exc:
        logger.warning(f"AI insight generation failed: {exc}. Using deterministic grounded fallback.")
        # Fallback to deterministic grounded insights
        fallback_insights = []
        weather_data = aggregated_data.get("mood_vs_weather", [])
        if weather_data:
            best_weather = max(weather_data, key=lambda x: x["avgMood"])
            fallback_insights.append({
                "title": f"{best_weather['condition']} Energy Correlation",
                "description": f"Your average mood peaks at {best_weather['avgMood']}/10 during {best_weather['condition']} conditions across {best_weather['count']} recorded sessions.",
                "type": "weather",
            })

        topics = aggregated_data.get("topics", [])
        if topics:
            top_topic = topics[0]
            fallback_insights.append({
                "title": f"Primary Focus: {top_topic['name']}",
                "description": f"'{top_topic['name']}' represents {top_topic['value']}% of your recent journal reflections.",
                "type": "general",
            })

        return fallback_insights
