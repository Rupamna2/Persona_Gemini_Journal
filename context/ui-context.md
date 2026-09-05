# UI Context

## Theme

Dark only, calm aesthetic. Deep navy/charcoal background with one
accent color used sparingly for CTAs and active states. This theme
must be consistent across every screen — landing, onboarding,
dashboard, chat, memory vault, patterns, and subscription — since
they are generated as separate Stitch prompts and must still read
as one product.

## Colors

Define as CSS custom properties in `frontend/src/index.css`. Every
component consumes these tokens — no hardcoded hex values in `.tsx`
files. Exact hex values are chosen when the first Stitch export
lands (Stitch is the source of the palette); record the finalized
values here immediately after and treat this table as the
authoritative reference from then on.

| Role | CSS Variable | Value |
|---|---|---|
| Page background | `--bg-base` | `#0B0F17` (deep navy charcoal) |
| Surface (cards/tiles) | `--bg-surface` | `#131B2A` (slate navy surface) |
| Primary text | `--text-primary` | `#F1F5F9` (crisp slate light) |
| Muted text | `--text-muted` | `#94A3B8` (slate muted secondary) |
| Primary accent | `--accent-primary` | `#3B82F6` (calm vibrant cobalt blue) |
| Border | `--border-default` | `#1E293B` (subtle slate border) |
| Error / rate-limit | `--state-error` | `#EF4444` (crimson error) |
| Success / streak | `--state-success` | `#10B981` (emerald success) |

## Typography

| Role | Font | Variable |
|---|---|---|
| UI text | Stitch default export font | `--font-sans` |
| Numeric (streaks, mood scores) | Same as UI, tabular figures | `--font-sans` |

## Border Radius

| Context | Class |
|---|---|
| Inline / small UI (badges, chips) | `rounded-md` |
| Cards / bento tiles | `rounded-xl` |
| Modals / overlays (rate-limit modal) | `rounded-2xl` |

## Component Library

React + Tailwind CSS, generated per-screen via Stitch MCP. Raw
exports land in `frontend/src/design/` and are translated into real
components in `frontend/src/pages/` — never import a raw Stitch
export directly into a page.

## Layout Patterns

- **Dashboard**: CSS-grid bento layout, tiles of varying size (see
  Screen Inventory below for the exact tile set).
- **Chat**: message bubbles, user right-aligned, Gemini
  left-aligned; fixed "End Session & Summarize" button pinned to
  the bottom of the viewport.
- **Modals**: centered overlay with backdrop blur (used for the
  429 rate-limit block).
- **Forms** (onboarding, master prompt): single-column, generous
  whitespace, segmented controls over dropdowns where the option
  set is small (e.g. Tone).

## Icons

Lucide React. Stroke-based icons only. `h-4 w-4` for inline icons,
`h-5 w-5` for buttons.

## Screen Inventory (Stitch prompts — source of truth for design)

1. **Landing/Login** — centered card, app name, one-line tagline,
   single "Continue with Google" button. No email/password fields.
2. **Onboarding / Master Prompt** — "About Me" textarea, "Tone"
   segmented control (Logical / Empathetic / Direct / Playful /
   Tough Love), tag-style multi-add "My Goals" input, checkboxes for
   frameworks (5-Why, Pros-Cons, Decision Matrix, SWOT,
   First-Principles), "Things to Avoid" textarea.
3. **Dashboard (bento grid)** — (1) large: mood trend sparkline,
   last 30 days; (2) medium: current streak, flame icon + count;
   (3) medium: "Start Journaling" CTA with mode picker; (4) large:
   recent journal entries with mood emoji per entry; (5) small:
   Memory Vault search box; (6) small: "My Patterns" teaser card;
   (7) small: export buttons (weekly/monthly/all).
4. **Journal chat session** — message bubbles, mode badge at top,
   typing indicator, fixed "End Session & Summarize" button.
5. **Memory Vault results** — search bar ("Ask about your past
   journals..."), result cards below with date, excerpt, mood
   emoji, relevance indicator.
6. **My Patterns (analytics, Phase 3)** — mood trend line chart,
   mood-vs-weather bar chart, topics pie chart, 2–3 AI insight cards
   underneath.
7. **Subscription / Pricing** — two cards side by side. Card 1
   "Free Trial": badge "Current Plan," bullets ("10 AI messages per
   month," "Basic Memory Vault," "No analytics," "No export"),
   progress bar of messages used vs. limit. Card 2 "Pro": badge
   "Coming Soon," bullets ("Unlimited messages," "Full Memory
   Vault," "Full analytics," "Excel export"), disabled "Upgrade —
   Contact Us" button, visually muted/locked.

Each screen is generated via the Stitch MCP, saved to
`frontend/src/design/`, then implemented as real React + Tailwind
components in `frontend/src/pages/` using Recharts for any charts.
