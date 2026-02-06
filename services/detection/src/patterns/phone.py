"""
Phone number detection patterns for Contact Integrity System.

This module provides comprehensive phone number detection across multiple formats,
obfuscation techniques, and international variations. Designed for production use
with high precision and recall.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class PatternMatch:
    """Represents a detected pattern match in text."""
    offset: int
    length: int
    type: str
    confidence: float
    value: str


# Digit word mappings for spelled-out number detection
DIGIT_WORDS = {
    'zero': '0', 'oh': '0', 'o': '0',
    'one': '1', 'won': '1',
    'two': '2', 'to': '2', 'too': '2',
    'three': '3', 'tree': '3',
    'four': '4', 'for': '4', 'fore': '4',
    'five': '5',
    'six': '6', 'sicks': '6',
    'seven': '7',
    'eight': '8', 'ate': '8',
    'nine': '9', 'niner': '9'
}

# Common phone number prefixes/suffixes for context
PHONE_INDICATORS = [
    r'\b(?:call|text|phone|mobile|cell|contact|reach)\s+(?:me\s+)?(?:at|on)\b',
    r'\b(?:my|the)\s+(?:number|phone|mobile|cell)\s+(?:is|:)\b',
    r'\b(?:dial|ring)\b',
    r'\b(?:tel|phone|mob|cell)[:.]?\b',
]


class PhoneDetector:
    """Detects phone numbers in various formats and obfuscations."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for phone detection."""

        # International format: +1-555-123-4567, +44 20 7946 0958
        self.international_pattern = re.compile(
            r'\+\d{1,4}[\s.\-]?'  # Country code
            r'(?:\(?\d{1,4}\)?[\s.\-]?)?'  # Optional area code
            r'\d{1,4}[\s.\-]?\d{1,4}[\s.\-]?\d{1,9}',
            re.IGNORECASE
        )

        # US format: (555) 123-4567, 555-123-4567, 555.123.4567, 5551234567
        self.us_format_pattern = re.compile(
            r'(?:\+?1[\s.\-]?)?'  # Optional country code
            r'(?:\(?\d{3}\)?[\s.\-]?|\d{3}[\s.\-])'  # Area code
            r'\d{3}[\s.\-]?\d{4}'  # Number
            r'(?:\s*(?:x|ext|extension)[\s.\-]?\d{1,5})?',  # Optional extension
            re.IGNORECASE
        )

        # Spaced digits: "5 5 5 1 2 3 4 5 6 7"
        self.spaced_digits_pattern = re.compile(
            r'\b\d(?:\s+\d){6,14}\b'
        )

        # Heavily spaced/separated: "5-5-5-1-2-3-4-5-6-7"
        self.separated_digits_pattern = re.compile(
            r'\b\d(?:[\s.\-]+\d){6,14}\b'
        )

        # Spelled-out numbers: "five five five one two three"
        digit_word_pattern = '|'.join(DIGIT_WORDS.keys())
        self.spelled_pattern = re.compile(
            rf'\b(?:{digit_word_pattern})(?:[\s\-]+(?:{digit_word_pattern})){{6,14}}\b',
            re.IGNORECASE
        )

        # Mixed spelled and numeric: "call me at five five five 123 4567"
        self.mixed_pattern = re.compile(
            rf'\b(?:\d|{digit_word_pattern})(?:[\s.\-]+(?:\d|{digit_word_pattern})){{6,14}}\b',
            re.IGNORECASE
        )

        # Context patterns for confidence boosting
        self.context_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in PHONE_INDICATORS
        ]

    def _normalize_spelled_number(self, text: str) -> str:
        """Convert spelled-out numbers to digits."""
        words = text.lower().split()
        digits = []
        for word in words:
            word = word.strip('.,!?;:-')
            if word in DIGIT_WORDS:
                digits.append(DIGIT_WORDS[word])
            elif word.isdigit():
                digits.append(word)
        return ''.join(digits)

    def _extract_digits(self, text: str) -> str:
        """Extract only digits from text."""
        return re.sub(r'\D', '', text)

    def _is_valid_phone_length(self, digits: str) -> bool:
        """Check if digit count is reasonable for a phone number."""
        length = len(digits)
        # 7 digits (local), 10 digits (US), 11 digits (+1),
        # 7-15 for international
        return 7 <= length <= 15

    def _has_phone_context(self, text: str, match_pos: int, window: int = 30) -> bool:
        """Check if there's phone-related context near the match."""
        start = max(0, match_pos - window)
        end = min(len(text), match_pos + window)
        context = text[start:end]

        for pattern in self.context_patterns:
            if pattern.search(context):
                return True
        return False

    def _calculate_confidence(self, match_text: str, full_text: str,
                             match_pos: int, pattern_type: str) -> float:
        """Calculate confidence score for a phone match."""
        confidence = 0.5  # Base confidence

        digits = self._extract_digits(match_text)

        # Boost for valid length
        if self._is_valid_phone_length(digits):
            confidence += 0.2

        # Boost for standard formats
        if pattern_type in ['international', 'us_format']:
            confidence += 0.2

        # Boost for phone context nearby
        if self._has_phone_context(full_text, match_pos):
            confidence += 0.15

        # Boost for country code
        if match_text.strip().startswith('+'):
            confidence += 0.1

        # Penalize very long digit sequences (likely not phone)
        if len(digits) > 15:
            confidence -= 0.3

        # Penalize if starts with 0 or 1 (in US context, less common)
        if len(digits) == 10 and digits[0] in ['0', '1']:
            confidence -= 0.1

        # Penalize repeated digits (555-5555, etc.)
        if len(set(digits)) <= 3 and len(digits) >= 7:
            confidence -= 0.25

        return max(0.0, min(1.0, confidence))

    def detect_international(self, text: str) -> List[PatternMatch]:
        """Detect international format phone numbers."""
        matches = []
        for match in self.international_pattern.finditer(text):
            matched_text = match.group(0)
            digits = self._extract_digits(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'international'
                )
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_us_format(self, text: str) -> List[PatternMatch]:
        """Detect US format phone numbers."""
        matches = []
        for match in self.us_format_pattern.finditer(text):
            matched_text = match.group(0)
            digits = self._extract_digits(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'us_format'
                )
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_spaced_digits(self, text: str) -> List[PatternMatch]:
        """Detect spaced-out digit sequences."""
        matches = []
        for match in self.spaced_digits_pattern.finditer(text):
            matched_text = match.group(0)
            digits = self._extract_digits(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'spaced'
                )
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_separated_digits(self, text: str) -> List[PatternMatch]:
        """Detect heavily separated digit sequences."""
        matches = []
        for match in self.separated_digits_pattern.finditer(text):
            matched_text = match.group(0)
            digits = self._extract_digits(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'separated'
                )
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_spelled_out(self, text: str) -> List[PatternMatch]:
        """Detect spelled-out phone numbers."""
        matches = []
        for match in self.spelled_pattern.finditer(text):
            matched_text = match.group(0)
            digits = self._normalize_spelled_number(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'spelled'
                )
                # Boost confidence for spelled numbers (intentional obfuscation)
                confidence = min(1.0, confidence + 0.1)
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_mixed_format(self, text: str) -> List[PatternMatch]:
        """Detect mixed spelled and numeric formats."""
        matches = []
        for match in self.mixed_pattern.finditer(text):
            matched_text = match.group(0)
            # Normalize to get digit count
            digits = self._normalize_spelled_number(matched_text)
            if not digits:
                digits = self._extract_digits(matched_text)

            if self._is_valid_phone_length(digits):
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), 'mixed'
                )
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='phone',
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
    Run all phone detection patterns against the text.

    Args:
        text: Input text to scan for phone numbers

    Returns:
        List of PatternMatch objects for detected phone numbers,
        deduplicated and sorted by offset
    """
    detector = PhoneDetector()

    all_matches = []
    all_matches.extend(detector.detect_international(text))
    all_matches.extend(detector.detect_us_format(text))
    all_matches.extend(detector.detect_spaced_digits(text))
    all_matches.extend(detector.detect_separated_digits(text))
    all_matches.extend(detector.detect_spelled_out(text))
    all_matches.extend(detector.detect_mixed_format(text))

    return _deduplicate_matches(all_matches)
