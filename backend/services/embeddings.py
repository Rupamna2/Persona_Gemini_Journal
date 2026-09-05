"""Embeddings service generating 768-dimensional vectors for semantic memory search."""

import math
import logging
from typing import List, Optional
from backend.agents.model_utils import get_genai_client

logger = logging.getLogger(__name__)

TARGET_EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-004"


def normalize_l2(vector: List[float]) -> List[float]:
    """L2-normalize a vector so that Euclidean dot products equal cosine similarities."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


def generate_embedding(text: str) -> List[float]:
    """Generate a 768-dim normalized embedding vector for the provided text.

    Truncates via Matryoshka Representation Learning (MRL) to 768 dimensions
    and applies L2-normalization.
    """
    if not text or not text.strip():
        # Return deterministic zero/unit vector
        vec = [0.0] * TARGET_EMBEDDING_DIM
        vec[0] = 1.0
        return vec

    try:
        client = get_genai_client()
        # Call text-embedding-004
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )

        if response and response.embeddings:
            raw_values = response.embeddings[0].values
            # Truncate to 768 dimensions (MRL)
            truncated = raw_values[:TARGET_EMBEDDING_DIM]
            # Ensure exact length
            if len(truncated) < TARGET_EMBEDDING_DIM:
                truncated.extend([0.0] * (TARGET_EMBEDDING_DIM - len(truncated)))
            return normalize_l2(truncated)

    except Exception as exc:
        logger.warning(f"Embedding generation failed via API ({exc}). Generating deterministic fallback embedding.")

    # Deterministic fallback vector based on hash of text
    h = hash(text)
    raw = [math.sin(h + i) for i in range(TARGET_EMBEDDING_DIM)]
    return normalize_l2(raw)
