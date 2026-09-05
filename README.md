# Personal Gemini Journal — Agentic IDE Context Package

Drop this entire folder's contents into your Antigravity project
root (this replaces `frontend/`/`backend/` scaffolding — those get
created *by* the agent in Unit 02, they aren't in this package).

## Load Order

`AGENTS.md` is auto-loaded by Antigravity on every turn — nothing to
do manually there. Before your first prompt, just confirm it's at
the project root alongside `firestore.rules` and `.agent/workflows/`.

## Execution Order

Work through `context/feature-specs/00-build-plan.md` in numeric
order: 01 → 18. Each spec has a Goal, Design, Implementation,
Dependencies, and Verification Checklist. Don't skip ahead — later
units assume earlier ones are done (e.g. Unit 08 assumes Unit 07's
`/api/chat` exists).

## Standard Prompts

**To implement a unit:**
> Read context/feature-specs/[filename].md, update the
> progress-tracker.md file to mark this as in progress, and
> implement it exactly as specified.

**To fix a bug or error:**
1. Document it in `context/current-issues.md`.
2. Then run:
> Explore the current-issues.md file and deeply analyze the
> problem. Only when you have the analysis, give it back to me with
> the idea of how you're planning to solve it and then wait for me
> to give it the green light to execute it.

**Before your first prompt of the whole build:**
> Read AGENTS.md and confirm you understand the security rules
> before we start.

**On-demand workflows** (invoke by name when needed, not every turn):
- `/security-review` — before any deploy or after touching auth,
  Firestore rules, or agent instruction handling
- `/test-walkthrough` — before Unit 18 (deploy)
- `/generate-readme` — once feature-complete, to produce the
  submission README (this file is the *context-package* README —
  `/generate-readme` produces a separate, submission-facing one)

## What's in this package

```
AGENTS.md                          — always-on Rules (Antigravity's Custom Instructions equivalent)
firestore.rules                    — owner-bound access control, ready to deploy in Unit 04
.agent/workflows/
    security-review.md
    generate-readme.md
    test-walkthrough.md
context/
    project-overview.md            — product, scope, success criteria
    architecture.md                — stack, schema, agent design, invariants, threat model
    ui-context.md                  — theme tokens, Stitch screen inventory
    code-standards.md               — Python/FastAPI/React conventions
    ai-workflow-rules.md            — scoping, autonomy profiles, missing-requirement handling
    progress-tracker.md             — current phase, open questions, architecture decisions
    current-issues.md               — bug-loop template, empty
    source-blueprint-reference.md   — the original resolved blueprint this package was built from
    feature-specs/
        00-build-plan.md            — full sequenced roadmap, Phase 1–3 + Deploy
        01 through 18                — one spec per unit, in build order
```

## Open Questions Needing Your Input Before/During the Build

See `context/progress-tracker.md`'s Open Questions section — most
notably: the exact Stitch-derived color palette (resolved in
Unit 06), which Phase 3 enhancement(s) to build (both compose fine
if time allows), and confirming a Visa/Mastercard card is on hand
before Unit 18's Blaze billing step.
