# 06 — UI Shells (Stitch Screens, Unwired)

## Goal

Generate all remaining screens via the Stitch MCP and land them as
static, unwired React shells, so frontend structure exists before
any real-data wiring begins (per the UI-shells-before-real-data
ordering rule).

## Design

Use the exact Stitch prompts in `ui-context.md`'s Screen Inventory
for: Dashboard (bento grid), Journal chat session, Memory Vault
results, My Patterns, and Subscription/Pricing. (Landing and
Onboarding may already exist from Units 03/05 — if so, restyle them
to match once the palette is set here, rather than regenerating.)
The first screen generated in this unit sets the canonical palette
— fill in the actual hex values in `ui-context.md`'s Colors table
immediately after, before generating the remaining screens, so they
share tokens.

## Implementation

1. Confirm Stitch MCP is installed and authenticated (Prerequisites
   in `00-build-plan.md`).
2. Run each Stitch prompt from `ui-context.md`'s Screen Inventory in
   order, saving each export to `frontend/src/design/`.
3. After the first export, extract its palette into
   `frontend/src/index.css` as the CSS custom properties defined in
   `ui-context.md`, then update `ui-context.md`'s Colors table with
   the real hex values (replacing the "set from Stitch export"
   placeholders) — this is a required doc-sync step, not optional.
4. For each screen, hand the export to the agent with: *"Implement
   this Stitch design as React + Tailwind components in
   `frontend/src/pages/`, matching the existing design tokens. Use
   Recharts for any charts."* At this stage these are static shells
   — placeholder data, no API calls, no real auth-gated routing
   beyond what Units 03/05 already wired.
5. Wire basic client-side routing between screens (Landing →
   Onboarding → Dashboard → Chat → Memory Vault → Patterns →
   Subscription) so navigation works end to end even with
   placeholder content.

## Dependencies

- Stitch MCP (installed per Prerequisites)
- `recharts` (frontend)
- Unit 02 (frontend scaffold)

## MCPs Used & When to Invoke

- **Stitch MCP** — *Steps 1–2, mandatory, this is the core of the
  unit.* Every one of the 5 remaining screen generations (Dashboard,
  Chat, Memory Vault, My Patterns, Subscription) is a Stitch MCP
  call. This unit cannot start until Stitch MCP is installed and
  authenticated per the Prerequisites in `00-build-plan.md` — verify
  with "List my Stitch projects" (expect an empty list, not an
  error) before running the first design prompt.
- No other MCP is used in this unit — translating a Stitch export
  into a real React component (Step 4) is ordinary code work, not
  an MCP call.

## Verification Checklist

- [ ] All 7 screens exist as real components in
      `frontend/src/pages/`, none importing directly from
      `frontend/src/design/`
- [ ] `ui-context.md`'s Colors table has real hex values, not
      placeholders
- [ ] Client-side routing connects all 7 screens
- [ ] `npm run build` passes with the full screen set in place
- [ ] No screen makes a real API call yet — this unit is
      placeholder data only
