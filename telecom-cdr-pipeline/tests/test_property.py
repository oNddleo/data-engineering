"""Hypothesis property tests covering rating, billing, and IO invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from cdrpipe.billing import aggregate_bills
from cdrpipe.carriers import all_profiles, carrier_for, normalise_msisdn
from cdrpipe.io_jsonl import (
    cdr_from_dict,
    cdr_to_dict,
    dump_cdrs,
    load_cdrs,
)
from cdrpipe.rating import VAT_BPS, billable_minutes, rate
from cdrpipe.schema import CDR, VN_TZ, CDRKind

# ---------- strategy helpers ------------------------------------------------


_all_prefixes = tuple(pfx for prof in all_profiles() for pfx in prof.prefixes)


@st.composite
def vn_msisdn(draw: st.DrawFn) -> str:
    prefix = draw(st.sampled_from(_all_prefixes))
    tail = draw(st.integers(min_value=0, max_value=9_999_999))
    return f"{prefix}{tail:07d}"


@st.composite
def voice_cdrs(draw: st.DrawFn) -> CDR:
    sub = draw(vn_msisdn())
    peer = draw(vn_msisdn())
    duration = draw(st.integers(min_value=1, max_value=3600))
    day_offset = draw(st.integers(min_value=0, max_value=29))
    hour = draw(st.integers(min_value=0, max_value=23))
    cdr_id = draw(st.text(min_size=1, max_size=8, alphabet="0123456789ABCDEF"))
    return CDR(
        cdr_id=f"V-{cdr_id}-{day_offset}-{hour}",
        subscriber_msisdn=sub,
        peer_msisdn=peer,
        kind=CDRKind.VOICE,
        occurred_at=datetime(2026, 5, 1, hour, 0, tzinfo=VN_TZ) + timedelta(days=day_offset),
        duration_seconds=duration,
    )


# ---------- properties ------------------------------------------------------


@given(st.integers(min_value=0, max_value=100_000))
def test_billable_minutes_monotonic(seconds: int) -> None:
    assert billable_minutes(seconds) <= billable_minutes(seconds + 1)


@given(st.integers(min_value=0, max_value=10_000))
def test_billable_minutes_never_negative(seconds: int) -> None:
    assert billable_minutes(seconds) >= 0


@given(st.integers(min_value=6, max_value=86_400))
def test_billable_minutes_at_least_one_above_block(seconds: int) -> None:
    assert billable_minutes(seconds) >= 1


@given(voice_cdrs())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_rate_vat_is_exactly_ten_percent(c: CDR) -> None:
    r = rate(c)
    expected_vat = (r.rated_amount_vnd * VAT_BPS) // 10_000
    assert r.vat_amount_vnd == expected_vat


@given(voice_cdrs())
@settings(max_examples=80)
def test_rate_amounts_non_negative(c: CDR) -> None:
    r = rate(c)
    assert r.rated_amount_vnd >= 0
    assert r.vat_amount_vnd >= 0
    assert r.total_vnd >= 0


@given(voice_cdrs())
@settings(max_examples=80)
def test_rate_total_consistent(c: CDR) -> None:
    r = rate(c)
    assert r.total_vnd == r.rated_amount_vnd + r.vat_amount_vnd


@given(st.lists(voice_cdrs(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_bill_total_equals_sum_of_rated(cdrs: list[CDR]) -> None:
    """Sum of per-CDR amounts equals the bill total — pure conservation."""
    # Deduplicate by cdr_id to avoid hypothesis dup collisions.
    seen: set[str] = set()
    unique: list[CDR] = []
    for c in cdrs:
        if c.cdr_id not in seen:
            seen.add(c.cdr_id)
            unique.append(c)
    assume(unique)
    rated = [rate(c) for c in unique]
    bills = aggregate_bills(rated)
    total_pre_vat = sum(r.rated_amount_vnd for r in rated)
    total_vat = sum(r.vat_amount_vnd for r in rated)
    assert sum(b.pre_vat_amount_vnd for b in bills) == total_pre_vat
    assert sum(b.vat_amount_vnd for b in bills) == total_vat


@given(voice_cdrs())
@settings(max_examples=60)
def test_cdr_jsonl_roundtrip(c: CDR) -> None:
    assert cdr_from_dict(cdr_to_dict(c)) == c


@given(st.lists(voice_cdrs(), min_size=0, max_size=10))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_cdr_list_jsonl_roundtrip(cdrs: list[CDR]) -> None:
    seen: set[str] = set()
    unique: list[CDR] = []
    for c in cdrs:
        if c.cdr_id not in seen:
            seen.add(c.cdr_id)
            unique.append(c)
    assert load_cdrs(dump_cdrs(unique)) == unique


@given(vn_msisdn())
def test_normalise_msisdn_idempotent(m: str) -> None:
    assert normalise_msisdn(normalise_msisdn(m)) == normalise_msisdn(m)


@given(vn_msisdn())
def test_carrier_for_known_for_any_vn_msisdn(m: str) -> None:
    """Any MSISDN generated with a known VN prefix resolves to a real carrier."""
    c = carrier_for(m)
    assert c.value != "UNKNOWN"


@given(vn_msisdn())
def test_normalise_msisdn_e164_equivalent(m: str) -> None:
    """The +84 form of an MSISDN normalises to the same 0X form."""
    e164 = "+84" + m[1:]
    assert normalise_msisdn(e164) == normalise_msisdn(m)
