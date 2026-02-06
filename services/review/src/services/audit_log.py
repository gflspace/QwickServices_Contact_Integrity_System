"""Immutable audit log service for moderation actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models import (
    ActorRole,
    CreateActionRequest,
    ModerationAction,
    ModerationActionType,
)


class AuditLog:
    """Append-only audit log for moderation actions.

    In production, this writes to integrity_moderation_action table
    which has NO update_at column and no UPDATE/DELETE operations allowed.
    """

    def __init__(self):
        self._log: list[ModerationAction] = []

    def record_action(
        self,
        case_id: str,
        request: CreateActionRequest,
    ) -> ModerationAction:
        """Record an immutable moderation action."""
        # Permanent actions require human approval
        requires_human = request.is_permanent

        action = ModerationAction(
            id=str(uuid.uuid4()),
            case_id=case_id,
            actor_id=request.actor_id,
            actor_role=request.actor_role,
            action_type=request.action_type,
            target_user_id=request.target_user_id,
            target_scope=request.target_scope,
            reason_code=request.reason_code,
            metadata=request.metadata,
            is_permanent=request.is_permanent,
            requires_human=requires_human,
            approved_by=None,  # Will be set when human approves
            created_at=datetime.now(timezone.utc),
        )

        self._log.append(action)
        return action

    def get_actions_for_case(self, case_id: str) -> list[ModerationAction]:
        return [a for a in self._log if a.case_id == case_id]

    def get_actions_for_user(
        self,
        target_user_id: str,
        limit: int = 50,
    ) -> list[ModerationAction]:
        user_actions = [a for a in self._log if a.target_user_id == target_user_id]
        # Most recent first
        user_actions.sort(key=lambda a: a.created_at, reverse=True)
        return user_actions[:limit]

    def get_pending_approvals(self) -> list[ModerationAction]:
        """Get permanent actions that require human approval."""
        return [
            a for a in self._log
            if a.requires_human and a.approved_by is None
        ]

    @property
    def total_actions(self) -> int:
        return len(self._log)
