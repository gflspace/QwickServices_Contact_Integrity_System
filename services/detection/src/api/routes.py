"""Detection Service API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..engine.pipeline import DetectionPipeline
from ..models import AnalyzeRequest, AnalyzeResponse, BatchAnalyzeRequest, BatchAnalyzeResponse

router = APIRouter()

# Singleton pipeline instance
_pipeline = DetectionPipeline()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_message(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a single chat message for contact information exchange attempts."""
    try:
        result = await _pipeline.analyze(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
async def analyze_batch(request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    """Analyze multiple messages in batch."""
    results = []
    for msg in request.messages:
        try:
            result = await _pipeline.analyze(msg)
            results.append(result)
        except Exception:
            # On individual failure, return zero-score result
            results.append(AnalyzeResponse(
                message_id=msg.message_id,
                risk_score=0.0,
                labels=["analysis_error"],
                evidence_spans=[],
                hashed_tokens=[],
                stage=0,
                ruleset_version="1.0.0",
                processing_ms=0,
            ))
    return BatchAnalyzeResponse(results=results)
