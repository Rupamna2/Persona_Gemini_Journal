# Build Plan — Personal Gemini Journal

Ordering rules applied throughout: dependencies first; security
before functionality; backend before frontend wiring; UI shells
before real data.

## Prerequisites (before Unit 01)

- [x] `gcloud auth login` / `gcloud auth application-default login`
- [x] `firebase login`
- [x] Core MCPs installed: `cloudrun`, `firebase-mcp-server`,
      `google-cloud-firestore`, `google-cloud-logging`,
      `google-cloud-pubsub`, `google-cloud-quotas`,
      `google-cloud-resource-manager`, `google-developer-knowledge`
- [ ] Stitch MCP installed + API key — Agent panel → `...` → MCP
      Servers → search "stitch" → Install; key from
      stitch.withgoogle.com → Stitch Settings → API Key. Verify with
      "List my Stitch projects" (should return empty list, not an
      error).
- [ ] BigQuery MCP installed — only required if building Unit 16
      (Life Pattern Analytics). Requires billing enabled + BigQuery
      API enabled (`gcloud services enable bigquery.googleapis.com`)
      + `roles/bigquery.user`.
- [ ] Secret Manager: no MCP exists or is needed — the agent runs
      `gcloud secrets ...` directly in the integrated terminal.

## Phase 1 — Security Constitution (Challenge requirement #1)

| # | Unit | Autonomy Profile |
|---|---|---|
| 01 | Security constitution drop-in + sanity check | Secure mode |

## Phase 2 — Core App (Challenge requirement #2)

| # | Unit | Autonomy Profile | Depends On |
|---|---|---|---|
| 02 | Project scaffold + Firebase project setup | Agent-driven | 01 |
| 03 | Auth — Google Sign-In only | Secure mode | 02 |
| 04 | Firestore security rules | Secure mode | 02, 03 |
| 05 | Master Prompt config (backend + wiring) | Review-driven | 03, 04 |
| 06 | UI shells — all 7 Stitch screens, unwired | Agent-driven | 02 |
| 07 | Journal chat agents (backend: root_agent, journal_coach, mood_analyzer, `/api/chat`) | Review-driven | 03, 04, 05 |
| 08 | Chat UI wiring | Agent-driven | 06, 07 |
| 09 | Session save pipeline (backend: summary_agent, embedding, transaction, Pub/Sub publish) | Secure mode | 07 |
| 10 | Rate limit + subscription service (backend) | Secure mode | 03, 04 |
| 11 | Dashboard + subscription UI wiring (streaks, mood chart, recent entries, quota badge, 429 modal, pricing page) | Agent-driven | 06, 09, 10 |
| 12 | Memory Vault backend (memory_agent, vector search, `/api/memory/search`) | Review-driven | 09 |
| 13 | Memory Vault UI wiring | Agent-driven | 06, 12 |
| 14 | Excel export | Agent-driven | 09 |

## Phase 3 — Unique Enhancement (Challenge requirement #3, pick one or both)

| # | Unit | Autonomy Profile | Depends On |
|---|---|---|---|
| 15 | Weather enrichment subscriber (Pub/Sub → Cloud Run → BigQuery, patches journal.weather) | Review-driven | 09 |
| 16 | Life Pattern Analytics (analytics_agent + My Patterns UI wiring) | Review-driven | 06, 15 |
| 17 | Grounding Check safety net (optional, composes independently) | Review-driven | 07 |
| 19 | Geo-Location Memory & Location-Mood Happiness Predictor (Open-Meteo free API + India/Global support) | Review-driven | 09, 12, 15, 16 |

## Deploy

| # | Unit | Autonomy Profile | Depends On |
|---|---|---|---|
| 18 | Deploy — Cloud Run backend + Firebase Hosting frontend + firestore.rules | Secure mode | All units built this session |

## MCP Usage Map (consolidated — see each spec's own "MCPs Used & When to Invoke" for detail)

| # | Unit | MCP(s) Used | When |
|---|---|---|---|
| 01 | Security constitution | `google-developer-knowledge` (optional) | Before authoring `AGENTS.md`/workflows, to confirm current Antigravity conventions |
| 02 | Scaffold + Firebase setup | `firebase-mcp-server`, `google-cloud-resource-manager`, `google-cloud-quotas` (optional) | Creating the Firebase project, enabling Google Sign-In, creating Firestore in `asia-south1` |
| 03 | Auth | `firebase-mcp-server` | Confirming the auth provider config before writing verification code |
| 04 | Firestore rules | `firebase-mcp-server`, `google-cloud-firestore` (optional) | Deploying + validating `firestore.rules` |
| 05 | Master Prompt | `google-cloud-firestore` (optional) | Spot-checking the written doc shape during testing |
| 06 | UI shells | **Stitch MCP** | Every one of the 5 screen generations — install first per Prerequisites |
| 07 | Chat agents backend | `google-developer-knowledge`, `google-cloud-quotas` (optional) | Confirming current ADK API + Gemini model aliases before writing `model_utils.py` |
| 08 | Chat UI wiring | None | — |
| 09 | Save pipeline backend | `google-cloud-pubsub`, `google-cloud-firestore`, `google-cloud-logging` | Creating/verifying the `journal-created` topic, inspecting the transaction, confirming publish-failure logging |
| 10 | Rate limit backend | `google-cloud-firestore`, `google-cloud-logging` | Inspecting subscription/status doc; confirming zero Gemini calls on a blocked request |
| 11 | Dashboard/subscription UI | `google-cloud-logging` (optional) | Only if badge numbers mismatch during testing |
| 12 | Memory Vault backend | `google-cloud-firestore` | Creating the composite vector index — mandatory, this unit depends on it |
| 13 | Memory Vault UI | None | — |
| 14 | Excel export | None | — |
| 15 | Weather subscriber | `google-cloud-pubsub`, `cloudrun`, **BigQuery MCP**, `google-cloud-logging` | Topic/subscription setup, subscriber deploy, `noaa_gsod` query, spoofing/failure log checks |
| 16 | Life Pattern Analytics | **BigQuery MCP**, `google-cloud-firestore` (optional), `google-cloud-logging` (optional) | Aggregate queries for `analytics_agent` |
| 17 | Grounding Check | None | — |
| 18 | Deploy | `google-cloud-resource-manager`, `google-cloud-quotas` (optional), `cloudrun`, `firebase-mcp-server`, `google-cloud-logging`, `google-developer-knowledge` (optional) | Billing check → deploy backend/frontend/rules → confirm clean logs |

Two MCPs must be installed before their first use: **Stitch MCP**
(required, blocks Unit 06) and **BigQuery MCP** (only required if
building Unit 15/16). Everything else in this table is already
installed per the Prerequisites list above.

## Testing

Run `/test-walkthrough` before Unit 18 (deploy). See
`.agent/workflows/test-walkthrough.md`.

## Deliverables Checklist (from the Challenge brief)

- [ ] `AGENTS.md` + workflows (configured security directives)
- [ ] Working app meeting all 4 core requirements
- [ ] At least one Phase 3 enhancement, built with an MCP
- [ ] README (`/generate-readme`)
- [ ] Screenshots: AGENTS.md, login, master prompt, chat, summary,
      memory vault, patterns dashboard, Excel download,
      firestore.rules, Cloud Run deploy confirmation
