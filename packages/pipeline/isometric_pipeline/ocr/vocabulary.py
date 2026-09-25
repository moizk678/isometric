"""Engineering vocabulary normalization (never replaces raw OCR)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class OcrVocabulary:
    terms: frozenset[str]
    abbreviations: dict[str, str]

    @classmethod
    def from_profile(
        cls, terms: list[str], abbreviations: dict[str, str]
    ) -> OcrVocabulary:
        lowered = {t.lower(): t for t in terms}
        merged = {**{k.lower(): v for k, v in abbreviations.items()}, **lowered}
        return cls(terms=frozenset(t.lower() for t in terms), abbreviations=merged)


_ABBREV_PATTERN = re.compile(
    r"\b([a-z]{2,})\.\b",
    re.IGNORECASE,
)


def propose_normalized_text(raw: str, vocabulary: OcrVocabulary) -> str | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    text = _expand_abbreviations(text, vocabulary)
    text = _apply_known_terms(text, vocabulary)
    text = _sentence_case(text)
    if text == raw.strip():
        return None
    return text


def vocabulary_alternatives(
    raw: str, vocabulary: OcrVocabulary
) -> list[tuple[str, float]]:
    normalized = propose_normalized_text(raw, vocabulary)
    if normalized is None or normalized == raw.strip():
        return []
    return [(normalized, 0.55)]


def _expand_abbreviations(text: str, vocabulary: OcrVocabulary) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        full = vocabulary.abbreviations.get(key)
        if full and full.lower() != key:
            return full
        return match.group(0)

    return _ABBREV_PATTERN.sub(repl, text)


def _apply_known_terms(text: str, vocabulary: OcrVocabulary) -> str:
    words = text.split()
    out: list[str] = []
    for word in words:
        bare = word.strip(".,;:")
        lower = bare.lower()
        if lower in vocabulary.terms:
            canonical = vocabulary.abbreviations.get(lower, bare)
            if canonical.isupper() or len(canonical) <= 4:
                out.append(
                    canonical.upper()
                    if canonical.isalpha() and len(canonical) <= 4
                    else canonical
                )
            else:
                out.append(canonical)
        else:
            out.append(word)
    return " ".join(out)


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]
