# 14 — Excel Export

## Goal

Let a user download their journal history as a `.xlsx` file, scoped
to weekly, monthly, or all-time ranges, with no server-side
persistence of the generated file.

## Design

Dashboard's export tile (Screen Inventory #3, tile 7): three
buttons — weekly / monthly / all-time.

## Implementation

1. `backend/routes/export.py`: `GET /api/export?range=weekly|
   monthly|all` behind `verify_token`. Queries
   `users/{uid}/journals` filtered by `createdAt` for the requested
   range, builds an in-memory `openpyxl` workbook (one row per
   entry: date, mode, topic, mood_score, key_insights,
   action_items), and returns it via `StreamingResponse` with the
   correct `Content-Disposition` and `.xlsx` content type.
2. Do not write the generated file to disk or to any blob store —
   generate, stream, discard.
3. Frontend: each export button triggers the request and downloads
   the streamed response directly (no intermediate "generating..."
   page needed beyond a simple loading state on the button itself).

## Dependencies

- `openpyxl` (backend)
- Unit 09 (journals exist to export)

## MCPs Used & When to Invoke

- None. Workbook generation is pure in-memory Python
  (`openpyxl` + `StreamingResponse`) against data already read via
  the Admin SDK — no MCP call is needed anywhere in this unit.

## Verification Checklist

- [ ] Each of the three range buttons produces a valid `.xlsx` file
      that opens correctly
- [ ] The file's rows match the actual saved journals for that
      range and account only
- [ ] No file is left on disk or in any storage bucket after the
      request completes
- [ ] A request for a range with zero entries still returns a
      valid (header-only) workbook, not an error
