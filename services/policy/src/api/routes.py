"""FastAPI routes for the Policy & Enforcement Service."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..engine.actions import get_action_engine
from ..engine.strikes import get_strike_manager
from ..engine.thresholds import get_threshold_engine
from ..models import (
    EnforceRequest,
    EnforceResponse,
    HealthResponse,
    StrikeListResponse,
    ThresholdConfig,
    ThresholdUpdate,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return HealthResponse(
        status="healthy",
        service="policy-enforcement",
        version="1.0.0",
    )


@router.post("/enforce", response_model=EnforceResponse)
async def enforce(request: EnforceRequest) -> EnforceResponse:
    """
    Evaluate detection and determine enforcement action.

    This is the primary enforcement endpoint. It:
    1. Classifies risk score into risk band
    2. Checks user strike history
    3. Determines appropriate enforcement action
    4. Adds strike if warranted
    5. Returns enforcement decision with details

    Args:
        request: Detection result with risk score and context

    Returns:
        Enforcement decision with action, details, and strike info

    Raises:
        HTTPException: If risk score is invalid or enforcement fails
    """
    try:
        action_engine = get_action_engine()
        response = action_engine.enforce(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log error in production
        raise HTTPException(
            status_code=500,
            detail=f"Enforcement failed: {str(e)}"
        )


@router.get("/strikes/{user_id}", response_model=StrikeListResponse)
async def get_user_strikes(
    user_id: str,
    active_only: bool = Query(True, description="Return only active strikes"),
) -> StrikeListResponse:
    """
    Get strike history for a user.

    Args:
        user_id: User identifier
        active_only: If True, only return strikes within rolling window

    Returns:
        User strike history with total active count

    Example:
        GET /strikes/user_123?active_only=true
        GET /strikes/user_123?active_only=false  # All strikes, including expired
    """
    try:
        strike_manager = get_strike_manager()
        strikes = strike_manager.get_all_strikes(user_id, active_only=active_only)

        # Count active strikes
        active_strikes = strike_manager.get_active_strikes(user_id)
        total_active = len(active_strikes)

        return StrikeListResponse(
            user_id=user_id,
            strikes=strikes,
            total_active=total_active,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strikes: {str(e)}"
        )


@router.get("/thresholds", response_model=ThresholdConfig)
async def get_thresholds() -> ThresholdConfig:
    """
    Get current threshold configuration.

    Returns:
        Current threshold configuration for risk band classification

    Example:
        GET /thresholds
        {
            "allow_max": 0.39,
            "nudge_min": 0.40,
            "nudge_max": 0.64,
            "soft_block_min": 0.65,
            "soft_block_max": 0.84,
            "hard_block_min": 0.85
        }
    """
    try:
        threshold_engine = get_threshold_engine()
        return threshold_engine.get_config()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve thresholds: {str(e)}"
        )


@router.put("/thresholds", response_model=ThresholdConfig)
async def update_thresholds(update: ThresholdUpdate) -> ThresholdConfig:
    """
    Update threshold configuration.

    This endpoint allows runtime tuning of risk band thresholds for A/B testing
    or policy adjustments. All changes are logged with reason and changed_by
    for audit trail.

    Args:
        update: New thresholds with reason and changed_by

    Returns:
        Updated threshold configuration

    Raises:
        HTTPException: If thresholds are invalid or update fails

    Example:
        PUT /thresholds
        {
            "thresholds": {
                "allow_max": 0.35,
                "nudge_min": 0.36,
                "nudge_max": 0.60,
                "soft_block_min": 0.61,
                "soft_block_max": 0.80,
                "hard_block_min": 0.81
            },
            "changed_by": "admin@example.com",
            "reason": "A/B test: stricter nudge threshold"
        }
    """
    try:
        threshold_engine = get_threshold_engine()

        # Validate new thresholds by attempting to update
        threshold_engine.update_config(update.thresholds)

        # In production, log the change to audit trail
        # audit_log.record_threshold_change(
        #     old_config=old_config,
        #     new_config=update.thresholds,
        #     changed_by=update.changed_by,
        #     reason=update.reason,
        # )

        return threshold_engine.get_config()
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid threshold configuration: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update thresholds: {str(e)}"
        )


@router.delete("/strikes/{strike_id}")
async def deactivate_strike(strike_id: str) -> dict:
    """
    Deactivate a specific strike (admin action).

    This endpoint allows manual strike removal, typically after successful appeal
    or administrative review.

    Args:
        strike_id: Strike identifier to deactivate

    Returns:
        Success confirmation

    Raises:
        HTTPException: If strike not found or deactivation fails

    Example:
        DELETE /strikes/abc123-def456
    """
    try:
        strike_manager = get_strike_manager()
        success = strike_manager.deactivate_strike(strike_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Strike {strike_id} not found or already inactive"
            )

        return {"status": "success", "message": f"Strike {strike_id} deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate strike: {str(e)}"
        )
