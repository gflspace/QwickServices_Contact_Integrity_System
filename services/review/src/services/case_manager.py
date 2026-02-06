"""Case management service — CRUD operations for moderation cases."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models import (
    Case,
    CaseDetail,
    CaseListResponse,
    CaseStatus,
    CreateCaseRequest,
    ModerationAction,
    Resolution,
    UpdateCaseRequest,
)


class CaseManager:
    """In-memory case manager. In production, backed by PostgreSQL."""

    def __init__(self):
        self._cases: dict[str, Case] = {}
        self._actions: dict[str, list[ModerationAction]] = {}  # case_id -> actions

    def create_case(self, request: CreateCaseRequest) -> Case:
        case = Case(
            id=str(uuid.uuid4()),
            detection_id=request.detection_id,
            user_id=request.user_id,
            thread_id=request.thread_id,
            priority=request.priority,
            status=CaseStatus.OPEN,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._cases[case.id] = case
        self._actions[case.id] = []
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self._cases.get(case_id)

    def get_case_detail(self, case_id: str) -> Optional[CaseDetail]:
        case = self._cases.get(case_id)
        if not case:
            return None
        actions = self._actions.get(case_id, [])
        return CaseDetail(
            **case.model_dump(),
            detection=None,
            actions=actions,
            strikes=[],
        )

    def list_cases(
        self,
        status: Optional[CaseStatus] = None,
        assigned_to: Optional[str] = None,
        user_id: Optional[str] = None,
        priority_min: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CaseListResponse:
        filtered = list(self._cases.values())

        if status:
            filtered = [c for c in filtered if c.status == status]
        if assigned_to:
            filtered = [c for c in filtered if c.assigned_to == assigned_to]
        if user_id:
            filtered = [c for c in filtered if c.user_id == user_id]
        if priority_min is not None:
            filtered = [c for c in filtered if c.priority >= priority_min]

        # Sort by priority descending, then created_at descending
        filtered.sort(key=lambda c: (-c.priority, c.created_at), reverse=False)

        total = len(filtered)
        page = filtered[offset : offset + limit]

        return CaseListResponse(
            cases=page,
            total=total,
            limit=limit,
            offset=offset,
        )

    def update_case(self, case_id: str, update: UpdateCaseRequest) -> Optional[Case]:
        case = self._cases.get(case_id)
        if not case:
            return None

        if update.status is not None:
            if not self._is_valid_transition(case.status, update.status):
                raise ValueError(
                    f"Invalid status transition: {case.status} -> {update.status}"
                )
            case.status = update.status

        if update.assigned_to is not None:
            case.assigned_to = update.assigned_to
            # Auto-transition to in_review when assigned
            if case.status == CaseStatus.OPEN and update.assigned_to:
                case.status = CaseStatus.IN_REVIEW

        if update.resolution is not None:
            case.resolution = update.resolution
        if update.resolution_note is not None:
            case.resolution_note = update.resolution_note

        case.updated_at = datetime.now(timezone.utc)
        self._cases[case_id] = case
        return case

    def file_appeal(self, case_id: str, reason: str) -> Optional[Case]:
        case = self._cases.get(case_id)
        if not case:
            return None

        if case.status not in (CaseStatus.RESOLVED,):
            raise ValueError(f"Cannot appeal a case with status: {case.status}")

        case.status = CaseStatus.APPEALED
        case.resolution_note = f"Appeal reason: {reason}"
        case.updated_at = datetime.now(timezone.utc)
        self._cases[case_id] = case
        return case

    def add_action(self, case_id: str, action: ModerationAction) -> None:
        if case_id not in self._actions:
            self._actions[case_id] = []
        self._actions[case_id].append(action)

    def get_actions(self, case_id: str) -> list[ModerationAction]:
        return self._actions.get(case_id, [])

    @staticmethod
    def _is_valid_transition(current: CaseStatus, target: CaseStatus) -> bool:
        valid_transitions = {
            CaseStatus.OPEN: {CaseStatus.IN_REVIEW, CaseStatus.RESOLVED},
            CaseStatus.IN_REVIEW: {CaseStatus.RESOLVED, CaseStatus.OPEN},
            CaseStatus.RESOLVED: {CaseStatus.APPEALED},
            CaseStatus.APPEALED: {CaseStatus.IN_REVIEW, CaseStatus.OVERTURNED},
            CaseStatus.OVERTURNED: set(),
        }
        return target in valid_transitions.get(current, set())
