# Personal Gemini Journal

## Overview

Personal Gemini Journal is a solo-user AI journaling companion built
for a developer challenge judged on: (1) a security constitution
governing the agent, (2) a working core app, and (3) at least one
"unique enhancement" built with an installed MCP. The user signs in
with Google, configures a one-time personalization profile (the
"Master Prompt"), then has multi-turn coaching conversations with
Gemini across five modes (Free Write, Decision Making, Gratitude,
Goal Setting, Problem Solving). Each session ends with an
auto-generated structured summary that is saved as an immutable
journal entry, embedded for semantic search, and enriched
asynchronously with local weather. A dashboard surfaces streaks,
mood trends, and past entries; a Memory Vault lets the user
semantically search their own journal history; an optional
analytics page correlates mood against weather.

## Goals

1. Ship all four core requirements from the Challenge brief: secure
   Google Sign-In auth, a working AI journaling loop with persistent
   memory, at least one MCP-powered unique enhancement, and a
   documented security constitution.
2. Guarantee the save path can never silently fail and can never be
   blocked by a non-critical external dependency (weather).
3. Protect the shared project-level Gemini free-tier quota
   (1,500 requests/day) from being exhausted by judges/testers,
   without requiring real payment processing.

## Core User Flow

1. Landing → "Continue with Google" (only auth method)
2. First-time onboarding → Master Prompt setup (about me, tone,
   goals, frameworks, things to avoid)
3. Dashboard (bento grid) → streak flame, mood sparkline,
   "Start Journaling" CTA, Memory Vault search, recent entries,
   export buttons, "My Patterns" teaser
4. New session → pick a mode → multi-turn chat with Gemini
5. End Session → auto-summary generated → journal saved
   (transactional) → streak updated → weather enrichment queued
   async via Pub/Sub
6. Back on Dashboard → new entry appears, streak/mood chart updates
7. Memory Vault → natural-language semantic search over past entries
8. My Patterns (Phase 3) → mood-vs-weather correlation, topic
   breakdown, AI insight cards
9. Export → download weekly / monthly / all-time `.xlsx`
10. Sign out

## Features

### Core Journaling
- Google Sign-In only (no password form)
- One-time Master Prompt personalization (tone, goals, frameworks,
  things to avoid)
- Five conversation modes, each with a dedicated coaching
  instruction
- Per-turn mood extraction (label, score 1–10, energy, topics) on a
  cheap classifier model
- End-of-session structured summary + transactional save
- 768-dim embedding per journal entry for semantic recall

### Dashboard & Recall
- Streak tracking (current/longest, last journal date)
- Mood trend sparkline
- Memory Vault: natural-language semantic search (Firestore vector
  KNN, COSINE) with citations to specific past entries
- Weekly / monthly / all-time Excel export via `openpyxl`

### Monetization Guardrail (also the SaaS-tier "unique feature")
- Free Trial tier: 10 chat messages per rolling 30-day period,
  enforced server-side, before any Gemini call is made
- Pro tier exists in the data model and UI as "Coming Soon" (no
  real payment processing); an admin can flip the Firestore field
  manually for a live demo

### Phase 3 — Unique Enhancement (pick one or both)
- **Life Pattern Analytics** — async weather enrichment via
  Pub/Sub → Cloud Run subscriber → BigQuery public dataset
  (`noaa_gsod`), surfaced as mood-vs-weather correlation and AI
  insight cards
- **Grounding Check** — a non-blocking, non-diagnostic resource
  card triggered by a sustained low mood score or explicit crisis
  language

## Scope

### In Scope
- Everything in "Core User Flow" and "Features" above
- Google Sign-In auth only
- Firestore as the single system of record and vector store
- Cloud Run backend, Firebase Hosting frontend
- One Phase 3 enhancement, built using an already-installed MCP
- A documented, versioned security constitution (`AGENTS.md` +
  workflows)

### Out of Scope
- Email/password authentication, password reset flows
- Real payment processing for the Pro tier
- Multi-user / shared / collaborative journals
- Any raw-SQL or arbitrary-URL tool access for agents
- A third-party vector database (Pinecone, etc.) — Firestore
  vector search covers this

## Success Criteria

1. A user can sign in with Google, complete onboarding, have a
   multi-turn journaling conversation, end the session, and see the
   entry appear on the dashboard with an updated streak.
2. A forced failure of the Firestore save transaction returns an
   error and does not clear the user's unsent input.
3. A second Google account signed into the same deployment has zero
   visibility into the first account's journals, sessions, or
   config (verified via `firestore.rules` and a manual
   cross-account test).
4. A free-trial account is blocked with a 429 (no Gemini call made)
   after its 10th message in a rolling 30-day period, and the
   remaining-count badge reflects this before and after.
5. At least one Phase 3 enhancement is live and demonstrably backed
   by a previously-unused installed MCP (`google-cloud-pubsub` and/or
   BigQuery).
6. `firestore.rules` deploys clean — no `allow read, write: if true`
   anywhere in the ruleset.
