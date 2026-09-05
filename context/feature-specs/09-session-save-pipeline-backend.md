# 09 — Session Save Pipeline (Backend)

## Goal

Implement the end-of-session flow: structured summary generation,
embedding, an atomic Firestore transaction (journal write + streak
update + session-ended flag), and an async Pub/Sub publish for
weather enrichment — with the save guaranteed to never silently
fail and never blocked by the weather step.

## Design

No new UI in this unit — it backs the "End Session & Summarize"
button from Unit 08.

## Implementation

1. `backend/agents/summary_agent.py`: takes the full session
   transcript, returns a schema-validated structured JSON summary
   matching the `summary` shape in `architecture.md` (`topic`,
   `mood_start`, `mood_end`, `mood_score`, `energy_level`,
   `key_insights[]`, `action_items[]`, `decision_status`,
   `emotional_themes[]`, `growth_areas[]`) — runs on
   `gemini-3.7-flash` via the fallback helper.
2. `backend/services/embeddings.py`: generates the 768-dim
   embedding of the summary via `gemini-embedding-001` (MRL-truncated
   from 3072).
3. `backend/services/save_pipeline.py`: a single
   `@firestore.transactional` function that, in one transaction:
   writes the `journals/{journalId}` doc (conversation copy,
   summary, embedding, `weather: null`), updates
   `stats/streaks` (current/longest streak logic: today = no
   change if already logged today, yesterday = increment, older =
   reset to 1), and marks the session `status: "ended"`. On any
   failure inside the transaction, it raises — the caller returns a
   5xx and does **not** publish to Pub/Sub.
4. `backend/routes/save.py`: `POST /api/save {session_id}` behind
   `verify_token`. Calls `summary_agent` → embedding → the
   transaction. On success, publishes `{uid, journalId, city}` to
   the `journal-created` Pub/Sub topic, then returns
   `{summary, streak}`. On transaction failure, returns 5xx with a
   body the frontend can use to show "Retry Save" — critically,
   this must happen without the frontend clearing its input buffer
   (frontend responsibility, verify in Unit 08/11's follow-up
   check).
5. Do not make the Pub/Sub publish call block or retry the HTTP
   response — fire it after the transaction succeeds and before
   returning; a publish failure should be logged (Cloud Logging
   MCP) but must never fail the already-successful save.

## Dependencies

- `google-cloud-pubsub`, `google-cloud-firestore` (backend)
- Unit 07 (session/messages exist to summarize)
- Unit 04 (rules protect the new `journals`/`stats` paths)

## MCPs Used & When to Invoke

- **`google-cloud-pubsub`** — *Step 4, mandatory.* Create the
  `journal-created` topic if it doesn't already exist (it may
  already if Unit 15 was scaffolded first), and use it during
  testing to confirm the publish actually lands after a successful
  save.
- **`google-cloud-firestore`** — *During Step 3 development and
  testing.* Inspect the transaction's actual write shape and confirm
  the vector-index-bearing `journals` collection is being written
  to as expected while iterating on the transactional save logic.
- **`google-cloud-logging`** — *During testing of the "publish
  failure never fails the save" behavior (Step 5).* Confirm a
  simulated Pub/Sub publish failure is logged without altering the
  already-200 HTTP response — this is how that verification
  checklist item is actually confirmed, not just by reading the
  response body.

## Verification Checklist

- [ ] A successful save writes the journal doc, updates the streak
      correctly for the today/yesterday/older cases, and marks the
      session ended — all in one transaction
- [ ] A forced transaction failure (e.g. inject a bad write) returns
      a 5xx and does **not** publish to Pub/Sub
- [ ] A successful save always publishes exactly one
      `journal-created` message
- [ ] The embedding stored is 768-dim, not the native 3072-dim
- [ ] `weather` field is `null` immediately after save (filled
      later by Unit 15, if built)
