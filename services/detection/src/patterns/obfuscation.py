"""
Unicode deobfuscation and detection patterns for Contact Integrity System.

This module handles detection and normalization of various text obfuscation
techniques including homoglyphs, zero-width characters, combining marks,
fullwidth characters, and leet speak. Designed for production use.
"""

import re
import unicodedata
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


# Zero-width and invisible characters
ZERO_WIDTH_CHARS = {
    '\u200B': 'ZWSP',  # Zero Width Space
    '\u200C': 'ZWNJ',  # Zero Width Non-Joiner
    '\u200D': 'ZWJ',   # Zero Width Joiner
    '\u200E': 'LRM',   # Left-to-Right Mark
    '\u200F': 'RLM',   # Right-to-Left Mark
    '\uFEFF': 'BOM',   # Zero Width No-Break Space (BOM)
    '\u2060': 'WJ',    # Word Joiner
    '\u2061': 'FA',    # Function Application
    '\u2062': 'IT',    # Invisible Times
    '\u2063': 'IS',    # Invisible Separator
    '\u2064': 'IP',    # Invisible Plus
    '\u206A': 'ISS',   # Inhibit Symmetric Swapping
    '\u206B': 'ASS',   # Activate Symmetric Swapping
    '\u206C': 'IAFS',  # Inhibit Arabic Form Shaping
    '\u206D': 'AAFS',  # Activate Arabic Form Shaping
    '\u206E': 'NADS',  # National Digit Shapes
    '\u206F': 'NODS',  # Nominal Digit Shapes
}

# Homoglyphs: characters that look alike but have different code points
HOMOGLYPH_MAP = {
    # Cyrillic -> Latin
    '\u0430': 'a',  # а -> a
    '\u0435': 'e',  # е -> e
    '\u043e': 'o',  # о -> o
    '\u0440': 'p',  # р -> p
    '\u0441': 'c',  # с -> c
    '\u0443': 'y',  # у -> y
    '\u0445': 'x',  # х -> x
    '\u0455': 's',  # ѕ -> s
    '\u0456': 'i',  # і -> i
    '\u0458': 'j',  # ј -> j
    '\u04bb': 'h',  # һ -> h
    '\u0405': 'S',  # Ѕ -> S
    '\u0406': 'I',  # І -> I
    '\u0408': 'J',  # Ј -> J
    '\u0410': 'A',  # А -> A
    '\u0412': 'B',  # В -> B
    '\u0415': 'E',  # Е -> E
    '\u041a': 'K',  # К -> K
    '\u041c': 'M',  # М -> M
    '\u041d': 'H',  # Н -> H
    '\u041e': 'O',  # О -> O
    '\u0420': 'P',  # Р -> P
    '\u0421': 'C',  # С -> C
    '\u0422': 'T',  # Т -> T
    '\u0425': 'X',  # Х -> X
    '\u0405': 'S',  # Ѕ -> S

    # Greek -> Latin
    '\u03b1': 'a',  # α -> a
    '\u03b5': 'e',  # ε -> e
    '\u03b9': 'i',  # ι -> i
    '\u03bf': 'o',  # ο -> o
    '\u03c1': 'p',  # ρ -> p
    '\u03c5': 'u',  # υ -> u
    '\u03c7': 'x',  # χ -> x
    '\u0391': 'A',  # Α -> A
    '\u0392': 'B',  # Β -> B
    '\u0395': 'E',  # Ε -> E
    '\u0397': 'H',  # Η -> H
    '\u0399': 'I',  # Ι -> I
    '\u039a': 'K',  # Κ -> K
    '\u039c': 'M',  # Μ -> M
    '\u039d': 'N',  # Ν -> N
    '\u039f': 'O',  # Ο -> O
    '\u03a1': 'P',  # Ρ -> P
    '\u03a4': 'T',  # Τ -> T
    '\u03a5': 'Y',  # Υ -> Y
    '\u03a7': 'X',  # Χ -> X
    '\u0396': 'Z',  # Ζ -> Z

    # Mathematical Bold -> Latin
    '\U0001d41a': 'A',
    '\U0001d41b': 'B',
    '\U0001d41c': 'C',
    '\U0001d41d': 'D',
    '\U0001d41e': 'E',

    # Other confusables
    '\u0131': 'i',  # ı (dotless i)
    '\u0237': 'j',  # ȷ (dotless j)
}

# Fullwidth character mappings (U+FF00 to U+FF5E range)
FULLWIDTH_START = 0xFF01
FULLWIDTH_END = 0xFF5E
FULLWIDTH_OFFSET = 0xFF00 - 0x20

# Leet speak mappings (common substitutions)
LEET_SPEAK_MAP = {
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '8': 'b',
    '9': 'g',
    '@': 'a',
    '$': 's',
    '!': 'i',
    '|': 'i',
    '(': 'c',
    '[': 'c',
    '<': 'c',
}


class ObfuscationDetector:
    """Detects and normalizes text obfuscation techniques."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for obfuscation detection."""

        # Pattern for detecting multiple zero-width chars
        zero_width_chars = ''.join(ZERO_WIDTH_CHARS.keys())
        self.zero_width_pattern = re.compile(f'[{re.escape(zero_width_chars)}]+')

        # Pattern for detecting fullwidth characters
        self.fullwidth_pattern = re.compile(
            f'[{chr(FULLWIDTH_START)}-{chr(FULLWIDTH_END)}]+'
        )

        # Pattern for detecting combining diacritical marks
        # Unicode categories: Mn (Nonspacing Mark), Mc (Spacing Mark), Me (Enclosing Mark)
        self.combining_marks_pattern = re.compile(r'[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]+')

        # Pattern for detecting excessive leet speak
        self.leet_pattern = re.compile(r'\b\w*[0-9@$!|()[\]<>]{2,}\w*\b')

        # Pattern for mixed script detection (Latin + Cyrillic/Greek)
        self.cyrillic_in_latin = re.compile(r'[a-zA-Z]+[\u0400-\u04ff]+[a-zA-Z]*|[\u0400-\u04ff]+[a-zA-Z]+')
        self.greek_in_latin = re.compile(r'[a-zA-Z]+[\u0370-\u03ff]+[a-zA-Z]*|[\u0370-\u03ff]+[a-zA-Z]+')

    def remove_zero_width_chars(self, text: str) -> str:
        """Remove zero-width and invisible characters."""
        for char in ZERO_WIDTH_CHARS.keys():
            text = text.replace(char, '')
        return text

    def normalize_homoglyphs(self, text: str) -> str:
        """Replace homoglyphs with their Latin equivalents."""
        for original, replacement in HOMOGLYPH_MAP.items():
            text = text.replace(original, replacement)
        return text

    def normalize_fullwidth(self, text: str) -> str:
        """Convert fullwidth characters to normal ASCII."""
        result = []
        for char in text:
            code = ord(char)
            if FULLWIDTH_START <= code <= FULLWIDTH_END:
                # Convert to normal ASCII
                result.append(chr(code - FULLWIDTH_OFFSET))
            else:
                result.append(char)
        return ''.join(result)

    def remove_combining_marks(self, text: str) -> str:
        """Remove combining diacritical marks."""
        # Normalize to NFD (decomposed form)
        nfd = unicodedata.normalize('NFD', text)
        # Remove combining marks
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    def normalize_leet_speak(self, text: str) -> str:
        """Normalize leet speak substitutions."""
        result = []
        for char in text:
            if char in LEET_SPEAK_MAP:
                result.append(LEET_SPEAK_MAP[char])
            else:
                result.append(char)
        return ''.join(result)

    def detect_zero_width_chars(self, text: str) -> List[PatternMatch]:
        """Detect zero-width character sequences."""
        matches = []
        for match in self.zero_width_pattern.finditer(text):
            matched_text = match.group(0)
            char_types = [ZERO_WIDTH_CHARS.get(c, 'UNKNOWN') for c in matched_text]

            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='obfuscation',
                confidence=0.95,  # High confidence for zero-width chars
                value=f"zero_width:{','.join(char_types)}"
            ))
        return matches

    def detect_homoglyphs(self, text: str) -> List[PatternMatch]:
        """Detect homoglyph usage."""
        matches = []

        # Check for homoglyphs character by character
        i = 0
        while i < len(text):
            if text[i] in HOMOGLYPH_MAP:
                # Found a homoglyph, extend to find consecutive homoglyphs
                start = i
                while i < len(text) and (
                    text[i] in HOMOGLYPH_MAP or
                    text[i].isalnum() or
                    text[i] in '._-@'
                ):
                    i += 1

                matched_text = text[start:i]
                # Only report if there's actual obfuscation (contains homoglyph)
                if any(c in HOMOGLYPH_MAP for c in matched_text):
                    matches.append(PatternMatch(
                        offset=start,
                        length=len(matched_text),
                        type='obfuscation',
                        confidence=0.85,
                        value=f"homoglyph:{matched_text}"
                    ))
            else:
                i += 1

        return matches

    def detect_mixed_scripts(self, text: str) -> List[PatternMatch]:
        """Detect mixed script usage (e.g., Latin + Cyrillic)."""
        matches = []

        # Detect Cyrillic mixed with Latin
        for match in self.cyrillic_in_latin.finditer(text):
            matched_text = match.group(0)
            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='obfuscation',
                confidence=0.90,
                value=f"mixed_script:cyrillic:{matched_text}"
            ))

        # Detect Greek mixed with Latin
        for match in self.greek_in_latin.finditer(text):
            matched_text = match.group(0)
            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='obfuscation',
                confidence=0.90,
                value=f"mixed_script:greek:{matched_text}"
            ))

        return matches

    def detect_fullwidth(self, text: str) -> List[PatternMatch]:
        """Detect fullwidth character usage."""
        matches = []
        for match in self.fullwidth_pattern.finditer(text):
            matched_text = match.group(0)
            matches.append(PatternMatch(
                offset=match.start(),
                length=len(matched_text),
                type='obfuscation',
                confidence=0.80,
                value=f"fullwidth:{matched_text}"
            ))
        return matches

    def detect_combining_marks(self, text: str) -> List[PatternMatch]:
        """Detect excessive combining diacritical marks."""
        matches = []

        # Find sequences with combining marks
        i = 0
        while i < len(text):
            if unicodedata.category(text[i]) in ['Mn', 'Mc', 'Me']:
                # Found combining mark, look for the base char and all combining marks
                start = max(0, i - 1)  # Include base character
                while i < len(text) and unicodedata.category(text[i]) in ['Mn', 'Mc', 'Me']:
                    i += 1

                matched_text = text[start:i]
                # Only report if there are multiple combining marks
                mark_count = sum(1 for c in matched_text if unicodedata.category(c) in ['Mn', 'Mc', 'Me'])
                if mark_count >= 2:
                    matches.append(PatternMatch(
                        offset=start,
                        length=len(matched_text),
                        type='obfuscation',
                        confidence=0.75,
                        value=f"combining_marks:{mark_count}"
                    ))
            else:
                i += 1

        return matches

    def detect_leet_speak(self, text: str) -> List[PatternMatch]:
        """Detect leet speak patterns."""
        matches = []
        for match in self.leet_pattern.finditer(text):
            matched_text = match.group(0)

            # Calculate confidence based on leet char density
            leet_chars = sum(1 for c in matched_text if c in LEET_SPEAK_MAP)
            total_chars = len(matched_text)
            leet_ratio = leet_chars / total_chars if total_chars > 0 else 0

            # Only report if there's significant leet speak
            if leet_ratio > 0.2:
                confidence = min(0.9, 0.5 + leet_ratio * 0.5)
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='obfuscation',
                    confidence=confidence,
                    value=f"leet_speak:{matched_text}"
                ))

        return matches

    def detect_unusual_spacing(self, text: str) -> List[PatternMatch]:
        """Detect unusual spacing patterns (e.g., 'h e l l o')."""
        matches = []

        # Pattern: single char followed by space, repeated
        spaced_pattern = re.compile(r'\b(\w\s){3,}\w\b')

        for match in spaced_pattern.finditer(text):
            matched_text = match.group(0)
            # Remove spaces to check if it forms a word
            unspaced = matched_text.replace(' ', '')

            # Check if it's suspiciously spaced
            if len(unspaced) >= 4:
                matches.append(PatternMatch(
                    offset=match.start(),
                    length=len(matched_text),
                    type='obfuscation',
                    confidence=0.70,
                    value=f"unusual_spacing:{matched_text}"
                ))

        return matches


def deobfuscate(text: str) -> str:
    """
    Apply all deobfuscation techniques to normalize text.

    This function should be applied to text before pattern matching
    to improve detection of obfuscated contact information.

    Args:
        text: Input text to deobfuscate

    Returns:
        Normalized text with obfuscation removed
    """
    detector = ObfuscationDetector()

    # Apply deobfuscation in order
    text = detector.remove_zero_width_chars(text)
    text = detector.normalize_homoglyphs(text)
    text = detector.normalize_fullwidth(text)
    text = detector.remove_combining_marks(text)
    text = detector.normalize_leet_speak(text)

    # Apply Unicode normalization (NFKC - compatibility composition)
    text = unicodedata.normalize('NFKC', text)

    return text


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


def detect_obfuscation(text: str) -> List[PatternMatch]:
    """
    Detect obfuscation techniques in text.

    This function identifies various obfuscation methods without
    modifying the original text.

    Args:
        text: Input text to scan for obfuscation

    Returns:
        List of PatternMatch objects for detected obfuscation,
        deduplicated and sorted by offset
    """
    detector = ObfuscationDetector()

    all_matches = []
    all_matches.extend(detector.detect_zero_width_chars(text))
    all_matches.extend(detector.detect_homoglyphs(text))
    all_matches.extend(detector.detect_mixed_scripts(text))
    all_matches.extend(detector.detect_fullwidth(text))
    all_matches.extend(detector.detect_combining_marks(text))
    all_matches.extend(detector.detect_leet_speak(text))
    all_matches.extend(detector.detect_unusual_spacing(text))

    return _deduplicate_matches(all_matches)


def detect(text: str) -> List[PatternMatch]:
    """
    Run all obfuscation detection patterns against the text.

    Alias for detect_obfuscation() to maintain consistent interface
    across all pattern modules.

    Args:
        text: Input text to scan for obfuscation

    Returns:
        List of PatternMatch objects for detected obfuscation,
        deduplicated and sorted by offset
    """
    return detect_obfuscation(text)
