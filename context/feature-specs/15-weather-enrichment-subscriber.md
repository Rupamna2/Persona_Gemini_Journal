# 15 — Weather Enrichment Subscriber (Phase 3)

## Goal

Asynchronously patch each journal entry's `weather` field after
save, without ever touching the synchronous save path — this is the
foundation Unit 16 (Life Pattern Analytics) builds on, and it's the
unit that puts the previously-unused `google-cloud-pubsub` MCP to
work.

## Design

No UI in this unit.

## Implementation

1. Create the `journal-created` Pub/Sub topic (via the
   google-cloud-pubsub MCP) if it doesn't already exist from Unit
   09's publish call.
2. Deploy a second, small Cloud Run service (the subscriber) with a
   push subscription to `journal-created`.
3. Subscriber handler: **first**, validate the Pub/Sub push
   request's OIDC `Authorization: Bearer` JWT against the expected
   service account — reject anything that doesn't verify, before
   processing the payload. This is a hard requirement per
   `architecture.md`'s threat model (Pub/Sub message spoofing).
4. On a validated message `{uid, journalId, city}`: query the
   allow-listed `bigquery-public-data.noaa_gsod` dataset for the
   nearest station/date match to `city`, then patch
   `users/{uid}/journals/{journalId}.weather` with
   `{condition, temperature_c, fetched_at}` via a direct field
   update (not a full document overwrite, to avoid racing any other
   concurrent write to that doc).
5. The weather tool only ever accepts the allow-listed dataset and
   the user's own profile city — no arbitrary URL fetch, no
   user-supplied query string reaching BigQuery directly (threat
   model: SSRF via the weather tool).
6. If the BigQuery lookup fails or times out, log it (Cloud Logging
   MCP) and leave `weather: null` — never retry indefinitely, never
   surface an error to the user, since this was never on their
   critical path.

## Dependencies

- `google-cloud-pubsub` MCP (already installed)
- BigQuery MCP (install per Prerequisites in `00-build-plan.md`)
- Unit 09 (publishes the `journal-created` message this subscribes
  to)

## MCPs Used & When to Invoke

- **`google-cloud-pubsub`** — *Step 1, mandatory.* Create the
  `journal-created` topic if Unit 09 hasn't already, then create the
  push subscription for the subscriber service. Also used during
  testing to confirm message delivery timing (the "within a few
  seconds" checklist item).
- **`cloudrun`** — *Step 2, mandatory.* Deploy the subscriber as its
  own Cloud Run service, separate from the main backend deployed in
  Unit 18 — this is a second, small service, not a route on the
  existing one.
- **BigQuery MCP** — *Step 4, mandatory, must be installed first per
  Prerequisites.* Query `bigquery-public-data.noaa_gsod` for the
  nearest station/date match — this is the one unit in the whole
  build that actually needs this MCP.
- **`google-cloud-logging`** — *During testing of Steps 3 and 6.*
  Confirm the spoofed-JWT rejection path and the
  BigQuery-failure-leaves-weather-null path are both logging
  correctly and not surfacing anywhere else.

## Verification Checklist

- [ ] A save with a valid `journal-created` publish results in the
      journal's `weather` field being patched within a few seconds
- [ ] A spoofed push request (invalid/missing OIDC JWT) is rejected
      before any BigQuery query runs
- [ ] A forced BigQuery failure leaves `weather: null` without
      affecting the already-saved journal or surfacing an error to
      the user
- [ ] The BigQuery query never contains raw user-supplied SQL or an
      arbitrary URL — only the allow-listed dataset and the
      profile's city
