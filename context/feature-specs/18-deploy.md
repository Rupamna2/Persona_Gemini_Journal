# 18 — Deploy

## Goal

Deploy the backend to Cloud Run and the frontend to Firebase
Hosting, with `firestore.rules` deployed clean, and confirm both
live URLs work end to end.

## Design

No UI changes in this unit.

## Implementation

1. Run `/test-walkthrough` first — do not deploy on a failing
   walkthrough.
2. Confirm a Visa/Mastercard debit or credit card is linked to the
   GCP project's Blaze plan (RuPay cards have been reported to fail
   verification) — Cloud Run, Pub/Sub, BigQuery, and Secret Manager
   all require Blaze even at $0 usage.
3. Using the Cloud Run MCP: deploy `backend/` as service
   `gemini-journal-api` in `asia-south1`, with `GEMINI_API_KEY`
   injected from Secret Manager (never a plaintext env var in the
   deploy command or committed config).
4. If Unit 15 was built: deploy the weather-enrichment subscriber
   as its own Cloud Run service with its Pub/Sub push subscription
   configured.
5. Using the Firebase MCP: deploy `frontend/` to Firebase Hosting
   and deploy `firestore.rules`.
6. Confirm both live URLs, and explicitly confirm the Firestore
   rules deployed clean — no `allow read, write: if true` anywhere.
7. Run `/generate-readme`.

## Dependencies

- All units intended for this submission, completed and verified
- Cloud Run MCP, Firebase MCP (already installed)

## MCPs Used & When to Invoke

- **`google-cloud-resource-manager`** — *Step 2, mandatory, before
  anything else in this unit.* Confirm the GCP project is on the
  Blaze plan with a valid card linked before attempting the Cloud
  Run deploy — Cloud Run, Pub/Sub, BigQuery, and Secret Manager all
  require this even at $0 usage, and this is the last checkpoint to
  catch a billing-verification failure before it blocks the deploy.
- **`google-cloud-quotas`** — *Optional, immediately before Step 3.*
  Pre-deploy check that nothing is near a quota ceiling.
- **`cloudrun`** — *Step 3–4, mandatory.* Deploy `backend/` as
  `gemini-journal-api` in `asia-south1` with `GEMINI_API_KEY`
  injected from Secret Manager; deploy the weather-enrichment
  subscriber as its own service if Unit 15 was built.
- **`firebase-mcp-server`** — *Step 5, mandatory.* Deploy
  `frontend/` to Firebase Hosting and deploy + validate
  `firestore.rules` one final time — re-run the rules-validation
  tool here even though Unit 04 already validated it, since this is
  the deploy that actually goes live.
- **`google-cloud-logging`** — *Step 6, mandatory.* Confirm both
  Cloud Run services are logging cleanly with no startup errors
  before declaring the deploy complete.
- **`google-developer-knowledge`** — *Optional, if any deploy
  command in Step 3 or 5 errors unexpectedly.* Confirm the current
  Cloud Run/Firebase MCP deploy command syntax hasn't changed since
  this spec was written.

## Verification Checklist

- [ ] `/test-walkthrough` passes before this unit starts
- [ ] Backend live URL responds correctly to a real
      Google-Sign-In-authenticated request
- [ ] Frontend live URL loads and completes the full core user flow
      against the live backend
- [ ] `firestore.rules` deployment confirmed clean (Firebase MCP's
      rules-validation tool, not just a visual check)
- [ ] `GEMINI_API_KEY` is not present in any deploy command output,
      committed file, or client bundle
- [ ] README generated and the Deliverables Checklist in
      `00-build-plan.md` fully checked off
