# 10 — Rate Limit + Subscription Service (Backend)

## Goal

Enforce the 10-messages-per-rolling-30-days free-trial cap
server-side, atomically, before any Gemini call — protecting the
shared project-level Gemini free-tier quota during the judging
window — and expose a status endpoint for the frontend badge.

## Design

No new UI in this unit (see Unit 11 for the badge, modal, and
pricing page).

## Implementation

1. `backend/services/rate_limit.py`: implement exactly as specified
   in the source blueprint §13 — `FREE_TRIAL_MESSAGE_LIMIT = 10`,
   `TRIAL_PERIOD_DAYS = 30`, a `RateLimitExceeded(HTTPException)`
   returning 429 with `{error: "RATE_LIMIT_EXCEEDED", tier, limit,
   resets_at}`, and `_check_and_increment` as an
   `@firestore.transactional` function against
   `users/{uid}/subscription/status`. Lazy period reset: no cron —
   the period rolls forward the first time someone chats after
   `period_end` has passed. `pro` tier increments usage but is
   never blocked.
2. `enforce_and_increment(db, uid)` is the single public entry
   point — wraps the transactional check and is meant to be called
   as the **first line** inside `/api/chat`, before `root_agent`
   runs. Go back to Unit 07's `POST /api/chat` and replace the
   `# TODO(unit-10)` marker with this call.
3. `GET /api/subscription/status`: reads (never increments) the
   current tier/usage, returning `{tier, limit, remaining,
   resets_at}` — `limit`/`remaining` are `null` for `pro`.
4. Optional (log as an open question if skipped, per
   `progress-tracker.md`): a shared `system/quota_guard` doc-based
   global circuit breaker that returns a friendly "high demand, try
   again shortly" response once total daily Gemini calls cross
   ~1,200. This doc lives outside `/users/**` and is covered by the
   deny-all fallback in `firestore.rules` automatically — server
   access only.

## Dependencies

- Unit 07 (the `/api/chat` call site this plugs into)
- Unit 04 (rules already cover `users/{uid}/subscription/status`
  under the owner-bound wildcard; the optional `system/quota_guard`
  doc is covered by the deny-all fallback, not the owner rule)

## MCPs Used & When to Invoke

- **`google-cloud-firestore`** — *During testing of Step 1's
  lazy-reset and pro-tier-bypass logic.* Inspect
  `users/{uid}/subscription/status` directly to confirm
  `period_start`/`period_end`/`messages_used_this_period` are
  transitioning correctly, rather than trusting only the API
  response.
- **`google-cloud-logging`** — *Mandatory for the 11th-call
  verification check.* Confirm the Gemini call count actually stays
  flat when a free-trial account is blocked — the whole point of
  this unit is that no model call happens, and the HTTP 429
  response alone doesn't prove that; the logs do.

## Verification Checklist

- [ ] The 1st through 10th `/api/chat` calls in a fresh 30-day
      period succeed and each response's `quota.remaining` counts
      down correctly
- [ ] The 11th call in the same period returns 429 with no Gemini
      call made (verify via Cloud Logging MCP call count, not just
      the HTTP response)
- [ ] After `period_end` passes, the next call resets usage to 1
      without any manual intervention
- [ ] A `pro`-tier account is never blocked regardless of usage
      count
- [ ] `GET /api/subscription/status` never increments usage on its
      own
