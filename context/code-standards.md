# Code Standards

## General

- Keep modules small and single-purpose — a route file does not
  contain agent prompt logic; an agent file does not contain
  Firestore transaction code.
- Fix root causes. Do not layer a workaround (retry loop, silent
  catch) over a bug whose actual cause hasn't been identified.
- Do not mix unrelated concerns in one component, route, or agent.

## Python (Backend)

- Type hints throughout; no bare `dict`/`Any` at a function
  boundary that crosses into Firestore or the Gemini API.
- Every FastAPI route takes a Pydantic model as its body — never a
  raw `dict` parsed ad hoc.
- Validate unknown external input (webhook payloads, Pub/Sub push
  bodies) at the boundary before trusting any field on it.
- Firestore transactions use the `@firestore.transactional`
  decorator pattern (see `backend/services/rate_limit.py` as the
  reference implementation) — never a manual read-then-write
  without a transaction when a race condition is possible.
- Model calls always go through
  `backend/agents/model_utils.py::generate_content_with_fallback`
  — never call `client.models.generate_content` directly from a
  route or another agent file.

## FastAPI

- Route handlers stay focused on: verify auth → validate input →
  delegate to `agents/` or `services/` → shape response. No
  agent-prompt construction or Firestore transaction code inline
  in a route.
- Every protected route depends on `verify_token` (Admin SDK ID
  token verification) — no route infers `uid` from anything other
  than the verified token.
- Return consistent, predictable response shapes. Errors return a
  structured `{error, ...}` body, not a bare string.

## React / Frontend

- Functional components with hooks only.
- Screens live one-per-file in `frontend/src/pages/`. Stitch's raw
  export lives in `frontend/src/design/` and is never imported
  directly — always translated into a real component first.
- Charts use Recharts (per the Stitch handoff convention).
- Never `dangerouslySetInnerHTML` with unsanitized model output —
  run it through `DOMPurify` first.
- No client-side trust of any quota, tier, or ownership value —
  the UI reflects what the backend returns; it never computes or
  overrides these itself.

## Styling

- Use the CSS custom property tokens defined in `ui-context.md` —
  no hardcoded hex values in components.
- Follow the border-radius scale defined in `ui-context.md`.

## API Routes

- Validate and parse request input before any logic runs; reject
  malformed input with 400, never let it reach a 500.
- Enforce auth and ownership (`request.auth.uid == path uid`)
  before any mutation — every route, every time, even ones that
  feel "obviously" scoped correctly by the frontend.
- Rate-limit-gated routes (`/api/chat`) call
  `enforce_and_increment` as the **first** line in the handler,
  before any agent or Gemini call.

## Data and Storage

- Metadata, conversation history, and journal content all live in
  Firestore — there is no separate blob/file store in this
  project's scope.
- Embeddings are stored inline on the journal document as a
  768-dim vector field, not in a separate collection.
- Do not persist generated Excel exports server-side — stream them
  directly via `StreamingResponse` and discard.

## File Organization

- `backend/agents/` — ADK agent definitions and model routing
- `backend/routes/` — FastAPI route handlers
- `backend/services/` — rate limiting, save-transaction logic,
  embedding generation, weather subscriber logic
- `frontend/src/pages/` — one real, wired screen per file
- `frontend/src/design/` — raw, unwired Stitch exports
- `firestore.rules` — access control, owned by nothing else
