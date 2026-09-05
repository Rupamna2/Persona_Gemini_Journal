# 05 — Master Prompt Config

## Goal

Let a first-time user configure their one-time personalization
profile (the Master Prompt) and persist it, so every later agent
unit has real data to read instead of a placeholder.

## Design

Onboarding screen (Screen Inventory #2): single-column form —
"About Me" textarea, "Tone" segmented control (Logical / Empathetic
/ Direct / Playful / Tough Love), tag-style multi-add "My Goals"
input, checkboxes for frameworks (5-Why, Pros-Cons, Decision Matrix,
SWOT, First-Principles), "Things to Avoid" textarea. Friendly,
generous whitespace, matching the dark theme once tokens are set.
Build the real form now (not a shell) since its shape is fully
specified and it has no dependency on Stitch's visual polish to
function correctly — restyle later if Unit 06's Stitch export
differs cosmetically.

## Implementation

1. `backend/routes/master_prompt.py`: `GET /api/master-prompt`
   (returns the doc, or a sensible empty default if it doesn't
   exist yet) and `POST /api/master-prompt` (validates and writes
   it) — both behind `verify_token`.
2. Pydantic model matching the `master_prompt` schema in
   `architecture.md`: `aboutMe: str`, `tone: Literal[...]`,
   `goals: list[Goal]`, `frameworks: list[str]`,
   `thingsToAvoid: str`, `customInstructions: str`.
3. `POST` writes to `users/{uid}/config/master_prompt` with
   `updatedAt` set server-side (never trust a client-supplied
   timestamp).
4. Frontend onboarding page: controlled form matching the fields
   above, calls `POST /api/master-prompt` on submit, then routes to
   Dashboard.
5. Once saved, this doc is read (never re-created) by
   `root_agent` in Unit 07 — do not duplicate the read logic
   in the frontend beyond what's needed to pre-fill an "edit
   profile" view if one is added later.

## Dependencies

- Unit 03 (auth — every call is per-`uid`)
- Unit 04 (Firestore rules already protect this path)

## MCPs Used & When to Invoke

- **`google-cloud-firestore`** — *Optional, during manual testing
  of Step 3–4.* Spot-check that
  `users/{uid}/config/master_prompt` was written with the expected
  shape after a test `POST`, rather than inferring correctness only
  from the HTTP response.
- No MCP is required to build the route or the form component
  themselves — this is a standard CRUD path against the Admin SDK,
  already covered by Unit 04's deployed rules.

## Verification Checklist

- [ ] `GET /api/master-prompt` returns 401 with no token, an empty
      default for a new user, and the saved doc for a returning one
- [ ] `POST /api/master-prompt` rejects a malformed body with 400
      (e.g. an invalid `tone` value)
- [ ] Submitting the onboarding form persists to
      `users/{uid}/config/master_prompt` and routes to Dashboard
- [ ] A second account's `POST` cannot write to the first account's
      `master_prompt` doc (covered by Unit 04's rule, spot-checked
      here)
