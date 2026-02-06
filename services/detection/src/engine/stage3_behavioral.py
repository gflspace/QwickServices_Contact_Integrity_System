"""Stage 3: Behavioral analysis — repetition detection and escalation scoring."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from ..models import EvidenceSpan, EvidenceType, StageResult


@dataclass
class UserThreadHistory:
    """Tracks detection history for a user in a thread."""
    detection_count: int = 0
    last_detection_ts: float = 0.0
    types_seen: set = field(default_factory=set)
    message_count: int = 0


class BehavioralContext:
    """In-memory store for behavioral context across messages.

    In production, this would be backed by Redis for cross-instance state.
    """

    def __init__(self, window_seconds: int = 3600):
        self.window_seconds = window_seconds
        # user_id -> thread_id -> history
        self._user_threads: dict[str, dict[str, UserThreadHistory]] = defaultdict(
            lambda: defaultdict(UserThreadHistory)
        )
        # user_id -> global detection count (across all threads)
        self._user_global: dict[str, int] = defaultdict(int)

    def record(
        self,
        user_id: str,
        thread_id: str,
        detected_types: list[str],
    ) -> None:
        """Record a detection event for behavioral tracking."""
        now = time.time()
        h = self._user_threads[user_id][thread_id]
        h.detection_count += 1
        h.last_detection_ts = now
        h.types_seen.update(detected_types)
        h.message_count += 1
        self._user_global[user_id] += 1

    def get_history(self, user_id: str, thread_id: str) -> UserThreadHistory:
        return self._user_threads[user_id][thread_id]

    def get_global_count(self, user_id: str) -> int:
        return self._user_global.get(user_id, 0)

    def get_thread_count(self, user_id: str) -> int:
        """How many distinct threads has this user had detections in?"""
        return len(self._user_threads.get(user_id, {}))


def run_stage3(
    text: str,
    user_id: str,
    thread_id: str,
    context: BehavioralContext,
) -> StageResult:
    """Run behavioral analysis looking for repetition and escalation patterns.

    Signals:
    - Repeated detection attempts in same thread (persistence)
    - Detections across multiple threads (pattern of behavior)
    - Rapid-fire attempts (burst detection)
    - Escalating sophistication (trying different types)
    """
    labels: list[str] = []
    evidence: list[EvidenceSpan] = []
    score = 0.0

    history = context.get_history(user_id, thread_id)
    global_count = context.get_global_count(user_id)
    thread_count = context.get_thread_count(user_id)

    # Signal 1: Repeated attempts in same thread
    if history.detection_count >= 3:
        persistence_score = min(0.3 + (history.detection_count - 3) * 0.1, 0.7)
        score = max(score, persistence_score)
        labels.append("persistent_contact_attempts")
        evidence.append(EvidenceSpan(
            offset=0,
            length=len(text),
            type=EvidenceType.INTENT,
            confidence=persistence_score,
        ))
    elif history.detection_count >= 1:
        # Mild signal for any repeat
        mild_score = 0.1 * history.detection_count
        score = max(score, mild_score)

    # Signal 2: Cross-thread behavior
    if thread_count >= 2:
        cross_thread_score = min(0.25 + (thread_count - 2) * 0.15, 0.6)
        score = max(score, cross_thread_score)
        labels.append("multi_thread_pattern")

    # Signal 3: Burst detection (multiple attempts in short window)
    if history.detection_count >= 2 and history.last_detection_ts > 0:
        time_since_last = time.time() - history.last_detection_ts
        if time_since_last < 60:  # Less than 1 minute between attempts
            burst_score = 0.5
            score = max(score, burst_score)
            labels.append("burst_attempts")
        elif time_since_last < 300:  # Less than 5 minutes
            burst_score = 0.3
            score = max(score, burst_score)

    # Signal 4: Type diversity (trying different methods)
    if len(history.types_seen) >= 3:
        diversity_score = min(0.4 + (len(history.types_seen) - 3) * 0.1, 0.7)
        score = max(score, diversity_score)
        labels.append("diverse_evasion_methods")

    # Signal 5: Global volume escalation
    if global_count >= 5:
        volume_score = min(0.3 + (global_count - 5) * 0.05, 0.6)
        score = max(score, volume_score)
        labels.append("high_volume_user")

    return StageResult(
        stage=3,
        score=round(min(score, 1.0), 3),
        labels=labels,
        evidence_spans=evidence,
    )
