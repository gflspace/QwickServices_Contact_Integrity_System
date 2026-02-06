"""Simple test runner to validate the Policy & Enforcement Engine."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine.thresholds import ThresholdEngine
from engine.strikes import StrikeManager
from engine.actions import ActionEngine
from models import EnforceRequest, RiskBand, ActionType


def test_threshold_classification():
    """Test basic threshold classification."""
    print("Testing threshold classification...")
    engine = ThresholdEngine()

    # Test boundaries
    assert engine.classify_risk(0.20) == RiskBand.LOW, "0.20 should be LOW"
    assert engine.classify_risk(0.39) == RiskBand.LOW, "0.39 should be LOW"
    assert engine.classify_risk(0.40) == RiskBand.MEDIUM, "0.40 should be MEDIUM"
    assert engine.classify_risk(0.64) == RiskBand.MEDIUM, "0.64 should be MEDIUM"
    assert engine.classify_risk(0.65) == RiskBand.HIGH, "0.65 should be HIGH"
    assert engine.classify_risk(0.84) == RiskBand.HIGH, "0.84 should be HIGH"
    assert engine.classify_risk(0.85) == RiskBand.CRITICAL, "0.85 should be CRITICAL"
    assert engine.classify_risk(1.00) == RiskBand.CRITICAL, "1.00 should be CRITICAL"

    print("  ✓ All threshold classifications passed")


def test_action_mapping():
    """Test action mapping from risk bands."""
    print("Testing action mapping...")
    engine = ThresholdEngine()

    assert engine.get_base_action(RiskBand.LOW) == ActionType.ALLOW
    assert engine.get_base_action(RiskBand.MEDIUM) == ActionType.NUDGE
    assert engine.get_base_action(RiskBand.HIGH) == ActionType.SOFT_BLOCK
    assert engine.get_base_action(RiskBand.CRITICAL) == ActionType.HARD_BLOCK

    print("  ✓ All action mappings passed")


def test_strike_escalation():
    """Test strike escalation logic."""
    print("Testing strike escalation...")
    manager = StrikeManager()

    assert manager.compute_escalation(1) == ActionType.WARNING
    assert manager.compute_escalation(2) == ActionType.COOLDOWN
    assert manager.compute_escalation(3) == ActionType.RESTRICTION
    assert manager.compute_escalation(4) == ActionType.SUSPENSION_CANDIDATE
    assert manager.compute_escalation(5) == ActionType.SUSPENSION_CANDIDATE

    print("  ✓ All strike escalations passed")


def test_strike_management():
    """Test strike creation and tracking."""
    print("Testing strike management...")
    manager = StrikeManager()

    # Add first strike
    strike1 = manager.add_strike("user_123", "det_001", "case_001")
    assert strike1.user_id == "user_123"
    assert strike1.strike_number == 1
    assert strike1.action_taken == ActionType.WARNING.value

    # Add second strike
    strike2 = manager.add_strike("user_123", "det_002", "case_002")
    assert strike2.strike_number == 2
    assert strike2.action_taken == ActionType.COOLDOWN.value

    # Get active strikes
    active = manager.get_active_strikes("user_123")
    assert len(active) == 2

    print("  ✓ All strike management tests passed")


def test_enforcement_engine():
    """Test end-to-end enforcement."""
    print("Testing enforcement engine...")
    engine = ActionEngine()

    # Test low risk - no strike
    request1 = EnforceRequest(
        detection_id="det_001",
        user_id="user_test",
        risk_score=0.20,
        labels=["spam"],
    )
    response1 = engine.enforce(request1)
    assert response1.action == ActionType.ALLOW
    assert response1.risk_band == RiskBand.LOW
    assert response1.strike_count == 0
    assert response1.strike_id is None

    # Test high risk - adds strike
    request2 = EnforceRequest(
        detection_id="det_002",
        user_id="user_test2",
        risk_score=0.75,
        labels=["harassment"],
    )
    response2 = engine.enforce(request2)
    assert response2.action == ActionType.WARNING  # First strike
    assert response2.risk_band == RiskBand.HIGH
    assert response2.strike_count == 1
    assert response2.strike_id is not None
    assert response2.case_id is not None

    # Test second high risk violation - escalates
    request3 = EnforceRequest(
        detection_id="det_003",
        user_id="user_test2",
        risk_score=0.75,
        labels=["harassment"],
    )
    response3 = engine.enforce(request3)
    assert response3.action == ActionType.COOLDOWN  # Second strike
    assert response3.strike_count == 2

    print("  ✓ All enforcement tests passed")


def test_enforcement_messages():
    """Test that enforcement details are generated."""
    print("Testing enforcement messages...")
    engine = ActionEngine()

    request = EnforceRequest(
        detection_id="det_msg",
        user_id="user_msg",
        risk_score=0.75,
        labels=["spam"],
    )
    response = engine.enforce(request)

    assert response.enforcement_details is not None
    assert len(response.enforcement_details.message) > 0
    assert response.enforcement_details.scope is not None

    print("  ✓ Enforcement message generation passed")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Policy & Enforcement Engine - Quick Validation")
    print("=" * 60 + "\n")

    try:
        test_threshold_classification()
        test_action_mapping()
        test_strike_escalation()
        test_strike_management()
        test_enforcement_engine()
        test_enforcement_messages()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
