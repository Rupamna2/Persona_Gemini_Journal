"""Memory Vault API routes for semantic search and grounded recall."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client
from backend.agents.memory_agent import run_memory_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


class CitationItem(BaseModel):
    journalId: str
    date: str
    title: str
    excerpt: str
    similarity_score: Optional[float] = None


class MemorySearchResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem]


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory_vault(
    q: str = Query(..., description="Natural language search query over personal journal history"),
    current_user: Any = Depends(verify_token),
) -> MemorySearchResponse:
    """Execute natural-language semantic vector search over past journal entries with grounded citations."""
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    # 1. Validate query string length and presence
    trimmed_query = q.strip()
    if not trimmed_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' cannot be empty",
        )

    if len(trimmed_query) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' exceeds 500 characters limit",
        )

    # 2. Run grounded memory search agent scoped to user
    db = get_firestore_client()
    result = run_memory_search(db=db, uid=uid, query_text=trimmed_query)

    return MemorySearchResponse(
        query=trimmed_query,
        answer=result.get("answer", ""),
        citations=[CitationItem(**c) for c in result.get("citations", [])],
    )
