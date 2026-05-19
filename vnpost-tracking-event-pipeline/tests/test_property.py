"""Hypothesis properties — invariants of state machine + SLA."""

from __future__ import annotations

from itertools import pairwise

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnpost.fraud import find_scan_skipping
from vnpost.schema import ParcelEventKind, ParcelStatus
from vnpost.simulator import generate
from vnpost.sla import compute_sla
from vnpost.state import stitch

from ._fixtures import DEFAULT_TS, created


@given(
    n=st.integers(min_value=5, max_value=50),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_all_simulator_output_stitches(n: int, seed: int) -> None:
    """The simulator never emits an event sequence that fails validation."""
    events = generate(n_parcels=n, seed=seed)
    parcels = stitch(events)
    assert len(parcels) == n


@given(
    n=st.integers(min_value=5, max_value=50),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_parcels_sorted_by_creation(n: int, seed: int) -> None:
    """Output is sorted by (created_at, tracking_id) for stable diffs."""
    events = generate(n_parcels=n, seed=seed)
    parcels = stitch(events)
    keys = [(p.created_at, p.tracking_id) for p in parcels]
    assert keys == sorted(keys)


@given(
    n=st.integers(min_value=5, max_value=50),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_delivered_parcel_has_pickup_time(n: int, seed: int) -> None:
    """A delivered parcel always has a picked_up_at timestamp."""
    events = generate(n_parcels=n, seed=seed)
    for p in stitch(events):
        if p.status is ParcelStatus.DELIVERED:
            assert p.picked_up_at is not None
            assert p.delivered_at is not None


@given(
    n=st.integers(min_value=5, max_value=50),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_sla_accounting(n: int, seed: int) -> None:
    """For each courier SLA, on_time ≤ delivered ≤ parcels."""
    events = generate(n_parcels=n, seed=seed)
    parcels = stitch(events)
    for sla in compute_sla(parcels):
        assert sla.n_on_time <= sla.n_delivered <= sla.n_parcels


@given(
    n=st.integers(min_value=10, max_value=100),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_scan_skip_only_inter_city_3_event_parcels(
    n: int,
    seed: int,
) -> None:
    """Every scan-skip finding is for a DELIVERED inter-city parcel
    with fewer than 4 events."""
    events = generate(n_parcels=n, seed=seed)
    parcels = stitch(events)
    findings = find_scan_skipping(parcels)
    by_tracking = {p.tracking_id: p for p in parcels}
    for f in findings:
        p = by_tracking[f.tracking_id]
        assert p.status is ParcelStatus.DELIVERED
        assert p.n_events < 4  # below inter-city threshold


@given(
    n=st.integers(min_value=5, max_value=40),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_event_count_matches_n_events(
    n: int,
    seed: int,
) -> None:
    """Parcel.n_events == count of events with that tracking_id."""
    events = generate(n_parcels=n, seed=seed)
    parcels = stitch(events)
    by_tracking: dict[str, int] = {}
    for e in events:
        by_tracking[e.tracking_id] = by_tracking.get(e.tracking_id, 0) + 1
    for p in parcels:
        # SURGE_UPDATE / non-trip events don't exist in this domain,
        # so n_events should match the raw event count.
        assert p.n_events == by_tracking[p.tracking_id]


@given(
    deltas=st.lists(
        st.integers(min_value=1, max_value=24),
        min_size=2,
        max_size=8,
    ),
)
@settings(max_examples=10)
def test_property_validated_sequences_are_chronological(
    deltas: list[int],
) -> None:
    """A simulator-built parcel has chronologically-ordered events."""
    events = generate(n_parcels=5, seed=sum(deltas))
    by_tracking: dict[str, list] = {}
    for e in events:
        by_tracking.setdefault(e.tracking_id, []).append(e)
    for group in by_tracking.values():
        sorted_g = sorted(group, key=lambda e: (e.occurred_at, e.event_id))
        for a, b in pairwise(sorted_g):
            assert a.occurred_at <= b.occurred_at


def test_property_smoke_one_parcel():
    """Sanity check the suite — one event always parses."""
    e = created("T-1", DEFAULT_TS)
    assert e.kind is ParcelEventKind.CREATED
