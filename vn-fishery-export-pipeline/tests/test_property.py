"""Hypothesis property tests."""

from __future__ import annotations

from datetime import date

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnfishery.aggregate import aggregate_by_species, aggregate_by_species_market
from vnfishery.benchmark import benchmark_usd_cents_per_kg, is_dumping_risk
from vnfishery.schema import ExportRecord, Form, Grade, Market, Species

_species = st.sampled_from(list(Species))
_market = st.sampled_from(list(Market))
_grade = st.sampled_from(list(Grade))
_form = st.sampled_from(list(Form))


@st.composite
def _record(draw: st.DrawFn) -> ExportRecord:
    return ExportRecord(
        shipment_id=f"S-{draw(st.integers(min_value=0, max_value=999_999)):06d}",
        exporter_tax_code=f"03{draw(st.integers(min_value=10_000_000, max_value=99_999_999))}",
        species=draw(_species),
        market=draw(_market),
        grade=draw(_grade),
        form=draw(_form),
        weight_kg=draw(st.integers(min_value=1, max_value=100_000)),
        fob_price_usd_cents_per_kg=draw(st.integers(min_value=0, max_value=10_000)),
        shipped_on=date(2026, 1, 1),
    )


@given(st.lists(_record(), min_size=0, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_aggregate_species_totals_match_input(records: list[ExportRecord]) -> None:
    """Sum of per-species totals = grand total."""
    agg = aggregate_by_species(records)
    assert sum(v.n_shipments for v in agg.values()) == len(records)
    assert sum(v.total_weight_kg for v in agg.values()) == sum(r.weight_kg for r in records)
    assert sum(v.total_fob_value_usd_cents for v in agg.values()) == sum(
        r.fob_value_usd_cents for r in records
    )


@given(st.lists(_record(), min_size=0, max_size=50))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_aggregate_species_market_totals_match_input(records: list[ExportRecord]) -> None:
    """Same invariant at the (species, market) granularity."""
    agg = aggregate_by_species_market(records)
    assert sum(v.n_shipments for v in agg.values()) == len(records)


@given(_species, _market, _grade, st.integers(min_value=0, max_value=10_000))
@settings(max_examples=60)
def test_dumping_risk_below_benchmark_minus_threshold(
    species: Species,
    market: Market,
    grade: Grade,
    quoted: int,
) -> None:
    """If benchmark exists, dumping iff quoted < bench * (1 - threshold).
    If no benchmark, never flagged."""
    bench = benchmark_usd_cents_per_kg(species, market, grade)
    flagged = is_dumping_risk(species, market, grade, quoted)
    if bench is None:
        assert flagged is False
    else:
        floor = int(round(bench * 0.75))
        assert flagged == (quoted < floor)
