"""Moderator service — assignment and workflow management."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ..models import Case, CaseStatus


class ModeratorService:
    """Manages moderator assignments and workload balancing."""

    def __init__(self):
        # moderator_id -> set of assigned case_ids
        self._assignments: dict[str, set[str]] = defaultdict(set)
        self._max_concurrent: int = 10  # Max cases per moderator

    def assign_case(self, case: Case, moderator_id: str) -> bool:
        """Assign a case to a moderator, respecting workload limits."""
        current_load = len(self._assignments[moderator_id])
        if current_load >= self._max_concurrent:
            return False

        self._assignments[moderator_id].add(case.id)
        return True

    def unassign_case(self, case_id: str, moderator_id: str) -> None:
        """Remove a case assignment from a moderator."""
        self._assignments[moderator_id].discard(case_id)

    def get_moderator_load(self, moderator_id: str) -> int:
        """Get current number of assigned cases for a moderator."""
        return len(self._assignments[moderator_id])

    def get_assigned_cases(self, moderator_id: str) -> set[str]:
        """Get all case IDs assigned to a moderator."""
        return self._assignments[moderator_id].copy()

    def find_least_loaded_moderator(
        self, moderator_ids: list[str]
    ) -> Optional[str]:
        """Find the moderator with the fewest active assignments."""
        if not moderator_ids:
            return None

        available = [
            (mid, len(self._assignments[mid]))
            for mid in moderator_ids
            if len(self._assignments[mid]) < self._max_concurrent
        ]

        if not available:
            return None

        available.sort(key=lambda x: x[1])
        return available[0][0]

    def on_case_resolved(self, case_id: str) -> None:
        """Clean up assignments when a case is resolved."""
        for moderator_id, cases in self._assignments.items():
            cases.discard(case_id)
