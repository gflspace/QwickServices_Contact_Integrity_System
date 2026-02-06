"""Threshold-based risk band classification and action mapping."""

from __future__ import annotations

from typing import Optional

from ..models import ActionType, RiskBand, ThresholdConfig


class ThresholdEngine:
    """
    Maps risk scores to risk bands and determines enforcement actions.

    Risk Bands:
        - LOW: 0.00 - 0.39 → allow
        - MEDIUM: 0.40 - 0.64 → nudge
        - HIGH: 0.65 - 0.84 → soft_block
        - CRITICAL: 0.85 - 1.00 → hard_block

    Thresholds are configurable at runtime to support A/B testing and tuning.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        """
        Initialize threshold engine with configurable thresholds.

        Args:
            config: Threshold configuration. Uses defaults if not provided.
        """
        self.config = config or ThresholdConfig()
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate that thresholds form a coherent, non-overlapping spectrum.

        Raises:
            ValueError: If thresholds are invalid or overlapping.
        """
        # Validate boundaries are in ascending order
        if not (0.0 <= self.config.allow_max < self.config.nudge_min):
            raise ValueError(
                f"Invalid threshold: allow_max ({self.config.allow_max}) must be "
                f"less than nudge_min ({self.config.nudge_min})"
            )

        if not (self.config.nudge_min <= self.config.nudge_max < self.config.soft_block_min):
            raise ValueError(
                f"Invalid threshold: nudge_max ({self.config.nudge_max}) must be "
                f"less than soft_block_min ({self.config.soft_block_min})"
            )

        if not (self.config.soft_block_min <= self.config.soft_block_max < self.config.hard_block_min):
            raise ValueError(
                f"Invalid threshold: soft_block_max ({self.config.soft_block_max}) must be "
                f"less than hard_block_min ({self.config.hard_block_min})"
            )

        if not (self.config.hard_block_min <= 1.0):
            raise ValueError(
                f"Invalid threshold: hard_block_min ({self.config.hard_block_min}) "
                f"must be <= 1.0"
            )

    def classify_risk(self, risk_score: float) -> RiskBand:
        """
        Classify a risk score into a risk band.

        Args:
            risk_score: Risk score from detection service (0.0 - 1.0)

        Returns:
            Risk band classification

        Raises:
            ValueError: If risk_score is out of valid range [0.0, 1.0]
        """
        if not 0.0 <= risk_score <= 1.0:
            raise ValueError(f"Risk score must be in [0.0, 1.0], got {risk_score}")

        if risk_score <= self.config.allow_max:
            return RiskBand.LOW
        elif risk_score <= self.config.nudge_max:
            return RiskBand.MEDIUM
        elif risk_score <= self.config.soft_block_max:
            return RiskBand.HIGH
        else:  # risk_score >= self.config.hard_block_min
            return RiskBand.CRITICAL

    def get_base_action(self, risk_band: RiskBand) -> ActionType:
        """
        Map a risk band to its base enforcement action.

        This is the action applied before considering strike history.
        Strike escalation may override this base action.

        Args:
            risk_band: Classified risk band

        Returns:
            Base enforcement action for the band
        """
        action_map = {
            RiskBand.LOW: ActionType.ALLOW,
            RiskBand.MEDIUM: ActionType.NUDGE,
            RiskBand.HIGH: ActionType.SOFT_BLOCK,
            RiskBand.CRITICAL: ActionType.HARD_BLOCK,
        }
        return action_map[risk_band]

    def update_config(self, new_config: ThresholdConfig) -> None:
        """
        Update threshold configuration at runtime.

        Args:
            new_config: New threshold configuration

        Raises:
            ValueError: If new configuration is invalid
        """
        # Validate before updating
        old_config = self.config
        self.config = new_config
        try:
            self._validate_config()
        except ValueError:
            # Rollback on validation failure
            self.config = old_config
            raise

    def get_config(self) -> ThresholdConfig:
        """
        Get current threshold configuration.

        Returns:
            Current threshold configuration
        """
        return self.config


# Global instance with default configuration
# In production, this would be initialized from database
_default_engine = ThresholdEngine()


def get_threshold_engine() -> ThresholdEngine:
    """
    Get the global threshold engine instance.

    Returns:
        Global threshold engine
    """
    return _default_engine
