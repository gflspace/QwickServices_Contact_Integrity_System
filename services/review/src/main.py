"""Review Queue Service — FastAPI application entry point."""

from __future__ import annotations

import time

from fastapi import FastAPI

from .api.routes import router

_start_time = time.time()

app = FastAPI(
    title="CIS Review Queue Service",
    version="1.0.0",
    description="Contact Integrity System — Moderation review queue",
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "review",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
    }
