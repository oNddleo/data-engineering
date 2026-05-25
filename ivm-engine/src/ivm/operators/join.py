"""Incremental multi-table join operator.

Supports INNER JOIN and LEFT JOIN, both with full retraction correctness.

Algorithm (differential / hash-join style)
-------------------------------------------
Maintain two indexes:
  left_index[join_key]  = Counter{ frozen_record: multiplicity }
  right_index[join_key] = Counter{ frozen_record: multiplicity }

When a LEFT update (r, t, d) arrives:
  1. For every right record s with multiplicity m matching the same join key:
       emit (r ⋈ s, t, d * m)           ← the join delta
  2. Update left_index[key][freeze(r)] += d

When a RIGHT update arrives: symmetric.

This is exactly differential dataflow's "join" rule — correctness follows from
linearity: the cross-product distributes over addition (and retraction is just
negative addition).

LEFT JOIN extension
--------------------
A left record with no matching right records must still appear in the output
with NULL right columns.  We track the match count per left record and emit
the "unmatched" row when the count transitions 0↔1.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable

from ivm.operators.base import Operator
from ivm.types import Record, Update, freeze_record, record_key


# ---------------------------------------------------------------------------
# Key extractors
# ---------------------------------------------------------------------------


def _make_key_fn(spec: Any) -> Callable[[Record], tuple[Any, ...]]:
    """Accept a column name, list of names, or callable."""
    if callable(spec):
        return spec  # type: ignore[return-value]
    if isinstance(spec, str):
        return lambda r, _s=spec: (_s and (r[_s],) or ())  # type: ignore[return-value]
    cols: list[str] = list(spec)
    return lambda r: tuple(r[col] for col in cols)


# ---------------------------------------------------------------------------
# JoinOperator
# ---------------------------------------------------------------------------


class JoinOperator(Operator):
    """Incremental hash-join operator supporting INNER and LEFT join semantics.

    Parameters
    ----------
    left_key : str | list[str] | callable
        Key extractor for the left stream.
    right_key : str | list[str] | callable
        Key extractor for the right stream.
    join_type : "inner" | "left"
        Type of join.  RIGHT JOIN = swap left/right at call site.
    right_prefix : str, optional
        Prefix added to right column names on conflict (default: "right_").
    """

    def __init__(
        self,
        left_key: Any,
        right_key: Any,
        join_type: str = "inner",
        right_prefix: str = "right_",
    ) -> None:
        super().__init__()
        self._left_key_fn = _make_key_fn(left_key)
        self._right_key_fn = _make_key_fn(right_key)
        self.join_type = join_type.lower()
        self.right_prefix = right_prefix

        # key -> Counter{ frozen_record -> multiplicity }
        self._left_idx: dict[tuple[Any, ...], Counter[Any]] = defaultdict(Counter)
        self._right_idx: dict[tuple[Any, ...], Counter[Any]] = defaultdict(Counter)

        # LEFT JOIN only: track match count per frozen left record
        # so we know when to emit/retract the unmatched placeholder.
        self._left_match_count: Counter[Any] = Counter()  # frozen_left -> int

    # ------------------------------------------------------------------
    # Record merging (handle column name conflicts with prefix)
    # ------------------------------------------------------------------

    def _merge(self, left: Record, right: Record) -> Record:
        result: Record = dict(left)
        for k, v in right.items():
            if k in result:
                result[self.right_prefix + k] = v
            else:
                result[k] = v
        return result

    def _null_right(self, left: Record) -> Record:
        """Left record with no matching right — all right columns are absent."""
        return dict(left)

    # ------------------------------------------------------------------
    # Entry points (called by Operator.join wiring)
    # ------------------------------------------------------------------

    def handle_left(self, updates: list[Update]) -> None:
        """Process updates arriving on the left side."""
        out = self._process_left(updates)
        if out:
            self._emit(out)

    def handle_right(self, updates: list[Update]) -> None:
        """Process updates arriving on the right side."""
        out = self._process_right(updates)
        if out:
            self._emit(out)

    # process() required by ABC but not directly called for join
    def process(self, updates: list[Update]) -> list[Update]:  # pragma: no cover
        return []

    # ------------------------------------------------------------------
    # Left side processing
    # ------------------------------------------------------------------

    def _process_left(self, updates: list[Update]) -> list[Update]:
        out: list[Update] = []
        for u in updates:
            key = self._left_key_fn(u.record)
            right_bucket = self._right_idx[key]

            if self.join_type == "left":
                # Before updating index, check current match state
                prev_matches = sum(right_bucket.values())
                if prev_matches == 0 and u.diff < 0:
                    # Retract the unmatched placeholder
                    out.append(Update(self._null_right(u.record), u.timestamp, +1))

            # Emit join results with all current right matches
            for frozen_right, right_mult in right_bucket.items():
                if right_mult == 0:
                    continue
                right_rec = dict(frozen_right)
                merged = self._merge(u.record, right_rec)
                out.append(Update(merged, u.timestamp, u.diff * right_mult))

            # Update left index
            frozen_left = freeze_record(u.record)
            self._left_idx[key][frozen_left] += u.diff
            if self._left_idx[key][frozen_left] == 0:
                del self._left_idx[key][frozen_left]

            # LEFT JOIN: emit unmatched row if no right matches
            if self.join_type == "left":
                total_right = sum(right_bucket.values())
                if total_right == 0:
                    out.append(Update(self._null_right(u.record), u.timestamp, u.diff))

        return out

    # ------------------------------------------------------------------
    # Right side processing
    # ------------------------------------------------------------------

    def _process_right(self, updates: list[Update]) -> list[Update]:
        out: list[Update] = []
        for u in updates:
            key = self._right_key_fn(u.record)
            left_bucket = self._left_idx[key]

            prev_right_total = sum(self._right_idx[key].values()) if self.join_type == "left" else 0

            # Emit join results for all current left matches
            for frozen_left, left_mult in left_bucket.items():
                if left_mult == 0:
                    continue
                left_rec = dict(frozen_left)
                merged = self._merge(left_rec, u.record)
                out.append(Update(merged, u.timestamp, left_mult * u.diff))

            # Update right index
            frozen_right = freeze_record(u.record)
            self._right_idx[key][frozen_right] += u.diff
            if self._right_idx[key][frozen_right] == 0:
                del self._right_idx[key][frozen_right]

            # LEFT JOIN: when right side transitions 0→1 or 1→0, update unmatched rows
            if self.join_type == "left":
                new_right_total = sum(self._right_idx[key].values())
                for frozen_left, left_mult in left_bucket.items():
                    if left_mult == 0:
                        continue
                    left_rec = dict(frozen_left)
                    if prev_right_total == 0 and new_right_total > 0:
                        # Right matches appeared: retract the NULL-right placeholder
                        out.append(
                            Update(self._null_right(left_rec), u.timestamp, -left_mult)
                        )
                    elif prev_right_total > 0 and new_right_total == 0:
                        # Right matches disappeared: emit the NULL-right placeholder
                        out.append(
                            Update(self._null_right(left_rec), u.timestamp, +left_mult)
                        )

        return out

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def left_index_size(self) -> int:
        """Number of distinct frozen left records tracked."""
        return sum(len(v) for v in self._left_idx.values())

    def right_index_size(self) -> int:
        """Number of distinct frozen right records tracked."""
        return sum(len(v) for v in self._right_idx.values())
