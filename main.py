"""
Raveya AI — FastAPI application entry point.

Modules implemented:
  - Module 2: B2B Proposal Generator  (/api/v1/proposals)
  - Module 4: WhatsApp Support Bot    (/api/v1/whatsapp)

Architecture outline for remaining modules is in README.md.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logger import setup_logging
from database.database import init_db
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

    # Seed demo data in development
    if settings.app_env == "development":
        from seed import seed_demo_data
        await seed_demo_data()
        logger.info("Demo seed data loaded.")

    yield

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
