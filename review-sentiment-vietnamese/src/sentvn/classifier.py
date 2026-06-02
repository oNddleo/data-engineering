"""Sentiment Classifier Protocol + lexicon-based baseline implementation.

We deliberately don't bundle PhoBERT / VinAI / underthesea —
they're heavy ML stacks that would dwarf this codebase. The
:class:`SentimentClassifier` Protocol is the narrow contract a
production wrapper has to satisfy; everything downstream
(aggregations, CLI) works against any implementation.

:class:`LexiconClassifier` is a reasonable baseline for short
Shopee-style reviews. It applies negator + intensifier look-back
so ``rất tốt`` and ``không tốt`` get correctly signed scores:

| Text                | Tokens (normalised)  | Score | Label    |
| ------------------- | -------------------- | ----- | -------- |
| ``Tốt``             | ``[tot]``            | +1    | POSITIVE |
| ``Rất tốt``         | ``[rat, tot]``       | +2    | POSITIVE |
| ``Không tốt``       | ``[khong, tot]``     | −1    | NEGATIVE |
| ``Rất không tốt``   | ``[rat, khong, tot]``| −2    | NEGATIVE |
| ``Tốt nhưng chậm``  | ``[tot, nhung, cham]``| 0    | NEUTRAL  |

The third row is the classic case the production baseline misses
and a real ML model catches — see the README.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from sentvn.lexicon import (
    INTENSIFIERS,
    NEGATIVE_WORDS,
    NEGATORS,
    POSITIVE_WORDS,
    tokenize,
)
from sentvn.schema import SentimentLabel, SentimentResult

if TYPE_CHECKING:
    from sentvn.schema import Review


class SentimentClassifier(Protocol):
    """Production callers plug in their PhoBERT / VinAI wrapper here."""

    def classify(self, review: Review) -> SentimentResult: ...


_CLAUSE_DELIMITERS = ".,;!?\n"


def _score_clause(text: str) -> tuple[int, int]:
    """Score one clause; negators / intensifiers don't escape it."""
    tokens = tokenize(text)
    score = 0
    n_hits = 0
    negate = False
    intensify = 1.0
    for token in tokens:
        if token in NEGATORS:
            negate = True
            continue
        if token in INTENSIFIERS:
            intensify *= 2.0
            continue
        delta = 0
        if token in POSITIVE_WORDS:
            delta = 1
        elif token in NEGATIVE_WORDS:
            delta = -1
        if delta == 0:
            continue
        if negate:
            delta = -delta
        score += int(delta * intensify)
        n_hits += 1
        negate = False
        intensify = 1.0
    return score, n_hits


def score_text(text: str) -> tuple[int, int]:
    """Compute the raw sentiment score for one text and the number of hits.

    Negators / intensifiers do **not** cross punctuation — we split
    the text on ``.,;!?\\n`` and score each clause independently.
    Without this scoping, ``không nên mua, kém chất lượng`` would
    let the ``không`` from clause 1 flip the ``kém`` in clause 3
    and cancel out a genuinely negative review.

    Returns ``(score, n_hits)``. ``n_hits`` is summed across clauses.
    """
    score = 0
    n_hits = 0
    current: list[str] = []
    for ch in text:
        if ch in _CLAUSE_DELIMITERS:
            if current:
                s, h = _score_clause("".join(current))
                score += s
                n_hits += h
                current = []
        else:
            current.append(ch)
    if current:
        s, h = _score_clause("".join(current))
        score += s
        n_hits += h
    return score, n_hits


def score_to_label(score: int) -> SentimentLabel:
    if score > 0:
        return SentimentLabel.POSITIVE
    if score < 0:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


def _confidence_from(score: int, n_hits: int) -> float:
    """Normalise the absolute score to ``[0, 1]``.

    The peak possible score per hit is ``2`` (one intensifier × +1
    word), so the max-possible total is ``n_hits × 2``. Confidence
    is ``|score| / (n_hits × 2)``, clamped to ``[0, 1]``. Zero hits →
    zero confidence.
    """
    if n_hits == 0:
        return 0.0
    return min(abs(score) / (n_hits * 2.0), 1.0)


class LexiconClassifier:
    """Lexicon-based VN sentiment classifier — the bundled baseline."""

    def classify(self, review: Review) -> SentimentResult:
        score, n_hits = score_text(review.text)
        return SentimentResult(
            review_id=review.review_id,
            label=score_to_label(score),
            score=score,
            confidence=_confidence_from(score, n_hits),
        )

    def classify_text(self, text: str) -> SentimentResult:
        """Classify a free-form text snippet. Useful for the CLI."""
        score, n_hits = score_text(text)
        return SentimentResult(
            review_id="",
            label=score_to_label(score),
            score=score,
            confidence=_confidence_from(score, n_hits),
        )


__all__ = [
    "LexiconClassifier",
    "SentimentClassifier",
    "score_text",
    "score_to_label",
]
