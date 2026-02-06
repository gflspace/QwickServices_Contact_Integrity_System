"""Tests for Policy & Enforcement API endpoints."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.engine.strikes import get_strike_manager
from src.engine.thresholds import get_threshold_engine
from src.main import app
from src.models import ActionType, RiskBand, ThresholdConfig

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    # Reset strike manager
    strike_manager = get_strike_manager()
    strike_manager._strikes.clear()

    # Reset threshold engine to defaults
    threshold_engine = get_threshold_engine()
    threshold_engine.config = ThresholdConfig()

    yield


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_200(self):
        """Test that health endpoint returns 200 status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_returns_correct_structure(self):
        """Test that health endpoint returns expected structure."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data

        assert data["status"] == "healthy"
        assert data["service"] == "policy-enforcement"
        assert data["version"] == "1.0.0"


class TestEnforceEndpoint:
    """Test enforcement decision endpoint."""

    def test_enforce_low_risk_returns_allow(self):
        """Test that low risk score results in ALLOW action."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_001",
                "user_id": "user_123",
                "risk_score": 0.20,
                "labels": ["spam"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["action"] == ActionType.ALLOW.value
        assert data["risk_band"] == RiskBand.LOW.value
        assert data["strike_count"] == 0
        assert data["strike_id"] is None
        assert data["case_id"] is None

    def test_enforce_medium_risk_returns_nudge(self):
        """Test that medium risk score results in NUDGE action."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_002",
                "user_id": "user_123",
                "risk_score": 0.50,
                "labels": ["inappropriate"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["action"] == ActionType.NUDGE.value
        assert data["risk_band"] == RiskBand.MEDIUM.value
        assert data["strike_count"] == 0

    def test_enforce_high_risk_adds_strike(self):
        """Test that high risk score adds strike and returns SOFT_BLOCK."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_003",
                "user_id": "user_456",
                "risk_score": 0.75,
                "labels": ["harassment"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["action"] == ActionType.SOFT_BLOCK.value  # Base action more severe than strike 1
        assert data["risk_band"] == RiskBand.HIGH.value
        assert data["strike_count"] == 1
        assert data["strike_id"] is not None
        assert data["case_id"] is not None

    def test_enforce_critical_risk_adds_strike(self):
        """Test that critical risk score adds strike and escalates appropriately."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_004",
                "user_id": "user_789",
                "risk_score": 0.95,
                "labels": ["hate_speech"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["action"] == ActionType.HARD_BLOCK.value  # Base action more severe than strike 1
        assert data["risk_band"] == RiskBand.CRITICAL.value
        assert data["strike_count"] == 1

    def test_enforce_multiple_strikes_escalate(self):
        """Test that multiple high risk detections escalate strikes."""
        user_id = "user_escalate"

        # First strike: SOFT_BLOCK (base action more severe than WARNING)
        response1 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_001",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )
        assert response1.json()["action"] == ActionType.SOFT_BLOCK.value
        assert response1.json()["strike_count"] == 1

        # Second strike: COOLDOWN
        response2 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_002",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )
        assert response2.json()["action"] == ActionType.COOLDOWN.value
        assert response2.json()["strike_count"] == 2

        # Third strike: RESTRICTION
        response3 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_003",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )
        assert response3.json()["action"] == ActionType.RESTRICTION.value
        assert response3.json()["strike_count"] == 3

        # Fourth strike: SUSPENSION_CANDIDATE
        response4 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_004",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )
        assert response4.json()["action"] == ActionType.SUSPENSION_CANDIDATE.value
        assert response4.json()["strike_count"] == 4

    def test_enforce_includes_enforcement_details(self):
        """Test that enforcement response includes detailed enforcement info."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_005",
                "user_id": "user_detail",
                "risk_score": 0.75,
                "labels": ["harassment", "inappropriate"],
            },
        )

        data = response.json()
        assert "enforcement_details" in data

        details = data["enforcement_details"]
        assert "message" in details
        assert "scope" in details
        assert len(details["message"]) > 0

    def test_enforce_invalid_risk_score_below_zero(self):
        """Test that risk score below 0 returns 422 validation error."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_006",
                "user_id": "user_invalid",
                "risk_score": -0.1,
                "labels": [],
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_enforce_invalid_risk_score_above_one(self):
        """Test that risk score above 1.0 returns 422 validation error."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_007",
                "user_id": "user_invalid",
                "risk_score": 1.5,
                "labels": [],
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_enforce_missing_required_fields(self):
        """Test that missing required fields returns 422 validation error."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "user_id": "user_123",
                "risk_score": 0.5,
                # Missing detection_id
            },
        )

        assert response.status_code == 422

    def test_enforce_with_optional_thread_id(self):
        """Test enforcement with optional thread_id field."""
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_008",
                "user_id": "user_thread",
                "thread_id": "thread_abc",
                "risk_score": 0.50,
                "labels": ["spam"],
            },
        )

        assert response.status_code == 200


class TestStrikesEndpoint:
    """Test strike retrieval endpoint."""

    def test_get_strikes_empty_user(self):
        """Test getting strikes for user with no strikes."""
        response = client.get("/api/v1/strikes/user_empty")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "user_empty"
        assert data["strikes"] == []
        assert data["total_active"] == 0

    def test_get_strikes_with_active_strikes(self):
        """Test getting active strikes for user."""
        user_id = "user_with_strikes"

        # Add strikes via enforce endpoint
        client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_001",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )

        client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_002",
                "user_id": user_id,
                "risk_score": 0.80,
                "labels": ["spam"],
            },
        )

        # Retrieve strikes
        response = client.get(f"/api/v1/strikes/{user_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == user_id
        assert len(data["strikes"]) == 2
        assert data["total_active"] == 2

    def test_get_strikes_active_only_true(self):
        """Test getting active strikes only."""
        response = client.get("/api/v1/strikes/user_123?active_only=true")

        assert response.status_code == 200
        # Default behavior is active_only=true

    def test_get_strikes_active_only_false(self):
        """Test getting all strikes including expired."""
        response = client.get("/api/v1/strikes/user_123?active_only=false")

        assert response.status_code == 200

    def test_get_strikes_returns_strike_details(self):
        """Test that strike response includes all strike details."""
        user_id = "user_details"

        # Add a strike
        client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_001",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )

        response = client.get(f"/api/v1/strikes/{user_id}")
        data = response.json()

        assert len(data["strikes"]) == 1
        strike = data["strikes"][0]

        assert "id" in strike
        assert "user_id" in strike
        assert "strike_number" in strike
        assert "action_taken" in strike
        assert "is_active" in strike
        assert "window_start" in strike
        assert "window_end" in strike
        assert "detection_id" in strike
        assert "case_id" in strike


class TestThresholdsEndpoint:
    """Test threshold configuration endpoints."""

    def test_get_thresholds_returns_default(self):
        """Test that GET /thresholds returns default configuration."""
        response = client.get("/api/v1/thresholds")

        assert response.status_code == 200
        data = response.json()

        assert data["allow_max"] == 0.39
        assert data["nudge_min"] == 0.40
        assert data["nudge_max"] == 0.64
        assert data["soft_block_min"] == 0.65
        assert data["soft_block_max"] == 0.84
        assert data["hard_block_min"] == 0.85

    def test_update_thresholds_valid_config(self):
        """Test updating thresholds with valid configuration."""
        response = client.put(
            "/api/v1/thresholds",
            json={
                "thresholds": {
                    "allow_max": 0.35,
                    "nudge_min": 0.36,
                    "nudge_max": 0.60,
                    "soft_block_min": 0.61,
                    "soft_block_max": 0.80,
                    "hard_block_min": 0.81,
                },
                "changed_by": "admin@example.com",
                "reason": "A/B test: stricter thresholds",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["allow_max"] == 0.35
        assert data["nudge_min"] == 0.36

    def test_update_thresholds_affects_enforcement(self):
        """Test that threshold updates affect subsequent enforcement decisions."""
        # Update thresholds
        client.put(
            "/api/v1/thresholds",
            json={
                "thresholds": {
                    "allow_max": 0.30,
                    "nudge_min": 0.31,
                    "nudge_max": 0.60,
                    "soft_block_min": 0.61,
                    "soft_block_max": 0.80,
                    "hard_block_min": 0.81,
                },
                "changed_by": "admin@example.com",
                "reason": "Test threshold impact",
            },
        )

        # Risk score 0.35 should now be MEDIUM (was LOW with default thresholds)
        response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_threshold_test",
                "user_id": "user_threshold",
                "risk_score": 0.35,
                "labels": [],
            },
        )

        data = response.json()
        assert data["risk_band"] == RiskBand.MEDIUM.value

    def test_update_thresholds_invalid_config(self):
        """Test that invalid threshold configuration is rejected."""
        response = client.put(
            "/api/v1/thresholds",
            json={
                "thresholds": {
                    "allow_max": 0.50,  # Invalid: overlaps with nudge
                    "nudge_min": 0.40,
                    "nudge_max": 0.64,
                    "soft_block_min": 0.65,
                    "soft_block_max": 0.84,
                    "hard_block_min": 0.85,
                },
                "changed_by": "admin@example.com",
                "reason": "Invalid config test",
            },
        )

        assert response.status_code == 400
        assert "Invalid threshold" in response.json()["detail"]

    def test_update_thresholds_missing_fields(self):
        """Test that missing required fields in update are rejected."""
        response = client.put(
            "/api/v1/thresholds",
            json={
                "thresholds": {
                    "allow_max": 0.35,
                    "nudge_min": 0.36,
                    "nudge_max": 0.60,
                    "soft_block_min": 0.61,
                    "soft_block_max": 0.80,
                    "hard_block_min": 0.81,
                },
                # Missing changed_by and reason
            },
        )

        assert response.status_code == 422  # Pydantic validation error


class TestDeactivateStrikeEndpoint:
    """Test strike deactivation endpoint."""

    def test_deactivate_existing_strike(self):
        """Test deactivating an active strike."""
        user_id = "user_deactivate"

        # Add a strike
        enforce_response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_deactivate",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )

        strike_id = enforce_response.json()["strike_id"]

        # Deactivate the strike
        response = client.delete(f"/api/v1/strikes/{strike_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify strike is deactivated
        strikes_response = client.get(f"/api/v1/strikes/{user_id}?active_only=true")
        assert strikes_response.json()["total_active"] == 0

    def test_deactivate_nonexistent_strike(self):
        """Test deactivating a strike that doesn't exist."""
        response = client.delete("/api/v1/strikes/nonexistent_strike_id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_deactivate_already_inactive_strike(self):
        """Test deactivating a strike that is already inactive."""
        user_id = "user_double_deactivate"

        # Add a strike
        enforce_response = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_double",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )

        strike_id = enforce_response.json()["strike_id"]

        # Deactivate once
        client.delete(f"/api/v1/strikes/{strike_id}")

        # Try to deactivate again
        response = client.delete(f"/api/v1/strikes/{strike_id}")

        assert response.status_code == 404
        assert "already inactive" in response.json()["detail"]


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_user_journey_low_to_high_risk(self):
        """Test a user's journey from low risk to high risk violations."""
        user_id = "user_journey"

        # First message: low risk, allowed
        response1 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_j1",
                "user_id": user_id,
                "risk_score": 0.20,
                "labels": [],
            },
        )
        assert response1.json()["action"] == ActionType.ALLOW.value
        assert response1.json()["strike_count"] == 0

        # Second message: medium risk, nudge
        response2 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_j2",
                "user_id": user_id,
                "risk_score": 0.50,
                "labels": ["borderline"],
            },
        )
        assert response2.json()["action"] == ActionType.NUDGE.value
        assert response2.json()["strike_count"] == 0

        # Third message: high risk, first strike
        response3 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_j3",
                "user_id": user_id,
                "risk_score": 0.75,
                "labels": ["spam"],
            },
        )
        assert response3.json()["action"] == ActionType.SOFT_BLOCK.value
        assert response3.json()["strike_count"] == 1

        # Fourth message: high risk, second strike
        response4 = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_j4",
                "user_id": user_id,
                "risk_score": 0.80,
                "labels": ["harassment"],
            },
        )
        assert response4.json()["action"] == ActionType.COOLDOWN.value
        assert response4.json()["strike_count"] == 2

    def test_different_users_independent_enforcement(self):
        """Test that enforcement decisions are independent per user."""
        # User A: high risk
        response_a = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_a1",
                "user_id": "user_a",
                "risk_score": 0.90,
                "labels": ["harassment"],
            },
        )

        # User B: low risk
        response_b = client.post(
            "/api/v1/enforce",
            json={
                "detection_id": "det_b1",
                "user_id": "user_b",
                "risk_score": 0.10,
                "labels": [],
            },
        )

        # Each should have independent strike counts
        assert response_a.json()["strike_count"] == 1
        assert response_b.json()["strike_count"] == 0
