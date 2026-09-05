# 02 — Project Scaffold + Firebase Setup

## Goal

Stand up the repo skeleton (`backend/`, `frontend/`) and the
Firebase project itself, so every later unit has a place to put
code and a live Firebase project to configure against.

## Design

No screens yet — this unit produces structure, not UI. Frontend
scaffold uses Vite's React + TypeScript template with Tailwind
configured per `ui-context.md`'s token approach (CSS custom
properties, no hardcoded hex).

## Implementation

1. Create `backend/` — FastAPI app skeleton with
   `backend/agents/`, `backend/routes/`, `backend/services/`
   subfolders per `architecture.md`'s System Boundaries (empty
   `__init__.py` files, one `main.py` with a health-check route).
2. Create `frontend/` — Vite + React 18 + TypeScript scaffold,
   Tailwind CSS installed and configured, `frontend/src/pages/` and
   `frontend/src/design/` subfolders created empty.
3. Create `firebase.json` at project root wiring Hosting to
   `frontend/dist` and Firestore rules to `firestore.rules`.
4. Using the Firebase MCP: create the Firebase project, enable the
   Google Sign-In provider only (do not enable Email/Password), and
   create a Firestore database in native mode, region `asia-south1`.
5. Confirm the Firebase project ID and web app config are captured
   into `frontend/.env` (client-safe config only — no secrets) and
   documented in `progress-tracker.md`'s Session Notes.

## Dependencies

- `google-adk`, `fastapi`, `uvicorn` (backend)
- `react`, `vite`, `tailwindcss` (frontend)
- Firebase MCP (already installed)

## MCPs Used & When to Invoke

- **`firebase-mcp-server`** — *Step 4, mandatory.* Create the
  Firebase project, enable the Google Sign-In provider only, and
  create the Firestore database in native mode, `asia-south1`. This
  is the core MCP dependency for this unit — do this via the MCP,
  not the Firebase console, so the config is reproducible from the
  agent's terminal history.
- **`google-cloud-resource-manager`** — *Before Step 4, if a fresh
  GCP project needs to be created or selected first.* Firebase MCP
  needs a target project to attach to; use this MCP to create/list
  projects if one doesn't already exist.
- **`google-cloud-quotas`** — *Optional, before Step 4.* Spot-check
  that `asia-south1` has the regional capacity/quota needed for the
  Firestore + eventual Cloud Run resources before committing to the
  region, so a quota surprise doesn't surface later at deploy time
  (Unit 18).

## Verification Checklist

- [ ] `backend/` runs a FastAPI health-check route locally
- [ ] `frontend/` runs `npm run build` clean with no errors
- [ ] Firebase project exists with Google Sign-In enabled and
      Email/Password provider explicitly **not** enabled
- [ ] Firestore database exists in native mode, `asia-south1`
- [ ] `firebase.json` correctly points Hosting at `frontend/dist`
      and rules at `firestore.rules`
- [ ] `progress-tracker.md` updated with the Firebase project ID
