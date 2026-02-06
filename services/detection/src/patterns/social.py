"""
Social platform handle detection patterns for Contact Integrity System.

This module detects mentions of social media platforms and handles across
WhatsApp, Telegram, Instagram, Snapchat, Signal, Discord, and others.
Designed for production use with high precision and recall.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class PatternMatch:
    """Represents a detected pattern match in text."""
    offset: int
    length: int
    type: str
    confidence: float
    value: str


# Platform-specific patterns and indicators
PLATFORM_CONFIG = {
    'whatsapp': {
        'handles': [
            r'\bwa\.me/[\w\d+]+',
            r'\bwhatsapp\.com/[\w\d+]+',
            r'\b(?:my\s+)?whatsapp\s+(?:is|number|:)\s*[+\d\s\-()]+',
        ],
        'mentions': [
            r'\b(?:whatsapp|wassup|whats\s*app|wa)\s+me\b',
            r'\b(?:on|via|through)\s+(?:whatsapp|wa)\b',
            r'\b(?:text|message|msg|contact)\s+(?:me\s+)?(?:on|via)\s+(?:whatsapp|wa)\b',
            r'\b(?:add|reach|find)\s+(?:me\s+)?(?:on|via)\s+(?:whatsapp|wa)\b',
        ],
        'indicators': ['whatsapp', 'wa.me', 'wassup', 'wapp'],
    },
    'telegram': {
        'handles': [
            r'\bt\.me/[\w\d_]+',
            r'\btelegram\.me/[\w\d_]+',
            r'\btelegram\.org/[\w\d_]+',
            r'@[\w\d_]{5,32}(?!\w)',  # Telegram username format
        ],
        'mentions': [
            r'\b(?:telegram|tg)\s+me\b',
            r'\b(?:on|via|through)\s+(?:telegram|tg)\b',
            r'\b(?:text|message|msg|contact)\s+(?:me\s+)?(?:on|via)\s+(?:telegram|tg)\b',
            r'\b(?:add|reach|find)\s+(?:me\s+)?(?:on|via)\s+(?:telegram|tg)\b',
            r'\bmy\s+(?:telegram|tg)\s+(?:is|handle|username|:)\b',
        ],
        'indicators': ['telegram', 't.me', 'tg', 'telegrm'],
    },
    'instagram': {
        'handles': [
            r'\binstagram\.com/[\w\d_.]+',
            r'\binstagr\.am/[\w\d_.]+',
            r'@[\w\d_.]{1,30}(?!\w)',  # Instagram username format
        ],
        'mentions': [
            r'\b(?:instagram|insta|ig)\s+me\b',
            r'\b(?:on|via|through)\s+(?:instagram|insta|ig)\b',
            r'\b(?:follow|dm|message|msg)\s+(?:me\s+)?(?:on|via)\s+(?:instagram|insta|ig)\b',
            r'\b(?:add|find)\s+(?:me\s+)?(?:on|via)\s+(?:instagram|insta|ig)\b',
            r'\bmy\s+(?:instagram|insta|ig)\s+(?:is|handle|username|:)\b',
        ],
        'indicators': ['instagram', 'insta', 'ig', 'instagr'],
    },
    'snapchat': {
        'handles': [
            r'\bsnapchat\.com/add/[\w\d_.]+',
        ],
        'mentions': [
            r'\b(?:snapchat|snap)\s+me\b',
            r'\b(?:on|via|through)\s+(?:snapchat|snap)\b',
            r'\b(?:add|message|msg|contact)\s+(?:me\s+)?(?:on|via)\s+(?:snapchat|snap)\b',
            r'\bmy\s+(?:snapchat|snap)\s+(?:is|handle|username|:)\b',
            r'\badd\s+me\s+(?:on\s+)?snap\b',
        ],
        'indicators': ['snapchat', 'snap', 'snapcht'],
    },
    'signal': {
        'handles': [
            r'\bsignal\.org/[\w\d+]+',
            r'\bsignal\.me/[\w\d+]+',
        ],
        'mentions': [
            r'\b(?:signal|sig)\s+me\b',
            r'\b(?:on|via|through)\s+(?:signal|sig)\b',
            r'\b(?:text|message|msg|contact)\s+(?:me\s+)?(?:on|via)\s+(?:signal|sig)\b',
            r'\bmy\s+(?:signal|sig)\s+(?:is|number|:)\b',
        ],
        'indicators': ['signal', 'sig'],
    },
    'discord': {
        'handles': [
            r'\bdiscord\.gg/[\w\d]+',
            r'\bdiscord\.com/invite/[\w\d]+',
            r'[\w\d_]{2,32}#\d{4}',  # Discord tag format username#1234
        ],
        'mentions': [
            r'\b(?:discord|disc)\s+me\b',
            r'\b(?:on|via|through)\s+(?:discord|disc)\b',
            r'\b(?:message|msg|dm|contact)\s+(?:me\s+)?(?:on|via)\s+(?:discord|disc)\b',
            r'\bmy\s+(?:discord|disc)\s+(?:is|tag|username|:)\b',
            r'\bjoin\s+(?:my\s+)?discord\b',
        ],
        'indicators': ['discord', 'disc', 'discrd'],
    },
    'messenger': {
        'handles': [
            r'\bm\.me/[\w\d.]+',
            r'\bmessenger\.com/t/[\w\d.]+',
            r'\bfb\.me/[\w\d.]+',
        ],
        'mentions': [
            r'\b(?:facebook\s+)?messenger\s+me\b',
            r'\b(?:on|via|through)\s+(?:facebook\s+)?messenger\b',
            r'\b(?:message|msg|contact)\s+(?:me\s+)?(?:on|via)\s+(?:facebook\s+)?messenger\b',
            r'\bfb\s+(?:message|msg|me)\b',
        ],
        'indicators': ['messenger', 'fb.me', 'm.me', 'facebook'],
    },
    'tiktok': {
        'handles': [
            r'\btiktok\.com/@[\w\d_.]+',
            r'@[\w\d_.]{2,24}(?!\w)',  # TikTok username format
        ],
        'mentions': [
            r'\b(?:tiktok|tik\s*tok|tt)\s+me\b',
            r'\b(?:on|via|through)\s+(?:tiktok|tik\s*tok|tt)\b',
            r'\b(?:follow|message|dm)\s+(?:me\s+)?(?:on|via)\s+(?:tiktok|tik\s*tok|tt)\b',
            r'\bmy\s+(?:tiktok|tik\s*tok|tt)\s+(?:is|handle|username|:)\b',
        ],
        'indicators': ['tiktok', 'tik tok', 'tt'],
    },
}

# Generic patterns
GENERIC_DM_PATTERNS = [
    r'\bdm\s+me\b',
    r'\bslide\s+into\s+(?:my\s+)?dms?\b',
    r'\bhit\s+(?:up\s+)?(?:my\s+)?dms?\b',
    r'\bcheck\s+(?:your\s+)?dms?\b',
    r'\bmessage\s+me\s+(?:directly|privately|private)\b',
    r'\btext\s+me\s+(?:directly|privately|private)\b',
    r'\bcontact\s+me\s+(?:directly|privately|off\s*[-\s]*platform)\b',
]


class SocialDetector:
    """Detects social media platform mentions and handles."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for social platform detection."""
        self.platform_patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}

        for platform, config in PLATFORM_CONFIG.items():
            self.platform_patterns[platform] = {
                'handles': [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in config['handles']
                ],
                'mentions': [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in config['mentions']
                ],
            }

        # Compile generic DM patterns
        self.generic_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in GENERIC_DM_PATTERNS
        ]

    def _calculate_confidence(self, match_text: str, full_text: str,
                             match_pos: int, platform: str,
                             match_type: str) -> float:
        """Calculate confidence score for a social media match."""
        confidence = 0.5  # Base confidence

        # Boost for handle patterns (more explicit)
        if match_type == 'handle':
            confidence += 0.3

        # Boost for mention patterns
        if match_type == 'mention':
            confidence += 0.2

        # Boost for URL-like patterns
        if any(c in match_text.lower() for c in ['.me/', '.com/', '.gg/', '.org/']):
            confidence += 0.15

        # Boost for @ mentions
        if '@' in match_text:
            confidence += 0.1

        # Check for platform name near match
        window_start = max(0, match_pos - 40)
        window_end = min(len(full_text), match_pos + len(match_text) + 40)
        context = full_text[window_start:window_end].lower()

        if platform in PLATFORM_CONFIG:
            indicators = PLATFORM_CONFIG[platform]['indicators']
            if any(indicator in context for indicator in indicators):
                confidence += 0.15

        # Boost for phrases indicating off-platform contact
        off_platform_phrases = [
            'off platform', 'outside of here', 'not here',
            'reach me', 'contact me', 'find me', 'add me'
        ]
        if any(phrase in context for phrase in off_platform_phrases):
            confidence += 0.1

        # Penalize very short handles without clear context
        if match_type == 'handle' and len(match_text.strip('@')) < 3:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def detect_platform(self, text: str, platform: str) -> List[PatternMatch]:
        """Detect mentions and handles for a specific platform."""
        matches = []

        if platform not in self.platform_patterns:
            return matches

        patterns = self.platform_patterns[platform]

        # Detect handle patterns
        for pattern in patterns['handles']:
            for match in pattern.finditer(text):
                matched_text = match.group(0)
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), platform, 'handle'
                )

                if confidence > 0.4:
                    matches.append(PatternMatch(
                        offset=match.start(),
                        length=len(matched_text),
                        type='social',
                        confidence=confidence,
                        value=matched_text
                    ))

        # Detect mention patterns
        for pattern in patterns['mentions']:
            for match in pattern.finditer(text):
                matched_text = match.group(0)
                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), platform, 'mention'
                )

                if confidence > 0.5:
                    matches.append(PatternMatch(
                        offset=match.start(),
                        length=len(matched_text),
                        type='social',
                        confidence=confidence,
                        value=matched_text
                    ))

        return matches

    def detect_generic_dm(self, text: str) -> List[PatternMatch]:
        """Detect generic DM/contact requests."""
        matches = []

        for pattern in self.generic_patterns:
            for match in pattern.finditer(text):
                matched_text = match.group(0)

                # Calculate confidence based on context
                confidence = 0.6  # Base confidence for generic DM

                # Check for platform context nearby
                window_start = max(0, match.start() - 50)
                window_end = min(len(text), match.end() + 50)
                context = text[window_start:window_end].lower()

                # Boost if there's platform mention nearby
                has_platform_context = False
                for platform, config in PLATFORM_CONFIG.items():
                    if any(indicator in context for indicator in config['indicators']):
                        has_platform_context = True
                        confidence += 0.15
                        break

                # Boost for off-platform indicators
                if any(phrase in context for phrase in [
                    'off platform', 'outside', 'not here', 'privately'
                ]):
                    confidence += 0.1

                if confidence > 0.5:
                    matches.append(PatternMatch(
                        offset=match.start(),
                        length=len(matched_text),
                        type='social',
                        confidence=confidence,
                        value=matched_text
                    ))

        return matches

    def detect_at_mentions(self, text: str) -> List[PatternMatch]:
        """
        Detect @username patterns that might be social handles.
        This is intentionally conservative to avoid false positives.
        """
        matches = []

        # Pattern for @username (must have platform context nearby)
        at_pattern = re.compile(r'@[\w\d_]{3,30}(?!\w)', re.IGNORECASE)

        for match in at_pattern.finditer(text):
            matched_text = match.group(0)

            # Check for platform context within 50 chars
            window_start = max(0, match.start() - 50)
            window_end = min(len(text), match.end() + 50)
            context = text[window_start:window_end].lower()

            # Only accept if there's platform context
            has_context = False
            detected_platform = None

            for platform, config in PLATFORM_CONFIG.items():
                if any(indicator in context for indicator in config['indicators']):
                    has_context = True
                    detected_platform = platform
                    break

            if has_context:
                confidence = 0.65  # Moderate confidence for context-based @mention

                # Boost for specific platform indicators
                if detected_platform in ['instagram', 'telegram', 'tiktok']:
                    confidence += 0.15

                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='social',
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
    Run all social media detection patterns against the text.

    Args:
        text: Input text to scan for social media mentions

    Returns:
        List of PatternMatch objects for detected social media references,
        deduplicated and sorted by offset
    """
    detector = SocialDetector()

    all_matches = []

    # Detect platform-specific patterns
    for platform in PLATFORM_CONFIG.keys():
        all_matches.extend(detector.detect_platform(text, platform))

    # Detect generic DM patterns
    all_matches.extend(detector.detect_generic_dm(text))

    # Detect @mentions with context
    all_matches.extend(detector.detect_at_mentions(text))

    return _deduplicate_matches(all_matches)
