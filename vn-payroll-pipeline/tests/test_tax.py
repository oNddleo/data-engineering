"""PIT computation tests."""

from __future__ import annotations

import pytest

from payroll.schema import ResidencyStatus
from payroll.tax import (
    DEPENDENT_ALLOWANCE_VND,
    NON_RESIDENT_RATE_BPS,
    PERSONAL_ALLOWANCE_VND,
    compute_pit,
    resident_brackets,
    taxable_income,
)


def test_personal_allowance_11m() -> None:
    """Nghị quyết 954/2020/UBTVQH14."""
    assert PERSONAL_ALLOWANCE_VND == 11_000_000


def test_dependent_allowance_4_4m() -> None:
    assert DEPENDENT_ALLOWANCE_VND == 4_400_000


def test_seven_brackets() -> None:
    assert len(resident_brackets()) == 7


def test_taxable_below_personal_allowance() -> None:
    """Gross 10M, no dependents, no insurance → 0 taxable."""
    assert taxable_income(10_000_000, 0, 0) == 0


def test_taxable_above_allowance() -> None:
    """Gross 30M − insurance 3M − personal 11M − dep 4.4M = 11.6M."""
    assert taxable_income(30_000_000, 3_000_000, 1) == 11_600_000


def test_compute_pit_zero_for_below_threshold() -> None:
    pit, taxable = compute_pit(
        gross_vnd=10_000_000,
        insurance_employee_vnd=1_050_000,
        n_dependents=0,
        residency=ResidencyStatus.RESIDENT,
    )
    assert pit == 0
    assert taxable == 0


def test_compute_pit_first_bracket() -> None:
    """Taxable 3M → 5% bracket → 150k PIT."""
    pit, taxable = compute_pit(
        gross_vnd=14_000_000,
        insurance_employee_vnd=0,
        n_dependents=0,
        residency=ResidencyStatus.RESIDENT,
    )
    # Taxable = 14M - 11M = 3M → 3M × 5% = 150k.
    assert taxable == 3_000_000
    assert pit == 150_000


def test_compute_pit_spans_two_brackets() -> None:
    """Taxable 7M → 5M × 5% + 2M × 10% = 250k + 200k = 450k."""
    pit, _ = compute_pit(
        gross_vnd=18_000_000,
        insurance_employee_vnd=0,
        n_dependents=0,
        residency=ResidencyStatus.RESIDENT,
    )
    # Taxable = 18M - 11M = 7M.
    assert pit == 5_000_000 * 5 // 100 + 2_000_000 * 10 // 100


def test_compute_pit_non_resident_flat_20() -> None:
    """Non-residents pay flat 20% on gross with no deductions."""
    pit, taxable = compute_pit(
        gross_vnd=50_000_000,
        insurance_employee_vnd=5_250_000,
        n_dependents=3,
        residency=ResidencyStatus.NON_RESIDENT,
    )
    assert pit == 50_000_000 * 20 // 100
    assert taxable == 50_000_000


def test_non_resident_rate_20_percent() -> None:
    assert NON_RESIDENT_RATE_BPS == 2_000


def test_pit_brackets_strictly_progressive() -> None:
    """Each bracket has a higher rate than the previous."""
    brackets = resident_brackets()
    for i in range(1, len(brackets)):
        assert brackets[i].rate_bps > brackets[i - 1].rate_bps


def test_pit_top_bracket_open_ended() -> None:
    assert resident_brackets()[-1].upper_bound_vnd is None


def test_pit_rejects_negative_input() -> None:
    with pytest.raises(ValueError):
        taxable_income(-1, 0, 0)
