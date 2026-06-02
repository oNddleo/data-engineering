"""Aggregations: bucketed sentiment stats per seller / product / category."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sentvn.schema import SentimentLabel

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sentvn.schema import Review, SentimentResult


@dataclass(frozen=True, slots=True)
class Bucket:
    """One aggregation bucket (per seller / product / category)."""

    key: str
    n_reviews: int
    n_positive: int
    n_negative: int
    n_neutral: int
    avg_score: float
    avg_rating_x100: float

    @property
    def positive_pct(self) -> float:
        return self.n_positive / self.n_reviews * 100 if self.n_reviews else 0.0

    @property
    def negative_pct(self) -> float:
        return self.n_negative / self.n_reviews * 100 if self.n_reviews else 0.0

    @property
    def net_promoter_pct(self) -> float:
        """Promoters minus detractors as a percentage."""
        return self.positive_pct - self.negative_pct


def _aggregate(
    reviews_with_results: Iterable[tuple[Review, SentimentResult]],
    key_fn: Callable[[Review], object],
) -> dict[str, Bucket]:
    grouped: dict[str, list[tuple[Review, SentimentResult]]] = {}
    for review, result in reviews_with_results:
        if review.review_id != result.review_id:
            raise ValueError(
                f"review_id mismatch: review={review.review_id} result={result.review_id}"
            )
        key = str(key_fn(review))
        grouped.setdefault(key, []).append((review, result))
    out: dict[str, Bucket] = {}
    for key, entries in grouped.items():
        n_pos = sum(1 for _, r in entries if r.label is SentimentLabel.POSITIVE)
        n_neg = sum(1 for _, r in entries if r.label is SentimentLabel.NEGATIVE)
        n_neu = sum(1 for _, r in entries if r.label is SentimentLabel.NEUTRAL)
        n = len(entries)
        avg_score = sum(r.score for _, r in entries) / n
        avg_rating = sum(rv.rating_x100 for rv, _ in entries) / n
        out[key] = Bucket(
            key=key,
            n_reviews=n,
            n_positive=n_pos,
            n_negative=n_neg,
            n_neutral=n_neu,
            avg_score=avg_score,
            avg_rating_x100=avg_rating,
        )
    return out


def by_seller(
    pairs: Iterable[tuple[Review, SentimentResult]],
) -> dict[str, Bucket]:
    return _aggregate(pairs, lambda r: r.seller_id)


def by_product(
    pairs: Iterable[tuple[Review, SentimentResult]],
) -> dict[str, Bucket]:
    return _aggregate(pairs, lambda r: r.product_id)


def by_category(
    pairs: Iterable[tuple[Review, SentimentResult]],
) -> dict[str, Bucket]:
    return _aggregate(pairs, lambda r: r.category_key)


def top_n(buckets: dict[str, Bucket], n: int = 10, *, by_npp: bool = True) -> list[Bucket]:
    """Top-N buckets, sorted by net-promoter % descending (or avg_score)."""
    if n <= 0:
        raise ValueError("n must be > 0")
    items = list(buckets.values())
    if by_npp:
        items.sort(key=lambda b: (-b.net_promoter_pct, b.key))
    else:
        items.sort(key=lambda b: (-b.avg_score, b.key))
    return items[:n]


def worst_n(buckets: dict[str, Bucket], n: int = 10) -> list[Bucket]:
    """Lowest net-promoter buckets — useful for surfacing problem sellers."""
    if n <= 0:
        raise ValueError("n must be > 0")
    items = list(buckets.values())
    items.sort(key=lambda b: (b.net_promoter_pct, b.key))
    return items[:n]


__all__ = ["Bucket", "by_category", "by_product", "by_seller", "top_n", "worst_n"]
