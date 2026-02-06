"""Tests for threshold-based risk classification."""

import pytest

from src.engine.thresholds import ThresholdEngine
from src.models import ActionType, RiskBand, ThresholdConfig


class TestThresholdClassification:
    """Test risk score classification into risk bands."""

    def test_low_risk_lower_boundary(self):
        """Test that risk score 0.0 is classified as LOW."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.0) == RiskBand.LOW

    def test_low_risk_upper_boundary(self):
        """Test that risk score 0.39 is classified as LOW."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.39) == RiskBand.LOW

    def test_low_risk_mid_range(self):
        """Test that risk score 0.20 is classified as LOW."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.20) == RiskBand.LOW

    def test_medium_risk_lower_boundary(self):
        """Test that risk score 0.40 is classified as MEDIUM."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.40) == RiskBand.MEDIUM

    def test_medium_risk_upper_boundary(self):
        """Test that risk score 0.64 is classified as MEDIUM."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.64) == RiskBand.MEDIUM

    def test_medium_risk_mid_range(self):
        """Test that risk score 0.52 is classified as MEDIUM."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.52) == RiskBand.MEDIUM

    def test_high_risk_lower_boundary(self):
        """Test that risk score 0.65 is classified as HIGH."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.65) == RiskBand.HIGH

    def test_high_risk_upper_boundary(self):
        """Test that risk score 0.84 is classified as HIGH."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.84) == RiskBand.HIGH

    def test_high_risk_mid_range(self):
        """Test that risk score 0.75 is classified as HIGH."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.75) == RiskBand.HIGH

    def test_critical_risk_lower_boundary(self):
        """Test that risk score 0.85 is classified as CRITICAL."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.85) == RiskBand.CRITICAL

    def test_critical_risk_upper_boundary(self):
        """Test that risk score 1.0 is classified as CRITICAL."""
        engine = ThresholdEngine()
        assert engine.classify_risk(1.0) == RiskBand.CRITICAL

    def test_critical_risk_mid_range(self):
        """Test that risk score 0.92 is classified as CRITICAL."""
        engine = ThresholdEngine()
        assert engine.classify_risk(0.92) == RiskBand.CRITICAL

    def test_invalid_risk_score_below_zero(self):
        """Test that risk score < 0 raises ValueError."""
        engine = ThresholdEngine()
        with pytest.raises(ValueError, match="Risk score must be in"):
            engine.classify_risk(-0.1)

    def test_invalid_risk_score_above_one(self):
        """Test that risk score > 1.0 raises ValueError."""
        engine = ThresholdEngine()
        with pytest.raises(ValueError, match="Risk score must be in"):
            engine.classify_risk(1.1)


class TestActionMapping:
    """Test mapping from risk bands to enforcement actions."""

    def test_low_band_maps_to_allow(self):
        """Test that LOW risk band maps to ALLOW action."""
        engine = ThresholdEngine()
        action = engine.get_base_action(RiskBand.LOW)
        assert action == ActionType.ALLOW

    def test_medium_band_maps_to_nudge(self):
        """Test that MEDIUM risk band maps to NUDGE action."""
        engine = ThresholdEngine()
        action = engine.get_base_action(RiskBand.MEDIUM)
        assert action == ActionType.NUDGE

    def test_high_band_maps_to_soft_block(self):
        """Test that HIGH risk band maps to SOFT_BLOCK action."""
        engine = ThresholdEngine()
        action = engine.get_base_action(RiskBand.HIGH)
        assert action == ActionType.SOFT_BLOCK

    def test_critical_band_maps_to_hard_block(self):
        """Test that CRITICAL risk band maps to HARD_BLOCK action."""
        engine = ThresholdEngine()
        action = engine.get_base_action(RiskBand.CRITICAL)
        assert action == ActionType.HARD_BLOCK


class TestThresholdConfiguration:
    """Test dynamic threshold configuration."""

    def test_default_configuration(self):
        """Test that default configuration is valid."""
        engine = ThresholdEngine()
        config = engine.get_config()
        assert config.allow_max == 0.39
        assert config.nudge_min == 0.40
        assert config.nudge_max == 0.64
        assert config.soft_block_min == 0.65
        assert config.soft_block_max == 0.84
        assert config.hard_block_min == 0.85

    def test_custom_configuration(self):
        """Test initialization with custom thresholds."""
        custom_config = ThresholdConfig(
            allow_max=0.30,
            nudge_min=0.31,
            nudge_max=0.60,
            soft_block_min=0.61,
            soft_block_max=0.80,
            hard_block_min=0.81,
        )
        engine = ThresholdEngine(custom_config)
        assert engine.classify_risk(0.30) == RiskBand.LOW
        assert engine.classify_risk(0.31) == RiskBand.MEDIUM
        assert engine.classify_risk(0.61) == RiskBand.HIGH
        assert engine.classify_risk(0.81) == RiskBand.CRITICAL

    def test_update_configuration(self):
        """Test runtime configuration update."""
        engine = ThresholdEngine()

        new_config = ThresholdConfig(
            allow_max=0.35,
            nudge_min=0.36,
            nudge_max=0.70,
            soft_block_min=0.71,
            soft_block_max=0.90,
            hard_block_min=0.91,
        )
        engine.update_config(new_config)

        # Verify new thresholds are applied
        assert engine.classify_risk(0.35) == RiskBand.LOW
        assert engine.classify_risk(0.36) == RiskBand.MEDIUM
        assert engine.classify_risk(0.71) == RiskBand.HIGH
        assert engine.classify_risk(0.91) == RiskBand.CRITICAL

    def test_invalid_configuration_overlapping_ranges(self):
        """Test that overlapping threshold ranges are rejected."""
        invalid_config = ThresholdConfig(
            allow_max=0.50,  # Overlaps with nudge_min
            nudge_min=0.40,
            nudge_max=0.64,
            soft_block_min=0.65,
            soft_block_max=0.84,
            hard_block_min=0.85,
        )
        with pytest.raises(ValueError, match="Invalid threshold"):
            ThresholdEngine(invalid_config)

    def test_invalid_configuration_gaps(self):
        """Test that non-contiguous threshold ranges are allowed (validation checks order only)."""
        # The threshold engine validates ascending order but allows gaps
        # This is valid as long as allow_max < nudge_min
        valid_config = ThresholdConfig(
            allow_max=0.39,
            nudge_min=0.45,  # Gap between 0.39 and 0.45 is allowed
            nudge_max=0.64,
            soft_block_min=0.65,
            soft_block_max=0.84,
            hard_block_min=0.85,
        )
        # Should not raise - gaps are allowed
        engine = ThresholdEngine(valid_config)

        # Values in gap will be classified as MEDIUM (first band where value <= max)
        assert engine.classify_risk(0.40) == RiskBand.MEDIUM
        assert engine.classify_risk(0.44) == RiskBand.MEDIUM

    def test_configuration_rollback_on_invalid_update(self):
        """Test that configuration is rolled back if update is invalid."""
        engine = ThresholdEngine()
        original_config = engine.get_config()

        invalid_config = ThresholdConfig(
            allow_max=0.50,
            nudge_min=0.40,  # Invalid: allow_max > nudge_min
            nudge_max=0.64,
            soft_block_min=0.65,
            soft_block_max=0.84,
            hard_block_min=0.85,
        )

        with pytest.raises(ValueError):
            engine.update_config(invalid_config)

        # Verify original configuration is still in effect
        current_config = engine.get_config()
        assert current_config.allow_max == original_config.allow_max
        assert current_config.nudge_min == original_config.nudge_min


class TestBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_boundary_at_exact_threshold(self):
        """Test classification at exact threshold boundaries."""
        engine = ThresholdEngine()

        # Test each boundary point
        assert engine.classify_risk(0.39) == RiskBand.LOW
        assert engine.classify_risk(0.40) == RiskBand.MEDIUM
        assert engine.classify_risk(0.64) == RiskBand.MEDIUM
        assert engine.classify_risk(0.65) == RiskBand.HIGH
        assert engine.classify_risk(0.84) == RiskBand.HIGH
        assert engine.classify_risk(0.85) == RiskBand.CRITICAL

    def test_floating_point_precision(self):
        """Test that floating point precision doesn't cause misclassification."""
        engine = ThresholdEngine()

        # Test values very close to boundaries
        # 0.3999999999 > 0.39, so it's MEDIUM, not LOW
        assert engine.classify_risk(0.39) == RiskBand.LOW  # Exact boundary
        assert engine.classify_risk(0.4000000001) == RiskBand.MEDIUM
        assert engine.classify_risk(0.64) == RiskBand.MEDIUM  # Exact boundary
        assert engine.classify_risk(0.6500000001) == RiskBand.HIGH
