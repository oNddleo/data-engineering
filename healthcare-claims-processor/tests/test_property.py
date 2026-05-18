"""Hypothesis properties — invariants of card / coverage / calculator."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bhyt.calculator import calculate
from bhyt.card import decode_prefix, is_valid_format
from bhyt.coverage import base_rate_bps, effective_rate_bps
from bhyt.schema import CareLevel, ExemptionCategory

from ._fixtures import make_card, make_claim, make_item


@given(
    scheme=st.sampled_from("DHTCGX"),
    priority=st.sampled_from("12345"),
    suffix=st.text(alphabet="0123456789", min_size=13, max_size=13),
)
@settings(max_examples=100)
def test_any_valid_format_decodes(scheme: str, priority: str, suffix: str) -> None:
    """A correctly-shaped card always decodes without raising."""
    card = scheme + priority + suffix
    assert is_valid_format(card) is True
    info = decode_prefix(card)
    assert info.scheme_letter == scheme
    assert info.priority_letter == priority


@given(
    scheme=st.sampled_from("ABEFIJKL"),  # not in DHTCGX
    priority=st.sampled_from("12345"),
    suffix=st.text(alphabet="0123456789", min_size=13, max_size=13),
)
@settings(max_examples=50)
def test_unknown_scheme_letter_rejected(
    scheme: str,
    priority: str,
    suffix: str,
) -> None:
    """Any letter outside the registered scheme set fails validation."""
    card = scheme + priority + suffix
    assert is_valid_format(card) is False


@given(category=st.sampled_from(list(ExemptionCategory)))
@settings(max_examples=10)
def test_base_rate_in_valid_range(category: ExemptionCategory) -> None:
    """Base rate is always in [0, 10_000] basis points."""
    bps = base_rate_bps(category)
    assert 0 <= bps <= 10_000


@given(
    visited=st.sampled_from(list(CareLevel)),
    has_ref=st.booleans(),
    same_prov=st.booleans(),
    emergency=st.booleans(),
)
@settings(max_examples=60)
def test_effective_rate_in_valid_range(
    visited: CareLevel,
    has_ref: bool,
    same_prov: bool,
    emergency: bool,
) -> None:
    """Both components of the effective rate are in [0, 10_000]."""
    base, penalty = effective_rate_bps(
        category=ExemptionCategory.UU_TIEN_4,
        visited_level=visited,
        has_referral=has_ref,
        same_province=same_prov,
        emergency=emergency,
    )
    assert 0 <= base <= 10_000
    assert 0 <= penalty <= 10_000


@given(
    subtotal=st.integers(min_value=0, max_value=10_000_000_000),
    care=st.sampled_from(list(CareLevel)),
    referral=st.booleans(),
    same_prov=st.booleans(),
)
@settings(max_examples=80)
def test_calc_insurer_plus_patient_equals_subtotal(
    subtotal: int,
    care: CareLevel,
    referral: bool,
    same_prov: bool,
) -> None:
    """Co-pay arithmetic: ``insurer + patient == subtotal`` for any claim."""
    item = make_item(quantity=1, unit_price_vnd=subtotal, line_total_vnd=subtotal)
    claim = make_claim(
        items=(item,),
        subtotal_vnd=subtotal,
        care_level=care,
        has_referral=referral,
        same_province=same_prov,
    )
    r = calculate(claim)
    assert r.insurer_pays_vnd + r.patient_pays_vnd == subtotal


@given(
    subtotal=st.integers(min_value=0, max_value=1_000_000_000),
)
@settings(max_examples=30)
def test_calc_insurer_never_exceeds_subtotal(subtotal: int) -> None:
    """Insurer payment is always in [0, subtotal]."""
    item = make_item(quantity=1, unit_price_vnd=subtotal, line_total_vnd=subtotal)
    claim = make_claim(items=(item,), subtotal_vnd=subtotal)
    r = calculate(claim)
    assert 0 <= r.insurer_pays_vnd <= subtotal


@given(
    subtotal=st.integers(min_value=1_000, max_value=1_000_000_000),
)
@settings(max_examples=30)
def test_calc_emergency_pays_at_least_as_much_as_non_emergency(
    subtotal: int,
) -> None:
    """Emergency calc always pays >= non-emergency for the same claim."""
    item = make_item(quantity=1, unit_price_vnd=subtotal, line_total_vnd=subtotal)
    claim = make_claim(
        items=(item,),
        subtotal_vnd=subtotal,
        care_level=CareLevel.TU,
        has_referral=False,
        same_province=False,
    )
    normal = calculate(claim)
    emerg = calculate(claim, emergency=True)
    assert emerg.insurer_pays_vnd >= normal.insurer_pays_vnd


def test_default_card_passes():
    """Sanity property test entry point — fixture is well-formed."""
    assert is_valid_format(make_card().card_number)
