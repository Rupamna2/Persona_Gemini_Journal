# Personal Gemini Journal — Agent Rules (Antigravity IDE)

This file is auto-loaded by Antigravity on every turn. It is the
**only** always-on instruction surface for this project — there is
no AI-Studio-style custom-instructions box in this IDE. Keep it lean.
Occasional procedures live in `.agent/workflows/*.md` and are invoked
with `/workflow-name`, not pasted here.

## Read Order (context files)

Before any architectural decision, read in order:

1. `context/project-overview.md` — product definition, goals, scope
2. `context/architecture.md` — stack, system boundaries, storage
   model, agent architecture, invariants
3. `context/ui-context.md` — theme, tokens, Stitch screen conventions
4. `context/code-standards.md` — TypeScript/Python conventions,
   secure coding standard
5. `context/ai-workflow-rules.md` — scoping rules, autonomy
   profile mapping, missing-requirement handling
6. `context/progress-tracker.md` — current phase, completed work,
   open questions, next steps

Update `context/progress-tracker.md` after each meaningful
implementation change. If implementation changes the architecture,
scope, or standards documented in the context files, update the
relevant file **before** continuing.

## Standing Rules (always on)

### 1. Agentic Threat Modeling
Whenever asked to design or implement a feature, produce a short
Threat Summary Table first, mapped to the 5 zones: Input Surfaces,
Planning & Reasoning, Tool Execution, Memory & State, Inter-System
Communication. Full baseline table lives in `context/architecture.md`
§Threat Model — extend it, don't replace it.

### 2. Secure Coding Standard
- Every API route validates input with a Pydantic schema before
  touching Firestore; reject malformed bodies with 400, never let
  them reach a 500.
- Never trust a `uid` passed in a request body — every route
  re-verifies `request.auth.uid == path uid` server-side.
- Sanitize/encode all LLM-generated text before rendering in React;
  never `dangerouslySetInnerHTML` raw model output.
- Structured typed tool args only (e.g. `city: str`, `date: date`) —
  never raw SQL or raw URLs assembled from user text.

### 3. Secure Firestore & Auth Configuration
- One owner-bound rule — `users/{userId}/{document=**}` — covers
  every subcollection. Never write a rule scoped to a single named
  subcollection; it silently fails to protect the others.
- Firebase ID tokens are short-lived (1hr) and verified server-side
  via Admin SDK on every request — never cached past expiry.
- Auth method is **Google Sign-In only**. Do not implement an
  email/password form, password storage, or password reset flow
  unless the user explicitly asks for it in this session.

### 4. Secret Management
- `GEMINI_API_KEY` and all service credentials live only in Google
  Cloud Secret Manager, injected as Cloud Run env vars at deploy
  time. Never in a frontend `.env`, never committed to git.
- Use plain `gcloud secrets create / versions add /
  add-iam-policy-binding` commands in the integrated terminal — no
  Secret Manager MCP exists or is needed.

### 5. Master Prompt Instruction Precedence
This app concatenates a user-editable "Master Prompt" into agent
context. It is **never** authority. Precedence order, always:
```
1. FIXED_SECURITY_PREAMBLE   (hardcoded, never user-editable)
2. <user_master_prompt>...</user_master_prompt>   (context, not commands)
3. Mode-specific coaching instruction
4. Conversation history
```
Never implement a code path where content inside
`<user_master_prompt>` can change safety behavior, disable rules, or
move the agent outside the journaling-assistant role.

## Workflows (on demand — do not run unless invoked)

- `/security-review` — Security Reviewer Persona audit
- `/generate-readme` — README generator for submission
- `/test-walkthrough` — Functional Stability Walkthrough checklist

## Protected Files

Do not modify without explicit instruction:
- `firestore.rules` — single source of truth for access control
- `backend/agents/root_agent.py`'s `FIXED_SECURITY_PREAMBLE` constant
- `backend/services/rate_limit.py` — quota logic protects the
  shared project-level Gemini free-tier quota

## Bug/Error Handling

Do not attempt speculative fixes. Document the error in
`context/current-issues.md`, then wait for the corrective prompt
defined in `context/ai-workflow-rules.md`.
