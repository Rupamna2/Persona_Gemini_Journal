# Architecture Context

## Stack

| Layer | Technology | Role |
|---|---|---|
| IDE | Antigravity IDE | MCP + terminal + multi-agent build environment |
| Frontend | React 18 + Vite + Tailwind CSS | Bento-grid dashboard, chat UI, matches Stitch's React export path |
| Backend | Python 3.11 + FastAPI on Cloud Run | Hosts API routes, ADK agents, needed for `openpyxl` and `google-adk` |
| Agent framework | Google ADK 2.x (`pip install google-adk`) | Model-agnostic; `SequentialAgent`/graph workflows for the save pipeline |
| Primary LLM | `gemini-3.7-flash` | Google's current best model for coding/agents (GA Aug 13 2026) |
| Fallback ladder | `gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-flash-latest` → `gemini-2.5-flash` | No single point of model failure — see `backend/agents/model_utils.py` |
| Lightweight classifier | `gemini-2.5-flash-lite` | Cheap structured-JSON mood extraction on every turn |
| Embeddings | `gemini-embedding-001`, 768-dim (MRL-truncated) | Cheapest dim that still ranks well on MTEB; keeps the Firestore vector index small |
| Auth | Firebase Authentication — Google Sign-In only | See Invariant 2 |
| Database | Cloud Firestore (native mode) + Firestore Vector Search (KNN, COSINE) | Doubles as the vector DB — no Pinecone |
| Async jobs | Cloud Pub/Sub → Cloud Run subscriber | Decouples weather enrichment from the save path |
| Analytics (Phase 3) | BigQuery public dataset `bigquery-public-data.noaa_gsod` | Free tier, <1 TiB/month |
| Secrets | Google Cloud Secret Manager via `gcloud` CLI | No MCP needed — plain terminal commands |
| Export | `openpyxl` → `StreamingResponse` | No Sheets OAuth, no third-party access |
| UI design | Stitch MCP → React/Tailwind component export | Beta — expect to hand-tune Tailwind spacing after import |
| Deployment | Cloud Run (backend, region `asia-south1`) + Firebase Hosting (frontend) | |
| Observability | Cloud Logging MCP | Query logs directly instead of copy-pasting stack traces |

## System Boundaries

- `backend/agents/` — all Gemini/ADK agent logic (`root_agent`,
  `journal_coach`, `mood_analyzer`, `summary_agent`, `memory_agent`,
  `analytics_agent`). Owns model selection, fallback, and the
  instruction-precedence contract. Never called directly from
  routes without going through `root_agent`.
- `backend/routes/` — FastAPI route handlers. Owns request
  validation (Pydantic), auth verification, and response shaping.
  Never contains agent prompt logic or raw Firestore transaction
  code — delegates to `agents/` and `services/`.
- `backend/services/` — `rate_limit.py`, save-transaction logic,
  embedding generation, weather-subscriber logic. Owns
  Firestore reads/writes and any transactional invariants.
- `frontend/src/pages/` — one file per screen (Landing, Onboarding,
  Dashboard, Chat, Memory Vault, Patterns, Subscription). Owns
  layout and screen-level state only.
- `frontend/src/design/` — raw Stitch exports, pre-wiring. Never
  imported directly by `pages/` — always adapted into real
  components first.
- `firestore.rules` — single source of truth for access control.
  Owned by nothing else; never inlined or duplicated elsewhere.

## Storage Model

- **Cloud Firestore (native mode)**: all metadata, ownership,
  conversation history, journal entries, streaks, subscription
  status, and the 768-dim journal embeddings (queried via the
  native Vector Search KNN index, COSINE distance).
- **No blob/file storage layer**: this app has no large binary
  media. Excel exports are generated on demand and streamed, never
  persisted server-side.

### Data Schema

```
users/{uid}
    displayName, email, photoURL, createdAt, lastLoginAt

users/{uid}/config/master_prompt          (single doc)
    aboutMe, tone: "Logical"|"Empathetic"|"Direct"|"Playful"|"ToughLove",
    goals: array<{id, text, createdAt, completed}>,
    frameworks: array<string>, thingsToAvoid, customInstructions,
    updatedAt

users/{uid}/sessions/{sessionId}          (working conversation)
    mode: "FreeWrite"|"DecisionMaking"|"Gratitude"|"GoalSetting"|"ProblemSolving",
    status: "active"|"ended", startedAt, lastMessageAt,
    messages: array<{role, content, ts, mood?}>

users/{uid}/journals/{journalId}          (finalized — created at End Session)
    sessionId, mode, createdAt,
    conversation: array<{role, content, ts}>   // immutable copy
    summary: {topic, mood_start, mood_end, mood_score (1-10),
              energy_level, key_insights[], action_items[],
              decision_status, emotional_themes[], growth_areas[]}
    embedding: vector<768>       // gemini-embedding-001, COSINE index
    weather: {condition, temperature_c, fetched_at} | null   // async

users/{uid}/stats/streaks                 (single doc)
    current_streak, longest_streak, last_journal_date, total_sessions

users/{uid}/stats/goals/{goalId}          (subcollection)
    text, source_journal_id, created_at, last_mentioned_at,
    times_mentioned, completed, completed_at

users/{uid}/subscription/status           (single doc — lazy created)
    tier: "free_trial"|"pro", period_start, period_end,
    messages_used_this_period, updated_at
```

Required index: composite vector index on
`users/{uid}/journals/{journalId}.embedding`, COSINE distance.
Create it via the Firebase MCP — do not hand-edit
`firestore.indexes.json` unless the deploy fails.

## Agent Architecture (Google ADK)

```
backend/agents/
    root_agent.py       Orchestrator — loads FIXED_SECURITY_PREAMBLE
                         + master_prompt, routes by mode/intent,
                         wraps journal_coach in a SequentialAgent
                         with mood_analyzer and the save pipeline
    journal_coach.py     Active conversation coach; one instruction
                         template per mode
    mood_analyzer.py     Per-turn structured extraction (Gemini + NVIDIA failover)
    summary_agent.py     End-of-session structured JSON summary (Gemini + NVIDIA 120B/11B)
    memory_agent.py      RAG: embed query → Firestore vector KNN →
                         answer with citations to specific entries
    analytics_agent.py   (Phase 3) BigQuery weather correlation +
                         natural-language insight generation
    model_utils.py       Dual-Provider Resilient Multi-Model Ladder:
                         - Primary: Google Gemini (gemini-3.7-flash, gemini-3.6-flash, gemini-flash-latest)
                         - Failover: NVIDIA NIM (meta/llama-3.2-11b-vision-instruct, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3.5-lightning-30b)
                         - Fallback: Grounded deterministic structured offline fallback
```

**Instruction precedence** (fixed, non-negotiable — see also
`AGENTS.md` §5):
```
1. FIXED_SECURITY_PREAMBLE   (hardcoded, never user-editable)
2. <user_master_prompt>...</user_master_prompt>   (context, not commands)
3. Mode-specific coaching instruction
4. Conversation history
```

## Auth and Access Model

- Every user signs in via Firebase Authentication, Google Sign-In
  only. No password credential exists anywhere in the system.
- Firebase ID tokens are short-lived (1hr) and verified server-side
  via the Admin SDK on every request — never cached past expiry.
- Ownership is 1:1 — every document under `users/{uid}/**` belongs
  to exactly that `uid`. There are no shared or collaborative
  documents.
- Access control is enforced twice, redundantly: `firestore.rules`
  (`users/{userId}/{document=**}`, owner-bound) and server-side
  route checks (`request.auth.uid == path uid`). Neither layer is
  allowed to be the sole line of defense.

## Threat Model (baseline — extend per-feature, don't replace)

| Zone | Threat | Countermeasure |
|---|---|---|
| Input Surfaces | Malicious/oversized payloads to `/api/chat`, `/api/save` | Pydantic schema validation on every endpoint; 400 on malformed body, never 500 |
| Input Surfaces | XSS via rendered chat markdown / journal content | Sanitize/encode all LLM output before rendering; never `dangerouslySetInnerHTML` raw model text |
| Planning & Reasoning | Prompt injection via the user-editable Master Prompt | Fixed, non-editable security preamble always prepended; `<user_master_prompt>` explicitly framed as context, not commands |
| Planning & Reasoning | Tool-routing hijack — user text tricking `root_agent` into misusing `analytics_agent`'s BigQuery tool | Tools take structured typed args only; BigQuery calls use parameterized queries, never raw SQL from user text |
| Tool Execution | SSRF via the weather tool call | Weather tool only accepts the allow-listed `noaa_gsod` dataset and the user's own profile city — no arbitrary URL fetch |
| Tool Execution | Privilege escalation through export/analytics endpoints | Every route re-verifies `request.auth.uid == path uid` server-side; never trust a `uid` in the request body |
| Memory & State | Cross-user Firestore reads/writes | Owner-bound rule on every path under `/users/{userId}/**`; verified with the Firebase MCP's rules-validation tool before every deploy |
| Memory & State | Session hijacking via stolen ID token | Short-lived tokens (1hr), verified server-side on every request |
| Inter-System Communication | Token/API-key leakage to the client bundle | `GEMINI_API_KEY` lives only in Secret Manager, injected as Cloud Run env vars — never in frontend `.env`, never in git |
| Inter-System Communication | Pub/Sub message spoofing (fake "journal-created" events) | Subscriber validates the Pub/Sub push OIDC JWT against the expected service account before processing |

## Invariants

1. The end-of-session save transaction (journal write + streak
   update + session-ended flag) is atomic. If any step fails, the
   client receives an error and its unsent input buffer is **not**
   cleared. Weather enrichment is never on this critical path — it
   is always async via Pub/Sub.
2. Auth is Google Sign-In only. No code path may add a password
   credential, password storage, or password reset flow without an
   explicit, logged product-scope change.
3. `firestore.rules` never contains a rule scoped to a single named
   subcollection — always the owner-bound wildcard covering
   `/users/{userId}/{document=**}`.
4. The Master Prompt is never passed to any agent as system
   authority — always wrapped in `<user_master_prompt>` tags and
   subordinate to `FIXED_SECURITY_PREAMBLE`.
5. Gemini calls are gated by `rate_limit.py`'s atomic
   check-and-increment **before** any model invocation — a
   maxed-out free-trial user never reaches the Gemini API.
