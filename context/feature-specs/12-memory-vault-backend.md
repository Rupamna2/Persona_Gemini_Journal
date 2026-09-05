# 12 — Memory Vault Backend

## Goal

Implement natural-language semantic search over a user's past
journal entries via Firestore Vector Search, with citations to the
specific entries used.

## Design

No new UI in this unit (see Unit 13).

## Implementation

1. Confirm the composite vector index on
   `users/{uid}/journals/{journalId}.embedding` (COSINE distance)
   exists — create it via the Firebase MCP if not (per
   `architecture.md`'s Data Schema note); do not hand-edit
   `firestore.indexes.json` unless the MCP-driven deploy fails.
2. `backend/agents/memory_agent.py`: embeds the incoming query text
   via `gemini-embedding-001` (768-dim, matching the stored
   embeddings), runs a KNN search scoped to
   `users/{uid}/journals`, and generates a natural-language answer
   that cites the specific journal entries retrieved (by date/topic,
   not by inventing content not present in the retrieved docs).
3. `backend/routes/memory.py`: `GET /api/memory/search?q=...` behind
   `verify_token`. Validates the query string is non-empty and
   under a reasonable length before running the agent. Returns
   `{answer, citations: [{journalId, date, excerpt}]}`.
4. Ensure the KNN query is always scoped by `uid` — never a
   cross-user search, even accidentally, since this is the one
   endpoint in the app whose entire purpose is "search a lot of
   documents."

## Dependencies

- Unit 09 (journals with embeddings exist)
- Firestore Vector Search composite index

## MCPs Used & When to Invoke

- **`google-cloud-firestore`** — *Step 1, mandatory, this unit
  cannot function without it.* Create the composite vector index on
  `users/{uid}/journals/{journalId}.embedding` (COSINE distance) if
  it doesn't already exist. Do not hand-edit
  `firestore.indexes.json` unless the MCP-driven index creation
  fails — the MCP path is the one this whole spec assumes.

## Verification Checklist

- [ ] A search against an account with several saved journals
      returns relevant results with citations pointing to real
      entries
- [ ] The agent's answer does not state anything not attributable
      to a retrieved entry
- [ ] A search from a second account never returns the first
      account's entries
- [ ] An empty or excessively long query is rejected with 400
      before reaching the embedding call
