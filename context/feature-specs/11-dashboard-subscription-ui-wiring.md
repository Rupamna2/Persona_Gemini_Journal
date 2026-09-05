# 11 — Dashboard + Subscription UI Wiring

## Goal

Wire the Dashboard bento-grid shell (Unit 06) to real streak, mood,
and recent-entry data, and wire the quota badge, 429 modal, and
Subscription/Pricing screen to Unit 10's endpoints.

## Design

Dashboard per Screen Inventory #3 (7 tiles). Subscription screen
per Screen Inventory #7 (two cards: Free Trial "Current Plan" with
a usage progress bar; Pro "Coming Soon," visually muted, disabled
"Upgrade — Contact Us"). Quota badge: small persistent element on
the dashboard and in the chat header — *"Free Trial · 7/10 messages
left · resets [date]"*.

## Implementation

1. On Dashboard mount: `GET /api/subscription/status` to populate
   the quota badge; `GET` (a small aggregation route, or reuse
   existing reads) for `stats/streaks`, recent `journals` (ordered
   by `createdAt` desc, limited), and mood trend data for the
   sparkline.
2. Wire the 7 bento tiles to this real data: streak flame + count,
   mood sparkline (last 30 days), recent entries list with mood
   emoji, "Start Journaling" CTA → mode picker → Chat screen,
   Memory Vault search box (wired in Unit 13), "My Patterns" teaser
   (wired in Unit 16 if built), export buttons (wired in Unit 14).
3. Update the quota badge from the `quota` field returned by every
   `/api/chat` response (not just on page load) so it stays live
   during a session.
4. On a 429 from `/api/chat`: show a blocking modal — *"You've used
   all 10 free messages this month."* with a "View Plans" button
   routing to the Subscription page. Do not lose the user's unsent
   draft text in the chat input.
5. Wire the Subscription page's Free Trial card to
   `GET /api/subscription/status` for its progress bar; the Pro
   card stays static/disabled per design (no backend call needed —
   there is no real payment processing in scope).

## Dependencies

- Unit 06 (Dashboard and Subscription shells)
- Unit 09 (streaks/journals data to read)
- Unit 10 (subscription status endpoint)

## MCPs Used & When to Invoke

- **`google-cloud-logging`** — *Optional, only if the quota badge's
  numbers don't match the backend during testing.* Use it to check
  for a mismatched read between what `/api/subscription/status`
  returned and what actually got logged server-side.
- No MCP is required to build the tile wiring itself — this unit
  consumes existing REST endpoints from Units 09/10.

## Verification Checklist

- [ ] Dashboard shows real streak count, real recent entries, and a
      real mood sparkline for a test account with at least one
      saved journal
- [ ] Quota badge shows the correct remaining count on load and
      updates live after a chat message
- [ ] Reaching the 10-message cap triggers the blocking modal
      without clearing the chat input
- [ ] Subscription page's Free Trial progress bar matches the
      badge's numbers
- [ ] Pro card's "Upgrade — Contact Us" button is visibly disabled
