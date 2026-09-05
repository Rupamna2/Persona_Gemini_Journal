# 01 — Security Constitution Drop-In

## Goal

Establish the always-on security rules and on-demand workflows in
the Antigravity IDE before any product code is written, and confirm
the agent has actually loaded them.

## Design

No UI. This unit produces the repo-root instruction surface that
every later unit is governed by: `AGENTS.md` plus three workflow
files under `.agent/workflows/`.

## Implementation

1. Place `AGENTS.md` at the project root (already authored — see
   the repo-root file in this context package).
2. Create `.agent/workflows/security-review.md`,
   `.agent/workflows/generate-readme.md`, and
   `.agent/workflows/test-walkthrough.md` (already authored — see
   this context package's `.agent/workflows/` directory).
3. Create `firestore.rules` at the project root (already authored)
   even though it won't be deployed until Unit 04 — this lets every
   subsequent unit reference the final rule shape from the start.
4. Ask the agent directly: *"Read AGENTS.md and confirm you
   understand the security rules before we start."* This is a
   cheap sanity check that the Rules file loaded — do not proceed
   to Unit 02 until the agent's summary correctly reflects the
   Google-Sign-In-only rule, the owner-bound Firestore rule, and
   the Master Prompt instruction-precedence order.

## Dependencies

- None (this is the first unit).

## MCPs Used & When to Invoke

- **`google-developer-knowledge`** — *Optional, before authoring
  `AGENTS.md`/workflow files.* Antigravity's Rules-file and
  Workflows conventions can shift between IDE releases; ask it to
  confirm the current `AGENTS.md` / `.agent/workflows/*.md`
  conventions are still accurate before treating the files in this
  package as final, since this spec was written against a specific
  point-in-time understanding of the IDE.
- No other MCP is needed for this unit — it's file placement plus a
  verbal comprehension check, not a live Google Cloud/Firebase
  operation.

## Verification Checklist

- [ ] `AGENTS.md` exists at project root and is not empty
- [ ] All three workflow files exist under `.agent/workflows/`
- [ ] `firestore.rules` exists at project root
- [ ] The agent's summary of `AGENTS.md`, when asked, correctly
      states: Google Sign-In only, one owner-bound Firestore rule,
      and the 4-step Master Prompt instruction precedence
- [ ] `progress-tracker.md` updated: Phase 1 marked in progress →
      complete
