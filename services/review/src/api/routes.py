"""Review Queue API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models import (
    AppealRequest,
    Case,
    CaseDetail,
    CaseListResponse,
    CaseStatus,
    CreateActionRequest,
    CreateCaseRequest,
    ModerationAction,
    QueueStats,
    UpdateCaseRequest,
)
from ..services.audit_log import AuditLog
from ..services.case_manager import CaseManager
from ..services.moderator import ModeratorService

router = APIRouter()

# Singleton service instances
_case_manager = CaseManager()
_audit_log = AuditLog()
_moderator_service = ModeratorService()


def get_case_manager() -> CaseManager:
    return _case_manager


def get_audit_log() -> AuditLog:
    return _audit_log


def get_moderator_service() -> ModeratorService:
    return _moderator_service


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    status: Optional[CaseStatus] = None,
    assigned_to: Optional[str] = None,
    user_id: Optional[str] = None,
    priority_min: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> CaseListResponse:
    """List moderation cases with optional filters."""
    return _case_manager.list_cases(
        status=status,
        assigned_to=assigned_to,
        user_id=user_id,
        priority_min=priority_min,
        limit=min(limit, 100),
        offset=offset,
    )


@router.post("/cases", response_model=Case, status_code=201)
async def create_case(request: CreateCaseRequest) -> Case:
    """Create a new moderation case."""
    return _case_manager.create_case(request)


@router.get("/cases/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str) -> CaseDetail:
    """Get full case details including actions and detection info."""
    detail = _case_manager.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return detail


@router.patch("/cases/{case_id}", response_model=Case)
async def update_case(case_id: str, request: UpdateCaseRequest) -> Case:
    """Update case status, assignment, or resolution."""
    try:
        case = _case_manager.update_case(case_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Handle moderator assignment tracking
    if request.assigned_to:
        success = _moderator_service.assign_case(case, request.assigned_to)
        if not success:
            raise HTTPException(
                status_code=409,
                detail="Moderator has reached maximum concurrent case limit",
            )

    # Clean up on resolution
    if request.status == CaseStatus.RESOLVED and case.assigned_to:
        _moderator_service.on_case_resolved(case_id)

    return case


@router.post("/cases/{case_id}/actions", response_model=ModerationAction, status_code=201)
async def create_moderation_action(
    case_id: str, request: CreateActionRequest
) -> ModerationAction:
    """Record an immutable moderation action on a case."""
    case = _case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    action = _audit_log.record_action(case_id, request)
    _case_manager.add_action(case_id, action)
    return action


@router.post("/cases/{case_id}/appeal", response_model=Case)
async def file_appeal(case_id: str, request: AppealRequest) -> Case:
    """File an appeal for a resolved case."""
    try:
        case = _case_manager.file_appeal(case_id, request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/stats", response_model=QueueStats)
async def get_stats(period_days: int = 7) -> QueueStats:
    """Get review queue statistics."""
    all_cases = _case_manager.list_cases(limit=10000)

    open_count = sum(1 for c in all_cases.cases if c.status == CaseStatus.OPEN)
    in_review_count = sum(1 for c in all_cases.cases if c.status == CaseStatus.IN_REVIEW)
    resolved_count = sum(1 for c in all_cases.cases if c.status == CaseStatus.RESOLVED)

    # Calculate false positive rate from resolved cases
    resolved_cases = [c for c in all_cases.cases if c.status == CaseStatus.RESOLVED]
    false_positives = sum(
        1 for c in resolved_cases if c.resolution and c.resolution.value == "false_positive"
    )
    fp_rate = false_positives / len(resolved_cases) if resolved_cases else 0.0

    return QueueStats(
        open_cases=open_count,
        in_review_cases=in_review_count,
        resolved_today=resolved_count,
        avg_resolution_hours=0.0,
        false_positive_rate=round(fp_rate, 3),
    )
