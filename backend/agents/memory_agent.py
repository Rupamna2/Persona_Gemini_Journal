"""Memory Agent performing KNN semantic search and grounded synthesis over past journal entries with geolocation awareness."""

import logging
import math
from typing import List, Dict, Any, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from backend.services.embeddings import generate_embedding
from backend.agents.model_utils import generate_content_with_fallback

logger = logging.getLogger(__name__)

MEMORY_SYNTHESIS_SYSTEM_PROMPT = """You are the Personal Gemini Journal Memory Vault Assistant.
Your goal is to answer the user's query about their life, thoughts, decisions, history, and places they visited using ONLY the retrieved journal entries provided below.

GROUNDING & INTEGRITY INSTRUCTIONS:
1. Base your answer STRICTLY and EXCLUSIVELY on the retrieved journal entries.
2. DO NOT invent, hallucinate, extrapolate, or assume any facts, events, or decisions not directly mentioned in the entries.
3. If the retrieved entries do not contain sufficient information to answer the question, clearly state: "Based on your past journal entries, I couldn't find specific details regarding [topic]."
4. Explicitly reference relevant dates, locations, or journal titles in your answer so the user knows when and where those reflections took place.
5. Keep your tone empathetic, clear, structured, and insightful.
"""


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors (dot product if normalized)."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_user_journals_knn(
    db: firestore.Client,
    uid: str,
    query_vector: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Execute KNN search scoped strictly to users/{uid}/journals."""
    journals_ref = db.collection("users").document(uid).collection("journals")
    retrieved_entries: List[Dict[str, Any]] = []

    # Attempt native Firestore Vector Search
    try:
        if hasattr(journals_ref, "find_nearest"):
            vector_query = journals_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(query_vector),
                distance_measure=DistanceMeasure.COSINE,
                limit=top_k,
            )
            docs = list(vector_query.stream())
            for doc in docs:
                data = doc.to_dict() or {}
                retrieved_entries.append({
                    "journalId": data.get("journalId", doc.id),
                    "date": data.get("date", "Unknown Date"),
                    "title": data.get("title", "Journal Entry"),
                    "mode": data.get("mode", "FreeWrite"),
                    "summary": data.get("summary", {}),
                    "location": data.get("location"),
                    "weather": data.get("weather"),
                    "embedding": data.get("embedding", []),
                    "createdAt": data.get("createdAt", ""),
                })
            if retrieved_entries:
                return retrieved_entries
    except Exception as exc:
        logger.info(f"Native vector query unavailable or fallback needed for user {uid}: {exc}")

    # Resilient fallback: Fetch user's journals and compute cosine similarity
    try:
        docs = list(journals_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(100).stream())
        scored_entries = []

        for doc in docs:
            data = doc.to_dict() or {}
            doc_vec = data.get("embedding")
            score = 0.0
            if doc_vec and isinstance(doc_vec, list) and len(doc_vec) > 0:
                score = compute_cosine_similarity(query_vector, doc_vec)

            scored_entries.append({
                "journalId": data.get("journalId", doc.id),
                "date": data.get("date", "Unknown Date"),
                "title": data.get("title", "Journal Entry"),
                "mode": data.get("mode", "FreeWrite"),
                "summary": data.get("summary", {}),
                "location": data.get("location"),
                "weather": data.get("weather"),
                "createdAt": data.get("createdAt", ""),
                "similarity_score": score,
            })

        # Sort by similarity score descending
        scored_entries.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_entries[:top_k]

    except Exception as exc:
        logger.error(f"Failed to query journals for user {uid}: {exc}")
        return []


def run_memory_search(
    db: firestore.Client,
    uid: str,
    query_text: str,
    top_k: int = 4,
) -> Dict[str, Any]:
    """Search user's journal vault and synthesize a grounded, cited answer."""
    # 1. Embed query text into 768-dim normalized vector
    query_vector = generate_embedding(query_text)

    # 2. Retrieve top-K most relevant journals for this user
    entries = search_user_journals_knn(db, uid, query_vector, top_k=top_k)

    if not entries:
        return {
            "answer": "You haven't recorded any journal entries yet. Once you complete and save a journaling session, your memories and reflections will appear here in the Vault.",
            "citations": [],
        }

    # 3. Format retrieved context for grounding
    context_blocks = []
    citations = []

    for entry in entries:
        j_id = entry.get("journalId", "")
        j_date = entry.get("date", "")
        j_title = entry.get("title", "")
        summary_dict = entry.get("summary", {}) or {}
        location_dict = entry.get("location") or {}
        weather_dict = entry.get("weather") or {}

        insights = summary_dict.get("key_insights", [])
        actions = summary_dict.get("action_items", [])
        topic = summary_dict.get("topic", "")

        loc_label = location_dict.get("display_name") or location_dict.get("city")
        weather_label = weather_dict.get("condition")

        meta_parts = [f"Date: {j_date}"]
        if loc_label:
            meta_parts.append(f"Location: {loc_label}")
        if weather_label:
            meta_parts.append(f"Weather: {weather_label}")

        excerpt_text = f"Title: {j_title}\n{', '.join(meta_parts)}\nKey Insights: {', '.join(insights) if insights else topic}"
        if actions:
            excerpt_text += f"\nAction Items: {', '.join(actions)}"

        context_blocks.append(f"--- Journal Entry ({j_date} - {j_title}) ---\n{excerpt_text}")

        citations.append({
            "journalId": j_id,
            "date": j_date,
            "title": j_title,
            "excerpt": insights[0] if insights else (topic or j_title),
            "similarity_score": round(entry.get("similarity_score", 0.85), 3),
            "location": location_dict if location_dict else None,
            "weather": weather_dict if weather_dict else None,
        })

    full_context_str = "\n\n".join(context_blocks)

    user_prompt = f"""User Question:
"{query_text}"

Retrieved Journal Entries from User's Private Vault:
{full_context_str}

Please synthesize a clear, helpful response answering the question based ONLY on the entries above. Cite specific dates, locations, and titles where appropriate."""

    try:
        answer_text = generate_content_with_fallback(
            contents=user_prompt,
            system_instruction=MEMORY_SYNTHESIS_SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.error(f"Failed to generate memory synthesis for user {uid}: {exc}")
        answer_text = f"Here are your most relevant entries regarding '{query_text}'. Review the citations below for details."

    return {
        "answer": answer_text,
        "citations": citations,
    }
