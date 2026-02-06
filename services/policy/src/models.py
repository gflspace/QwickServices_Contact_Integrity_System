"""Pydantic models for the Policy & Enforcement Service."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    ALLOW = "allow"
    NUDGE = "nudge"
    SOFT_BLOCK = "soft_block"
    HARD_BLOCK = "hard_block"
    WARNING = "warning"
    COOLDOWN = "cooldown"
    RESTRICTION = "restriction"
    SUSPENSION_CANDIDATE = "suspension_candidate"


class TargetScope(str, Enum):
    MESSAGE = "message"
    THREAD = "thread"
    ACCOUNT = "account"


class EnforceRequest(BaseModel):
    detection_id: str
    user_id: str
    thread_id: Optional[str] = None
    risk_score: float = Field(ge=0.0, le=1.0)
    labels: list[str] = Field(default_factory=list)


class EnforcementDetails(BaseModel):
    duration_hours: Optional[int] = None
    message: str
    scope: TargetScope


class EnforceResponse(BaseModel):
    action: ActionType
    risk_band: RiskBand
    strike_count: int = 0
    strike_id: Optional[str] = None
    case_id: Optional[str] = None
    enforcement_details: Optional[EnforcementDetails] = None


class Strike(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    strike_number: int
    action_taken: str
    is_active: bool = True
    window_start: datetime
    window_end: datetime
    case_id: Optional[str] = None
    detection_id: Optional[str] = None


class StrikeListResponse(BaseModel):
    user_id: str
    strikes: list[Strike]
    total_active: int


class ThresholdConfig(BaseModel):
    allow_max: float = 0.39
    nudge_min: float = 0.40
    nudge_max: float = 0.64
    soft_block_min: float = 0.65
    soft_block_max: float = 0.84
    hard_block_min: float = 0.85


class ThresholdUpdate(BaseModel):
    thresholds: ThresholdConfig
    changed_by: str
    reason: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
