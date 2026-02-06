"""Enforcement action determination and message generation."""

from __future__ import annotations

import uuid
from typing import Optional

from ..models import (
    ActionType,
    EnforcementDetails,
    EnforceRequest,
    EnforceResponse,
    RiskBand,
    Strike,
    TargetScope,
)
from .strikes import StrikeManager, get_strike_manager
from .thresholds import ThresholdEngine, get_threshold_engine


class ActionEngine:
    """
    Determines final enforcement action based on risk band and strike history.

    The action engine combines threshold-based risk classification with
    strike-based escalation to produce a final enforcement decision.

    Decision Logic:
        1. Classify risk score → risk band → base action
        2. Check user strike history
        3. If strike escalation is more severe, use escalated action
        4. Generate appropriate enforcement message and details
        5. Create moderation record for audit trail
    """

    def __init__(
        self,
        threshold_engine: Optional[ThresholdEngine] = None,
        strike_manager: Optional[StrikeManager] = None,
    ):
        """
        Initialize action engine with dependencies.

        Args:
            threshold_engine: Threshold classifier (uses global if not provided)
            strike_manager: Strike manager (uses global if not provided)
        """
        self.threshold_engine = threshold_engine or get_threshold_engine()
        self.strike_manager = strike_manager or get_strike_manager()

    def enforce(self, request: EnforceRequest) -> EnforceResponse:
        """
        Evaluate detection and determine enforcement action.

        Args:
            request: Enforcement request with risk score and context

        Returns:
            Enforcement response with action, details, and strike info
        """
        # Step 1: Classify risk and get base action
        risk_band = self.threshold_engine.classify_risk(request.risk_score)
        base_action = self.threshold_engine.get_base_action(risk_band)

        # Step 2: Get active strikes for user
        active_strikes = self.strike_manager.get_active_strikes(request.user_id)
        strike_count = len(active_strikes)

        # Step 3: Determine if we need to add a strike
        # Strikes are added for HIGH and CRITICAL risk detections
        should_add_strike = risk_band in [RiskBand.HIGH, RiskBand.CRITICAL]

        strike_id: Optional[str] = None
        case_id: Optional[str] = None

        if should_add_strike:
            # Generate case ID for tracking
            case_id = f"case_{uuid.uuid4().hex[:12]}"

            # Add strike and get updated count
            new_strike = self.strike_manager.add_strike(
                user_id=request.user_id,
                detection_id=request.detection_id,
                case_id=case_id,
            )
            strike_id = new_strike.id
            strike_count = new_strike.strike_number

        # Step 4: Compute escalated action if there are strikes
        final_action = base_action
        if strike_count > 0:
            escalated_action = self.strike_manager.compute_escalation(strike_count)
            # Use escalated action if it's more severe than base action
            final_action = self._select_more_severe_action(base_action, escalated_action)

        # Step 5: Generate enforcement details
        enforcement_details = self._generate_enforcement_details(
            action=final_action,
            risk_band=risk_band,
            strike_count=strike_count,
            labels=request.labels,
        )

        return EnforceResponse(
            action=final_action,
            risk_band=risk_band,
            strike_count=strike_count,
            strike_id=strike_id,
            case_id=case_id,
            enforcement_details=enforcement_details,
        )

    def _select_more_severe_action(
        self, base_action: ActionType, escalated_action: ActionType
    ) -> ActionType:
        """
        Select the more severe of two actions.

        Severity order (least to most severe):
            ALLOW < NUDGE < WARNING < SOFT_BLOCK < COOLDOWN < HARD_BLOCK < RESTRICTION < SUSPENSION_CANDIDATE

        Args:
            base_action: Base action from risk band
            escalated_action: Escalated action from strike history

        Returns:
            More severe action
        """
        severity_order = [
            ActionType.ALLOW,
            ActionType.NUDGE,
            ActionType.WARNING,
            ActionType.SOFT_BLOCK,
            ActionType.COOLDOWN,
            ActionType.HARD_BLOCK,
            ActionType.RESTRICTION,
            ActionType.SUSPENSION_CANDIDATE,
        ]

        base_severity = severity_order.index(base_action)
        escalated_severity = severity_order.index(escalated_action)

        return escalated_action if escalated_severity > base_severity else base_action

    def _generate_enforcement_details(
        self,
        action: ActionType,
        risk_band: RiskBand,
        strike_count: int,
        labels: list[str],
    ) -> EnforcementDetails:
        """
        Generate enforcement details with message and scope.

        Args:
            action: Final enforcement action
            risk_band: Risk band classification
            strike_count: Number of active strikes
            labels: Detection labels for context

        Returns:
            Enforcement details with message and scope
        """
        message = self._generate_message(action, risk_band, strike_count, labels)
        duration_hours = self._get_action_duration(action)
        scope = self._get_action_scope(action)

        return EnforcementDetails(
            duration_hours=duration_hours,
            message=message,
            scope=scope,
        )

    def _generate_message(
        self,
        action: ActionType,
        risk_band: RiskBand,
        strike_count: int,
        labels: list[str],
    ) -> str:
        """
        Generate user-facing enforcement message.

        Messages are calibrated to be clear, actionable, and non-hostile.
        They explain what happened and what the user should do.

        Args:
            action: Enforcement action
            risk_band: Risk band
            strike_count: Number of strikes
            labels: Detection labels

        Returns:
            User-facing message
        """
        label_str = ", ".join(labels[:3]) if labels else "policy violation"

        messages = {
            ActionType.ALLOW: "Your message has been delivered.",
            ActionType.NUDGE: (
                f"We detected potential {label_str} in your message. "
                "Please review our community guidelines before sending."
            ),
            ActionType.WARNING: (
                f"Your message was flagged for {label_str}. "
                "This is your first warning. Repeated violations may result in restrictions. "
                "Please familiarize yourself with our community standards."
            ),
            ActionType.SOFT_BLOCK: (
                f"Your message could not be delivered due to {label_str}. "
                "Please revise your message to comply with our guidelines."
            ),
            ActionType.COOLDOWN: (
                f"Your messaging has been temporarily restricted for 24 hours due to repeated {label_str}. "
                f"This is strike {strike_count} on your account. "
                "Use this time to review our community guidelines."
            ),
            ActionType.HARD_BLOCK: (
                f"Your message has been blocked due to severe {label_str}. "
                "This action has been logged and may result in further restrictions."
            ),
            ActionType.RESTRICTION: (
                f"Your account has been placed under elevated monitoring for 72 hours due to repeated violations. "
                f"This is strike {strike_count}. "
                "Future violations may result in account suspension."
            ),
            ActionType.SUSPENSION_CANDIDATE: (
                f"Your account has been flagged for review by our moderation team due to {strike_count} policy violations. "
                "Your messaging capabilities are restricted pending review. "
                "You will be notified of the outcome within 48 hours."
            ),
        }

        return messages.get(action, "Action required by moderation team.")

    def _get_action_duration(self, action: ActionType) -> Optional[int]:
        """
        Get duration in hours for temporary actions.

        Args:
            action: Enforcement action

        Returns:
            Duration in hours, or None for permanent/instant actions
        """
        durations = {
            ActionType.COOLDOWN: 24,
            ActionType.RESTRICTION: 72,
            # SUSPENSION_CANDIDATE has no automatic duration - requires human review
        }
        return durations.get(action)

    def _get_action_scope(self, action: ActionType) -> TargetScope:
        """
        Get scope of enforcement action.

        Args:
            action: Enforcement action

        Returns:
            Target scope (message, thread, or account)
        """
        scopes = {
            ActionType.ALLOW: TargetScope.MESSAGE,
            ActionType.NUDGE: TargetScope.MESSAGE,
            ActionType.WARNING: TargetScope.MESSAGE,
            ActionType.SOFT_BLOCK: TargetScope.MESSAGE,
            ActionType.COOLDOWN: TargetScope.ACCOUNT,
            ActionType.HARD_BLOCK: TargetScope.MESSAGE,
            ActionType.RESTRICTION: TargetScope.ACCOUNT,
            ActionType.SUSPENSION_CANDIDATE: TargetScope.ACCOUNT,
        }
        return scopes.get(action, TargetScope.MESSAGE)


# Global instance
_default_engine = ActionEngine()


def get_action_engine() -> ActionEngine:
    """
    Get the global action engine instance.

    Returns:
        Global action engine
    """
    return _default_engine
