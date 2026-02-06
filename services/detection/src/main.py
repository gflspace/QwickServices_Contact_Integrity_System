"""Detection Service — FastAPI application entry point."""

from __future__ import annotations

import time

from fastapi import FastAPI

from .api.routes import router
from .config import settings

_start_time = time.time()

app = FastAPI(
    title="CIS Detection Service",
    version="1.0.0",
    description="Contact Integrity System — NLP + rules detection engine",
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "detection",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
    }
