"""Model invocation utilities and resilient multi-provider fallback ladder (Gemini + NVIDIA NIM)."""

import os
import time
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional, Any, Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Primary Gemini fallback ladder
DEFAULT_FALLBACK_LADDER: List[str] = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]

# Lightweight classifier fallback ladder (for mood extraction)
CLASSIFIER_FALLBACK_LADDER: List[str] = [
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]

# High-performance NVIDIA NIM models ladder (Meta Llama 3.2 11B & Nemotron 120B)
NVIDIA_MODELS_LADDER: List[str] = [
    "meta/llama-3.2-11b-vision-instruct",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
]

# HTTP/API status codes that warrant fallback progression
RETRYABLE_ERROR_CODES = {404, 429, 500, 503}
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def get_genai_client() -> genai.Client:
    """Instantiate a Google GenAI client with environment API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def normalize_contents_for_openai(contents: Any) -> List[Dict[str, str]]:
    """Convert Gemini contents structure or raw strings/dicts into standard OpenAI format."""
    messages = []
    if isinstance(contents, str):
        return [{"role": "user", "content": contents}]
    if isinstance(contents, dict):
        role = "assistant" if contents.get("role") in ("model", "assistant") else "user"
        if "content" in contents:
            return [{"role": role, "content": str(contents["content"])}]
        if "parts" in contents:
            text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in contents.get("parts", []))
            return [{"role": role, "content": text}]
        return [{"role": role, "content": str(contents)}]
    if isinstance(contents, list):
        for item in contents:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                role = "assistant" if item.get("role") in ("model", "assistant") else "user"
                if "content" in item:
                    messages.append({"role": role, "content": str(item["content"])})
                elif "parts" in item:
                    text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in item.get("parts", []))
                    messages.append({"role": role, "content": text})
                else:
                    messages.append({"role": role, "content": str(item)})
            else:
                messages.append({"role": "user", "content": str(item)})
    return messages


def extract_text_from_nvidia_content(raw_content: Any) -> str:
    """Extract string content whether NVIDIA returned a plain string, dict, or list of parts."""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, dict):
        if "text" in raw_content:
            return str(raw_content["text"])
        return str(raw_content)
    if isinstance(raw_content, list):
        parts = []
        for p in raw_content:
            if isinstance(p, dict) and "text" in p:
                parts.append(str(p["text"]))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(raw_content or "")


def generate_nvidia_content(
    contents: Any,
    system_instruction: Optional[str] = None,
    model: str = "meta/llama-3.2-11b-vision-instruct",
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    """Generate content using NVIDIA NIM OpenAI-compatible API."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not found in environment")

    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    messages.extend(normalize_contents_for_openai(contents))

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PersonalGeminiJournal/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=20.0) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if "choices" in result and len(result["choices"]) > 0:
            raw_content = result["choices"][0]["message"]["content"]
            return extract_text_from_nvidia_content(raw_content)
        return ""


def generate_content_with_fallback(
    contents: Any,
    system_instruction: Optional[str] = None,
    response_schema: Optional[Any] = None,
    response_mime_type: Optional[str] = None,
    temperature: float = 0.7,
    models: Optional[List[str]] = None,
    max_retries_per_model: int = 0,
) -> str:
    """Generate content through a resilient multi-provider fallback ladder (Gemini -> NVIDIA NIM -> Grounded Fallback).

    1. Tries Gemini models. If quota exhausted (429), immediately fails over to NVIDIA NIM.
    2. Uses NVIDIA NIM models (Llama 3.2 11B / Nemotron 120B).
    3. If all external APIs are unreachable, safely returns a deterministic structured fallback.
    """
    model_ladder = models if models is not None else DEFAULT_FALLBACK_LADDER
    nvidia_key = os.environ.get("NVIDIA_API_KEY")

    # Step 1: Try Gemini API
    try:
        client = get_genai_client()
        if client:
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction,
            )
            if response_mime_type:
                config.response_mime_type = response_mime_type
            if response_schema:
                config.response_schema = response_schema

            for model_name in model_ladder:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    if response and response.text is not None:
                        return response.text
                    elif response and hasattr(response, "candidates") and response.candidates:
                        parts = response.candidates[0].content.parts
                        return "".join(part.text for part in parts if hasattr(part, "text") and part.text)
                except Exception as exc:
                    error_str = str(exc).lower()
                    logger.warning(f"Gemini call for {model_name} returned: {exc}")
                    if "429" in error_str or "quota" in error_str or "prepayment" in error_str or "resource_exhausted" in error_str:
                        # Shared quota exhausted across project; immediately failover to NVIDIA
                        logger.info("Gemini project quota exhausted. Triggering instant failover to NVIDIA NIM.")
                        break
                    # For 503/404/500, continue loop to test next model in Gemini ladder
    except Exception as exc:
        logger.warning(f"Gemini client encountered error: {exc}. Attempting failover to NVIDIA NIM.")

    # Step 2: Failover to NVIDIA NIM if key is present
    if nvidia_key:
        logger.info("Invoking NVIDIA NIM multi-model provider...")
        for n_model in NVIDIA_MODELS_LADDER:
            try:
                nvidia_output = generate_nvidia_content(
                    contents=contents,
                    system_instruction=system_instruction,
                    model=n_model,
                    temperature=temperature,
                )
                if nvidia_output and nvidia_output.strip():
                    logger.info(f"NVIDIA NIM successfully generated content via {n_model}")
                    return nvidia_output
            except Exception as exc:
                logger.warning(f"NVIDIA NIM call failed for {n_model}: {exc}")

    # Step 3: Deterministic Fallback if all external providers fail
    logger.warning("All LLM providers (Gemini & NVIDIA) exhausted or offline. Providing grounded fallback output.")
    if response_mime_type == "application/json" or "json" in (system_instruction or "").lower():
        if "mood" in (str(contents) + str(system_instruction)).lower():
            return json.dumps({
                "mood_label": "Reflective",
                "mood_score": 7.0,
                "energy_level": "Moderate Energy",
                "topics": ["Reflection", "Mindfulness"],
            })
        return json.dumps({
            "title": "Reflective Journal Session",
            "topic": "Personal Reflection",
            "mood_start": "Reflective",
            "mood_end": "Clear",
            "mood_score": 7.5,
            "energy_level": "Moderate Energy",
            "key_insights": ["Reflected on daily experiences and emotional clarity."],
            "action_items": ["Take a moment for daily breathwork and mindful focus."],
            "decision_status": "Exploring",
            "emotional_themes": ["Mindfulness", "Clarity"],
            "growth_areas": ["Self-awareness"],
        })

    return "Thank you for sharing your thoughts. Let's take a deep breath together. What is the single most important thing you'd like to focus on next?"
