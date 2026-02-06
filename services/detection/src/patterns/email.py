"""
Email detection patterns for Contact Integrity System.

This module provides comprehensive email detection including standard formats,
obfuscation techniques, and unicode tricks. Designed for production use with
high precision and recall.
"""

import re
from dataclasses import dataclass
from typing import List
import unicodedata


@dataclass
class PatternMatch:
    """Represents a detected pattern match in text."""
    offset: int
    length: int
    type: str
    confidence: float
    value: str


# Common email indicators for context
EMAIL_INDICATORS = [
    r'\b(?:email|mail|e-mail|contact)\s+(?:me\s+)?(?:at|on)\b',
    r'\bmy\s+(?:email|e-mail|mail)\s+(?:is|address)\b',
    r'\bsend\s+(?:me\s+)?(?:an?\s+)?(?:email|mail)\b',
    r'\breach\s+(?:me\s+)?(?:via|by)\s+(?:email|mail)\b',
]


class EmailDetector:
    """Detects email addresses in various formats and obfuscations."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for email detection."""

        # Standard email format: user@domain.com
        # More permissive to catch edge cases
        self.standard_pattern = re.compile(
            r'\b[a-zA-Z0-9]'  # Start with alphanumeric
            r'[a-zA-Z0-9._+\-]*'  # Middle can have special chars
            r'@'
            r'[a-zA-Z0-9]'  # Domain starts with alphanumeric
            r'[a-zA-Z0-9.\-]*'  # Domain can have dots and hyphens
            r'\.'  # Must have at least one dot
            r'[a-zA-Z]{2,}',  # TLD at least 2 chars
            re.IGNORECASE
        )

        # Spaced out format: "user at domain dot com"
        self.spaced_pattern = re.compile(
            r'\b[a-zA-Z0-9]'
            r'[a-zA-Z0-9._+\-]*'
            r'\s+(?:at|@)\s+'
            r'[a-zA-Z0-9]'
            r'[a-zA-Z0-9.\-\s]*'
            r'\s+dot\s+'
            r'[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )

        # Obfuscated brackets: "user [at] domain [dot] com"
        self.bracket_pattern = re.compile(
            r'\b[a-zA-Z0-9]'
            r'[a-zA-Z0-9._+\-]*'
            r'\s*[\[\(]?\s*(?:at|@)\s*[\]\)]?\s*'
            r'[a-zA-Z0-9]'
            r'[a-zA-Z0-9.\-\s]*'
            r'\s*[\[\(]?\s*dot\s*[\]\)]?\s*'
            r'[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )

        # Alternative separators: "user (at) domain (dot) com"
        self.alt_separator_pattern = re.compile(
            r'\b[a-zA-Z0-9]'
            r'[a-zA-Z0-9._+\-]*'
            r'[\s\(\[\{]*'
            r'(?:at|@|AT|\(at\)|\[at\])'
            r'[\s\)\]\}]*'
            r'[a-zA-Z0-9]'
            r'[a-zA-Z0-9.\-\s]*'
            r'[\s\(\[\{]*'
            r'(?:dot|DOT|\(dot\)|\[dot\]|\.)'
            r'[\s\)\]\}]*'
            r'[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )

        # Domain with "dot" spelled out: user@domain dot com
        self.mixed_dot_pattern = re.compile(
            r'\b[a-zA-Z0-9]'
            r'[a-zA-Z0-9._+\-]*'
            r'@'
            r'[a-zA-Z0-9]'
            r'[a-zA-Z0-9.\-]*'
            r'(?:\s+dot\s+|\s*\.\s*)'
            r'[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )

        # Context patterns for confidence boosting
        self.context_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in EMAIL_INDICATORS
        ]

        # Common TLDs for validation
        self.common_tlds = {
            'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
            'co', 'io', 'ai', 'app', 'dev', 'tech', 'info',
            'biz', 'name', 'pro', 'mobi', 'tel', 'travel',
            'uk', 'us', 'ca', 'au', 'de', 'fr', 'jp', 'cn',
            'ru', 'br', 'in', 'it', 'es', 'nl', 'se', 'no'
        }

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to catch unicode tricks."""
        # Normalize to NFKC (compatibility composition)
        normalized = unicodedata.normalize('NFKC', text)

        # Replace common homoglyphs
        homoglyphs = {
            '\u0430': 'a',  # Cyrillic a
            '\u0435': 'e',  # Cyrillic e
            '\u043e': 'o',  # Cyrillic o
            '\u0440': 'p',  # Cyrillic p
            '\u0441': 'c',  # Cyrillic c
            '\u0445': 'x',  # Cyrillic x
            '\u0455': 's',  # Cyrillic s
            '\u0456': 'i',  # Cyrillic i
            '\u0458': 'j',  # Cyrillic j
            '\u04bb': 'h',  # Cyrillic h
        }

        for original, replacement in homoglyphs.items():
            normalized = normalized.replace(original, replacement)

        return normalized

    def _has_email_context(self, text: str, match_pos: int, window: int = 30) -> bool:
        """Check if there's email-related context near the match."""
        start = max(0, match_pos - window)
        end = min(len(text), match_pos + window)
        context = text[start:end]

        for pattern in self.context_patterns:
            if pattern.search(context):
                return True
        return False

    def _extract_tld(self, email: str) -> str:
        """Extract TLD from email address."""
        # Normalize spaces and obfuscation
        email = email.lower()
        email = re.sub(r'\s*dot\s*', '.', email)
        email = re.sub(r'[\[\]\(\)]', '', email)

        # Get last part after final dot
        parts = email.split('.')
        if parts:
            return parts[-1].strip()
        return ''

    def _is_valid_tld(self, tld: str) -> bool:
        """Check if TLD is valid."""
        tld = tld.lower().strip()
        # Check common TLDs or if it's at least 2 chars alpha
        return tld in self.common_tlds or (len(tld) >= 2 and tld.isalpha())

    def _normalize_email(self, text: str) -> str:
        """Normalize obfuscated email to standard format."""
        normalized = text.lower()

        # Replace "at" with @
        normalized = re.sub(r'\s*[\[\(]?\s*(?:at)\s*[\]\)]?\s*', '@', normalized)

        # Replace "dot" with .
        normalized = re.sub(r'\s*[\[\(]?\s*(?:dot)\s*[\]\)]?\s*', '.', normalized)

        # Remove extra spaces
        normalized = re.sub(r'\s+', '', normalized)

        return normalized

    def _calculate_confidence(self, match_text: str, full_text: str,
                             match_pos: int, pattern_type: str) -> float:
        """Calculate confidence score for an email match."""
        confidence = 0.5  # Base confidence

        # Normalize to check TLD
        normalized = self._normalize_email(match_text)
        tld = self._extract_tld(normalized)

        # Boost for valid TLD
        if self._is_valid_tld(tld):
            confidence += 0.2
            # Extra boost for common TLDs
            if tld in self.common_tlds:
                confidence += 0.1

        # Boost for standard format (no obfuscation)
        if pattern_type == 'standard':
            confidence += 0.15

        # Boost for obfuscation (indicates intent to hide)
        if pattern_type in ['spaced', 'bracket', 'alt_separator']:
            confidence += 0.1

        # Boost for email context nearby
        if self._has_email_context(full_text, match_pos):
            confidence += 0.15

        # Penalize very short local parts (before @)
        local_part = normalized.split('@')[0] if '@' in normalized else ''
        if len(local_part) < 2:
            confidence -= 0.2

        # Penalize suspicious patterns
        if '..' in normalized or '@@' in normalized:
            confidence -= 0.3

        # Penalize if it looks like a file path
        if normalized.count('/') > 0 or normalized.count('\\') > 0:
            confidence -= 0.3

        return max(0.0, min(1.0, confidence))

    def detect_standard(self, text: str) -> List[PatternMatch]:
        """Detect standard format email addresses."""
        # Normalize unicode first
        normalized_text = self._normalize_unicode(text)

        matches = []
        for match in self.standard_pattern.finditer(normalized_text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, normalized_text, match.start(), 'standard'
            )

            if confidence > 0.3:  # Threshold to filter false positives
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='email',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_spaced(self, text: str) -> List[PatternMatch]:
        """Detect spaced-out email addresses."""
        matches = []
        for match in self.spaced_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'spaced'
            )

            # Higher threshold for obfuscated patterns
            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='email',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_bracket_obfuscation(self, text: str) -> List[PatternMatch]:
        """Detect bracket-obfuscated email addresses."""
        matches = []
        for match in self.bracket_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'bracket'
            )

            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='email',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_alt_separator(self, text: str) -> List[PatternMatch]:
        """Detect alternative separator email addresses."""
        matches = []
        for match in self.alt_separator_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'alt_separator'
            )

            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='email',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_mixed_dot(self, text: str) -> List[PatternMatch]:
        """Detect emails with mixed dot notation."""
        matches = []
        for match in self.mixed_dot_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'mixed'
            )

            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='email',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches


def _deduplicate_matches(matches: List[PatternMatch]) -> List[PatternMatch]:
    """Remove overlapping matches, keeping highest confidence."""
    if not matches:
        return []

    # Sort by position, then by confidence descending
    sorted_matches = sorted(matches, key=lambda m: (m.offset, -m.confidence))

    result = []
    for match in sorted_matches:
        # Check if this match overlaps with any accepted match
        overlaps = False
        for accepted in result:
            # Check for overlap
            if not (match.offset >= accepted.offset + accepted.length or
                    match.offset + match.length <= accepted.offset):
                overlaps = True
                break

        if not overlaps:
            result.append(match)

    return sorted(result, key=lambda m: m.offset)


def detect(text: str) -> List[PatternMatch]:
    """
    Run all email detection patterns against the text.

    Args:
        text: Input text to scan for email addresses

    Returns:
        List of PatternMatch objects for detected emails,
        deduplicated and sorted by offset
    """
    detector = EmailDetector()

    all_matches = []
    all_matches.extend(detector.detect_standard(text))
    all_matches.extend(detector.detect_spaced(text))
    all_matches.extend(detector.detect_bracket_obfuscation(text))
    all_matches.extend(detector.detect_alt_separator(text))
    all_matches.extend(detector.detect_mixed_dot(text))

    return _deduplicate_matches(all_matches)
