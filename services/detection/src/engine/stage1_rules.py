"""Stage 1: Deterministic rules engine — regex/pattern-based detection."""

from __future__ import annotations

import hashlib

from ..models import EvidenceSpan, EvidenceType, StageResult
from ..patterns.phone import detect as detect_phone
from ..patterns.email import detect as detect_email
from ..patterns.url import detect as detect_url
from ..patterns.social import detect as detect_social
from ..patterns.obfuscation import detect_obfuscation, deobfuscate
from ..patterns.intent_phrases import detect as detect_intent


# Map pattern types to evidence types
_TYPE_MAP = {
    "phone": EvidenceType.PHONE,
    "email": EvidenceType.EMAIL,
    "url": EvidenceType.URL,
    "social": EvidenceType.SOCIAL,
    "intent": EvidenceType.INTENT,
    "obfuscation": EvidenceType.OBFUSCATION,
}

# Score contribution by detection type
_TYPE_WEIGHT = {
    "phone": 0.85,
    "email": 0.80,
    "url": 0.50,
    "social": 0.75,
    "intent": 0.35,
    "obfuscation": 0.15,  # Obfuscation alone is just a signal
}


def run_stage1(text: str) -> StageResult:
    """Run all deterministic pattern detections against the text.

    1. First deobfuscate the text (normalize unicode tricks).
    2. Run pattern detectors on both original and deobfuscated text.
    3. Combine results, dedup, and compute a score.
    """
    labels: list[str] = []
    evidence: list[EvidenceSpan] = []
    hashed_tokens: list[str] = []

    # Check for obfuscation first
    obfuscation_matches = detect_obfuscation(text)
    has_obfuscation = len(obfuscation_matches) > 0

    # Deobfuscate for pattern matching
    clean_text = deobfuscate(text)

    # Run all pattern detectors on original text
    all_matches = []
    all_matches.extend(detect_phone(text))
    all_matches.extend(detect_email(text))
    all_matches.extend(detect_url(text))
    all_matches.extend(detect_social(text))
    all_matches.extend(detect_intent(text))

    # If text was obfuscated, also run on clean version
    if clean_text != text:
        all_matches.extend(detect_phone(clean_text))
        all_matches.extend(detect_email(clean_text))
        all_matches.extend(detect_url(clean_text))
        all_matches.extend(detect_social(clean_text))
        all_matches.extend(detect_intent(clean_text))

    if has_obfuscation:
        labels.append("obfuscation")

    # Deduplicate by (type, offset) — keep highest confidence
    seen: dict[tuple[str, int], float] = {}
    unique_matches = []
    for m in all_matches:
        key = (m.type, m.offset)
        if key not in seen or m.confidence > seen[key]:
            seen[key] = m.confidence
            unique_matches.append(m)

    # Build evidence spans and labels
    seen_labels: set[str] = set()
    for m in unique_matches:
        etype = _TYPE_MAP.get(m.type, EvidenceType.OBFUSCATION)
        evidence.append(EvidenceSpan(
            offset=m.offset,
            length=m.length,
            type=etype,
            confidence=m.confidence,
        ))

        label = _label_for_type(m.type)
        if label and label not in seen_labels:
            labels.append(label)
            seen_labels.add(label)

        # Hash the matched value for storage
        if m.value and m.type in ("phone", "email", "url", "social"):
            token_hash = hashlib.sha256(m.value.strip().lower().encode()).hexdigest()
            if token_hash not in hashed_tokens:
                hashed_tokens.append(token_hash)

    # Compute score based on weighted combination of detected types
    score = _compute_score(unique_matches, has_obfuscation)

    return StageResult(
        stage=1,
        score=round(score, 3),
        labels=labels,
        evidence_spans=evidence,
        hashed_tokens=hashed_tokens,
    )


def _compute_score(matches: list, has_obfuscation: bool) -> float:
    """Compute a risk score from pattern matches.

    Strategy:
    - Take the highest-weighted match type as base score.
    - Boost for multiple types detected.
    - Boost for obfuscation presence.
    - Factor in confidence of individual matches.
    """
    if not matches:
        return 0.0

    # Get max score by type (weighted by confidence)
    type_scores: dict[str, float] = {}
    for m in matches:
        base_weight = _TYPE_WEIGHT.get(m.type, 0.3)
        effective = base_weight * m.confidence
        if m.type not in type_scores or effective > type_scores[m.type]:
            type_scores[m.type] = effective

    if not type_scores:
        return 0.0

    # Base score = highest type score
    base_score = max(type_scores.values())

    # Multi-type boost: +0.10 for each additional contact-type detection
    contact_types = {t for t in type_scores if t in ("phone", "email", "url", "social")}
    multi_boost = min(0.15, 0.08 * (len(contact_types) - 1)) if len(contact_types) > 1 else 0.0

    # Obfuscation boost: if user is trying to hide, increase suspicion
    obfuscation_boost = 0.12 if has_obfuscation and contact_types else 0.0

    total = base_score + multi_boost + obfuscation_boost
    return min(total, 1.0)


def _label_for_type(pattern_type: str) -> str | None:
    label_map = {
        "phone": "phone_number",
        "email": "email_address",
        "url": "url_link",
        "social": "social_handle",
        "intent": "intent_phrase",
        "obfuscation": "obfuscation",
    }
    return label_map.get(pattern_type)
