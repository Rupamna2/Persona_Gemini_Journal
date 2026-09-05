# 13 — Memory Vault UI Wiring

## Goal

Wire the Memory Vault search shell (Unit 06) and the Dashboard's
search tile (Unit 11) to the real `/api/memory/search` endpoint.

## Design

Memory Vault results per Screen Inventory #5: search bar ("Ask
about your past journals..."), result cards below with date, short
excerpt, mood emoji, and a relevance indicator.

## Implementation

1. Dashboard's Memory Vault search tile: typing a query and
   submitting navigates to the Memory Vault screen with the query
   pre-filled and already searched.
2. Memory Vault screen: on submit, call
   `GET /api/memory/search?q=...`, show a loading state, then render
   the answer plus result cards from `citations`.
3. Each result card shows date, a short excerpt (from the
   citation's returned excerpt, not the full journal — do not fetch
   or render the full conversation here), mood emoji derived from
   `mood_score`/`mood_label`, and a simple relevance indicator (e.g.
   a subtle bar or rank number — do not invent a numeric similarity
   score if the backend doesn't return one).
4. Handle the empty-results case with a plain, non-alarming empty
   state — not an error state.

## Dependencies

- Unit 06 (Memory Vault shell)
- Unit 12 (search backend)

## MCPs Used & When to Invoke

- None. This is pure frontend wiring against Unit 12's already-built
  `/api/memory/search` endpoint — no live MCP operation in this
  unit.

## Verification Checklist

- [ ] Submitting a query from the Dashboard tile lands on Memory
      Vault with results already shown
- [ ] Submitting directly on the Memory Vault screen works
      identically
- [ ] Result cards render date, excerpt, and mood emoji correctly
      for real saved entries
- [ ] An empty-results query shows a calm empty state, not an error
