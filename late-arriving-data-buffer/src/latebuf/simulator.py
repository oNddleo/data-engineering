"""Seeded synthetic event stream with controllable lateness distribution.

Produces an ordered (by ``ingest_time``) sequence of ``Event``s where
each event's ``event_time`` is the *intended* generation time minus a
**lateness draw** from one of two distributions:

* **bounded** — ``lateness_seconds = randint(0, max_lateness_seconds)``
* **heavy_tail** — 95% in [0, p95_seconds]; 5% in [p95, max_lateness_seconds].
  Mimics real-world streams (e.g. mobile event uploads, where a
  small minority arrive minutes late from offline devices).

A small fraction of events are tagged ``is_punctuation=True`` —
useful for testing the PUNCTUATED watermark strategy.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from enum import Enum

from latebuf.schema import VN_TZ, Event


class LatenessDistribution(str, Enum):
    """Two distributions for event lateness in the simulator."""

    BOUNDED = "BOUNDED"
    HEAVY_TAIL = "HEAVY_TAIL"


def generate(
    *,
    n_events: int = 1_000,
    base_time: datetime | None = None,
    interval_seconds: float = 1.0,
    distribution: LatenessDistribution = LatenessDistribution.BOUNDED,
    max_lateness_seconds: int = 30,
    p95_seconds: int = 5,
    punctuation_every: int = 100,
    seed: int = 0,
) -> list[Event]:
    """Generate a synthetic event stream sorted by ``ingest_time``."""
    if n_events < 0:
        raise ValueError(f"n_events must be >= 0, got {n_events}")
    if interval_seconds <= 0:
        raise ValueError(f"interval_seconds must be > 0, got {interval_seconds}")
    if max_lateness_seconds < 0:
        raise ValueError(
            f"max_lateness_seconds must be >= 0, got {max_lateness_seconds}",
        )
    if distribution is LatenessDistribution.HEAVY_TAIL and p95_seconds < 0:
        raise ValueError(f"p95_seconds must be >= 0, got {p95_seconds}")
    if punctuation_every < 1:
        raise ValueError(f"punctuation_every must be >= 1, got {punctuation_every}")

    rng = random.Random(seed)
    base = base_time or datetime(2026, 5, 18, 9, 0, 0, tzinfo=VN_TZ)
    events: list[Event] = []
    for i in range(n_events):
        ingest_at = base + timedelta(
            seconds=int(i * interval_seconds),
            microseconds=int((i * interval_seconds % 1) * 1_000_000),
        )
        lateness = _draw_lateness(rng, distribution, max_lateness_seconds, p95_seconds)
        event_at = ingest_at - timedelta(seconds=lateness)
        events.append(
            Event(
                event_id=f"E-{i:08d}",
                event_time=event_at,
                ingest_time=ingest_at,
                payload=f"payload-{i}",
                is_punctuation=(i % punctuation_every == punctuation_every - 1),
            )
        )
    return events


def _draw_lateness(
    rng: random.Random,
    distribution: LatenessDistribution,
    max_l: int,
    p95: int,
) -> int:
    """Draw a non-negative lateness value (seconds)."""
    if distribution is LatenessDistribution.BOUNDED:
        return rng.randint(0, max_l)
    # HEAVY_TAIL
    if rng.random() < 0.95:
        return rng.randint(0, min(p95, max_l))
    return rng.randint(min(p95, max_l), max_l)


__all__ = ["LatenessDistribution", "generate"]
