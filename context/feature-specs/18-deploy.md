# 18 — Deploy

## Goal

Deploy the backend to Cloud Run in `asia-south1` and the frontend to Firebase Hosting for project `personal-gemini-journal-507113`, with `firestore.rules` deployed clean, secrets securely mounted via Google Cloud Secret Manager, and confirm both live URLs work end to end with resilient multi-provider AI failover.

## Design

No UI changes in this unit. Production builds connect live frontend to Cloud Run backend with full Google Auth, Firestore persistence, and multi-model failover ladder.

## Implementation Steps

### 1. Pre-Deployment Verification
- Run all unit and integration tests: `pytest backend/tests/` (64/64 passing).
- Verify TypeScript compilation: `npm run build` in `frontend/`.
- Confirm GCP Project `personal-gemini-journal-507113` has Billing enabled (Blaze plan).

### 2. Enable Required GCP APIs
Enable required services if not already active:
```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  --project=personal-gemini-journal-507113
```

### 3. Google Cloud Secret Manager Setup
Create and populate secrets in Secret Manager (never commit or log plaintext values):
```bash
# 1. Create GEMINI_API_KEY secret
gcloud secrets create GEMINI_API_KEY --project=personal-gemini-journal-507113 --replication-policy="automatic" || true
printf "%s" "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --project=personal-gemini-journal-507113 --data-file=-

# 2. Create NVIDIA_API_KEY secret (for multi-model zero-downtime failover)
gcloud secrets create NVIDIA_API_KEY --project=personal-gemini-journal-507113 --replication-policy="automatic" || true
printf "%s" "$NVIDIA_API_KEY" | gcloud secrets versions add NVIDIA_API_KEY --project=personal-gemini-journal-507113 --data-file=-

# 3. Grant Cloud Run Compute service account permission to access secrets
PROJECT_NUM=$(gcloud projects describe personal-gemini-journal-507113 --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --project=personal-gemini-journal-507113 \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding NVIDIA_API_KEY \
  --project=personal-gemini-journal-507113 \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Deploy Backend to Cloud Run
Deploy `backend/` as service `gemini-journal-api` in `asia-south1`:
```bash
gcloud run deploy gemini-journal-api \
  --source . \
  --region asia-south1 \
  --project personal-gemini-journal-507113 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=personal-gemini-journal-507113,FIREBASE_PROJECT_ID=personal-gemini-journal-507113 \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest,NVIDIA_API_KEY=NVIDIA_API_KEY:latest \
  --min-instances 0 \
  --max-instances 5 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60
```

### 5. Configure Pub/Sub Push Subscription for Weather Enrichment
Wire the `journal-enrichment` topic to push to `/api/subscriber/weather-enrichment`:
```bash
BACKEND_URL=$(gcloud run services describe gemini-journal-api --region=asia-south1 --project=personal-gemini-journal-507113 --format="value(status.url)")

# Ensure topic exists
gcloud pubsub topics create journal-enrichment --project=personal-gemini-journal-507113 || true

# Create / update push subscription
gcloud pubsub subscriptions create journal-enrichment-sub \
  --topic=journal-enrichment \
  --push-endpoint="${BACKEND_URL}/api/subscriber/weather-enrichment" \
  --project=personal-gemini-journal-507113 || true
```

### 6. Deploy Firestore Security Rules & Indexes
Validate and deploy `firestore.rules`:
```bash
npx -y firebase-tools deploy --only firestore:rules,firestore:indexes --project personal-gemini-journal-507113
```

### 7. Build and Deploy Frontend to Firebase Hosting
1. Update `frontend/.env` with `VITE_API_BASE_URL=${BACKEND_URL}` (or configure Firebase Hosting rewrites in `firebase.json` to proxy `/api/**` to Cloud Run).
2. Build production assets:
```bash
cd frontend && npm run build
```
3. Deploy to Firebase Hosting:
```bash
npx -y firebase-tools deploy --only hosting --project personal-gemini-journal-507113
```

### 8. Verification & Live Smoke Test
- Confirm health endpoint: `curl -s "${BACKEND_URL}/api/health"` returns 200 OK.
- Confirm live frontend loads at `https://personal-gemini-journal-507113.web.app` or `https://personal-gemini-journal-507113.firebaseapp.com`.
- Perform full Google Sign-In, Onboarding / Master Prompt configuration, and live multi-turn chat session.

## Dependencies
- Cloud Run, Secret Manager, Cloud Build, Artifact Registry, Pub/Sub, Firestore APIs enabled on `personal-gemini-journal-507113`.
- `gcloud` CLI authenticated with active project `personal-gemini-journal-507113`.
- `firebase-tools` CLI authenticated.

## Verification Checklist
- [ ] 64/64 pytest tests passing locally before deployment
- [ ] Cloud Run backend service `gemini-journal-api` deployed in `asia-south1`
- [ ] `GEMINI_API_KEY` and `NVIDIA_API_KEY` mounted from Secret Manager (never exposed in plaintext)
- [ ] `firestore.rules` deployed clean with single owner-bound rule
- [ ] Firebase Hosting deployed and serving compiled React app
- [ ] Live end-to-end user flow confirmed (Auth -> Dashboard -> Chat -> Save -> Analytics)
