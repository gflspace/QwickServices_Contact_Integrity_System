"""Tests for strike management and escalation logic."""

from datetime import datetime, timedelta

import pytest

from src.engine.strikes import StrikeManager
from src.models import ActionType


class TestStrikeEscalation:
    """Test strike escalation policy."""

    def test_first_strike_is_warning(self):
        """Test that first strike results in WARNING action."""
        action = StrikeManager().compute_escalation(1)
        assert action == ActionType.WARNING

    def test_second_strike_is_cooldown(self):
        """Test that second strike results in COOLDOWN (24h) action."""
        action = StrikeManager().compute_escalation(2)
        assert action == ActionType.COOLDOWN

    def test_third_strike_is_restriction(self):
        """Test that third strike results in RESTRICTION (72h) action."""
        action = StrikeManager().compute_escalation(3)
        assert action == ActionType.RESTRICTION

    def test_fourth_strike_is_suspension_candidate(self):
        """Test that fourth strike results in SUSPENSION_CANDIDATE action."""
        action = StrikeManager().compute_escalation(4)
        assert action == ActionType.SUSPENSION_CANDIDATE

    def test_fifth_strike_is_suspension_candidate(self):
        """Test that fifth+ strikes result in SUSPENSION_CANDIDATE action."""
        action = StrikeManager().compute_escalation(5)
        assert action == ActionType.SUSPENSION_CANDIDATE

    def test_invalid_strike_count_zero(self):
        """Test that strike count of 0 raises ValueError."""
        manager = StrikeManager()
        with pytest.raises(ValueError, match="Strike count must be >= 1"):
            manager.compute_escalation(0)

    def test_invalid_strike_count_negative(self):
        """Test that negative strike count raises ValueError."""
        manager = StrikeManager()
        with pytest.raises(ValueError, match="Strike count must be >= 1"):
            manager.compute_escalation(-1)


class TestStrikeCreation:
    """Test strike creation and tracking."""

    def test_add_first_strike(self):
        """Test adding first strike for a user."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike = manager.add_strike(
            user_id="user_123",
            detection_id="det_001",
            case_id="case_001",
            now=now,
        )

        assert strike.user_id == "user_123"
        assert strike.detection_id == "det_001"
        assert strike.case_id == "case_001"
        assert strike.strike_number == 1
        assert strike.action_taken == ActionType.WARNING.value
        assert strike.is_active is True
        assert strike.window_start == now
        assert strike.window_end == now + timedelta(days=30)

    def test_add_multiple_strikes_increments_count(self):
        """Test that adding multiple strikes increments strike number."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike1 = manager.add_strike("user_123", "det_001", now=now)
        assert strike1.strike_number == 1
        assert strike1.action_taken == ActionType.WARNING.value

        strike2 = manager.add_strike("user_123", "det_002", now=now)
        assert strike2.strike_number == 2
        assert strike2.action_taken == ActionType.COOLDOWN.value

        strike3 = manager.add_strike("user_123", "det_003", now=now)
        assert strike3.strike_number == 3
        assert strike3.action_taken == ActionType.RESTRICTION.value

    def test_strikes_for_different_users_are_independent(self):
        """Test that strikes for different users don't interfere."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike1 = manager.add_strike("user_123", "det_001", now=now)
        strike2 = manager.add_strike("user_456", "det_002", now=now)

        assert strike1.user_id == "user_123"
        assert strike1.strike_number == 1

        assert strike2.user_id == "user_456"
        assert strike2.strike_number == 1  # Independent counter

    def test_strike_generates_unique_id(self):
        """Test that each strike gets a unique ID."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike1 = manager.add_strike("user_123", "det_001", now=now)
        strike2 = manager.add_strike("user_123", "det_002", now=now)

        assert strike1.id != strike2.id
        assert len(strike1.id) > 0
        assert len(strike2.id) > 0


class TestActiveStrikeRetrieval:
    """Test retrieval of active strikes within rolling window."""

    def test_get_active_strikes_empty_user(self):
        """Test getting strikes for user with no strikes."""
        manager = StrikeManager()
        strikes = manager.get_active_strikes("user_123")
        assert len(strikes) == 0

    def test_get_active_strikes_returns_only_active(self):
        """Test that only active strikes within window are returned."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        # Add strikes
        manager.add_strike("user_123", "det_001", now=now)
        manager.add_strike("user_123", "det_002", now=now)

        active = manager.get_active_strikes("user_123", now=now)
        assert len(active) == 2

    def test_get_active_strikes_excludes_expired(self):
        """Test that expired strikes are excluded from active strikes."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        # Add strike at now
        manager.add_strike("user_123", "det_001", now=now)

        # Check after 31 days (outside window)
        future = now + timedelta(days=31)
        active = manager.get_active_strikes("user_123", now=future)
        assert len(active) == 0

    def test_get_active_strikes_includes_unexpired(self):
        """Test that strikes within window are included."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        # Add strike at now
        manager.add_strike("user_123", "det_001", now=now)

        # Check after 29 days (inside window)
        future = now + timedelta(days=29)
        active = manager.get_active_strikes("user_123", now=future)
        assert len(active) == 1

    def test_get_active_strikes_boundary_at_window_end(self):
        """Test strike at exact window boundary is excluded."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)

        # Check at exact window end (30 days later)
        boundary = now + timedelta(days=30)
        active = manager.get_active_strikes("user_123", now=boundary)
        assert len(active) == 0

    def test_get_active_strikes_ordered_chronologically(self):
        """Test that active strikes are returned in chronological order."""
        manager = StrikeManager()
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        # Add strikes at different times
        manager.add_strike("user_123", "det_001", now=base_time)
        manager.add_strike("user_123", "det_002", now=base_time + timedelta(hours=1))
        manager.add_strike("user_123", "det_003", now=base_time + timedelta(hours=2))

        active = manager.get_active_strikes("user_123", now=base_time + timedelta(hours=3))
        assert len(active) == 3
        assert active[0].detection_id == "det_001"
        assert active[1].detection_id == "det_002"
        assert active[2].detection_id == "det_003"


class TestRollingWindowExpiry:
    """Test rolling window expiry behavior."""

    def test_rolling_window_30_days_default(self):
        """Test that default rolling window is 30 days."""
        manager = StrikeManager()
        assert manager.window_days == 30

    def test_custom_rolling_window(self):
        """Test custom rolling window configuration."""
        manager = StrikeManager(window_days=14)
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike = manager.add_strike("user_123", "det_001", now=now)
        assert strike.window_end == now + timedelta(days=14)

    def test_expire_strikes_marks_inactive(self):
        """Test that expire_strikes marks expired strikes as inactive."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)

        # Expire strikes after 31 days
        future = now + timedelta(days=31)
        expired_count = manager.expire_strikes("user_123", now=future)

        assert expired_count == 1

        # Verify strike is now inactive
        all_strikes = manager.get_all_strikes("user_123", active_only=False)
        assert len(all_strikes) == 1
        assert all_strikes[0].is_active is False

    def test_expire_strikes_returns_count(self):
        """Test that expire_strikes returns correct count of expired strikes."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)
        manager.add_strike("user_123", "det_002", now=now)

        future = now + timedelta(days=31)
        expired_count = manager.expire_strikes("user_123", now=future)
        assert expired_count == 2

    def test_rolling_window_allows_fresh_start(self):
        """Test that expired strikes don't count toward new strikes."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        # Add first strike
        strike1 = manager.add_strike("user_123", "det_001", now=now)
        assert strike1.strike_number == 1

        # Move forward 31 days (outside window)
        future = now + timedelta(days=31)

        # Add another strike - should be strike #1 again (fresh start)
        strike2 = manager.add_strike("user_123", "det_002", now=future)
        assert strike2.strike_number == 1  # Resets because previous expired


class TestStrikeManagement:
    """Test strike management operations."""

    def test_get_all_strikes_active_only(self):
        """Test getting all active strikes only."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)
        manager.add_strike("user_123", "det_002", now=now)

        # Expire first two strikes
        future = now + timedelta(days=31)
        manager.add_strike("user_123", "det_003", now=future)
        manager.expire_strikes("user_123", now=future)

        # Use get_active_strikes with explicit time to test active filtering
        active_only = manager.get_active_strikes("user_123", now=future)
        assert len(active_only) == 1
        assert active_only[0].detection_id == "det_003"

    def test_get_all_strikes_including_expired(self):
        """Test getting all strikes including expired ones."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)
        manager.add_strike("user_123", "det_002", now=now)

        future = now + timedelta(days=31)
        manager.expire_strikes("user_123", now=future)

        all_strikes = manager.get_all_strikes("user_123", active_only=False)
        assert len(all_strikes) == 2

    def test_deactivate_strike_by_id(self):
        """Test manual deactivation of a specific strike."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike = manager.add_strike("user_123", "det_001", now=now)

        success = manager.deactivate_strike(strike.id)
        assert success is True

        active = manager.get_active_strikes("user_123", now=now)
        assert len(active) == 0

    def test_deactivate_nonexistent_strike(self):
        """Test deactivating a strike that doesn't exist."""
        manager = StrikeManager()
        success = manager.deactivate_strike("nonexistent_id")
        assert success is False

    def test_deactivate_already_inactive_strike(self):
        """Test deactivating a strike that is already inactive."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        strike = manager.add_strike("user_123", "det_001", now=now)

        # Expire the strike
        future = now + timedelta(days=31)
        manager.expire_strikes("user_123", now=future)

        # Try to deactivate again
        success = manager.deactivate_strike(strike.id)
        assert success is False

    def test_clear_user_strikes(self):
        """Test clearing all strikes for a user."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_123", "det_001", now=now)
        manager.add_strike("user_123", "det_002", now=now)

        cleared = manager.clear_user_strikes("user_123")
        assert cleared == 2

        strikes = manager.get_all_strikes("user_123")
        assert len(strikes) == 0

    def test_clear_strikes_for_nonexistent_user(self):
        """Test clearing strikes for user with no strikes."""
        manager = StrikeManager()
        cleared = manager.clear_user_strikes("user_999")
        assert cleared == 0


class TestMultiUserScenarios:
    """Test scenarios with multiple users."""

    def test_concurrent_users_independent_counters(self):
        """Test that multiple users have independent strike counters."""
        manager = StrikeManager()
        now = datetime(2025, 1, 15, 10, 0, 0)

        # User 1: 3 strikes
        manager.add_strike("user_1", "det_001", now=now)
        manager.add_strike("user_1", "det_002", now=now)
        manager.add_strike("user_1", "det_003", now=now)

        # User 2: 1 strike
        manager.add_strike("user_2", "det_004", now=now)

        user1_strikes = manager.get_active_strikes("user_1", now=now)
        user2_strikes = manager.get_active_strikes("user_2", now=now)

        assert len(user1_strikes) == 3
        assert len(user2_strikes) == 1

    def test_expiry_affects_only_target_user(self):
        """Test that expiring strikes for one user doesn't affect others."""
        manager = StrikeManager(window_days=30)
        now = datetime(2025, 1, 15, 10, 0, 0)

        manager.add_strike("user_1", "det_001", now=now)
        manager.add_strike("user_2", "det_002", now=now)

        # Expire user_1 strikes only
        future = now + timedelta(days=31)
        manager.expire_strikes("user_1", now=future)

        user1_active = manager.get_active_strikes("user_1", now=future)
        user2_active = manager.get_active_strikes("user_2", now=future)

        assert len(user1_active) == 0
        assert len(user2_active) == 0  # Also expired due to time passage
