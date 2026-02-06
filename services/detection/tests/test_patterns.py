"""Tests for individual pattern detection modules."""

import pytest
from src.patterns.phone import detect as detect_phone
from src.patterns.email import detect as detect_email
from src.patterns.url import detect as detect_url
from src.patterns.social import detect as detect_social
from src.patterns.obfuscation import deobfuscate, detect_obfuscation
from src.patterns.intent_phrases import detect as detect_intent


class TestPhonePatterns:
    def test_us_standard(self):
        matches = detect_phone("Call me at 555-123-4567")
        assert len(matches) >= 1
        assert any(m.type == "phone" for m in matches)

    def test_international(self):
        matches = detect_phone("My number is +1-555-123-4567")
        assert len(matches) >= 1

    def test_parenthetical(self):
        matches = detect_phone("Reach me at (555) 123-4567")
        assert len(matches) >= 1

    def test_dotted(self):
        matches = detect_phone("555.123.4567")
        assert len(matches) >= 1

    def test_spaced_digits(self):
        matches = detect_phone("5 5 5 1 2 3 4 5 6 7")
        assert len(matches) >= 1

    def test_no_false_positive_short(self):
        matches = detect_phone("I have 42 items")
        phone_matches = [m for m in matches if m.type == "phone"]
        assert len(phone_matches) == 0

    def test_no_false_positive_dates(self):
        matches = detect_phone("The date is 2024-01-15")
        # Dates should not trigger high-confidence phone matches
        high_conf = [m for m in matches if m.type == "phone" and m.confidence > 0.7]
        assert len(high_conf) == 0


class TestEmailPatterns:
    def test_standard_email(self):
        matches = detect_email("Email me at user@example.com")
        assert len(matches) >= 1
        assert any(m.type == "email" for m in matches)

    def test_plus_alias(self):
        matches = detect_email("Send to user+tag@example.com")
        assert len(matches) >= 1

    def test_spaced_out(self):
        matches = detect_email("user at example dot com")
        assert len(matches) >= 1

    def test_bracket_obfuscation(self):
        matches = detect_email("user [at] example [dot] com")
        assert len(matches) >= 1

    def test_no_false_positive(self):
        matches = detect_email("I went to the store at noon")
        email_matches = [m for m in matches if m.type == "email"]
        assert len(email_matches) == 0


class TestUrlPatterns:
    def test_full_url(self):
        matches = detect_url("Check https://example.com/path")
        assert len(matches) >= 1
        assert any(m.type == "url" for m in matches)

    def test_no_protocol(self):
        matches = detect_url("Visit example.com")
        assert len(matches) >= 1

    def test_shortener(self):
        matches = detect_url("Link: bit.ly/abc123")
        assert len(matches) >= 1

    def test_spelled_domain(self):
        matches = detect_url("go to example dot com")
        assert len(matches) >= 1


class TestSocialPatterns:
    def test_whatsapp(self):
        matches = detect_social("message me on whatsapp")
        assert len(matches) >= 1
        assert any(m.type == "social" for m in matches)

    def test_telegram(self):
        matches = detect_social("my telegram is @username")
        assert len(matches) >= 1

    def test_instagram(self):
        matches = detect_social("follow me on instagram @myhandle")
        assert len(matches) >= 1

    def test_snapchat(self):
        matches = detect_social("add me on snap")
        assert len(matches) >= 1

    def test_dm_pattern(self):
        matches = detect_social("just DM me directly")
        assert len(matches) >= 1


class TestObfuscation:
    def test_zero_width_removal(self):
        text = "h\u200be\u200bl\u200bl\u200bo"
        clean = deobfuscate(text)
        assert clean == "hello"

    def test_fullwidth_normalization(self):
        text = "\uff48\uff45\uff4c\uff4c\uff4f"  # fullwidth "hello"
        clean = deobfuscate(text)
        assert clean == "hello"

    def test_leet_speak(self):
        text = "h3ll0 w0rld"
        clean = deobfuscate(text)
        assert "hello" in clean.lower() or "hell0" in clean.lower()

    def test_detection(self):
        text = "c\u200ball me\u200b"
        matches = detect_obfuscation(text)
        assert len(matches) >= 1


class TestIntentPhrases:
    def test_direct_request(self):
        matches = detect_intent("Can you give me your phone number?")
        assert len(matches) >= 1
        assert any(m.type == "intent" for m in matches)

    def test_move_offplatform(self):
        matches = detect_intent("Let's take this conversation offline")
        assert len(matches) >= 1

    def test_contact_sharing(self):
        matches = detect_intent("Here's my number")
        assert len(matches) >= 1

    def test_no_false_positive(self):
        matches = detect_intent("The weather is nice today")
        intent_matches = [m for m in matches if m.type == "intent"]
        assert len(intent_matches) == 0
