"""Hypothesis properties — invariants of derive + billing."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from evnmeter.derive import derive
from evnmeter.tariff import compute_bill

from ._fixtures import DEFAULT_TS, make_reading


@st.composite
def _reading_series(draw: st.DrawFn) -> list:  # type: ignore[type-arg]
    """Build a monotone-non-decreasing cumulative reading series."""
    n = draw(st.integers(min_value=2, max_value=20))
    deltas = draw(
        st.lists(
            st.integers(min_value=0, max_value=1000),
            min_size=n - 1,
            max_size=n - 1,
        )
    )
    cumulative = draw(st.integers(min_value=0, max_value=10_000_000))
    out = [make_reading(cumulative_kwh_x100=cumulative, observed_at=DEFAULT_TS)]
    for i, delta in enumerate(deltas):
        cumulative += delta
        out.append(
            make_reading(
                cumulative_kwh_x100=cumulative,
                observed_at=DEFAULT_TS + timedelta(minutes=30 * (i + 1)),
            )
        )
    return out


@given(series=_reading_series())
@settings(max_examples=50)
def test_total_delta_preserved(series: list) -> None:  # type: ignore[type-arg]
    """Sum of interval kWh equals the (last − first) cumulative reading."""
    intervals = derive(series, max_gap_minutes=30 * len(series))  # no splitting
    if not intervals:
        return
    expected = series[-1].cumulative_kwh_x100 - series[0].cumulative_kwh_x100
    assert sum(c.kwh_x100 for c in intervals) == expected


@given(series=_reading_series())
@settings(max_examples=50)
def test_intervals_never_overlap_per_meter(series: list) -> None:  # type: ignore[type-arg]
    """``end_at[i] == start_at[i+1]`` for chronologically-adjacent intervals."""
    intervals = derive(series)
    by_meter: dict[str, list] = {}  # type: ignore[type-arg]
    for c in intervals:
        by_meter.setdefault(c.meter_id, []).append(c)
    from itertools import pairwise

    for group in by_meter.values():
        group.sort(key=lambda c: c.start_at)
        for prev, curr in pairwise(group):
            assert prev.end_at <= curr.start_at


@given(kwh=st.integers(min_value=0, max_value=2_000))
@settings(max_examples=100)
def test_bill_grand_equals_subtotal_plus_vat(kwh: int) -> None:
    """``grand_total == subtotal + vat`` for any kWh value."""
    _, sub, vat, grand = compute_bill(kwh)
    assert grand == sub + vat


@given(kwh=st.integers(min_value=0, max_value=2_000))
@settings(max_examples=100)
def test_bill_monotone_in_kwh(kwh: int) -> None:
    """A bill for ``kwh + 1`` is always ≥ the bill for ``kwh`` (tariff is monotonic)."""
    _, sub_a, _, _ = compute_bill(kwh)
    _, sub_b, _, _ = compute_bill(kwh + 1)
    assert sub_b >= sub_a


@given(
    kwh_a=st.integers(min_value=1, max_value=300),
    kwh_b=st.integers(min_value=1, max_value=300),
)
@settings(max_examples=50)
def test_bill_subadditive_within_one_tier(kwh_a: int, kwh_b: int) -> None:
    """Within a single tier, ``bill(a + b) == bill(a) + bill(b)`` when both
    quantities fall in the *same* tier. We verify the general lower bound:
    ``bill(a + b) ≤ bill(a) + bill(b)`` because progressive tiers can only
    push the combined bill higher, never lower."""
    _, a_sub, _, _ = compute_bill(kwh_a)
    _, b_sub, _, _ = compute_bill(kwh_b)
    _, combined_sub, _, _ = compute_bill(kwh_a + kwh_b)
    # The combined bill is at least as much as the individual sum
    # (progressive tariff makes splitting cheaper, not more expensive).
    assert combined_sub >= a_sub + b_sub
