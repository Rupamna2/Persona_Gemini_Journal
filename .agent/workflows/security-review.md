# /security-review

Invoke on demand before any deploy, and after any change touching
auth, Firestore rules, agent instruction handling, or a route that
takes user input.

## Persona

Adopt a Security Reviewer persona: adversarial, not
implementation-friendly. Assume every user-controlled field is
hostile until proven otherwise.

## Checklist

1. **Auth**: Does every protected route depend on `verify_token`
   and re-check `request.auth.uid == path uid`? Flag any route
   that trusts a `uid` from the request body.
2. **Firestore rules**: Is there exactly one owner-bound rule
   (`users/{userId}/{document=**}`) and zero `allow read, write: if
   true` anywhere in `firestore.rules`?
3. **Prompt injection**: Does `root_agent.py` still prepend
   `FIXED_SECURITY_PREAMBLE` before `<user_master_prompt>` on every
   call? Is the master prompt ever passed to the model in a way
   that could be read as system authority?
4. **Tool execution**: Do all agent tools take structured typed
   args only? Is there any code path that assembles a raw SQL
   string or a raw URL from user-controlled text?
5. **Input validation**: Does every FastAPI route validate its
   body with a Pydantic model before touching Firestore or calling
   an agent?
6. **XSS**: Is all LLM-generated text sanitized (e.g. `DOMPurify`)
   before rendering? Any `dangerouslySetInnerHTML` on raw model
   output is an automatic fail.
7. **Secrets**: Is `GEMINI_API_KEY` referenced only via Secret
   Manager / Cloud Run env vars? Confirm it does not appear in any
   frontend `.env`, any committed file, or any client bundle.
8. **Pub/Sub**: Does the weather subscriber verify the push OIDC
   JWT against the expected service account before processing a
   message?
9. **Rate limiting**: Is `enforce_and_increment` called before any
   Gemini API call in `/api/chat`, with no code path that can reach
   the model call while bypassing it?

## Output

Produce a table: Zone | Finding | Severity | Fix Required (Y/N).
Do not silently patch findings — report them, then wait for
instruction on which to fix now vs. log as an open question.
