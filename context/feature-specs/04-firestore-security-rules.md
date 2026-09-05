# 04 — Firestore Security Rules

## Goal

Deploy the owner-bound access-control rules so every subcollection
under `users/{uid}/**` is protected before any real data is written
to it.

## Design

No UI. This is the enforcement layer underneath every screen that
reads or writes user data.

## Implementation

1. Use the `firestore.rules` file already authored in this context
   package (root-level, owner-bound wildcard rule
   `users/{userId}/{document=**}` plus a deny-all fallback for
   everything else).
2. Do not write a narrower, per-subcollection rule under any
   circumstance — this is Invariant 3 in `architecture.md` and
   exists specifically because a prior version of this project's
   source docs had a rule that protected `interactions` while the
   actual code wrote to `journals`, leaving `journals` unprotected.
3. Deploy via the Firebase MCP's rules deploy tool, then run its
   rules-validation tool (not just a manual read) to confirm the
   ruleset compiles and the deny-all fallback exists.
4. Manually verify with two test accounts (can be deferred to the
   Unit 18 `/test-walkthrough` pass, but do at least one quick
   check here): sign in as account A, confirm reads/writes to
   `users/{A}/**` succeed and reads/writes to `users/{B}/**` are
   denied.

## Dependencies

- Firebase MCP (already installed)
- Unit 02 (Firestore database exists)
- Unit 03 (auth exists, so a real `request.auth.uid` is available
  to test against)

## MCPs Used & When to Invoke

- **`firebase-mcp-server`** — *Step 3, mandatory, this is the core
  of the unit.* Deploy `firestore.rules` and then run its
  rules-validation tool — do not treat a successful deploy alone as
  proof the rules are correct; the validation tool is the actual
  check that the ruleset compiles as intended and the deny-all
  fallback exists.
- **`google-cloud-firestore`** — *Optional, if the validation tool
  reports something unexpected in Step 3.* Inspect the currently
  deployed ruleset/indexes directly to diagnose a mismatch before
  re-deploying.

## Verification Checklist

- [ ] Deployed ruleset contains exactly one rule scoped to
      `users/{userId}/{document=**}` and one deny-all fallback —
      no per-subcollection rules
- [ ] Firebase MCP's rules-validation tool reports a clean compile
- [ ] No `allow read, write: if true` appears anywhere in the
      deployed ruleset
- [ ] A manual cross-account read attempt against another user's
      data is denied
- [ ] `progress-tracker.md` updated confirming rules are deployed
