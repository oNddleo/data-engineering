"""Hypothesis properties — invariants over MST checksum + validator."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from vntax.schema import VATRate
from vntax.taxcode import compute_check_digit, is_valid

from ._fixtures import make_invoice, make_item


@given(prefix=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=200)
def test_compute_check_digit_always_single_digit(prefix: str) -> None:
    """Output is always in ``[0, 9]`` for any 9-digit input."""
    digit = compute_check_digit(prefix)
    assert 0 <= digit <= 9


@given(prefix=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=200)
def test_computed_check_digit_validates(prefix: str) -> None:
    """For any 9-digit prefix, ``prefix + compute_check_digit(prefix)`` is a valid MST."""
    digit = compute_check_digit(prefix)
    assert is_valid(prefix + str(digit)) is True


@given(
    prefix=st.text(alphabet="0123456789", min_size=9, max_size=9),
    bad_digit=st.integers(min_value=0, max_value=9),
)
@settings(max_examples=200)
def test_wrong_check_digit_invalidates(prefix: str, bad_digit: int) -> None:
    """Any non-canonical 10th digit makes the MST invalid."""
    correct = compute_check_digit(prefix)
    if bad_digit == correct:
        return
    assert is_valid(prefix + str(bad_digit)) is False


@given(
    prefix=st.text(alphabet="0123456789", min_size=9, max_size=9),
    branch=st.text(alphabet="0123456789", min_size=3, max_size=3),
)
@settings(max_examples=100)
def test_any_branch_suffix_preserves_validity(prefix: str, branch: str) -> None:
    """A 13-digit MST is valid iff its 10-digit primary is valid."""
    digit = compute_check_digit(prefix)
    valid_primary = prefix + str(digit)
    assert is_valid(valid_primary + branch) is True


@given(
    qty=st.integers(min_value=1, max_value=100),
    unit_price=st.integers(min_value=1_000, max_value=10_000_000),
    rate=st.sampled_from([VATRate.ZERO, VATRate.FIVE, VATRate.EIGHT, VATRate.TEN]),
)
@settings(max_examples=50)
def test_clean_invoice_passes_math_checks(qty: int, unit_price: int, rate: VATRate) -> None:
    """A correctly-computed invoice never produces math-related findings."""
    from vntax.validator import _round_vat, validate  # type: ignore[attr-defined]

    line_total = qty * unit_price
    vat = _round_vat(line_total, rate)
    item = make_item(
        quantity=qty,
        unit_price_vnd=unit_price,
        vat_rate=rate,
        line_total_vnd=line_total,
        vat_amount_vnd=vat,
    )
    inv = make_invoice(items=[item])
    findings = validate(inv)
    math_codes = {
        "LINE_TOTAL_MISMATCH",
        "VAT_AMOUNT_MISMATCH",
        "HEADER_SUBTOTAL_MISMATCH",
        "HEADER_VAT_MISMATCH",
        "HEADER_GRAND_MISMATCH",
    }
    assert not any(f.code in math_codes for f in findings)


@given(
    qty=st.integers(min_value=1, max_value=100),
    unit_price=st.integers(min_value=1, max_value=1_000_000),
    rate_choice=st.sampled_from([VATRate.FIVE, VATRate.EIGHT, VATRate.TEN]),
)
@settings(max_examples=50)
def test_vat_rounding_is_within_one_vnd(qty: int, unit_price: int, rate_choice: VATRate) -> None:
    """Computed VAT differs from exact-division by at most 1 VND."""
    from vntax.validator import _round_vat  # type: ignore[attr-defined]

    line_total = qty * unit_price
    computed = _round_vat(line_total, rate_choice)
    exact = line_total * rate_choice.value / 10_000
    assert abs(computed - exact) <= 0.5 + 1e-9
