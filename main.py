"""
Raveya AI — FastAPI application entry point.

Modules implemented:
  - Module 2: B2B Proposal Generator  (/api/v1/proposals)
  - Module 4: WhatsApp Support Bot    (/api/v1/whatsapp)

Architecture outline for remaining modules is in README.md.
"""
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logger import setup_logging
from database.database import init_db, close_db
from modules.b2b_proposal.router import router as proposal_router
from modules.whatsapp_bot.router import router as whatsapp_router

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Raveya AI starting up — env=%s", settings.app_env)
    await init_db()
    logger.info("Database tables initialised.")

    # Always seed demo data (idempotent — skips existing records)
    from seed import seed_demo_data
    await seed_demo_data()
    logger.info("Demo seed data loaded.")

    yield

    await close_db()
    logger.info("Raveya AI shutting down.")


app = FastAPI(
    title="Raveya AI Platform",
    description=(
        "AI-powered modules for sustainable commerce:\n\n"
        "- **Module 2**: B2B Proposal Generator\n"
        "- **Module 4**: WhatsApp Support Bot\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler (surfaces real errors) ───────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
        },
    )

# ── Routers ───────────────────────────────────────────────
app.include_router(proposal_router)
app.include_router(whatsapp_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Raveya AI Platform",
        "version": "1.0.0",
        "status": "healthy",
        "modules": {
            "b2b_proposal": "/api/v1/proposals",
            "whatsapp_bot": "/api/v1/whatsapp",
        },
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/debug/config", tags=["Health"])
async def debug_config():
    """Shows whether critical env vars are configured (values masked)."""
    return {
        "ai_provider": settings.ai_provider,
        "openai_api_key_set": bool(settings.openai_api_key),
        "groq_api_key_set": bool(settings.groq_api_key),
        "openai_model": settings.openai_model,
        "mongodb_connected": bool(settings.mongodb_url),
        "app_env": settings.app_env,
        "twilio_configured": bool(settings.twilio_account_sid),
    }


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", settings.app_port))  # Render/Railway inject PORT
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
