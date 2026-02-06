"""Stage 2: NLP intent classification using spaCy."""

from __future__ import annotations

import re
from typing import Optional

from ..models import EvidenceSpan, EvidenceType, StageResult

# Lazy-load spaCy to avoid import overhead if stage 2 isn't used
_nlp = None
_MODEL_NAME = "en_core_web_sm"
_MODEL_VERSION = "spacy-3.7-sm"


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load(_MODEL_NAME)
        except OSError:
            # Model not installed — return None, stage will produce zero score
            _nlp = False
    return _nlp if _nlp is not False else None


# Intent keyword clusters with weights
_INTENT_CLUSTERS = {
    "direct_request": {
        "keywords": [
            r"\b(?:give|send|share|drop|leave)\s+(?:me\s+)?(?:your|ur)\s+(?:number|phone|cell|digits|email|contact|info)\b",
            r"\bwhat(?:'s| is)\s+(?:your|ur)\s+(?:number|phone|email|contact)\b",
            r"\bcan\s+(?:i|I)\s+(?:get|have|grab)\s+(?:your|ur)\s+(?:number|phone|email|contact)\b",
        ],
        "weight": 0.80,
    },
    "move_offplatform": {
        "keywords": [
            r"\b(?:let(?:'s|us)|we\s+(?:should|could|can))\s+(?:talk|chat|connect|continue|move|switch)\s+(?:off|outside|on|via|through|over)\b",
            r"\b(?:take\s+this|move\s+this|continue\s+this)\s+(?:offline|off[\s-]?platform|elsewhere|outside)\b",
            r"\b(?:rather|prefer)\s+(?:not\s+)?(?:use|chat|talk)\s+(?:on\s+)?(?:here|this\s+(?:app|platform|chat))\b",
        ],
        "weight": 0.70,
    },
    "contact_sharing": {
        "keywords": [
            r"\b(?:here(?:'s| is)|this\s+is)\s+my\s+(?:number|phone|cell|email|contact|whatsapp|telegram|snap)\b",
            r"\b(?:reach|contact|find|message|text|call|hit)\s+me\s+(?:at|on|via|through)\b",
            r"\bmy\s+(?:number|phone|cell|email|contact)\s+is\b",
        ],
        "weight": 0.75,
    },
    "platform_evasion": {
        "keywords": [
            r"\b(?:don(?:'t| not)|no\s+need\s+to)\s+(?:use|go\s+through|rely\s+on)\s+(?:this|the)\s+(?:app|platform|chat|system)\b",
            r"\b(?:outside|off)\s+(?:of\s+)?(?:this|the)\s+(?:app|platform|chat)\b",
            r"\b(?:middleman|fees?|commission|cut)\b.*\b(?:avoid|skip|bypass|save)\b",
        ],
        "weight": 0.65,
    },
}


async def run_stage2(
    text: str,
    context_texts: Optional[list[str]] = None,
) -> StageResult:
    """Run NLP intent classification on the message.

    Combines keyword-cluster matching with spaCy NER/dependency features
    for more nuanced intent detection.
    """
    labels: list[str] = []
    evidence: list[EvidenceSpan] = []
    combined_score = 0.0

    # Keyword cluster matching
    cluster_scores: dict[str, float] = {}
    for cluster_name, cluster in _INTENT_CLUSTERS.items():
        for pattern in cluster["keywords"]:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                cluster_scores[cluster_name] = cluster["weight"]
                for m in matches:
                    evidence.append(EvidenceSpan(
                        offset=m.start(),
                        length=m.end() - m.start(),
                        type=EvidenceType.INTENT,
                        confidence=cluster["weight"],
                    ))
                break  # One match per cluster is enough

    if cluster_scores:
        # Use the max cluster score as the base
        combined_score = max(cluster_scores.values())
        labels.append("nlp_intent")

        # Multi-cluster boost
        if len(cluster_scores) > 1:
            combined_score = min(combined_score + 0.10, 1.0)
            labels.append("multi_intent_signals")

    # Context window analysis — check if previous messages also had intent
    context_score = _analyze_context(context_texts or [])
    if context_score > 0:
        combined_score = min(combined_score + context_score * 0.15, 1.0)
        if context_score > 0.3:
            labels.append("context_escalation")

    # spaCy NER analysis for entity detection
    nlp_score = _spacy_analysis(text)
    if nlp_score > 0:
        combined_score = max(combined_score, nlp_score * 0.6)

    model_version = _MODEL_VERSION if _get_nlp() else None

    return StageResult(
        stage=2,
        score=round(min(combined_score, 1.0), 3),
        labels=labels,
        evidence_spans=evidence,
        model_version=model_version,
    )


def _spacy_analysis(text: str) -> float:
    """Use spaCy NER to detect contact-like entities."""
    nlp = _get_nlp()
    if nlp is None:
        return 0.0

    doc = nlp(text)
    score = 0.0

    for ent in doc.ents:
        # PERSON entities near contact-intent verbs
        if ent.label_ in ("PERSON", "ORG"):
            # Check if nearby tokens suggest contact exchange
            for token in doc:
                if token.lemma_ in ("call", "text", "email", "message", "contact", "reach"):
                    if abs(token.i - ent.start) < 5:
                        score = max(score, 0.4)

        # CARDINAL entities that could be phone numbers
        if ent.label_ == "CARDINAL" and len(ent.text.replace(" ", "")) >= 7:
            score = max(score, 0.5)

    return score


def _analyze_context(context_texts: list[str]) -> float:
    """Check context window for escalating intent patterns."""
    if not context_texts:
        return 0.0

    context_hits = 0
    for ctx in context_texts[-5:]:  # Look at last 5 messages
        for cluster in _INTENT_CLUSTERS.values():
            for pattern in cluster["keywords"]:
                if re.search(pattern, ctx, re.IGNORECASE):
                    context_hits += 1
                    break

    if context_hits == 0:
        return 0.0
    elif context_hits == 1:
        return 0.2
    elif context_hits == 2:
        return 0.4
    else:
        return 0.6
