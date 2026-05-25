"""Hypothesis property-based tests for the IVM engine.

Properties verified:
  P1  COUNT after n insertions equals n.
  P2  COUNT after n insertions + k retractions equals max(0, n-k).
  P3  SUM is commutative — order of insertion does not affect result.
  P4  SUM after full retraction equals SUM of remaining records.
  P5  Inserting and retracting the same record is a no-op on the view.
  P6  AVG(n=1) equals the single value inserted.
  P7  MIN always returns the minimum of remaining values.
  P8  MAX always returns the maximum of remaining values.
  P9  Net delta-log multiplicity is always non-negative for each record.
  P10 Row count reported by engine equals len(query()).
"""
from __future__ import annotations

from collections import Counter

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ivm import IVMEngine
from ivm.types import freeze_record
import ivm.aggregates as agg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_records = st.fixed_dictionaries({"g": st.sampled_from(["a", "b", "c"]),
                                   "v": st.integers(min_value=1, max_value=100)})

_values = st.lists(st.integers(min_value=1, max_value=1_000),
                   min_size=1, max_size=20)


# ---------------------------------------------------------------------------
# P1: COUNT after n insertions equals n
# ---------------------------------------------------------------------------


@given(n=st.integers(min_value=0, max_value=50))
def test_count_equals_n_insertions(n: int) -> None:
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"n": agg.Count()})
    e.register_view("v", view)

    for i in range(n):
        e.ingest("s", {"g": "x", "val": i}, timestamp=1)

    if n == 0:
        assert e.query("v") == []
    else:
        rows = {r["g"]: r["n"] for r in e.query("v")}
        assert rows["x"] == n


# ---------------------------------------------------------------------------
# P2: COUNT after n insertions + k retractions equals max(0, n-k)
# ---------------------------------------------------------------------------


@given(
    n=st.integers(min_value=1, max_value=20),
    k=st.integers(min_value=0, max_value=20),
)
def test_count_after_retractions(n: int, k: int) -> None:
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"n": agg.Count()})
    e.register_view("v", view)

    for _ in range(n):
        e.ingest("s", {"g": "x"}, timestamp=1)
    for _ in range(k):
        e.retract("s", {"g": "x"}, timestamp=2)

    expected = max(0, n - k)
    if expected == 0:
        assert e.query("v") == []
    else:
        rows = {r["g"]: r["n"] for r in e.query("v")}
        assert rows["x"] == expected


# ---------------------------------------------------------------------------
# P3: SUM is commutative
# ---------------------------------------------------------------------------


@given(values=_values)
def test_sum_commutative(values: list[int]) -> None:
    """Sum result is the same regardless of insertion order."""
    import random
    shuffled = list(values)
    random.shuffle(shuffled)

    e1 = IVMEngine()
    s1 = e1.source("s")
    e1.register_view("v", s1.group_by(["g"], {"total": agg.Sum("v")}))
    for val in values:
        e1.ingest("s", {"g": "x", "v": val}, timestamp=1)

    e2 = IVMEngine()
    s2 = e2.source("s")
    e2.register_view("v", s2.group_by(["g"], {"total": agg.Sum("v")}))
    for val in shuffled:
        e2.ingest("s", {"g": "x", "v": val}, timestamp=1)

    r1 = {r["g"]: r["total"] for r in e1.query("v")}
    r2 = {r["g"]: r["total"] for r in e2.query("v")}
    assert r1 == r2


# ---------------------------------------------------------------------------
# P4: SUM after retraction
# ---------------------------------------------------------------------------


@given(values=_values, retract_indices=st.lists(st.integers(min_value=0, max_value=19),
                                                 max_size=10))
def test_sum_after_retraction(values: list[int], retract_indices: list[int]) -> None:
    """SUM equals sum of values not retracted."""
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"total": agg.Sum("v")})
    e.register_view("v", view)

    for val in values:
        e.ingest("s", {"g": "x", "v": val}, timestamp=1)

    retracted: list[int] = []
    for idx in retract_indices:
        if idx < len(values):
            e.retract("s", {"g": "x", "v": values[idx]}, timestamp=2)
            retracted.append(values[idx])

    # Expected: sum of all values minus once-retracted values
    remaining_counts: Counter[int] = Counter(values)
    for v in retracted:
        remaining_counts[v] -= 1
        if remaining_counts[v] <= 0:
            del remaining_counts[v]
    expected = sum(v * cnt for v, cnt in remaining_counts.items())

    rows = {r["g"]: r["total"] for r in e.query("v")}
    if expected == 0:
        assert "x" not in rows
    else:
        assert rows.get("x") == expected


# ---------------------------------------------------------------------------
# P5: Insert then retract same record is a no-op
# ---------------------------------------------------------------------------


@given(records=st.lists(_records, min_size=1, max_size=10))
def test_insert_retract_noop(records: list[dict[str, object]]) -> None:
    """Inserting then retracting every record leaves the view empty."""
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"n": agg.Count()})
    e.register_view("v", view)

    for rec in records:
        e.ingest("s", rec, timestamp=1)
    for rec in records:
        e.retract("s", rec, timestamp=2)

    assert e.query("v") == []


# ---------------------------------------------------------------------------
# P6: AVG(n=1) equals the single value
# ---------------------------------------------------------------------------


@given(val=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False,
                     allow_infinity=False))
def test_avg_single_value(val: float) -> None:
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"avg": agg.Avg("v")})
    e.register_view("v", view)

    e.ingest("s", {"g": "x", "v": val}, timestamp=1)
    rows = {r["g"]: r["avg"] for r in e.query("v")}
    assert rows["x"] == pytest.approx(val, rel=1e-9)


# ---------------------------------------------------------------------------
# P7: MIN always returns the actual minimum of remaining values
# ---------------------------------------------------------------------------


@given(values=st.lists(st.integers(min_value=-100, max_value=100),
                       min_size=1, max_size=20, unique=True))
def test_min_is_actual_minimum(values: list[int]) -> None:
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"mn": agg.Min("v")})
    e.register_view("v", view)

    for v in values:
        e.ingest("s", {"g": "x", "v": v}, timestamp=1)

    rows = {r["g"]: r["mn"] for r in e.query("v")}
    assert rows["x"] == min(values)


# ---------------------------------------------------------------------------
# P8: MAX always returns the actual maximum of remaining values
# ---------------------------------------------------------------------------


@given(values=st.lists(st.integers(min_value=-100, max_value=100),
                       min_size=1, max_size=20, unique=True))
def test_max_is_actual_maximum(values: list[int]) -> None:
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"mx": agg.Max("v")})
    e.register_view("v", view)

    for v in values:
        e.ingest("s", {"g": "x", "v": v}, timestamp=1)

    rows = {r["g"]: r["mx"] for r in e.query("v")}
    assert rows["x"] == max(values)


# ---------------------------------------------------------------------------
# P9: Net delta-log multiplicity is always non-negative
# ---------------------------------------------------------------------------


@given(ops=st.lists(
    st.tuples(st.sampled_from(["insert", "retract"]),
              st.integers(min_value=1, max_value=5)),
    min_size=1, max_size=30,
))
@settings(max_examples=100)
def test_delta_log_nonnegative_multiplicity(ops: list[tuple[str, int]]) -> None:
    """Net multiplicity of every record in the delta log must stay >= 0."""
    e = IVMEngine()
    src = e.source("s")
    view = src.group_by(["g"], {"n": agg.Count()})
    e.register_view("v", view)

    for op, val in ops:
        rec = {"g": "x", "v": val}
        if op == "insert":
            e.ingest("s", rec, timestamp=1)
        else:
            e.retract("s", rec, timestamp=2)

    net: Counter[object] = Counter()
    for delta in e.delta_log("v"):
        net[freeze_record(delta.record)] += delta.diff

    for key, cnt in net.items():
        assert cnt >= 0, f"Negative net multiplicity for {key}: {cnt}"


# ---------------------------------------------------------------------------
# P10: row_count == len(query())
# ---------------------------------------------------------------------------


@given(values=_values)
def test_row_count_matches_query_length(values: list[int]) -> None:
    e = IVMEngine()
    src = e.source("s")
    # Use group_by so each unique (g,v) combo is one row
    view = src.group_by(["g", "v"], {"n": agg.Count()})
    e.register_view("v", view)

    for v in values:
        e.ingest("s", {"g": "x", "v": v}, timestamp=1)

    assert e.row_count("v") == len(e.query("v"))
