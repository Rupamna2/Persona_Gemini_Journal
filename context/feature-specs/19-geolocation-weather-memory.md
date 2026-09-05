# 19 — Geo-Location Memory & Location-Mood Happiness Predictor

## Goal

Add opt-in Geo-Location intelligence to Personal Gemini Journal:
1. **Geo-Location Memory**: Store structured location metadata (`latitude`, `longitude`, `city`, `state`, `country`, `display_name`) with journal entries and enable location-filtered semantic search in the Memory Vault.
2. **Location-Mood Happiness Predictor**: Analyze and predict locations where the user experiences peak happiness and well-being, surfacing interactive location-mood charts and grounded AI insight cards on the "My Patterns" screen.
3. **Free Global Weather Enrichment (India & Worldwide)**: Fetch real-time weather using Open-Meteo (100% free, zero API key required, global accuracy across India — Bengaluru, Mumbai, Delhi, Kolkata, Chennai, Hyderabad, Pune — and international cities) with BigQuery NOAA GSOD fallback.

## Threat Model (5 Threat Zones)

| Zone | Risk | Mitigation |
|---|---|---|
| **Input Surfaces** | Malicious or spoofed GPS coordinates, overly long or SQL-injectable city/state/country strings. | Pydantic validation on `LocationData` (`-90 <= lat <= 90`, `-180 <= lon <= 180`, strict regex whitelist on place names max 80 chars). |
| **Planning & Reasoning** | Prompt injection via malicious reverse-geocoded place names or external weather status strings. | Treat external geocoding/weather labels as pure data attributes, never concatenated into raw system instructions. |
| **Tool Execution** | SSRF or infinite HTTP loops querying third-party geocoding / weather APIs. | Strict URL parameterization via `urllib.parse`, hard timeout (3.0s), and fallback to offline climate normals / local estimates. |
| **Memory & State** | Cross-user location data leakage or unauthorized access to precise GPS coordinates. | Stored strictly under owner-bound Firestore subcollection `users/{userId}/journals/{journalId}.location`, protected by `request.auth.uid == userId`. |
| **Inter-System Communication** | Network failure or quota blocks from external weather APIs blocking journal saves. | Asynchronous or non-blocking fetching; default `location` and `weather` gracefully fall back to null or local approximations without throwing 500s. |

## Design

1. **Frontend Capture (`ChatPage.tsx` & Dashboard)**:
   - Optional "📍 Add Location" or automatic browser `navigator.geolocation` opt-in prompt.
   - Reverse-geocodes coordinates to `{ city, state, country, display_name }` via Open-Meteo Geocoding / Nominatim API or manual city input.
2. **Backend Storage (`users/{uid}/journals/{journalId}`)**:
   ```json
   {
     "location": {
       "latitude": 12.9716,
       "longitude": 77.5946,
       "city": "Bengaluru",
       "state": "Karnataka",
       "country": "India",
       "display_name": "Bengaluru, Karnataka, India"
     },
     "weather": {
       "condition": "Partly Cloudy",
       "temperature_c": 24.5,
       "source": "open-meteo"
     }
   }
   ```
3. **Memory Vault Location Filtering & Contextual Recall (`memory_agent.py`)**:
   - Allows users to search memories filtered by location (e.g. *"What did I reflect on in Bengaluru?"* or *"Trip to London"*).
   - Augments citation context with `📍 {city}, {country}` badges.
4. **Location-Mood Happiness Predictor (`analytics_agent.py` & `PatternsPage.tsx`)**:
   - Computes average mood score, journal count, and mood variance grouped by `location.city`.
   - Generates AI insight cards identifying the user's happiest environments (e.g., *"You report your highest mood (4.8/5.0) when journaling from Goa, +0.9 higher than your overall baseline."*).
   - Renders a **Mood by Location** comparative bar/radial chart on the My Patterns screen.

## Implementation

1. **Backend Location Schemas & Ingestion (`backend/routes/save.py` & `backend/services/save_pipeline.py`)**:
   - Update `SaveSessionRequest` Pydantic model with optional `location: Optional[LocationInput] = None`.
   - Sanitize all location fields and store within the atomic journal creation transaction.
2. **Weather Service Enhancement (`backend/services/weather_enrichment.py`)**:
   - Query Open-Meteo Free API (`https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&current=temperature_2m,weather_code`) if coordinates are available.
   - Support Indian cities and international locations with zero API key requirement.
   - Retain BigQuery NOAA GSOD and climate baseline fallbacks.
3. **Analytics Agent Location-Mood Predictor (`backend/agents/analytics_agent.py` & `backend/routes/analytics.py`)**:
   - Aggregate entries by `location.city` to build `mood_by_location: List[LocationMoodStat]`.
   - Identify statistically significant mood boosts associated with specific places.
4. **UI Integration**:
   - `frontend/src/pages/ChatPage.tsx`: Location pill with status ("📍 Bengaluru, India" / "📍 Detect Location").
   - `frontend/src/pages/MemoryVaultPage.tsx`: Location badges on memory citations.
   - `frontend/src/pages/PatternsPage.tsx`: "Mood by Location" chart & happiness predictor cards.

## Dependencies

- Unit 09 (Save pipeline)
- Unit 12 & 13 (Memory Vault)
- Unit 15 (Weather enrichment)
- Unit 16 (Life Pattern Analytics)

## MCPs Used & When to Invoke

- **`google-cloud-firestore`** — *Optional.* Validate schema updates on `users/{uid}/journals/{journalId}` location field.
- **BigQuery MCP** — *Optional.* Fallback NOAA GSOD station coordinate lookups.
- **`google-cloud-logging`** — *Optional.* Monitor reverse geocoding & Open-Meteo latency metrics.

## Verification Checklist

- [ ] Location metadata validated with Pydantic and persisted under `users/{uid}/journals/{journalId}.location`
- [ ] Open-Meteo free API fetches accurate weather for Indian cities (Bengaluru, Mumbai, Delhi) and international cities (New York, London, Tokyo)
- [ ] Memory Vault search correctly retrieves and cites location-specific memories
- [ ] Life Pattern Analytics computes `mood_by_location` and outputs grounded happiness predictions
- [ ] All 56+ backend tests continue passing with new unit tests covering location ingestion and analytics
