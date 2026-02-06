"""Tests for the detection pipeline orchestrator."""

import pytest
from src.models import AnalyzeRequest
from src.engine.pipeline import DetectionPipeline


@pytest.fixture
def pipeline():
    return DetectionPipeline()


class TestPipeline:
    @pytest.mark.asyncio
    async def test_clean_message(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-1",
            thread_id="thread-1",
            user_id="user-1",
            content="Hello, how are you doing today?",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score < 0.40
        assert result.message_id == "test-1"

    @pytest.mark.asyncio
    async def test_phone_number(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-2",
            thread_id="thread-1",
            user_id="user-1",
            content="Call me at 555-123-4567",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.40
        assert "phone_number" in result.labels

    @pytest.mark.asyncio
    async def test_email_detection(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-3",
            thread_id="thread-1",
            user_id="user-1",
            content="Send me an email at john@gmail.com",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.40
        assert "email_address" in result.labels

    @pytest.mark.asyncio
    async def test_high_risk_obfuscated_phone(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-4",
            thread_id="thread-1",
            user_id="user-1",
            content="call me at 5\u200b5\u200b5-1\u200b2\u200b3-4\u200b5\u200b6\u200b7",
        )
        result = await pipeline.analyze(req)
        # Should detect both phone and obfuscation
        assert result.risk_score >= 0.30

    @pytest.mark.asyncio
    async def test_stage1_only(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-5",
            thread_id="thread-1",
            user_id="user-1",
            content="Call me at 555-123-4567",
            stages=[1],
        )
        result = await pipeline.analyze(req, stages=[1])
        assert result.risk_score >= 0.40
        assert result.stage == 1

    @pytest.mark.asyncio
    async def test_intent_phrase(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-6",
            thread_id="thread-1",
            user_id="user-1",
            content="Let's take this conversation offline and chat directly",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score > 0

    @pytest.mark.asyncio
    async def test_social_handle(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-7",
            thread_id="thread-1",
            user_id="user-1",
            content="Add me on WhatsApp, my handle is @johndoe",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.30
        assert "social_handle" in result.labels

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-8",
            thread_id="thread-1",
            user_id="user-1",
            content="Hello",
        )
        result = await pipeline.analyze(req)
        assert result.processing_ms >= 0

    @pytest.mark.asyncio
    async def test_hashed_tokens(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-9",
            thread_id="thread-1",
            user_id="user-1",
            content="Email me at test@example.com",
        )
        result = await pipeline.analyze(req)
        # If email is detected, token should be hashed
        if "email_address" in result.labels:
            assert len(result.hashed_tokens) > 0
            # Should be SHA-256 hex (64 chars)
            assert all(len(h) == 64 for h in result.hashed_tokens)

    @pytest.mark.asyncio
    async def test_multiple_contact_types(self, pipeline):
        req = AnalyzeRequest(
            message_id="test-10",
            thread_id="thread-1",
            user_id="user-1",
            content="Email me at test@example.com or call 555-123-4567",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.50
        assert len(result.labels) >= 2


class TestAdversarialPatterns:
    """Adversarial test suite for obfuscation and evasion attempts."""

    @pytest.mark.asyncio
    async def test_spaced_phone(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-1", thread_id="t1", user_id="u1",
            content="five five five one two three four five six seven",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score > 0

    @pytest.mark.asyncio
    async def test_at_sign_replacement(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-2", thread_id="t1", user_id="u1",
            content="email me at user [at] gmail [dot] com",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.40

    @pytest.mark.asyncio
    async def test_url_obfuscation(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-3", thread_id="t1", user_id="u1",
            content="check out bit dot ly slash abc123",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score > 0

    @pytest.mark.asyncio
    async def test_whatsapp_number(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-4", thread_id="t1", user_id="u1",
            content="WhatsApp me at +1 555 123 4567",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.50

    @pytest.mark.asyncio
    async def test_zero_width_chars(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-5", thread_id="t1", user_id="u1",
            content="my e\u200bmail is t\u200best@g\u200bmail.com",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score >= 0.20  # Obfuscation detected, partial email match

    @pytest.mark.asyncio
    async def test_clean_message_no_alert(self, pipeline):
        req = AnalyzeRequest(
            message_id="adv-6", thread_id="t1", user_id="u1",
            content="I would like to schedule the appointment for next Tuesday at 3pm please",
        )
        result = await pipeline.analyze(req)
        assert result.risk_score < 0.40
