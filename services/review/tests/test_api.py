"""Tests for the Review Queue API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.api.routes import get_case_manager, get_audit_log


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health(self, client):
        async with client as c:
            response = await c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "review"


class TestCasesEndpoint:
    @pytest.mark.asyncio
    async def test_create_case(self, client):
        async with client as c:
            response = await c.post("/cases", json={
                "detection_id": "det-001",
                "user_id": "user-alice",
                "thread_id": "thread-100",
                "priority": 5,
            })
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "user-alice"
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_list_cases(self, client):
        async with client as c:
            # Create a case first
            await c.post("/cases", json={
                "detection_id": "det-list",
                "user_id": "user-list",
                "thread_id": "thread-list",
            })
            response = await c.get("/cases")
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_case(self, client):
        async with client as c:
            create_resp = await c.post("/cases", json={
                "detection_id": "det-get",
                "user_id": "user-get",
                "thread_id": "thread-get",
            })
            case_id = create_resp.json()["id"]
            response = await c.get(f"/cases/{case_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_case(self, client):
        async with client as c:
            response = await c.get("/cases/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_case(self, client):
        async with client as c:
            create_resp = await c.post("/cases", json={
                "detection_id": "det-update",
                "user_id": "user-update",
                "thread_id": "thread-update",
            })
            case_id = create_resp.json()["id"]
            response = await c.patch(f"/cases/{case_id}", json={
                "assigned_to": "mod-dan",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "mod-dan"
        assert data["status"] == "in_review"


class TestActionsEndpoint:
    @pytest.mark.asyncio
    async def test_create_action(self, client):
        async with client as c:
            create_resp = await c.post("/cases", json={
                "detection_id": "det-action",
                "user_id": "user-action",
                "thread_id": "thread-action",
            })
            case_id = create_resp.json()["id"]
            response = await c.post(f"/cases/{case_id}/actions", json={
                "actor_id": "mod-dan",
                "actor_role": "moderator",
                "action_type": "block",
                "target_user_id": "user-action",
                "target_scope": "message",
                "reason_code": "phone_detected",
            })
        assert response.status_code == 201
        data = response.json()
        assert data["action_type"] == "block"
        assert data["actor_id"] == "mod-dan"


class TestAppealEndpoint:
    @pytest.mark.asyncio
    async def test_file_appeal(self, client):
        async with client as c:
            # Create and resolve a case
            create_resp = await c.post("/cases", json={
                "detection_id": "det-appeal",
                "user_id": "user-appeal",
                "thread_id": "thread-appeal",
            })
            case_id = create_resp.json()["id"]
            await c.patch(f"/cases/{case_id}", json={
                "status": "in_review",
            })
            await c.patch(f"/cases/{case_id}", json={
                "status": "resolved",
                "resolution": "confirmed",
            })
            # File appeal
            response = await c.post(f"/cases/{case_id}/appeal", json={
                "reason": "I was discussing a different topic",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "appealed"


class TestStatsEndpoint:
    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        async with client as c:
            response = await c.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "open_cases" in data
        assert "false_positive_rate" in data
