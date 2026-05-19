"""Heavy-hitters extraction: top-K most-frequent values.

The CMS alone can answer "frequency of value v" but not "what are
the K most-frequent values?" — the sketch doesn't store the input
strings. To produce heavy hitters we **stream the input twice**:

1. First pass — feed every value into CMS.
2. Second pass — for each value, query its CMS estimate. Keep a
   bounded min-heap of the K largest estimates seen.

For streams that fit in memory (or for second-pass-from-disk
pipelines), this is the standard approach.

For true single-pass operation, a Misra-Gries "frequent items"
sketch can run alongside the CMS to maintain a candidate-set; we
expose this via ``HeavyHittersBuilder`` which interleaves both
passes online.

We return a list of ``HeavyHitter`` rows sorted by estimated
count descending.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cms.sketch import estimate, update

if TYPE_CHECKING:
    from cms.schema import CountMinSketch

from cms.schema import HeavyHitter


def top_k_two_pass(
    sketch: CountMinSketch,
    values: list[str],
    k: int = 10,
) -> list[HeavyHitter]:
    """Two-pass extraction: caller has already populated ``sketch`` from
    ``values``. We re-walk ``values`` (deduplicated) and rank by
    estimated count.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    distinct = set(values)
    candidates: list[tuple[str, int]] = [(v, estimate(sketch, v)) for v in distinct]
    candidates.sort(key=lambda kv: (-kv[1], kv[0]))
    total = sketch.total_count or 1
    return [
        HeavyHitter(
            value=v,
            estimated_count=c,
            fraction_of_total=c / total if total > 0 else 0.0,
        )
        for v, c in candidates[:k]
    ]


@dataclass(slots=True)
class HeavyHittersBuilder:
    """Online heavy-hitters tracker — Misra-Gries candidate set + CMS.

    Keeps **at most ``k + buffer`` candidate strings** in memory.
    When a new value arrives, we update the CMS and:

    * If the value is already a candidate, increment its tracker.
    * Otherwise, if we have room (< k + buffer candidates), add it.
    * Otherwise, decrement *every* candidate's tracker by 1 and
      drop those that hit 0 (the classic Misra-Gries step).

    At end-of-stream, ``top_k()`` reports the K candidates with the
    largest CMS estimates. The Misra-Gries tracker gives correctness
    guarantees (every true top-K element is in the candidate set
    if its frequency > total / (k+buffer)); the CMS gives a tight
    over-estimate.
    """

    sketch: CountMinSketch
    k: int = 10
    buffer: int = 50
    _candidates: dict[str, int] = field(default_factory=dict, init=False)

    def add(self, value: str, count: int = 1) -> None:
        """Process one value (or a batch with multiplicity ``count``)."""
        # Update CMS first.
        new_sketch = update(self.sketch, value, count=count)
        object.__setattr__(self, "sketch", new_sketch)

        max_candidates = self.k + self.buffer
        if value in self._candidates:
            self._candidates[value] += count
            return
        if len(self._candidates) < max_candidates:
            self._candidates[value] = count
            return
        # Misra-Gries: decrement every tracker, drop those at 0.
        to_drop = []
        for v in self._candidates:
            self._candidates[v] -= count
            if self._candidates[v] <= 0:
                to_drop.append(v)
        for v in to_drop:
            del self._candidates[v]
        # If we made room, insert.
        if len(self._candidates) < max_candidates:
            self._candidates[value] = count

    def top_k(self) -> list[HeavyHitter]:
        """Return the K candidates with the largest CMS estimates."""
        ranked = sorted(
            self._candidates,
            key=lambda v: (-estimate(self.sketch, v), v),
        )[: self.k]
        total = self.sketch.total_count or 1
        out: list[HeavyHitter] = []
        for v in ranked:
            est = estimate(self.sketch, v)
            out.append(
                HeavyHitter(
                    value=v,
                    estimated_count=est,
                    fraction_of_total=est / total if total > 0 else 0.0,
                )
            )
        return out


def exact_heavy_hitters(values: list[str], k: int = 10) -> list[HeavyHitter]:
    """Reference implementation — exact top-K via in-memory counting.

    Used for tests to validate the CMS estimate. Not suitable for
    large streams.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    counter: dict[str, int] = defaultdict(int)
    for v in values:
        counter[v] += 1
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    total = sum(counter.values()) or 1
    return [HeavyHitter(value=v, estimated_count=c, fraction_of_total=c / total) for v, c in ranked]


__all__ = [
    "HeavyHittersBuilder",
    "exact_heavy_hitters",
    "top_k_two_pass",
]
