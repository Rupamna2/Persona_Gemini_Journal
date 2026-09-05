# AI Workflow Rules

## Approach

Build this project incrementally using a spec-driven workflow. The
context files and `context/feature-specs/*.md` define what to build,
how to build it, and the current state of progress. Always implement
against these specs — do not infer or invent product behavior, API
shapes, or agent instructions from scratch. This is a judged
submission; unverifiable "vibe-coded" behavior is a liability, not a
shortcut.

## Autonomy Profile Mapping

Antigravity has 4 named profiles: Secure mode, Review-driven
development, Agent-driven development, Custom. Map every unit to
one before starting it:

| Task | Profile |
|---|---|
| Project scaffolding, frontend UI shells, Excel export | Agent-driven development |
| Firebase setup via MCP, ADK agent code, BigQuery queries, Cloud Run deploy | Review-driven development (default for most of this build) |
| Authentication, Firestore security rules, Secret Manager wiring, the save transaction | Secure mode (review every command) |

## Scoping Rules

- Work on one feature unit at a time, per
  `context/feature-specs/00-build-plan.md`.
- Prefer small, verifiable increments over large speculative
  changes.
- Do not combine unrelated system boundaries in a single
  implementation step (e.g. never combine an agent's prompt logic
  with the route that calls it, or a backend endpoint with its
  frontend wiring — those are separate specs).

## When to Split Work

Split an implementation step if it combines:

- Backend logic and frontend wiring for the same feature
- Two unrelated system boundaries (e.g. `backend/agents/` and
  `firestore.rules` changes in the same step)
- Behavior not clearly defined in a feature spec — stop and log an
  open question instead of guessing

If a change cannot be verified end to end quickly, the scope is too
broad — split it.

## Handling Missing Requirements

- Do not invent product behavior, exact copy, exact hex color
  values, or agent prompt wording not defined in the context files
  or feature specs.
- If a requirement is ambiguous (e.g. an exact Tailwind spacing
  value after a Stitch import), resolve it by matching the nearest
  existing screen's convention, then note the assumption in
  `progress-tracker.md`.
- If a requirement is genuinely missing (not just under-specified),
  add it as an open question in `progress-tracker.md` before
  continuing — do not block the whole session on it if the rest of
  the unit is unaffected.

## Protected Files

Do not modify the following unless explicitly instructed:

- `firestore.rules`
- `backend/agents/root_agent.py`'s `FIXED_SECURITY_PREAMBLE` constant
- `backend/services/rate_limit.py`
- `AGENTS.md` and `.agent/workflows/*.md`

## Keeping Docs in Sync

Update the relevant context file whenever implementation changes:

- System architecture, agent boundaries, or the data schema →
  `architecture.md`
- Storage model or invariant decisions → `architecture.md`
- Code conventions or standards → `code-standards.md`
- Feature scope or the screen inventory → `project-overview.md` /
  `ui-context.md`

## Before Moving to the Next Unit

1. The current unit works end to end within its defined scope.
2. No invariant defined in `architecture.md` was violated.
3. `progress-tracker.md` reflects the completed work.
4. The relevant build passes (`npm run build` for frontend units,
   a clean FastAPI startup + the unit's manual test steps for
   backend units).
5. If the unit touched auth, Firestore rules, or the save
   transaction: confirm no `allow read, write: if true` was
   introduced anywhere in `firestore.rules`.

## Bug / Error Handling Loop

1. Document the observed error, the request/response involved, and
   what was expected, in `context/current-issues.md`.
2. Run this exact prompt: *"Explore the current-issues.md file and
   deeply analyze the problem. Only when you have the analysis,
   give it back to me with the idea of how you're planning to solve
   it and then wait for me to give it the green light to execute
   it."*
3. Do not implement a fix until explicit green light is given.
