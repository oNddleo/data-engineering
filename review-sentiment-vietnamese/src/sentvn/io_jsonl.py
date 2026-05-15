"""JSONL codec for Review + SentimentResult."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from sentvn.schema import Review, SentimentLabel, SentimentResult

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def review_to_dict(r: Review) -> dict[str, object]:
    return {
        "review_id": r.review_id,
        "text": r.text,
        "seller_id": r.seller_id,
        "product_id": r.product_id,
        "category_key": r.category_key,
        "rating_x100": r.rating_x100,
        "posted_at": r.posted_at.isoformat(),
    }


def review_from_dict(d: dict[str, object]) -> Review:
    return Review(
        review_id=_require_str(d, "review_id"),
        text=_require_str(d, "text"),
        seller_id=_require_int(d, "seller_id"),
        product_id=_require_int(d, "product_id"),
        category_key=_require_str(d, "category_key"),
        rating_x100=_require_int(d, "rating_x100"),
        posted_at=datetime.fromisoformat(_require_str(d, "posted_at")),
    )


def result_to_dict(r: SentimentResult) -> dict[str, object]:
    return {
        "review_id": r.review_id,
        "label": r.label.value,
        "score": r.score,
        "confidence": r.confidence,
    }


def result_from_dict(d: dict[str, object]) -> SentimentResult:
    conf = d["confidence"]
    if isinstance(conf, bool) or not isinstance(conf, int | float):
        raise TypeError("confidence must be a number")
    return SentimentResult(
        review_id=_require_str(d, "review_id"),
        label=SentimentLabel(_require_str(d, "label")),
        score=_require_int(d, "score"),
        confidence=float(conf),
    )


def dump_reviews(rs: Iterable[Review]) -> str:
    return "\n".join(json.dumps(review_to_dict(r), ensure_ascii=False) for r in rs) + "\n"


def load_reviews(text: str) -> Iterator[Review]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield review_from_dict(json.loads(line))


def dump_results(rs: Iterable[SentimentResult]) -> str:
    return "\n".join(json.dumps(result_to_dict(r), ensure_ascii=False) for r in rs) + "\n"


def load_results(text: str) -> Iterator[SentimentResult]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield result_from_dict(json.loads(line))


__all__ = [
    "dump_results",
    "dump_reviews",
    "load_results",
    "load_reviews",
    "result_from_dict",
    "result_to_dict",
    "review_from_dict",
    "review_to_dict",
]
