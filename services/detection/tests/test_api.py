"""Tests for the Detection Service API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


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
        assert data["service"] == "detection"


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_clean(self, client):
        async with client as c:
            response = await c.post("/analyze", json={
                "message_id": "msg-1",
                "thread_id": "thread-1",
                "user_id": "user-1",
                "content": "Hello, nice to meet you!",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] < 0.40
        assert "message_id" in data
        assert "detection_id" in data

    @pytest.mark.asyncio
    async def test_analyze_phone(self, client):
        async with client as c:
            response = await c.post("/analyze", json={
                "message_id": "msg-2",
                "thread_id": "thread-1",
                "user_id": "user-1",
                "content": "Call me at 555-123-4567 please",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] >= 0.40
        assert "phone_number" in data["labels"]

    @pytest.mark.asyncio
    async def test_analyze_validation_error(self, client):
        async with client as c:
            response = await c.post("/analyze", json={
                "message_id": "msg-3",
                # Missing required fields
            })
        assert response.status_code == 422


class TestBatchEndpoint:
    @pytest.mark.asyncio
    async def test_batch_analyze(self, client):
        async with client as c:
            response = await c.post("/analyze/batch", json={
                "messages": [
                    {
                        "message_id": "batch-1",
                        "thread_id": "t1",
                        "user_id": "u1",
                        "content": "Hello there",
                    },
                    {
                        "message_id": "batch-2",
                        "thread_id": "t1",
                        "user_id": "u1",
                        "content": "Call me at 555-123-4567",
                    },
                ]
            })
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["risk_score"] < data["results"][1]["risk_score"]
