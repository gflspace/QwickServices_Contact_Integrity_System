"""Pydantic models for the Review Queue Service."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    APPEALED = "appealed"
    OVERTURNED = "overturned"


class Resolution(str, Enum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class ActorRole(str, Enum):
    SYSTEM = "system"
    MODERATOR = "moderator"
    OPS = "ops"
    ADMIN = "admin"


class ModerationActionType(str, Enum):
    NUDGE = "nudge"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    THREAD_LOCK = "thread_lock"
    COOLDOWN = "cooldown"
    RESTRICTION = "restriction"
    OVERRIDE = "override"
    APPEAL_GRANT = "appeal_grant"


class TargetScope(str, Enum):
    MESSAGE = "message"
    THREAD = "thread"
    ACCOUNT = "account"


class Case(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detection_id: str
    user_id: str
    thread_id: str
    status: CaseStatus = CaseStatus.OPEN
    priority: int = 0
    assigned_to: Optional[str] = None
    resolution: Optional[Resolution] = None
    resolution_note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaseDetail(Case):
    detection: Optional[dict[str, Any]] = None
    actions: list[ModerationAction] = Field(default_factory=list)
    strikes: list[dict[str, Any]] = Field(default_factory=list)


class CaseListResponse(BaseModel):
    cases: list[Case]
    total: int
    limit: int
    offset: int


class CreateCaseRequest(BaseModel):
    detection_id: str
    user_id: str
    thread_id: str
    priority: int = 0


class UpdateCaseRequest(BaseModel):
    status: Optional[CaseStatus] = None
    assigned_to: Optional[str] = None
    resolution: Optional[Resolution] = None
    resolution_note: Optional[str] = None


class ModerationAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    actor_id: str
    actor_role: ActorRole
    action_type: ModerationActionType
    target_user_id: str
    target_scope: TargetScope
    reason_code: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_permanent: bool = False
    requires_human: bool = False
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateActionRequest(BaseModel):
    actor_id: str
    actor_role: ActorRole
    action_type: ModerationActionType
    target_user_id: str
    target_scope: TargetScope
    reason_code: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_permanent: bool = False


class AppealRequest(BaseModel):
    reason: str = Field(max_length=2000)


class QueueStats(BaseModel):
    open_cases: int = 0
    in_review_cases: int = 0
    resolved_today: int = 0
    avg_resolution_hours: float = 0.0
    false_positive_rate: float = 0.0
    top_labels: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
