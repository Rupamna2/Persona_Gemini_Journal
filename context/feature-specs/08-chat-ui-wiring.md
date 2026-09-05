# 08 — Chat UI Wiring

## Goal

Wire the Chat screen shell (from Unit 06) to the real
`POST /api/chat` endpoint (from Unit 07), so a user can actually
have a multi-turn journaling conversation.

## Design

Chat screen per Screen Inventory #4: message bubbles (user
right-aligned, Gemini left-aligned), mode badge at top, typing
indicator during the request, fixed "End Session & Summarize"
button pinned to the bottom.

## Implementation

1. On entering the Chat screen from a mode selection (Dashboard's
   "Start Journaling" tile), create a new session via a small
   client-side call or a dedicated backend init, capturing
   `session_id` and `mode`.
2. On message send: optimistically render the user bubble, call
   `POST /api/chat` with `{session_id, mode, message}`, show the
   typing indicator while awaiting the response, then render the
   Gemini reply bubble with the returned mood rendered subtly (not
   as a distracting overlay).
3. Sanitize the rendered reply with `DOMPurify` before display —
   never `dangerouslySetInnerHTML` raw model text.
4. On network/API error: show an inline retry affordance, do not
   drop the user's already-sent message from the transcript.
5. "End Session & Summarize" button navigates into the Unit 09 save
   flow (implemented next) — for this unit, it's acceptable to stub
   the button's destination if Unit 09 isn't done yet, but leave a
   single clearly marked integration point.

## Dependencies

- Unit 06 (Chat screen shell)
- Unit 07 (`/api/chat` backend)

## MCPs Used & When to Invoke

- None. This is pure frontend wiring against an already-built
  endpoint (Unit 07) and an already-built shell (Unit 06) — no live
  Google Cloud/Firebase/Stitch operation happens in this unit.

## Verification Checklist

- [ ] A full multi-turn conversation (3+ turns) renders correctly
      with correct left/right alignment
- [ ] Typing indicator shows during each request and clears on
      response
- [ ] Model output is sanitized before rendering — verify by
      sending a message that elicits markdown/HTML-like text back
- [ ] A simulated API failure shows a retry affordance without
      losing the user's message
- [ ] `npm run build` passes
