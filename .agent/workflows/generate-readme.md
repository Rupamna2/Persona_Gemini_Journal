# /generate-readme

Invoke once the app is feature-complete and ready for submission.

## Output

Generate `README.md` at the project root with these sections, in
order:

1. **What this is** — one paragraph, pulled from
   `context/project-overview.md`'s Overview section.
2. **Architecture diagram** — reuse the system-architecture and
   agent-flow diagrams already defined for this project (see
   `context/architecture.md` and the source blueprint's Mermaid
   diagrams); do not invent a new diagram.
3. **Security constitution** — summarize `AGENTS.md`'s standing
   rules and link to it; do not paste the full file inline.
4. **Core requirements checklist** — the four Challenge brief
   requirements, each marked done/not-done with a one-line note on
   how it was satisfied.
5. **Unique enhancement** — which Phase 3 feature was built and
   which MCP it uses.
6. **Setup instructions** — MCPs required (installed vs. needing
   install per `context/feature-specs/00-build-plan.md` §9),
   environment variables, and the exact deploy commands used.
7. **Screenshots** — placeholders for the deliverables checklist in
   `context/feature-specs/00-build-plan.md` (AGENTS.md, login,
   master prompt, chat, summary, memory vault, patterns dashboard,
   Excel download, firestore.rules, Cloud Run deploy confirmation).
8. **Known limitations** — pull directly from any unresolved items
   still in `context/progress-tracker.md`'s Open Questions section
   at generation time. Do not invent limitations not already
   logged there.

Do not fabricate metrics, test coverage numbers, or claims not
verifiable from the codebase or `progress-tracker.md`.
