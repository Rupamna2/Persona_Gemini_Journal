# 03 — Auth: Google Sign-In Only

## Goal

Implement server-side Firebase ID token verification and the
client-side Google Sign-In flow — no password form, no password
storage, anywhere.

## Design

Landing screen (Screen Inventory #1 in `ui-context.md`) shows a
centered card with app name, tagline, and a single "Continue with
Google" button. This unit wires that button to real auth; the
visual shell can be built now or deferred to Unit 06 — if deferred,
use a plain unstyled button here and let Unit 06/08 restyle it.

## Implementation

1. `backend/auth.py`: a `verify_token` FastAPI dependency that
   extracts the Bearer token from the `Authorization` header,
   verifies it via the Firebase Admin SDK, and returns the `uid`.
   Returns 401 on missing or invalid token. No caching past token
   expiry (1hr).
2. `frontend/src/auth/`: Firebase client SDK config, a
   `signInWithGoogle()` function using `signInWithPopup` +
   `GoogleAuthProvider`, and an auth-state listener that stores the
   ID token for attaching to API requests.
3. Landing page button calls `signInWithGoogle()` on click; on
   success, redirect to Onboarding (first sign-in) or Dashboard
   (returning user) — determine which by checking whether
   `users/{uid}/config/master_prompt` exists.
4. On first sign-in, write the `users/{uid}` profile document
   (`displayName`, `email`, `photoURL`, `createdAt`, `lastLoginAt`)
   from the Google profile data; on subsequent sign-ins, update only
   `lastLoginAt`.
5. Explicitly do **not** add any password input, password reset
   link, or Email/Password provider call anywhere in this unit.

## Dependencies

- `firebase-admin` (backend)
- `firebase` client SDK (frontend)
- Unit 02 (Firebase project with Google Sign-In enabled)

## MCPs Used & When to Invoke

- **`firebase-mcp-server`** — *Before Step 1, as a confirmation
  check.* Inspect the Firebase project's auth provider config to
  confirm Google Sign-In is enabled and Email/Password is not,
  verifying Unit 02's setup before writing the Admin SDK
  verification code against it.
- No MCP is needed for the actual token-verification code itself —
  `verify_token` and `signInWithGoogle()` are written directly
  against the Firebase Admin SDK and client SDK libraries, not
  invoked through an MCP.

## Verification Checklist

- [ ] A request to any protected route with no Authorization header
      returns 401
- [ ] A request with an expired/invalid token returns 401
- [ ] A request with a valid token resolves to the correct `uid` in
      the route handler
- [ ] Clicking "Continue with Google" completes sign-in and lands
      on Onboarding for a new user, Dashboard for a returning one
- [ ] `users/{uid}` document is created on first sign-in and
      `lastLoginAt` updates on subsequent sign-ins
- [ ] No password input, password storage, or password reset code
      path exists anywhere in the diff
