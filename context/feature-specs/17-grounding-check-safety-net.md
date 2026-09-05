# 17 — Grounding Check Safety Net (Phase 3, Optional)

## Goal

Surface a gentle, non-blocking, non-diagnostic resource card when
`mood_analyzer` detects a sustained low mood score or explicit
crisis language — a responsible-AI safety net, not a clinical
feature.

## Design

A small, dismissible card appearing in the Chat screen (not a modal
that blocks journaling), visually distinct but calm — matching the
dark theme, not alarming red/urgent styling.

## Implementation

1. In `root_agent.py`, after `mood_analyzer` returns its per-turn
   result, check: has `mood_score` been ≤2 across 3+ consecutive
   sessions, or does the current message contain explicit crisis
   language? This check is a plain conditional — do not build a
   separate ML classifier for it beyond what `mood_analyzer` already
   extracts.
2. If triggered, the API response includes an additional
   `support_prompt: true` flag (and, if relevant, a jurisdiction-
   appropriate resource reference) alongside the normal
   `{reply, mood}` — it never replaces or blocks the coaching reply
   itself.
3. Frontend: render a small, dismissible card near the chat
   transcript when `support_prompt` is present. It never interrupts
   the conversation flow or forces a modal the user must dismiss
   before continuing.
4. This feature does not diagnose, does not store a "flagged" label
   on the user's profile in a way that changes their experience
   elsewhere in the app, and does not gate any other functionality.

## Dependencies

- Unit 07 (`mood_analyzer` output to check against)
- Unit 08 (Chat UI to render the card in)

## MCPs Used & When to Invoke

- None. This unit is a plain conditional added to `root_agent.py`
  reading `mood_analyzer`'s already-existing output, plus a small
  frontend card — no live Google Cloud/Firebase/Stitch operation is
  needed anywhere in this unit.

## Verification Checklist

- [ ] Three consecutive low-mood sessions trigger the flag on the
      next turn
- [ ] The flag never blocks or replaces the normal coaching reply
- [ ] The card is dismissible and does not reappear mid-conversation
      once dismissed for that session
- [ ] No other part of the app (dashboard, analytics, memory vault)
      changes behavior based on this flag
