# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- Phase 3 — Enhancements & Geolocation Engine (Completed) / Deploy (Ready)

## Current Goal

- Unit 19 completed. Ready to proceed to Unit 18: Deploy — Cloud Run backend + Firebase Hosting frontend + firestore.rules (`context/feature-specs/18-deploy.md`).

## Completed

- **Unit 01 — Security constitution drop-in + sanity check**: Verified `AGENTS.md` at root, verified `.agent/workflows/` (`security-review.md`, `generate-readme.md`, `test-walkthrough.md`), verified `firestore.rules` with single owner-bound wildcard rule, and confirmed agent comprehension of standing rules (Google-Sign-In only, owner-bound Firestore rule, 4-step Master Prompt instruction precedence, secret management, server-side rate-limit gating, and secure coding standards).
- **Unit 02 — Project scaffold + Firebase setup**: Created FastAPI backend skeleton (`backend/agents/`, `backend/routes/`, `backend/services/`, `backend/main.py`, `backend/requirements.txt`), React 18 + Vite + Tailwind frontend (`frontend/src/pages/`, `frontend/src/design/`, `frontend/src/firebase.ts`, `frontend/.env`), `firebase.json`, `.firebaserc`, verified local FastAPI `/api/health` 200 OK, confirmed `npm run build` passes clean, and verified active Firebase project `avid-pentameter-mr6mz` and Firestore database in `asia-south1`.
- **Unit 03 — Auth: Google Sign-In only**: Implemented `backend/auth.py` with `verify_token` dependency (rejects missing/invalid/expired tokens with 401), created `backend/services/user_service.py` (`users/{uid}` sync for `createdAt` and `lastLoginAt`), added `POST /api/auth/sync` and `GET /api/auth/me` route endpoints with Pydantic validation, created `frontend/src/auth/AuthContext.tsx` with Google popup auth and token management, created `LandingPage.tsx` with single Google Sign-In action (zero password/reset fields), and verified all 6 unit/integration tests passing.
- **Unit 04 — Firestore security rules**: Validated and enforced `firestore.rules` containing exactly one owner-bound rule (`users/{userId}/{document=**}`) covering all subcollections with `request.auth.uid == userId`, deny-all fallback on non-user resources, zero `allow read, write: if true` occurrences, and automated test verification (`backend/tests/test_firestore_rules.py`).
- **Unit 05 — Master Prompt config (backend + wiring)**: Built `backend/routes/master_prompt.py` with Pydantic validation for `aboutMe`, `tone` (`Logical`, `Empathetic`, `Direct`, `Playful`, `ToughLove`), `goals`, `frameworks` (`5-Why`, `Pros-Cons`, `Decision Matrix`, `SWOT`, `First-Principles`), `thingsToAvoid`, `customInstructions`, and server-side `updatedAt`. Created `frontend/src/pages/OnboardingPage.tsx` with full interactive form and token-authenticated sync to `users/{uid}/config/master_prompt`. Verified with 5 unit/integration tests (13 total tests passing).
- **Unit 06 — UI shells (Stitch screens, unwired)**: Established canonical calm dark design system tokens in `ui-context.md` and `frontend/src/index.css`. Built all 7 screens as modular React + Tailwind components in `frontend/src/pages/` (`LandingPage`, `OnboardingPage`, `DashboardPage` with Recharts bento grid, `ChatPage` with mode badges & live mood indicator, `MemoryVaultPage` with semantic search cards, `PatternsPage` with NOAA weather correlation charts, `SubscriptionPage` with quota tier comparison). Verified clean client-side routing in `App.tsx` and successful `npm run build` (2.14s).
- **Unit 07 — Journal chat agents backend**: Implemented `backend/agents/model_utils.py` (resilient fallback ladder `gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-flash-latest` → `gemini-2.5-flash`), `backend/agents/root_agent.py` with hardcoded `FIXED_SECURITY_PREAMBLE` and strict 4-step instruction precedence, `backend/agents/journal_coach.py` (5 mode templates), `backend/agents/mood_analyzer.py` (structured mood JSON extraction), and `backend/routes/chat.py` (`POST /api/chat` with session accumulation). Verified with 6 unit and integration tests (19 total tests passing).
- **Unit 08 — Chat UI wiring**: Wired `frontend/src/pages/ChatPage.tsx` to `POST /api/chat` using authenticated Bearer token. Implemented optimistic turn bubbles, DOMPurify HTML sanitization, live typing status, inline network/API error recovery with retry affordance without dropping draft turns, and marked session save hook for Unit 09. Verified clean `npm run build` (2.27s).
- **Unit 09 — Session save pipeline backend**: Built `backend/agents/summary_agent.py` (structured JSON synthesis: title, insights, action items, mood delta), `backend/services/embeddings.py` (768-dim normalized MRL vectors), `backend/services/save_pipeline.py` (single atomic transaction writing journal doc with `weather: null`, updating streak logic for today/yesterday/broken streak, and setting session `status: "ended"`), `backend/routes/save.py` (`POST /api/save` with non-blocking async Pub/Sub trigger), and wired frontend `ChatPage.tsx`. Verified with 6 unit and integration tests (25 total tests passing).
- **Unit 10 — Rate limit + subscription backend service**: Implemented `backend/services/rate_limit.py` with transactional atomic gating (`FREE_TRIAL_MESSAGE_LIMIT = 10`, `TRIAL_PERIOD_DAYS = 30`), lazy rolling 30-day period resets, pro-tier bypass, and custom `RateLimitExceeded` (HTTP 429) exception. Plugged `enforce_and_increment` into `POST /api/chat` before any prompt loading/model execution. Created `GET /api/subscription/status`. Verified with 6 unit and integration tests (31 total tests passing).
- **Unit 11 — Dashboard + subscription UI wiring**: Built `backend/routes/dashboard.py` (`GET /api/dashboard` aggregated endpoint). Wired `DashboardPage.tsx` with live streak flame, Recharts mood trend sparkline, recent entries with mood emojis, and plan quota badge. Wired `ChatPage.tsx` with live quota countdown and non-destructive 429 rate-limit blocking modal. Wired `SubscriptionPage.tsx` with live progress bar and disabled Pro card. Verified with 2 new backend integration tests (33 total backend tests passing) and clean frontend production build (2.29s).
- **Unit 12 — Memory Vault backend KNN search**: Created `firestore.indexes.json` with composite vector index on `embedding` (768-dim, COSINE). Built `backend/agents/memory_agent.py` with 768-dim MRL query embedding, Firestore KNN search strictly scoped to `users/{uid}/journals`, and grounded synthesis with strict anti-hallucination prompts. Created `backend/routes/memory.py` with `GET /api/memory/search`, 400 validation on empty/oversized inputs (>500 chars), and citation payloads. Verified with 6 unit and integration tests (39 total backend tests passing).
- **Unit 13 — Memory Vault UI wiring**: Connected `DashboardPage.tsx` semantic search tile with pre-fill query routing. Built live interactive search in `MemoryVaultPage.tsx` consuming `GET /api/memory/search` with Bearer auth, DOMPurify HTML sanitization for AI synthesis, citation cards displaying rank, match percentage, verified source badges, and informative calm zero-state screens. Verified clean frontend production build (2.26s).
- **Unit 14 — Excel export**: Created `backend/routes/export.py` with in-memory `openpyxl` workbook generator (`weekly`, `monthly`, `all`), custom header formatting, column auto-width, and `StreamingResponse` transmission (zero disk/cloud storage footprints). Wired the 3 export buttons in `DashboardPage.tsx` with loading indicators. Verified with 4 unit/integration tests (43 total backend tests passing) and clean frontend build (2.21s).
- **Unit 15 — Weather enrichment subscriber**: Built `backend/services/weather_enrichment.py`, `backend/subscriber/auth_oidc.py` (strict OIDC JWT verification blocking spoofed push requests before BigQuery invocation), and `backend/subscriber/main.py` (Cloud Run push subscriber service with `/pubsub/push` and `/health`). Implemented parameterized BigQuery NOAA GSOD dataset querying with resilient climate fallbacks and direct field updates on `users/{uid}/journals/{journalId}.weather`. Verified with 5 unit/integration tests (48 total backend tests passing) and clean frontend build (2.15s).
- **Unit 16 — Life Pattern Analytics**: Built `backend/agents/analytics_agent.py` (mood trends, NOAA weather condition grouping, topic breakdowns, and grounded Gemini AI insight generation) and `backend/routes/analytics.py` (`GET /api/analytics/patterns`). Connected `PatternsPage.tsx` to live analytics with honest "Not Enough Data Yet" zero-state and DOMPurify sanitization. Verified with 4 unit/integration tests (52 total backend tests passing) and clean frontend build (2.23s).
- **Unit 17 — Grounding check safety net**: Implemented non-diagnostic responsible-AI crisis phrase and sustained low-mood conditional detection in `root_agent.py` and `routes/chat.py`. Wired calm, dismissible, non-blocking support card with 24/7 lifeline chips and DOMPurify sanitization in `ChatPage.tsx`. Verified with 4 unit/integration tests (56 total backend tests passing) and clean frontend build (2.15s).
- **Multi-Provider Resilient LLM Engine (Gemini + NVIDIA NIM 120B/11B)**: Integrated dual-provider architecture in `backend/agents/model_utils.py` with instant failover from Google Gemini (when 429 quota exhausted) to NVIDIA NIM (`meta/llama-3.2-11b-vision-instruct`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3.5-lightning-30b`), robust JSON cleaning in `mood_analyzer.py` and `summary_agent.py`.
- **Unit 19 — Geo-Location Memory & Location-Mood Happiness Predictor with Free Weather Integration (India + Global)**: Implemented Open-Meteo free real-time weather API integration (no API key required) supporting Indian cities (Bengaluru, Mumbai, Delhi, Kolkata, Chennai, Hyderabad, Pune, Goa, Jaipur, Ahmedabad, Kochi, Chandigarh, Noida, Gurugram) and global metros with BigQuery NOAA fallback. Built Location-Mood Happiness Predictor in `analytics_agent.py` and `PatternsPage.tsx` comparing mood deltas across locations, location-enriched 768-dim embeddings in `routes/save.py`, geolocation metadata & weather badge cards in `MemoryVaultPage.tsx`, and geolocation header pill with auto-location detection in `ChatPage.tsx`. Verified with 8 unit/integration tests (64 total backend tests passing) and clean frontend build (7.51s).

## In Progress

- Unit 18 — Deploy: Cloud Run backend + Firebase Hosting frontend + firestore.rules (`context/feature-specs/18-deploy.md`)

## Next Up

- `context/feature-specs/18-deploy.md`

## Open Questions

- Which Phase 3 enhancement(s) to actually build: Life Pattern
  Analytics, Grounding Check, or both. Both compose well and share
  no conflicting scope, so building both is viable if time permits.
- Whether the optional global circuit breaker
  (`system/quota_guard` doc, §13 of the source blueprint) is worth
  the extra implementation step for a judging-window-scale demo, or
  whether per-account limits alone are sufficient.
- Confirm a Visa/Mastercard debit or credit card is available
  before the Cloud Run deploy step (RuPay cards have been reported
  to fail GCP Blaze billing verification).

## Architecture Decisions

- **Auth is Google Sign-In only, no email/password path.** Chosen
  over Blueprint 1/2's email/password suggestion because the
  official Challenge brief only ever asks for Google Sign-In, and
  the stricter security directive in the source docs prefers
  federated identity. Removes an entire OWASP surface (password
  storage/reset) for zero feature loss against the actual spec.
- **Weather enrichment is async via Pub/Sub, never on the save
  path.** A synchronous BigQuery weather call before the journal
  write returns would let an external API hiccup block a user's
  save — directly violates the "save must not silently fail"
  invariant. Reuses the already-installed but previously-unused
  `google-cloud-pubsub` MCP.
- **Model fallback ladder leads with `gemini-3.7-flash`**, not
  `gemini-3.6-flash` or the retired `gemini-2.0-flash`, because it
  is Google's current best model for coding/agents as of this
  build (GA Aug 13, 2026). `gemini-3.6-flash` stays in the chain as
  a named fallback so the brief's literal "3.6 Flash" wording is
  still technically satisfied.
- **Embeddings pinned to `gemini-embedding-001`, truncated to
  768-dim** (native is 3072-dim, MRL-truncatable) to keep the
  Firestore vector index cheap without a meaningful MTEB quality
  loss at this scale.
- **One owner-bound wildcard Firestore rule** —
  `users/{userId}/{document=**}` — instead of per-subcollection
  rules, so every current and future subcollection (`config`,
  `sessions`, `journals`, `stats`) is protected by construction
  rather than by remembering to update the rule each time a new
  subcollection is added.
- **Rate limiting is server-side only, enforced before the Gemini
  call**, not client-side and not post-hoc — this is what actually
  protects the shared project-level Gemini free-tier quota
  (1,500 requests/day) during the judging window.
- **Frontend stack is React + Vite + Tailwind**, not vanilla
  HTML/CSS/JS as one source doc suggested, because Stitch's native
  export target for Antigravity is React + Tailwind and it is a
  better fit for the bento-grid dashboard.

## Session Notes

- Source material for this context system is a pre-resolved
  production blueprint (gap analysis already performed against
  three conflicting source docs) — see the original blueprint
  document for the full gap table if any decision above needs
  re-litigating.
- Target IDE is Antigravity, not AI Studio Build Mode — this
  project's "Rules" live in `AGENTS.md` at the repo root, not in a
  custom-instructions text box. `.agent/workflows/*.md` holds the
  on-demand procedures (`/security-review`, `/generate-readme`,
  `/test-walkthrough`).
- Firebase project provisioned: `avid-pentameter-mr6mz` (Project Number: `666472073641`), Web App ID: `1:666472073641:web:debe8c1ad3c37130dddcb8`, Firestore native database in `asia-south1`. Client-safe parameters recorded in `frontend/.env`.
- MCPs already installed: `cloudrun`, `firebase-mcp-server`,
  `google-cloud-firestore`, `google-cloud-logging`,
  `google-cloud-pubsub`, `google-cloud-quotas`,
  `google-cloud-resource-manager`, `google-developer-knowledge`.
  Still need to install: Stitch MCP (required, §9), BigQuery MCP
  (only if building Life Pattern Analytics).
- Billing: Cloud Run, Pub/Sub, BigQuery, and Secret Manager all
  require the GCP project to be on the Blaze plan (card on file),
  even at $0 usage. Gemini API itself stays free via an AI Studio
  key as long as a Vertex AI project is not used instead.
