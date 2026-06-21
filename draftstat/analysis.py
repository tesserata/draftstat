from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import spacy
from wordfreq import zipf_frequency

from draftstat import config
from draftstat.highlight import to_segments, token_key


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


@lru_cache(maxsize=4096)
def _zipf(lemma: str) -> float:
    z = zipf_frequency(lemma, "en")
    return z if z > 0 else config.UNKNOWN_ZIPF


@lru_cache(maxsize=8)
def _tally(text: str, normalize: bool):
    doc = _parse(text)

    counts: Counter[str] = Counter()
    adverb_counts: Counter[str] = Counter()
    for token in doc:
        if not token.is_alpha:
            continue
        key = token_key(token, normalize)
        if len(key) < config.MIN_WORD_LEN:
            continue
        counts[key] += 1
        if token.pos_ == "ADV":
            adverb_counts[key] += 1

    segments = to_segments(doc, normalize=normalize)
    return counts, adverb_counts, segments


@lru_cache(maxsize=8)
def _ranked(text: str, normalize: bool, ceiling: float):
    counts, adverb_counts, segments = _tally(text, normalize)

    flagged: list[Flagged] = []
    for word, count in counts.items():
        if count < config.MIN_COUNT:
            continue
        zipf = _zipf(word)
        rarity = ceiling - zipf
        if rarity <= 0:
            continue
        score = round(count * rarity, 2)
        if score < config.MIN_SCORE:
            continue
        flagged.append(Flagged(word, count, round(zipf, 2), score))
    flagged.sort(key=lambda f: (f.count, f.score), reverse=True)

    adverbs_full = sorted(adverb_counts.items(), key=lambda x: x[1], reverse=True)
    return flagged, adverbs_full, segments


def analyze(
    text: str,
    ceiling: float = config.DEFAULT_CEILING,
    ignore_words: frozenset[str] = frozenset(),
    ignore_adverbs: frozenset[str] = frozenset(),
    normalize: bool = True,
    filter_adverbs: bool = True,
) -> AnalysisResult:
    flagged_full, adverbs_full, segments = _ranked(
        text or "", normalize, float(ceiling)
    )

    flagged = [f for f in flagged_full if f.word not in ignore_words]
    adverbs = [
        (w, c)
        for w, c in adverbs_full
        if w not in ignore_adverbs and (not filter_adverbs or w.endswith("ly"))
    ]
    return AnalysisResult(flagged=flagged, adverbs=adverbs, segments=segments)
