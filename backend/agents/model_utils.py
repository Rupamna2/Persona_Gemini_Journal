"""Model invocation utilities and resilient fallback ladder for Gemini models."""

import os
import time
import logging
from typing import List, Optional, Any, Dict
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Primary fallback ladder from architecture.md
DEFAULT_FALLBACK_LADDER: List[str] = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]

# Lightweight classifier fallback ladder (for mood extraction)
CLASSIFIER_FALLBACK_LADDER: List[str] = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

# HTTP/API status codes that warrant fallback progression
RETRYABLE_ERROR_CODES = {404, 429, 500, 503}


def get_genai_client() -> genai.Client:
    """Instantiate a Google GenAI client with environment API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def generate_content_with_fallback(
    contents: Any,
    system_instruction: Optional[str] = None,
    response_schema: Optional[Any] = None,
    response_mime_type: Optional[str] = None,
    temperature: float = 0.7,
    models: Optional[List[str]] = None,
    max_retries_per_model: int = 1,
) -> str:
    """Generate content through a resilient fallback ladder.

    Iterates through the model ladder if transient, rate-limit, or model-unavailability
    errors occur (503, 429, 404, 500), applying backoff and progressing to fallback models.
    """
    model_ladder = models if models is not None else DEFAULT_FALLBACK_LADDER
    client = get_genai_client()

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
    )

    if response_mime_type:
        config.response_mime_type = response_mime_type
    if response_schema:
        config.response_schema = response_schema

    last_exception = None

    for model_name in model_ladder:
        for attempt in range(max_retries_per_model + 1):
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
                return ""
            except Exception as exc:
                last_exception = exc
                error_str = str(exc).lower()
                logger.warning(
                    f"Model call failed for {model_name} (attempt {attempt + 1}/{max_retries_per_model + 1}): {exc}"
                )

                # Check if error is retryable / fallback eligible
                is_retryable = any(
                    str(code) in error_str for code in RETRYABLE_ERROR_CODES
                ) or "quota" in error_str or "unavailable" in error_str or "not found" in error_str or "rate limit" in error_str or "overloaded" in error_str

                if not is_retryable:
                    # Non-retryable error (e.g. invalid auth or unparseable prompt), raise immediately
                    raise exc

                time.sleep(0.3 * (attempt + 1))

    # If all models in the ladder were exhausted
    raise RuntimeError(
        f"All models in fallback ladder ({model_ladder}) failed. Last error: {last_exception}"
    )
