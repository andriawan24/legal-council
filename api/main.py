"""
Legal Council API - Main Application.

FastAPI application for the Legal Council virtual deliberation system.
Provides endpoints for session management, case search, deliberation chat,
and legal opinion generation.
"""

import logging
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import database as db
from config import get_settings
from routers import sessions_router, cases_router, deliberation_router
from schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Legal Council API...")
    settings = get_settings()

    # Initialize database pool
    if settings.database_url:
        try:
            await db.get_pool()
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Legal Council API...")
    await db.close_pool()
    logger.info("Database connection pool closed")


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    Legal Council API - AI-powered deliberation system for Indonesian judges.

    This API provides:
    - **Session Management**: Create and manage deliberation sessions
    - **Case Search**: Search legal cases using semantic and text search
    - **Deliberation**: Chat with AI judicial agents
    - **Legal Opinion**: Generate legal opinions from deliberations

    ## AI Agents
    Three AI judges with distinct perspectives:
    - **Strict Constructionist**: Literal law interpretation
    - **Humanist**: Rehabilitative justice focus
    - **Historian**: Precedent and jurisprudence expert
    """,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# Include routers
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(cases_router, prefix=settings.api_prefix)
app.include_router(deliberation_router, prefix=settings.api_prefix)


# Health check endpoints
@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API info."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the API and its dependencies.
    """
    # Check database connection
    db_status = "healthy"
    try:
        db_healthy = await db.check_health()
        if not db_healthy:
            db_status = "unhealthy"
    except Exception:
        db_status = "unavailable"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        version=settings.api_version,
    )


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """
    Readiness probe for Kubernetes/Cloud Run.

    Returns 200 if the service is ready to receive traffic.
    """
    db_healthy = await db.check_health()
    if not db_healthy:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "database unavailable"},
        )
    return {"status": "ready"}


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """
    Liveness probe for Kubernetes/Cloud Run.

    Returns 200 if the service is alive.
    """
    return {"status": "alive"}


# API documentation customization
@app.get("/api/v1", tags=["info"])
async def api_info():
    """Get API information and available endpoints."""
    return {
        "version": "1.0.0",
        "endpoints": {
            "sessions": {
                "POST /api/v1/sessions": "Create a new deliberation session",
                "GET /api/v1/sessions": "List all sessions",
                "GET /api/v1/sessions/{id}": "Get session details",
                "DELETE /api/v1/sessions/{id}": "Archive a session",
                "POST /api/v1/sessions/{id}/opinion": "Generate legal opinion",
            },
            "cases": {
                "POST /api/v1/cases/search": "Search cases",
                "GET /api/v1/cases/{id}": "Get case details",
                "GET /api/v1/cases/statistics": "Get case statistics",
            },
            "deliberation": {
                "POST /api/v1/sessions/{id}/messages": "Send message and get responses",
                "GET /api/v1/sessions/{id}/messages": "Get message history",
                "POST /api/v1/sessions/{id}/messages/stream": "Stream agent responses",
            },
        },
        "agents": {
            "strict": "Strict Constructionist - Literal law interpretation",
            "humanist": "Humanist - Rehabilitative justice focus",
            "historian": "Historian - Precedent and statistics expert",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=settings.debug,
    )
