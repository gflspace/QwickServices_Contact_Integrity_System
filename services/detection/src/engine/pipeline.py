"""Detection pipeline orchestrator — combines all stages into a single risk score."""

from __future__ import annotations

import hashlib
import time
from typing import Optional

from ..config import settings
from ..models import AnalyzeRequest, AnalyzeResponse, EvidenceSpan, EvidenceType, StageResult
from .stage1_rules import run_stage1
from .stage2_nlp import run_stage2
from .stage3_behavioral import run_stage3, BehavioralContext


class DetectionPipeline:
    """Orchestrates the 3-stage detection pipeline."""

    def __init__(
        self,
        stage1_weight: float = settings.STAGE1_WEIGHT,
        stage2_weight: float = settings.STAGE2_WEIGHT,
        stage3_weight: float = settings.STAGE3_WEIGHT,
    ):
        self.stage1_weight = stage1_weight
        self.stage2_weight = stage2_weight
        self.stage3_weight = stage3_weight
        self.behavioral_context = BehavioralContext()

    async def analyze(
        self,
        request: AnalyzeRequest,
        stages: Optional[list[int]] = None,
    ) -> AnalyzeResponse:
        """Run the detection pipeline on a message.

        Args:
            request: The message to analyze.
            stages: Optional list of stages to run (default: all [1, 2, 3]).
                    Stage 1 = deterministic rules,
                    Stage 2 = NLP intent,
                    Stage 3 = behavioral analysis.
        """
        start_ms = _now_ms()
        run_stages = stages or request.stages or [1, 2, 3]

        all_labels: list[str] = []
        all_evidence: list[EvidenceSpan] = []
        all_hashed: list[str] = []
        stage_results: list[StageResult] = []
        highest_stage = 0
        model_version: Optional[str] = None

        # Stage 1: Deterministic rules
        if 1 in run_stages:
            s1 = run_stage1(request.content)
            stage_results.append(s1)
            all_labels.extend(s1.labels)
            all_evidence.extend(s1.evidence_spans)
            all_hashed.extend(s1.hashed_tokens)
            if s1.score > 0:
                highest_stage = 1

        # Stage 2: NLP intent classification
        if 2 in run_stages:
            context_texts = [m.content for m in request.context_messages]
            s2 = await run_stage2(request.content, context_texts)
            stage_results.append(s2)
            all_labels.extend(s2.labels)
            all_evidence.extend(s2.evidence_spans)
            if s2.model_version:
                model_version = s2.model_version
            if s2.score > 0:
                highest_stage = max(highest_stage, 2)

        # Stage 3: Behavioral analysis
        if 3 in run_stages:
            s3 = run_stage3(
                request.content,
                request.user_id,
                request.thread_id,
                self.behavioral_context,
            )
            stage_results.append(s3)
            all_labels.extend(s3.labels)
            all_evidence.extend(s3.evidence_spans)
            if s3.score > 0:
                highest_stage = max(highest_stage, 3)

        # Combine scores using weighted average
        combined_score = self._combine_scores(stage_results, run_stages)

        # Deduplicate labels
        unique_labels = list(dict.fromkeys(all_labels))

        # Hash sensitive tokens
        unique_hashed = list(dict.fromkeys(all_hashed))

        processing_ms = _now_ms() - start_ms

        return AnalyzeResponse(
            message_id=request.message_id,
            risk_score=round(combined_score, 3),
            labels=unique_labels,
            evidence_spans=all_evidence,
            hashed_tokens=unique_hashed,
            stage=highest_stage if highest_stage > 0 else 1,
            ruleset_version=settings.RULESET_VERSION,
            model_version=model_version,
            processing_ms=processing_ms,
        )

    def _combine_scores(
        self, results: list[StageResult], run_stages: list[int]
    ) -> float:
        """Weighted combination of stage scores.

        If only a subset of stages ran, renormalize weights.
        Uses max-boosting: if any single stage is very high confidence,
        the combined score is at least as high as that stage's contribution.
        """
        if not results:
            return 0.0

        weight_map = {
            1: self.stage1_weight,
            2: self.stage2_weight,
            3: self.stage3_weight,
        }

        total_weight = sum(weight_map.get(s, 0) for s in run_stages)
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        max_score = 0.0
        for r in results:
            w = weight_map.get(r.stage, 0) / total_weight
            weighted_sum += r.score * w
            max_score = max(max_score, r.score)

        # Boost: if any stage has very high confidence (>0.85), use at least 80% of that
        if max_score >= 0.85:
            weighted_sum = max(weighted_sum, max_score * 0.80)

        return min(weighted_sum, 1.0)


def hash_token(value: str) -> str:
    """SHA-256 hash a detected contact value for storage."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def _now_ms() -> int:
    return int(time.time() * 1000)
