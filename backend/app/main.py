"""
OPUS — Vendor Risk Management System
FastAPI Application Entrypoint
"""
import os
import logging
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.api.routes import router
from app.core.vector import init_collections


# ═══════════════════════════════════════════════════════════════════
# Logging Configuration
# ═══════════════════════════════════════════════════════════════════

def setup_logging():
    """Configure structured logging with structlog."""
    settings = get_settings()

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ═══════════════════════════════════════════════════════════════════
# Application Lifecycle
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging()
    logger = logging.getLogger(__name__)

    settings = get_settings()

    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Initialize Qdrant collections
    try:
        init_collections()
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Qdrant collections: {e}")

    logger.info(
        f"OPUS Vendor Risk Management System started "
        f"(env={settings.app_env})"
    )

    yield

    logger.info("OPUS shutting down")


# ═══════════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="OPUS — Vendor Risk Management System",
    description=(
        "Multi-agent autonomous vendor risk assessment platform. "
        "Phase 1: Document Intake, Security Review, and Supervisor agents."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include API routes
app.include_router(router)


# ═══════════════════════════════════════════════════════════════════
# Root Endpoint
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Root endpoint — system information."""
    return {
        "system": "OPUS — Vendor Risk Management System",
        "version": "1.0.0",
        "phase": "Phase 1: Foundation & Core Infrastructure",
        "agents": [
            "Supervisor Agent",
            "Document Intake Agent",
            "Security Review Agent",
        ],
        "docs": "/docs",
        "health": "/api/v1/health",
    }
