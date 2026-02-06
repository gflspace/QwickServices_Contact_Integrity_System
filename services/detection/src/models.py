"""Pydantic models for the Detection Service."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    SOCIAL = "social"
    INTENT = "intent"
    OBFUSCATION = "obfuscation"


class EvidenceSpan(BaseModel):
    offset: int
    length: int
    type: EvidenceType
    confidence: float = 1.0


class ContextMessage(BaseModel):
    content: str
    user_id: str
    timestamp: Optional[datetime] = None


class AnalyzeRequest(BaseModel):
    message_id: str
    thread_id: str
    user_id: str
    content: str = Field(max_length=10000)
    context_messages: list[ContextMessage] = Field(default_factory=list)
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    stages: Optional[list[int]] = None  # Which stages to run (default: all)


class AnalyzeResponse(BaseModel):
    detection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    labels: list[str] = Field(default_factory=list)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    hashed_tokens: list[str] = Field(default_factory=list)
    stage: int = Field(description="Highest stage that contributed to the score")
    ruleset_version: str
    model_version: Optional[str] = None
    processing_ms: int = 0


class BatchAnalyzeRequest(BaseModel):
    messages: list[AnalyzeRequest] = Field(max_length=50)


class BatchAnalyzeResponse(BaseModel):
    results: list[AnalyzeResponse]


class StageResult(BaseModel):
    """Internal result from a single detection stage."""
    stage: int
    score: float = Field(ge=0.0, le=1.0)
    labels: list[str] = Field(default_factory=list)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    hashed_tokens: list[str] = Field(default_factory=list)
    model_version: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    service: str
    version: str
    uptime_seconds: Optional[float] = None
