"""FastAPI backend entrypoint for Personal Gemini Journal."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load backend/.env into environment at startup
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.auth_routes import router as auth_router
from backend.routes.master_prompt import router as master_prompt_router
from backend.routes.chat import router as chat_router
from backend.routes.save import router as save_router
from backend.routes.subscription import router as subscription_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.memory import router as memory_router
from backend.routes.export import router as export_router
from backend.subscriber.main import router as subscriber_router
from backend.routes.analytics import router as analytics_router

app = FastAPI(
    title="Personal Gemini Journal Backend",
    description="Backend API hosting Gemini journaling agents, auth verification, and persistence services.",
    version="1.0.0",
)

# Configure CORS for local development and Firebase Hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(master_prompt_router)
app.include_router(chat_router)
app.include_router(save_router)
app.include_router(subscription_router)
app.include_router(dashboard_router)
app.include_router(memory_router)
app.include_router(export_router)
app.include_router(subscriber_router)
app.include_router(analytics_router)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "personal-gemini-journal-backend",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
