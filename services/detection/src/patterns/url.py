"""
URL detection patterns for Contact Integrity System.

This module provides comprehensive URL detection including full URLs, link shorteners,
domain mentions, and obfuscation techniques. Designed for production use with
high precision and recall.
"""

import re
from dataclasses import dataclass
from typing import List, Set


@dataclass
class PatternMatch:
    """Represents a detected pattern match in text."""
    offset: int
    length: int
    type: str
    confidence: float
    value: str


# Common URL shortener domains
SHORTENER_DOMAINS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
    'is.gd', 'buff.ly', 'adf.ly', 'bl.ink', 'lnkd.in',
    'shorte.st', 'cutt.ly', 'rb.gy', 'clck.ru', 'tiny.cc',
    'short.io', 'rebrand.ly', 'v.gd', 'tr.im', 'cli.gs',
    'u.to', 'x.co', 'scrnch.me', 'fiverr.com/s', 'mcaf.ee',
    'su.pr', 'qr.ae', 'cur.lv', 'ity.im', 'q.gs'
}

# Common social/communication platforms
SOCIAL_DOMAINS = {
    'wa.me', 'whatsapp.com', 't.me', 'telegram.me', 'telegram.org',
    'instagram.com', 'facebook.com', 'fb.me', 'twitter.com',
    'snapchat.com', 'tiktok.com', 'discord.gg', 'discord.com',
    'signal.org', 'threema.ch', 'line.me', 'wechat.com',
    'viber.com', 'kik.com', 'skype.com', 'zoom.us'
}

# URL-related indicators for context
URL_INDICATORS = [
    r'\b(?:check\s+out|visit|go\s+to|see|view|click|open)\b',
    r'\b(?:link|url|website|site)\s*(?:is|:)?\b',
    r'\b(?:my|the)\s+(?:link|url|website|site|page)\b',
]


class URLDetector:
    """Detects URLs in various formats and obfuscations."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for URL detection."""

        # Full URLs with protocol: https://example.com/path
        self.full_url_pattern = re.compile(
            r'\b(?:https?|ftp)://'  # Protocol
            r'(?:[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)',  # Rest of URL
            re.IGNORECASE
        )

        # URLs without protocol: example.com, www.example.com
        self.no_protocol_pattern = re.compile(
            r'\b(?:www\.)?'  # Optional www
            r'[a-zA-Z0-9\-]+\.'  # Domain name
            r'[a-zA-Z]{2,}'  # TLD
            r'(?:/[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]*)?',  # Optional path
            re.IGNORECASE
        )

        # Link shorteners (more specific pattern)
        shortener_domains = '|'.join(
            re.escape(domain.replace('.', r'\.'))
            for domain in SHORTENER_DOMAINS
        )
        self.shortener_pattern = re.compile(
            rf'\b(?:https?://)?(?:www\.)?(?:{shortener_domains})'
            r'(?:/[a-zA-Z0-9\-_]+)?',
            re.IGNORECASE
        )

        # Social platform URLs (specific)
        social_domains = '|'.join(
            re.escape(domain.replace('.', r'\.'))
            for domain in SOCIAL_DOMAINS
        )
        self.social_url_pattern = re.compile(
            rf'\b(?:https?://)?(?:www\.)?(?:{social_domains})'
            r'(?:/[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]*)?',
            re.IGNORECASE
        )

        # Domain mentions: "go to example dot com"
        self.domain_mention_pattern = re.compile(
            r'\b[a-zA-Z0-9\-]+\s+dot\s+[a-zA-Z]{2,}\b'
            r'(?:\s+(?:slash|/)\s+[a-zA-Z0-9\-_]+)?',
            re.IGNORECASE
        )

        # Obfuscated URLs: "check out b1t(dot)ly slash abc"
        self.obfuscated_url_pattern = re.compile(
            r'\b[a-zA-Z0-9\-]+\s*[\(\[\{]?\s*dot\s*[\)\]\}]?\s*[a-zA-Z]{2,}'
            r'(?:\s*[\(\[\{]?\s*(?:slash|/)\s*[\)\]\}]?\s*[a-zA-Z0-9\-_]+)?',
            re.IGNORECASE
        )

        # Heavily obfuscated: "example[.]com/path"
        self.bracket_dot_pattern = re.compile(
            r'\b[a-zA-Z0-9\-]+[\[\(]\s*\.\s*[\]\)][a-zA-Z]{2,}'
            r'(?:[/\\\[\]\(\)][\[\(\s]*[a-zA-Z0-9\-._~:/?#@!$&\'*+,;=%]*)?',
            re.IGNORECASE
        )

        # Context patterns for confidence boosting
        self.context_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in URL_INDICATORS
        ]

        # Common TLDs for validation
        self.common_tlds = {
            'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
            'co', 'io', 'ai', 'app', 'dev', 'tech', 'info',
            'biz', 'name', 'pro', 'mobi', 'tel', 'travel',
            'uk', 'us', 'ca', 'au', 'de', 'fr', 'jp', 'cn',
            'ru', 'br', 'in', 'it', 'es', 'nl', 'se', 'no',
            'me', 'tv', 'cc', 'ws', 'be', 'at', 'ch', 'dk'
        }

    def _has_url_context(self, text: str, match_pos: int, window: int = 30) -> bool:
        """Check if there's URL-related context near the match."""
        start = max(0, match_pos - window)
        end = min(len(text), match_pos + window)
        context = text[start:end]

        for pattern in self.context_patterns:
            if pattern.search(context):
                return True
        return False

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        # Remove protocol
        url = re.sub(r'^(?:https?|ftp)://', '', url, flags=re.IGNORECASE)

        # Remove www
        url = re.sub(r'^www\.', '', url, flags=re.IGNORECASE)

        # Get domain part (before first slash or end)
        domain = url.split('/')[0]

        return domain.lower()

    def _extract_tld(self, domain: str) -> str:
        """Extract TLD from domain."""
        # Normalize obfuscation
        domain = domain.lower()
        domain = re.sub(r'\s*dot\s*', '.', domain)
        domain = re.sub(r'[\[\]\(\)]', '', domain)

        parts = domain.split('.')
        if parts:
            return parts[-1].strip()
        return ''

    def _is_valid_tld(self, tld: str) -> bool:
        """Check if TLD is valid."""
        tld = tld.lower().strip()
        return tld in self.common_tlds or (len(tld) >= 2 and tld.isalpha())

    def _is_shortener(self, domain: str) -> bool:
        """Check if domain is a known URL shortener."""
        domain = domain.lower().strip()
        return domain in SHORTENER_DOMAINS

    def _is_social_platform(self, domain: str) -> bool:
        """Check if domain is a known social platform."""
        domain = domain.lower().strip()
        return domain in SOCIAL_DOMAINS

    def _normalize_url(self, text: str) -> str:
        """Normalize obfuscated URL to standard format."""
        normalized = text.lower()

        # Replace "dot" with .
        normalized = re.sub(r'\s*[\[\(]?\s*dot\s*[\]\)]?\s*', '.', normalized)

        # Replace "slash" with /
        normalized = re.sub(r'\s*[\[\(]?\s*slash\s*[\]\)]?\s*', '/', normalized)

        # Remove extra spaces around special chars
        normalized = re.sub(r'\s*([./:])\s*', r'\1', normalized)

        return normalized

    def _calculate_confidence(self, match_text: str, full_text: str,
                             match_pos: int, pattern_type: str) -> float:
        """Calculate confidence score for a URL match."""
        confidence = 0.5  # Base confidence

        # Normalize to extract domain
        normalized = self._normalize_url(match_text)
        domain = self._extract_domain(normalized)
        tld = self._extract_tld(domain)

        # Boost for valid TLD
        if self._is_valid_tld(tld):
            confidence += 0.15

        # Boost for known shortener (high indicator)
        if self._is_shortener(domain):
            confidence += 0.25

        # Boost for known social platform (high indicator)
        if self._is_social_platform(domain):
            confidence += 0.25

        # Boost for full URL with protocol
        if pattern_type == 'full':
            confidence += 0.15

        # Boost for obfuscation (indicates intent to hide)
        if pattern_type in ['obfuscated', 'bracket', 'mention']:
            confidence += 0.15

        # Boost for URL context nearby
        if self._has_url_context(full_text, match_pos):
            confidence += 0.1

        # Penalize very short domains (likely false positive)
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2 and len(domain_parts[-2]) < 2:
            confidence -= 0.2

        # Penalize if looks like an email
        if '@' in match_text:
            confidence -= 0.5

        return max(0.0, min(1.0, confidence))

    def detect_full_urls(self, text: str) -> List[PatternMatch]:
        """Detect full URLs with protocol."""
        matches = []
        for match in self.full_url_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'full'
            )

            if confidence > 0.3:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='url',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_no_protocol(self, text: str) -> List[PatternMatch]:
        """Detect URLs without protocol."""
        matches = []
        for match in self.no_protocol_pattern.finditer(text):
            matched_text = match.group(0)

            # Filter out common false positives
            domain = self._extract_domain(matched_text)
            tld = self._extract_tld(domain)

            # Require valid TLD or known domain
            if not (self._is_valid_tld(tld) or
                    self._is_shortener(domain) or
                    self._is_social_platform(domain)):
                continue

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'no_protocol'
            )

            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='url',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_shorteners(self, text: str) -> List[PatternMatch]:
        """Detect known URL shortener links."""
        matches = []
        for match in self.shortener_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'shortener'
            )

            # High confidence for shorteners
            confidence = min(1.0, confidence + 0.1)

            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='url',
                confidence=confidence,
                value=matched_text
            ))
        return matches

    def detect_social_urls(self, text: str) -> List[PatternMatch]:
        """Detect social platform URLs."""
        matches = []
        for match in self.social_url_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'social'
            )

            # High confidence for social platform URLs
            confidence = min(1.0, confidence + 0.1)

            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='url',
                confidence=confidence,
                value=matched_text
            ))
        return matches

    def detect_domain_mentions(self, text: str) -> List[PatternMatch]:
        """Detect domain mentions with 'dot' spelled out."""
        matches = []
        for match in self.domain_mention_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'mention'
            )

            if confidence > 0.4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='url',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_obfuscated(self, text: str) -> List[PatternMatch]:
        """Detect obfuscated URLs."""
        matches = []
        for match in self.obfuscated_url_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'obfuscated'
            )

            if confidence > 0.5:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='url',
                    confidence=confidence,
                    value=matched_text
                ))
        return matches

    def detect_bracket_obfuscation(self, text: str) -> List[PatternMatch]:
        """Detect bracket-obfuscated URLs."""
        matches = []
        for match in self.bracket_dot_pattern.finditer(text):
            matched_text = match.group(0)

            confidence = self._calculate_confidence(
                matched_text, text, match.start(), 'bracket'
            )

            if confidence > 0.5:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='url',
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
    Run all URL detection patterns against the text.

    Args:
        text: Input text to scan for URLs

    Returns:
        List of PatternMatch objects for detected URLs,
        deduplicated and sorted by offset
    """
    detector = URLDetector()

    all_matches = []
    all_matches.extend(detector.detect_full_urls(text))
    all_matches.extend(detector.detect_shorteners(text))
    all_matches.extend(detector.detect_social_urls(text))
    all_matches.extend(detector.detect_no_protocol(text))
    all_matches.extend(detector.detect_domain_mentions(text))
    all_matches.extend(detector.detect_obfuscated(text))
    all_matches.extend(detector.detect_bracket_obfuscation(text))

    return _deduplicate_matches(all_matches)
