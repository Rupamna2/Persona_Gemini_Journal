# /test-walkthrough

Invoke before every deploy. Produces a manual verification
checklist — this is not an automated test suite substitute, it is
the pre-deploy sanity pass.

## Checklist to produce and walk through

- [ ] Google Sign-In completes and issues a valid session
- [ ] Master Prompt save/load round-trips correctly
- [ ] Multi-turn chat: at least 3 turns in one mode, mood extracted
      each turn
- [ ] End-session save: summary generated, journal doc written,
      streak incremented
- [ ] **Forced-failure retry test**: simulate a Firestore write
      failure during save — confirm the client shows an error and
      does **not** clear the unsent input
- [ ] Memory Vault search returns at least one relevant past entry
      with a citation
- [ ] Streak logic: today / yesterday / older-than-yesterday all
      produce the correct current_streak value
- [ ] Excel download: file opens, contains the expected
      weekly/monthly/all-time rows
- [ ] **Cross-user isolation**: sign in as a second Google account,
      confirm zero visibility into account 1's journals, sessions,
      or config
- [ ] Rate limiting: send 10 messages on a free-trial account,
      confirm the 11th is blocked with 429 and no Gemini call is
      made (check Cloud Logging MCP for call count)
- [ ] If Life Pattern Analytics was built: confirm the async
      weather patch lands on the journal doc within a few seconds
      of session end

## Output

Report pass/fail per item. Any failure gets logged to
`context/current-issues.md` per the bug-handling loop in
`ai-workflow-rules.md` — do not attempt an inline fix during this
walkthrough.
