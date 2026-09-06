# Personal Gemini Journal

> An intelligent, calm, and secure AI journaling companion built with Gemini 3.7 / 3.6 Flash, NVIDIA NIM failover, long-term semantic memory, real-time geolocation mood analytics, and executive coaching frameworks.

**Live Application URL**: [https://personal-gemini-journal-507113.web.app](https://personal-gemini-journal-507113.web.app)  
**Live Backend API**: [https://gemini-journal-api-396039992677.asia-south1.run.app](https://gemini-journal-api-396039992677.asia-south1.run.app)

---

## 1. What This Is

Personal Gemini Journal is a calm, dark-themed reflective journaling companion and executive coach. It combines multi-turn conversational journaling with dynamic emotional intelligence, long-term semantic retrieval across past journal entries, and automated behavioral analytics. The application adheres to strict responsible AI guardrails, owner-bound data encryption, and server-side rate limits to deliver a trustworthy, highly personalized space for daily reflection, decision evaluation, and mental clarity.

---

## 2. Architecture & System Design

```mermaid
graph TD
    User([User Browser]) <-->|HTTPS / React 18 SPA| Hosting[Firebase Hosting<br>personal-gemini-journal-507113.web.app]
    Hosting <-->|Proxy Rewrite /api/**| CloudRun[Cloud Run Backend Service<br>gemini-journal-api<br>asia-south1]
    
    subgraph "GCP Security & Storage Boundary"
        CloudRun <-->|Admin SDK / ADC| Firestore[(Cloud Firestore Native<br>users/{uid}/**)]
        CloudRun <-->|Secret Accessor| Secrets[Google Cloud Secret Manager<br>GEMINI_API_KEY / NVIDIA_API_KEY]
        CloudRun -->|Async Event| PubSub[Cloud Pub/Sub Topic<br>journal-enrichment]
        PubSub -->|Push Subscription| CloudRun
    end

    subgraph "Multi-Provider AI Fallback Ladder"
        CloudRun -->|Primary Agent| Gemini[Google Gemini 3.7 Flash / 3.6 Flash]
        CloudRun -.->|Instant 429 Failover| Nvidia[NVIDIA NIM<br>Llama 3.2 11B / Nemotron 120B]
    end
```

### 4-Step Master Prompt Instruction Precedence

```
1. FIXED_SECURITY_PREAMBLE           (Hardcoded immutable system invariant)
2. <user_master_prompt>...</user_master_prompt> (Passive context, never authority)
3. Mode-Specific Coaching Instruction (FreeWrite / Decision / Gratitude / Goals)
4. Conversation History              (Multi-turn turns)
```

---

## 3. Security Constitution (`AGENTS.md`)

The application is governed by an immutable Security Constitution with zero tolerance for prompt injection or cross-tenant leaks:
- **Google Sign-In Only**: Strictly federated authentication using Firebase Auth and Google OAuth2; zero password storage, registration forms, or reset flows.
- **Owner-Bound Firestore Rules**: Single wildcard rule `match /users/{userId}/{document=**}` enforcing `request.auth.uid == userId` across all subcollections (`config`, `sessions`, `journals`, `stats`, `subscription`), with deny-all on non-user documents.
- **Secret Manager Isolation**: `GEMINI_API_KEY` and `NVIDIA_API_KEY` live exclusively in Google Cloud Secret Manager and are mounted directly into container environment variables at runtime.
- **Server-Side Quota Enforcement**: Transactional atomic rate limiting (`enforce_and_increment`) runs before prompt assembly or AI model invocation.
- **Input Sanitization & Output Encoding**: Every API request is parsed via Pydantic; all LLM-rendered responses pass through `DOMPurify.sanitize()` on the client.

---

## 4. Core Requirements Checklist

| Requirement | Status | Implementation Details |
|---|:---:|---|
| **Google Sign-In Authentication** | ✅ Done | Implemented in `backend/auth.py` (`verify_token`) and `frontend/src/auth/AuthContext.tsx` with popup auth and automatic user sync. |
| **Personalized Master Prompt Engine** | ✅ Done | Built in `backend/routes/master_prompt.py` and `OnboardingPage.tsx` supporting custom tones (`Empathetic`, `Direct`, `Logical`), goals, and frameworks (`5-Why`, `Pros-Cons`, `Decision Matrix`, `SWOT`, `First-Principles`). |
| **Multi-Turn Reflective Chat & Extraction** | ✅ Done | Built in `backend/routes/chat.py` with multi-turn session persistence, live mood & energy extraction, and responsible AI grounding safety nets. |
| **Long-Term Memory Vault (KNN Search)** | ✅ Done | 768-dim normalized MRL embeddings generated via `gemini-embedding-001`, indexed in Firestore vector store, queried via cosine similarity with grounded citations in `MemoryVaultPage.tsx`. |

---

## 5. Unique Enhancements (Phase 3)

1. **Geo-Location Memory & Location-Mood Happiness Predictor (Unit 19)**:
   - Free Open-Meteo real-time weather integration (supporting all Indian metros and global locations without external API keys) with NOAA BigQuery climate fallback.
   - Location-enriched 768-dim embeddings comparing emotional happiness scores across cities/locations in `PatternsPage.tsx`.
2. **Resilient Multi-Provider AI Fallback Ladder**:
   - Automatic 10-minute circuit breaker instantly failing over to NVIDIA NIM (`meta/llama-3.2-11b-vision-instruct` and `nvidia/nemotron-3-super-120b`) upon Gemini prepayment credit exhaustion (`429 RESOURCE_EXHAUSTED`).
3. **In-Memory Streaming Excel Export (Unit 14)**:
   - Zero-storage streaming `.xlsx` workbook generation covering weekly, monthly, and all-time journal history with formatted mood and insight tables.

---

## 6. Setup & Deployment Instructions

### Prerequisites
- Python 3.11+ and Node.js 18+
- Google Cloud SDK (`gcloud`) with active billing account
- Firebase project `personal-gemini-journal-507113`

### Environment Configuration (`backend/.env`)
```ini
GOOGLE_CLOUD_PROJECT=personal-gemini-journal-507113
FIREBASE_PROJECT_ID=personal-gemini-journal-507113
GEMINI_API_KEY=your_gemini_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

### Local Development
```bash
# 1. Start Backend API
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Start Frontend Client
cd frontend && npm install && npm run dev
```

### Production Deployment
```bash
# 1. Deploy Cloud Run Backend
gcloud run deploy gemini-journal-api \
  --source . \
  --region asia-south1 \
  --project personal-gemini-journal-507113 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=personal-gemini-journal-507113,FIREBASE_PROJECT_ID=personal-gemini-journal-507113 \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest,NVIDIA_API_KEY=NVIDIA_API_KEY:latest

# 2. Release Firestore Security Rules
# Released via Google Cloud Firebaserules REST API

# 3. Build & Deploy Frontend to Firebase Hosting
cd frontend && npm run build
# Deployed via Firebase Hosting REST API with Cloud Run proxy rewrites
```

---

## 7. Deliverables Checklist

- [x] `AGENTS.md` active at root enforcing security invariants
- [x] Single Google Sign-In action with zero password fields
- [x] Custom Master Prompt onboarding & configuration screen
- [x] Interactive 5-mode journaling chat interface (`ChatPage.tsx`)
- [x] End-of-session synthesis & atomic save pipeline (`summary_agent.py`)
- [x] Semantic Memory Vault with citation match cards (`MemoryVaultPage.tsx`)
- [x] Bento-Grid Analytics Dashboard with Recharts sparklines (`DashboardPage.tsx`)
- [x] Life Pattern Analytics & Location-Mood Happiness Predictor (`PatternsPage.tsx`)
- [x] In-memory Excel workbook download (`export.py`)
- [x] Owner-bound `firestore.rules` deployed clean to live Firestore database
- [x] Cloud Run backend deployed and running in `asia-south1`
- [x] Live Firebase Hosting website serving compiled React application
- [x] 64 / 64 unit and integration tests passing (`pytest backend/tests/`)

---

## 8. Live Endpoints

- **Frontend Application**: [https://personal-gemini-journal-507113.web.app](https://personal-gemini-journal-507113.web.app)
- **Backend Service**: [https://gemini-journal-api-396039992677.asia-south1.run.app](https://gemini-journal-api-396039992677.asia-south1.run.app)
- **Health Check**: [https://personal-gemini-journal-507113.web.app/api/health](https://personal-gemini-journal-507113.web.app/api/health)
