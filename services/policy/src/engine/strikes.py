"""Rolling window strike management and escalation logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from ..config import settings
from ..models import ActionType, Strike


class StrikeManager:
    """
    Manages user strikes with a rolling time window.

    Strikes track repeated policy violations and escalate enforcement actions.
    Each strike has a 30-day rolling window (configurable). After the window
    expires, the strike becomes inactive and doesn't count toward escalation.

    Escalation Policy:
        - Strike 1: WARNING (education, no restriction)
        - Strike 2: COOLDOWN (24h message restriction)
        - Strike 3: RESTRICTION (72h elevated monitoring)
        - Strike 4+: SUSPENSION_CANDIDATE (requires human review)
    """

    def __init__(self, window_days: Optional[int] = None):
        """
        Initialize strike manager.

        Args:
            window_days: Number of days a strike remains active (default: 30)
        """
        self.window_days = window_days or settings.STRIKE_WINDOW_DAYS
        # In-memory storage: user_id -> list of strikes
        # In production, this would be backed by database/Redis
        self._strikes: dict[str, list[Strike]] = {}

    def get_active_strikes(self, user_id: str, now: Optional[datetime] = None) -> list[Strike]:
        """
        Get all active (non-expired) strikes for a user.

        Args:
            user_id: User identifier
            now: Current timestamp (defaults to datetime.utcnow())

        Returns:
            List of active strikes, ordered by window_start (oldest first)
        """
        if now is None:
            now = datetime.utcnow()

        user_strikes = self._strikes.get(user_id, [])

        # Filter to active strikes within the rolling window
        active = [
            strike for strike in user_strikes
            if strike.is_active and strike.window_end > now
        ]

        # Sort by window_start (chronological order)
        return sorted(active, key=lambda s: s.window_start)

    def get_all_strikes(self, user_id: str, active_only: bool = False) -> list[Strike]:
        """
        Get strikes for a user, optionally filtered to active only.

        Args:
            user_id: User identifier
            active_only: If True, only return active strikes

        Returns:
            List of strikes
        """
        if active_only:
            return self.get_active_strikes(user_id)

        user_strikes = self._strikes.get(user_id, [])
        return sorted(user_strikes, key=lambda s: s.window_start)

    def add_strike(
        self,
        user_id: str,
        detection_id: str,
        case_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Strike:
        """
        Add a new strike for a user.

        Args:
            user_id: User identifier
            detection_id: Detection that triggered the strike
            case_id: Optional case identifier for tracking
            now: Current timestamp (defaults to datetime.utcnow())

        Returns:
            The newly created strike
        """
        if now is None:
            now = datetime.utcnow()

        # Get current active strikes to determine strike number
        active_strikes = self.get_active_strikes(user_id, now)
        strike_number = len(active_strikes) + 1

        # Determine action based on escalation policy
        action = self.compute_escalation(strike_number)

        # Create strike with rolling window
        window_end = now + timedelta(days=self.window_days)
        strike = Strike(
            id=str(uuid.uuid4()),
            user_id=user_id,
            strike_number=strike_number,
            action_taken=action.value,
            is_active=True,
            window_start=now,
            window_end=window_end,
            case_id=case_id,
            detection_id=detection_id,
        )

        # Store strike
        if user_id not in self._strikes:
            self._strikes[user_id] = []
        self._strikes[user_id].append(strike)

        return strike

    def compute_escalation(self, strike_count: int) -> ActionType:
        """
        Compute escalated action based on strike count.

        Escalation Policy:
            - 1 strike: WARNING (educate user)
            - 2 strikes: COOLDOWN (24h timeout)
            - 3 strikes: RESTRICTION (72h elevated monitoring)
            - 4+ strikes: SUSPENSION_CANDIDATE (human review required)

        Args:
            strike_count: Number of active strikes (including new one)

        Returns:
            Escalated enforcement action

        Raises:
            ValueError: If strike_count is less than 1
        """
        if strike_count < 1:
            raise ValueError(f"Strike count must be >= 1, got {strike_count}")

        if strike_count == 1:
            return ActionType.WARNING
        elif strike_count == 2:
            return ActionType.COOLDOWN
        elif strike_count == 3:
            return ActionType.RESTRICTION
        else:  # strike_count >= 4
            return ActionType.SUSPENSION_CANDIDATE

    def expire_strikes(self, user_id: str, now: Optional[datetime] = None) -> int:
        """
        Mark expired strikes as inactive.

        Args:
            user_id: User identifier
            now: Current timestamp (defaults to datetime.utcnow())

        Returns:
            Number of strikes expired
        """
        if now is None:
            now = datetime.utcnow()

        user_strikes = self._strikes.get(user_id, [])
        expired_count = 0

        for strike in user_strikes:
            if strike.is_active and strike.window_end <= now:
                strike.is_active = False
                expired_count += 1

        return expired_count

    def deactivate_strike(self, strike_id: str) -> bool:
        """
        Manually deactivate a specific strike (e.g., after appeal).

        Args:
            strike_id: Strike identifier

        Returns:
            True if strike was found and deactivated, False otherwise
        """
        for user_strikes in self._strikes.values():
            for strike in user_strikes:
                if strike.id == strike_id and strike.is_active:
                    strike.is_active = False
                    return True
        return False

    def clear_user_strikes(self, user_id: str) -> int:
        """
        Clear all strikes for a user (admin action).

        Args:
            user_id: User identifier

        Returns:
            Number of strikes cleared
        """
        if user_id not in self._strikes:
            return 0

        count = len(self._strikes[user_id])
        del self._strikes[user_id]
        return count


# Global instance for in-memory strike tracking
# In production, this would be backed by persistent storage
_default_manager = StrikeManager()


def get_strike_manager() -> StrikeManager:
    """
    Get the global strike manager instance.

    Returns:
        Global strike manager
    """
    return _default_manager
