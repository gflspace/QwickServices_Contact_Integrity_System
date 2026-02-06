"""
Intent phrase detection for Contact Integrity System.

This module detects phrases indicating intent to share contact information
or move communication off-platform. Designed for production use with
high precision and recall.
"""

import re
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class PatternMatch:
    """Represents a detected pattern match in text."""
    offset: int
    length: int
    type: str
    confidence: float
    value: str


# Intent phrase categories with patterns and confidence modifiers
INTENT_CATEGORIES = {
    'direct_request': {
        'patterns': [
            # Asking for contact info
            r'\b(?:give|send|share|tell)\s+(?:me\s+)?(?:your|ur|u)\s+(?:number|phone|email|contact)\b',
            r'\b(?:what\'?s|whats)\s+(?:your|ur|u)\s+(?:number|phone|email|contact|whatsapp|insta|snap)\b',
            r'\bcan\s+(?:i\s+)?(?:get|have)\s+(?:your|ur|u)\s+(?:number|phone|email|contact)\b',
            r'\bgimme\s+(?:your|ur|u)\s+(?:number|phone|email|contact|digits)\b',
            r'\bhow\s+(?:can|do)\s+(?:i|we)\s+(?:contact|reach)\s+(?:you|u)\b',
            r'\bdo\s+(?:you|u)\s+have\s+(?:whatsapp|telegram|insta|snap|discord)\b',
        ],
        'confidence_boost': 0.3,
    },
    'suggestion_off_platform': {
        'patterns': [
            # Suggesting to move communication
            r'\blet\'?s\s+(?:take\s+this\s+)?(?:chat|talk|conversation|continue|move)\s+(?:off|outside|offline)\b',
            r'\blet\'?s\s+(?:talk|chat|discuss|continue)\s+(?:offline|privately|off[-\s]?platform)\b',
            r'\btake\s+this\s+(?:conversation|chat|discussion)\s+(?:offline|off[-\s]?platform|elsewhere|outside)\b',
            r'\bmessage\s+me\s+(?:directly|privately|outside|elsewhere|off\s+here)\b',
            r'\bcontact\s+me\s+(?:directly|privately|outside|elsewhere|off\s+here)\b',
            r'\btext\s+me\s+(?:directly|privately|outside|elsewhere|instead)\b',
            r'\breply\s+(?:directly|privately|off\s+here)\b',
            r'\breply\s+(?:to\s+)?(?:my\s+)?(?:dm|message|text)\b',
        ],
        'confidence_boost': 0.25,
    },
    'contact_sharing': {
        'patterns': [
            # Offering/sharing contact info
            r'\bhere\'?s\s+(?:my\s+)?(?:number|phone|email|contact|info|whatsapp|telegram|insta|snap)\b',
            r'\bmy\s+(?:number|phone|email|contact)\s+(?:is|:)\b',
            r'\b(?:reach|contact|find|add)\s+(?:me\s+)?(?:at|on|via)\b',
            r'\b(?:call|text|email|message)\s+me\s+at\b',
            r'\bget\s+(?:in\s+touch|back\s+to\s+me)\s+(?:at|on|via)\b',
            r'\bi\'?m\s+(?:available\s+)?(?:at|on)\s+(?:whatsapp|telegram|insta|snap|discord)\b',
            r'\byou\s+can\s+(?:reach|contact|find|text|call|message|dm)\s+me\b',
        ],
        'confidence_boost': 0.25,
    },
    'platform_evasion': {
        'patterns': [
            # Avoiding platform monitoring
            r'\b(?:so|because)\s+(?:we\s+)?(?:don\'?t|dont|wont|won\'t)\s+(?:have\s+to\s+)?(?:use|stay\s+on)\s+(?:this|here)\b',
            r'\boutside\s+(?:of\s+)?(?:this|here|the\s+app|the\s+platform|the\s+site)\b',
            r'\bnot\s+(?:on|through)\s+(?:this|here|the\s+app|the\s+platform)\b',
            r'\b(?:bypass|avoid|skip)\s+(?:this|the\s+app|the\s+platform|the\s+chat)\b',
            r'\bthis\s+(?:app|platform|site|chat)\s+(?:is\s+)?(?:not\s+good|slow|bad|annoying)\b',
            r'\bwithout\s+(?:using\s+)?(?:this|the\s+app|the\s+platform|the\s+site)\b',
            r'\boff\s+(?:of\s+)?(?:this|here|the\s+app|the\s+platform)\b',
        ],
        'confidence_boost': 0.3,
    },
    'coded_language': {
        'patterns': [
            # Slang/coded requests
            r'\bdrop\s+(?:me\s+)?(?:your|ur|u)\s+(?:digits|deets|info|contacts?)\b',
            r'\bslide\s+(?:into\s+)?(?:my\s+)?(?:dms?|inbox|messages?)\b',
            r'\bhit\s+(?:me\s+)?(?:up|back)\b',
            r'\bhmu\b',  # hit me up
            r'\bsend\s+(?:me\s+)?(?:a\s+)?dm\b',
            r'\bcheck\s+(?:your|ur|u)\s+(?:dms?|inbox|messages?)\b',
            r'\bhit\s+(?:my\s+)?(?:line|dm|inbox)\b',
            r'\bping\s+me\b',
            r'\bholla\s+(?:at\s+me|back)\b',
        ],
        'confidence_boost': 0.2,
    },
    'exchange_coordination': {
        'patterns': [
            # Coordinating information exchange
            r'\bi\'?ll\s+(?:send|share|give|dm)\s+(?:you|u)\s+(?:my\s+)?(?:number|contact|info|details)\b',
            r'\bcan\s+(?:you|u)\s+(?:send|share|give|dm)\s+(?:me\s+)?(?:your|ur)\s+(?:number|contact|info)\b',
            r'\blet\'?s\s+exchange\s+(?:numbers|contacts|info|details)\b',
            r'\bwanna\s+exchange\s+(?:numbers|contacts|info|details)\b',
            r'\bshare\s+(?:your|ur|my)\s+(?:number|contact|info|details)\s+(?:with\s+)?(?:me|you|u)\b',
            r'\bgive\s+(?:me|you|u)\s+(?:your|my|ur)\s+(?:real\s+)?(?:number|contact|email)\b',
        ],
        'confidence_boost': 0.25,
    },
    'privacy_language': {
        'patterns': [
            # Privacy/discretion mentions
            r'\b(?:let\'?s\s+)?(?:talk|chat|discuss)\s+(?:more\s+)?(?:privately|in\s+private)\b',
            r'\bthis\s+is\s+(?:too\s+)?(?:public|open)\b',
            r'\b(?:want|need)\s+(?:more\s+)?privacy\b',
            r'\bsomewhere\s+(?:more\s+)?(?:private|secure|discreet)\b',
            r'\bdiscretely?\b',
            r'\b(?:between|just)\s+(?:us|you\s+and\s+me)\b',
        ],
        'confidence_boost': 0.2,
    },
    'urgency_pressure': {
        'patterns': [
            # Creating urgency/pressure
            r'\bquick(?:ly)?\s+(?:give|send|share|tell)\s+me\b',
            r'\bneed\s+(?:to\s+)?(?:contact|reach|talk\s+to)\s+(?:you|u)\s+(?:asap|urgently|now|quickly)\b',
            r'\bright\s+now\b',
            r'\basap\b',
            r'\burgent(?:ly)?\b',
            r'\btime\s+sensitive\b',
            r'\bbefore\s+(?:this\s+)?(?:expires|closes|ends)\b',
        ],
        'confidence_boost': 0.15,
    },
}

# Context boosters - these increase confidence when found near intent phrases
CONTEXT_BOOSTERS = {
    'contact_terms': [
        'number', 'phone', 'email', 'contact', 'whatsapp', 'telegram',
        'instagram', 'snapchat', 'discord', 'signal', 'digits', 'info'
    ],
    'platform_terms': [
        'off platform', 'outside', 'privately', 'offline', 'directly',
        'app', 'site', 'chat', 'here'
    ],
    'action_terms': [
        'reach', 'contact', 'message', 'text', 'call', 'dm', 'ping',
        'reply', 'respond', 'get back', 'hit up'
    ],
}


class IntentDetector:
    """Detects phrases indicating intent to share contact information."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for intent detection."""
        self.category_patterns: Dict[str, Dict] = {}

        for category, config in INTENT_CATEGORIES.items():
            self.category_patterns[category] = {
                'patterns': [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in config['patterns']
                ],
                'confidence_boost': config['confidence_boost'],
            }

        # Compile context booster patterns
        self.context_booster_patterns = {}
        for category, terms in CONTEXT_BOOSTERS.items():
            self.context_booster_patterns[category] = re.compile(
                r'\b(?:' + '|'.join(re.escape(term) for term in terms) + r')\b',
                re.IGNORECASE
            )

    def _check_context_boosters(self, text: str, match_pos: int, window: int = 50) -> float:
        """Check for context boosters near the match and return confidence adjustment."""
        start = max(0, match_pos - window)
        end = min(len(text), match_pos + window)
        context = text[start:end]

        boost = 0.0
        for category, pattern in self.context_booster_patterns.items():
            if pattern.search(context):
                if category == 'contact_terms':
                    boost += 0.15
                elif category == 'platform_terms':
                    boost += 0.10
                elif category == 'action_terms':
                    boost += 0.05

        return min(0.3, boost)  # Cap total boost

    def _has_negation_nearby(self, text: str, match_pos: int, window: int = 20) -> bool:
        """Check if there's negation near the match that might invalidate it."""
        start = max(0, match_pos - window)
        context = text[start:match_pos]

        negation_patterns = [
            r'\bdon\'?t\b', r'\bdoesn\'?t\b', r'\bwon\'?t\b', r'\bwouldn\'?t\b',
            r'\bshouldn\'?t\b', r'\bnever\b', r'\bnot\b', r'\bno\b'
        ]

        for pattern in negation_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        return False

    def _calculate_confidence(self, match_text: str, full_text: str,
                             match_pos: int, category: str,
                             base_confidence: float) -> float:
        """Calculate final confidence score for an intent match."""
        confidence = base_confidence

        # Get category boost
        if category in self.category_patterns:
            confidence += self.category_patterns[category]['confidence_boost']

        # Check for context boosters
        context_boost = self._check_context_boosters(full_text, match_pos)
        confidence += context_boost

        # Penalize if negation is nearby
        if self._has_negation_nearby(full_text, match_pos):
            confidence -= 0.3

        # Boost for multiple contact types mentioned
        contact_types = ['number', 'phone', 'email', 'whatsapp', 'telegram',
                        'instagram', 'snapchat', 'discord', 'signal']
        window_start = max(0, match_pos - 50)
        window_end = min(len(full_text), match_pos + len(match_text) + 50)
        window = full_text[window_start:window_end].lower()

        contact_count = sum(1 for term in contact_types if term in window)
        if contact_count >= 2:
            confidence += 0.1

        # Boost for explicit platform evasion language
        evasion_terms = ['off platform', 'outside of here', 'not here',
                        'bypass', 'without using this']
        if any(term in window for term in evasion_terms):
            confidence += 0.15

        return max(0.0, min(1.0, confidence))

    def detect_category(self, text: str, category: str) -> List[PatternMatch]:
        """Detect intent phrases for a specific category."""
        matches = []

        if category not in self.category_patterns:
            return matches

        patterns = self.category_patterns[category]['patterns']

        for pattern in patterns:
            for match in pattern.finditer(text):
                matched_text = match.group(0)

                # Base confidence depends on category
                base_confidence = 0.5

                confidence = self._calculate_confidence(
                    matched_text, text, match.start(), category, base_confidence
                )

                # Only include matches above threshold
                if confidence > 0.4:
                    matches.append(PatternMatch(
                        offset=match.start(),
                        length=len(matched_text),
                        type='intent',
                        confidence=confidence,
                        value=matched_text
                    ))

        return matches

    def detect_compound_intent(self, text: str) -> List[PatternMatch]:
        """
        Detect compound intent patterns where multiple signals appear together.
        This catches cases where individual phrases might be weak but together
        indicate strong intent.
        """
        matches = []

        # Look for sentences with multiple intent signals
        sentences = re.split(r'[.!?]\s+', text)
        offset = 0

        for sentence in sentences:
            intent_count = 0
            categories_found = []

            # Check each category in this sentence
            for category, config in self.category_patterns.items():
                for pattern in config['patterns']:
                    if pattern.search(sentence):
                        intent_count += 1
                        categories_found.append(category)
                        break  # Count category once per sentence

            # If multiple intent signals in one sentence, create a compound match
            if intent_count >= 2:
                confidence = min(0.95, 0.6 + (intent_count * 0.15))

                matches.append(PatternMatch(
                    offset=offset,
                    length=len(sentence),
                    type='intent',
                    confidence=confidence,
                    value=f"compound:{','.join(set(categories_found))}"
                ))

            offset += len(sentence) + 1  # +1 for the separator

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
    Run all intent phrase detection patterns against the text.

    Args:
        text: Input text to scan for intent phrases

    Returns:
        List of PatternMatch objects for detected intent phrases,
        deduplicated and sorted by offset
    """
    detector = IntentDetector()

    all_matches = []

    # Detect each category
    for category in INTENT_CATEGORIES.keys():
        all_matches.extend(detector.detect_category(text, category))

    # Detect compound intent patterns
    all_matches.extend(detector.detect_compound_intent(text))

    return _deduplicate_matches(all_matches)
