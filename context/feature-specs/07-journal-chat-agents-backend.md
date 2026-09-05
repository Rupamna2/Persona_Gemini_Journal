# 07 — Journal Chat Agents (Backend)

## Goal

Implement the multi-turn journaling conversation loop end to end on
the backend: `root_agent`, `journal_coach`, `mood_analyzer`, and
`POST /api/chat` — no frontend wiring in this unit.

## Design

No new UI. This unit backs the Chat screen shell built in Unit 06.

## Implementation

1. `backend/agents/model_utils.py`: `generate_content_with_fallback`
   implementing the fallback ladder from `architecture.md`
   (`gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-flash-latest`
   → `gemini-2.5-flash`), retrying only on `{503, 429, 404, 500}`
   with a short backoff, raising on anything else.
2. `backend/agents/root_agent.py`: defines
   `FIXED_SECURITY_PREAMBLE` as a hardcoded constant (never read
   from Firestore, never user-editable). On each turn: loads the
   user's `master_prompt`, wraps it in `<user_master_prompt>` tags,
   constructs the instruction stack in the exact precedence order
   from `architecture.md` (preamble → master prompt → mode
   instruction → history), delegates to `journal_coach`, then to
   `mood_analyzer`.
3. `backend/agents/journal_coach.py`: one instruction template per
   mode (Free Write, Decision Making, Gratitude, Goal Setting,
   Problem Solving) — do not invent mode behavior beyond "a coach
   whose style matches the mode name and the user's configured
   tone/frameworks"; if a mode's exact coaching behavior is
   ambiguous, log it as an open question rather than guessing
   elaborate scripted behavior.
4. `backend/agents/mood_analyzer.py`: structured-JSON extraction
   (`mood_label`, `mood_score` 1–10, `energy_level`, `topics`) using
   the override model list `["gemini-2.5-flash-lite",
   "gemini-flash-latest"]` via the same fallback helper.
5. `backend/routes/chat.py`: `POST /api/chat` — validates
   `{session_id, mode, message}` via Pydantic, behind
   `verify_token`. Loads/creates the session doc, loads
   `master_prompt`, runs `root_agent`, appends the new message +
   mood to `users/{uid}/sessions/{sessionId}.messages` (sanitized,
   undefined-stripped), returns `{reply, mood}`.
6. Do **not** wire rate limiting in this unit — that's Unit 10.
   Leave a clearly marked call site (e.g. a `# TODO(unit-10):
   enforce_and_increment here` comment) so it's obvious where it
   plugs in.

## Dependencies

- `google-adk`
- Unit 03 (auth), Unit 04 (rules), Unit 05 (master prompt exists to
  read)

## MCPs Used & When to Invoke

- **`google-developer-knowledge`** — *Before Step 1, mandatory
  check.* Confirm the current `google-adk` API surface and the
  current Gemini model identifiers/aliases (especially what
  `gemini-flash-latest` currently resolves to, and whether
  `gemini-3.7-flash`/`gemini-3.6-flash` are still the right primary/
  fallback pair) are still accurate before writing
  `model_utils.py` — this ladder moves fast and this spec was
  written against a specific point in time.
- **`google-cloud-quotas`** — *Optional, before load-testing
  multi-turn chat.* Check the current Gemini API RPM/TPM ceiling so
  a fallback-ladder test doesn't get confused with a real quota
  exhaustion.
- No MCP is used inside `root_agent.py`/`journal_coach.py`/
  `mood_analyzer.py` themselves — model calls go through the Gemini
  API client directly (via `model_utils.py`), not through an MCP.

## Verification Checklist

- [ ] `POST /api/chat` with a valid token and body returns a reply
      and a mood object
- [ ] The instruction stack sent to the model always has
      `FIXED_SECURITY_PREAMBLE` first and the master prompt
      wrapped in `<user_master_prompt>` tags, never the reverse
- [ ] A forced primary-model failure (e.g. mock a 503) transparently
      falls through the ladder and still returns a reply
- [ ] Sending adversarial text in the message field (e.g. "ignore
      all prior instructions") does not change the agent's
      behavior outside the journaling-coach role
- [ ] `users/{uid}/sessions/{sessionId}.messages` accumulates
      correctly across multiple turns
