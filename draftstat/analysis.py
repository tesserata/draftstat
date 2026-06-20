from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import spacy
from wordfreq import zipf_frequency

from . import config
from .highlight import to_segments


@lru_cache(maxsize=1)
def _get_nlp():
    return spacy.load("en_core_web_sm", disable=["parser", "ner"])


@dataclass(frozen=True)
class Flagged:
    word: str
    count: int
    zipf: float
    score: float


@dataclass
class AnalysisResult:
    flagged: list[Flagged]
    adverbs: list[tuple[str, int]]
    segments: list[tuple[str, str | None]]


@lru_cache(maxsize=8)
def _parse(text: str):
    return _get_nlp()(text)


def _zipf(lemma: str) -> float:
    z = zipf_frequency(lemma, "en")
    return z if z > 0 else config.UNKNOWN_ZIPF


def analyze(
    text: str,
    ceiling: float = config.DEFAULT_CEILING,
    ignore_words: frozenset[str] = frozenset(),
    ignore_adverbs: frozenset[str] = frozenset(),
) -> AnalysisResult:
    doc = _parse(text)

    counts: Counter[str] = Counter()
    adverb_counts: Counter[str] = Counter()

    for token in doc:
        if not token.is_alpha:
            continue
        lemma = token.lemma_.lower()
        if len(lemma) < config.MIN_WORD_LEN:
            continue
        counts[lemma] += 1
        if token.pos_ == "ADV" and lemma not in ignore_adverbs:
            adverb_counts[lemma] += 1

    flagged: list[Flagged] = []
    score_by_lemma: dict[str, float] = {}
    for lemma, count in counts.items():
        if lemma in ignore_words or count < config.MIN_COUNT:
            continue
        zipf = _zipf(lemma)
        rarity = ceiling - zipf
        if rarity <= 0:
            continue
        score = round(count * rarity, 2)
        if score < config.MIN_SCORE:
            continue
        flagged.append(Flagged(lemma, count, round(zipf, 2), score))
        score_by_lemma[lemma] = score

    flagged.sort(key=lambda f: (f.count, f.score), reverse=True)

    adverbs = sorted(adverb_counts.items(), key=lambda x: x[1], reverse=True)
    segments = to_segments(doc, score_by_lemma)
    return AnalysisResult(flagged=flagged, adverbs=adverbs, segments=segments)
