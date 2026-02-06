"""FastAPI application entry point for Policy & Enforcement Service."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Contact Integrity System - Policy & Enforcement Service",
    description=(
        "Policy engine that enforces threshold-based risk decisions and manages "
        "user strike escalation. Provides enforcement actions ranging from "
        "educational nudges to account-level restrictions."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup tasks.

    In production, this would:
    - Initialize database connection pool
    - Load threshold configuration from database
    - Set up Redis connection for strike storage
    - Initialize monitoring/metrics
    """
    logger.info("Starting Policy & Enforcement Service")
    logger.info(f"Strike window: {settings.STRIKE_WINDOW_DAYS} days")
    logger.info(f"Service listening on port {settings.POLICY_PORT}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown tasks.

    In production, this would:
    - Close database connections
    - Flush pending metrics
    - Clean up resources
    """
    logger.info("Shutting down Policy & Enforcement Service")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.POLICY_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,  # Disable in production
    )
