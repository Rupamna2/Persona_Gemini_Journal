# 🧠 Personal Gemini Journal

> **Submission for the Google Cloud Gen AI Academy (APAC Edition) Ideathon**  
> **Theme:** Accelerate AI with Cloud Run  
> **Region:** APAC (Deployed in `asia-south1`)  
> **Security Constitution:** Governed by `AGENTS.md`  
> **Production Live Backend:** Deployed Serverless on Google Cloud Run  

---

## 🌟 The "Why": Solving the Burnout Epidemic
In today's fast-paced tech industry, professionals and developers face an unprecedented rate of **burnout**. Standard journals are static—they don't listen, they don't help you process emotions, and they don't connect the dots in your thinking. 

**Personal Gemini Journal** is an empathetic, secure, and resilient AI journaling companion designed to help users navigate professional stress, track mental energy, and uncover hidden life patterns. By integrating advanced generative AI with real-time environmental context and absolute data privacy, it transforms the humble journal into an active wellness partner.

---

## 🏗️ Production-Grade Architecture
This application is built from the ground up for stability, scalability, and airtight security, utilizing a fully-integrated Google Cloud and Firebase ecosystem.

```
                  ┌────────────────────────────────────────┐
                  │          React 18 + Vite + Tailwind    │
                  │             (Firebase Hosting)         │
                  └───────────────────┬────────────────────┘
                                      │ (Bearer ID Token)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           FastAPI Python API           │
                  │          (Serverless Cloud Run)        │
                  └──────┬────────────┬────────────┬───────┘
                         │            │            │
      ┌──────────────────┴─┐   ┌──────┴──────┐   ┌─┴──────────────────┐
      │  Google ADK 2.x    │   │  Firestore  │   │ Cloud Pub/Sub Topic│
      │  Multi-Agent Loop  │   │ Vector KNN  │   │ (journal-enrich)   │
      └────────┬───────────┘   └─────────────┘   └─────────┬──────────┘
               │                                           │ (Push Hook)
               ▼                                           ▼
      ┌──────────────────┐                       ┌──────────────────┐
      │   Gemini 3.7     │                       │ Cloud Run Worker │
      │  Resilient API   │                       │ (Weather Engine) │
      └──────────────────┘                       └─────────┬────────┘
                                                           │
                                                           ▼
                                                 ┌──────────────────┐
                                                 │ Open-Meteo &     │
                                                 │ BigQuery GSOD    │
                                                 └──────────────────┘
```

### 🛠️ Technology Stack
* **Frontend:** React 18, Vite, Tailwind CSS, Recharts (Responsive Bento-Grid UI)
* **Backend:** Python 3.11/3.12, FastAPI (Containerized on Google Cloud Run in `asia-south1`)
* **Orchestration:** Google ADK 2.x (Agent Development Kit) SequentialAgent Workflow
* **Primary LLM:** `gemini-3.7-flash` (GA August 13, 2026)
* **Fallback LLM Ladder:** `gemini-3.7-flash` ➡️ `gemini-3.6-flash` ➡️ `gemini-flash-latest` ➡️ `gemini-2.5-flash` (Ensures 100% uptime)
* **Database:** Cloud Firestore (Native Mode) + Native Firestore Vector Search (KNN, Cosine Distance)
* **Authentication:** Firebase Authentication (Strict Federated Google Sign-In only, removing password attack vectors)
* **Asynchronous Jobs:** Cloud Pub/Sub triggering a Cloud Run push subscriber for background weather data collection
* **Analytics Layer:** BigQuery public dataset `bigquery-public-data.noaa_gsod` for climate/historical fallback
* **Secrets Management:** Google Cloud Secret Manager (API keys never touch the repository or environment files)
* **Export Engine:** `openpyxl` generating streamed-on-demand Excel reports (zero persistent disk footprint)

---

## 🔒 Security Constitution & The Threat Model
To fulfill the Ideathon's rigorous security requirements, this project is designed around a formalized **Security Constitution** located in `AGENTS.md` and enforced programmatically at multiple boundaries.

### 🛡️ Mapped Countermeasure Matrix
| Zone | Target Threat | Hardened Solution |
| :--- | :--- | :--- |
| **Input Surfaces** | Prompt injection via personalized Master Prompt | An **immutable system preamble** (`FIXED_SECURITY_PREAMBLE` inside `root_agent.py`) is hardcoded and always executed first. User-configured customization values are cleanly isolated inside `<user_master_prompt>` tags and treated strictly as passive context, never commands. |
| **Input Surfaces** | Malicious / oversized payloads | Full schema validation via Pydantic on all inbound JSON request bodies at the FastAPI boundary before any database or LLM execution. |
| **Reasoning & Planning** | Tool Hijack / Rogue Execution | Sub-agents take strictly structured, typed arguments. No dynamic text-based system command or raw SQL generation is allowed. |
| **Memory & State** | Cross-User Data Leaks & Session Hijacking | Short-lived Firebase ID tokens verified on every request. **Redundant Access Control:** Airtight wildcard owner-bound firestore security rule (`users/{userId}/{document=**}`) coupled with server-side API routing logic that strictly verifies `request.auth.uid == path.userId`. |
| **Inter-System** | Key Leakage | No API keys exist in git, Dockerfiles, or client-side bundles. Keys are securely retrieved from Secret Manager at runtime. |

---

## ⚡ Key Features

### 1. Dual-Provider Resilient LLM Engine (Self-Healing)
Your journaling session shouldn't freeze during high API traffic. Our custom backend features an instant failover system. If Google's Gemini API hits rate limits (HTTP 429) or network errors, the agent engine instantly falls back through our model ladder, routing seamlessly to **NVIDIA NIM** endpoints running Llama 3.2 and Nemotron models to guarantee a flawless user experience.

### 2. Geo-Location Memory & Mood Happiness Predictor
Includes free real-time weather integration (using the Open-Meteo API) with automatic coordinates-to-city resolution supporting Indian hubs (Bengaluru, Delhi, Mumbai, Pune, etc.) and global cities. The app calculates mood delta scores against local microclimates and highlights geolocated entry badges inside your vault.

### 3. Decoupled Async Weather Enrichment
To enforce the **Save Path Atomicity Invariant**, fetching weather context is never performed on the main transaction path. When you end a session, your journal is instantly committed to Firestore. A Cloud Pub/Sub message is published, triggering a lightweight background subscriber that queries the BigQuery GSOD historical weather database to enrich your entry asynchronously without blocking you.

### 4. Memory Vault (Semantic Search & Citations)
Allows you to query your past entries using natural language. The backend uses `gemini-embedding-001` to generate a 768-dimensional normalized vector (truncated using MRL to save space and indexing costs), storing it directly inside the Firestore document. It queries entries via native **Firestore Vector Search (KNN, COSINE)** and returns summaries with precise rank and date citations.

### 5. Responsible-AI Grounding Safety Net
If the per-turn mood classifier (`gemini-2.5-flash-lite`) detects a sustained period of low mood scores (e.g., scores $\le$ 2 across three consecutive turns) or explicit crisis language, the UI renders a non-intrusive, supportive prompt card surfacing national 24/7 helpline chips (AASRA, Vandrevala Foundation, etc.) with DOMPurify sanitization.

### 6. SaaS Monetization Rate Limiter
Features transaction-level rolling rate limiting. Free Tier accounts are capped at **10 chat messages per rolling 30-day period**. The rate checks are transactional and executed *before* any Gemini call is made, protecting your API quota from automated scraping or testing. A "Coming Soon" premium Pro Tier toggle is visible on the dashboard.

---

## 📂 Repository Structure
```
├── AGENTS.md                    # Airtight Security Constitution & Precedence
├── firestore.rules              # Enforced owner-bound Firebase Firestore security rules
├── Dockerfile                   # Multi-stage production container build config
├── backend/
│   ├── main.py                  # FastAPI app router and server initialization
│   ├── auth.py                  # Firebase Admin SDK short-lived ID token validation
│   ├── agents/
│   │   ├── model_utils.py       # Dual-Provider Resilient Multi-Model Fallback Ladder
│   │   ├── root_agent.py        # Master Orchestrator & Fixed Security Preamble boundary
│   │   ├── journal_coach.py     # 5-mode active conversational journaling agent
│   │   ├── mood_analyzer.py     # Low-cost turn-by-turn structured JSON extraction
│   │   ├── summary_agent.py     # Post-session structured metadata synthesis
│   │   ├── memory_agent.py      # Grounded RAG agent over Firestore vector index
│   │   └── analytics_agent.py   # BigQuery + Open-Meteo correlation analytics agent
│   ├── services/
│   │   ├── rate_limit.py        # Atomic server-side transaction check-and-increment
│   │   ├── save_pipeline.py     # Atomic save transaction + Pub/Sub queueing
│   │   └── embeddings.py        # gemini-embedding-001 MRL-truncation helper
│   └── routes/
│       ├── chat.py              # Rate-limit-gated multi-turn journaling endpoint
│       ├── save.py              # Session end and transaction commitment route
│       ├── memory.py            # Vector KNN semantic query search route
│       └── export.py            # Streamed openpyxl Excel download exporter
└── frontend/
    ├── src/
    │   ├── pages/               # Fully-wired bento-grid pages
    │   ├── design/              # Raw Stitch Mockups
    │   └── firebase.ts          # client Firebase app initialization
```

---

## 🚀 Getting Started Locally

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```
Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
NVIDIA_API_KEY=your_nvidia_api_key_here
FIREBASE_PROJECT_ID=personal-gemini-journal-507113
# In production, Cloud Run reads these straight from Secret Manager!
```
Run the FastAPI developer server:
```bash
uvicorn main:app --reload --port 8000
```
Verify local health check:
```bash
curl http://localhost:8000/api/health
# {"status":"healthy"}
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🌟 Production Deployment Checklist
Our active backend is fully deployed to Cloud Run in the `asia-south1` region:
* **Production Live Health Endpoint:** `https://gemini-journal-api-396039992677.asia-south1.run.app/api/health` ➡️ Response: `{"status":"healthy","time":"..."}`

---

## 📜 Acknowledgements
Built for the **Google Cloud Gen AI Academy APAC Edition Ideathon** under the official campaign hashtag **`#AccelerateAIWithCloudRun`**. Special thanks to Google Cloud, Firebase, and Hack2skill for hosting an outstanding, challenge-based developer learning journey.
