# 16 — Life Pattern Analytics (Phase 3)

## Goal

Surface mood-vs-weather correlation, topic breakdown, and AI
insight cards on the "My Patterns" screen, backed by
`analytics_agent` and the weather data Unit 15 backfills.

## Design

My Patterns screen per Screen Inventory #6: mood trend line chart,
mood-vs-weather bar chart, topics pie chart, 2–3 AI-generated
insight cards in a row underneath.

## Implementation

1. `backend/agents/analytics_agent.py`: reads the user's `journals`
   (mood_score, emotional_themes, weather) over a chosen window,
   computes/queries any needed BigQuery aggregate via a structured
   typed tool call (`city: str`, `date_range: DateRange` — never raw
   SQL assembled from user text), and generates natural-language
   insight card text grounded in the actual retrieved data only.
2. `backend/routes/analytics.py`: `GET /api/analytics/patterns`
   behind `verify_token`. Returns
   `{mood_trend, mood_vs_weather, topics, insights}` shaped for
   direct Recharts consumption.
3. Wire the My Patterns screen and the Dashboard's teaser tile to
   this endpoint. If a user has too few entries with non-null
   weather for a meaningful correlation, show an explicit
   "not enough data yet" state — do not fabricate a chart from
   sparse or missing data.
4. Every route re-verifies `request.auth.uid == path uid`
   server-side, matching the threat-model countermeasure for
   privilege escalation through analytics endpoints.

## Dependencies

- Unit 15 (weather data to correlate against)
- Unit 06 (My Patterns shell)
- BigQuery MCP

## MCPs Used & When to Invoke

- **BigQuery MCP** — *Step 1, mandatory, same installed MCP as Unit
  15.* Used for `analytics_agent`'s aggregate queries against
  `noaa_gsod`, always via the structured typed tool call, never a
  raw SQL string built from user text.
- **`google-cloud-firestore`** — *Optional, if chart output looks
  wrong during testing.* Read the underlying `journals`/`weather`
  data directly to confirm what's actually stored before assuming
  the bug is in `analytics_agent`'s aggregation logic.
- **`google-cloud-logging`** — *Optional.* Check insight-generation
  latency if the "not enough data yet" state seems to trigger
  incorrectly for an account that should have sufficient entries.

## Verification Checklist

- [ ] Charts render correctly for a test account with enough
      weather-enriched entries
- [ ] A sparse-data account sees an honest "not enough data yet"
      state instead of a misleading empty/fabricated chart
- [ ] `analytics_agent`'s BigQuery access is always via a
      structured typed tool call, never a raw SQL string built from
      user text
- [ ] A second account cannot retrieve the first account's
      analytics via this endpoint
