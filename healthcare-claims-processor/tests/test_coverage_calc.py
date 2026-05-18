"""Coverage rules + reimbursement calculation."""

from __future__ import annotations

from bhyt.calculator import calculate
from bhyt.coverage import base_rate_bps, effective_rate_bps, referral_penalty_bps
from bhyt.schema import CareLevel, ExemptionCategory

from ._fixtures import make_card, make_claim, make_item

# ---------- coverage ------------------------------------------------------


def test_base_rate_uu_tien_1_is_100pct():
    assert base_rate_bps(ExemptionCategory.UU_TIEN_1) == 10_000


def test_base_rate_uu_tien_4_is_80pct():
    assert base_rate_bps(ExemptionCategory.UU_TIEN_4) == 8_000


def test_base_rate_uu_tien_3_is_95pct():
    """UU_TIEN_3 is the 95% near-poor band."""
    assert base_rate_bps(ExemptionCategory.UU_TIEN_3) == 9_500


def test_referral_penalty_no_penalty_at_huyen_without_referral():
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.HUYEN,
            has_referral=False,
            same_province=True,
        )
        == 10_000
    )


def test_referral_penalty_40pct_at_tu_without_referral():
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.TU,
            has_referral=False,
            same_province=True,
        )
        == 4_000
    )


def test_referral_penalty_60pct_at_tinh_without_referral():
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.TINH,
            has_referral=False,
            same_province=True,
        )
        == 6_000
    )


def test_referral_penalty_no_penalty_at_tu_with_referral_same_province():
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.TU,
            has_referral=True,
            same_province=True,
        )
        == 10_000
    )


def test_referral_penalty_applies_cross_province_at_tu_even_with_referral():
    """Cross-province at central hospital triggers penalty even with referral."""
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.TU,
            has_referral=True,
            same_province=False,
        )
        == 4_000
    )


def test_referral_penalty_emergency_overrides():
    assert (
        referral_penalty_bps(
            visited_level=CareLevel.TU,
            has_referral=False,
            same_province=False,
            emergency=True,
        )
        == 10_000
    )


def test_effective_rate_decomposes_base_and_penalty():
    base, penalty = effective_rate_bps(
        category=ExemptionCategory.UU_TIEN_4,
        visited_level=CareLevel.TINH,
        has_referral=False,
        same_province=True,
    )
    assert base == 8_000
    assert penalty == 6_000


# ---------- calculator ----------------------------------------------------


def test_calc_simple_huyen_employer_with_referral():
    """UU_TIEN_4 at HUYEN with referral → 80% coverage, no penalty."""
    claim = make_claim(
        items=(make_item(quantity=10, line_total_vnd=500_000),),
        care_level=CareLevel.HUYEN,
        has_referral=True,
        same_province=True,
    )
    r = calculate(claim)
    assert r.coverage_rate_bps == 8_000
    assert r.referral_penalty_bps == 10_000
    assert r.insurer_pays_vnd == 400_000  # 80% of 500_000
    assert r.patient_pays_vnd == 100_000


def test_calc_tu_without_referral_40pct_penalty():
    """UU_TIEN_4 at TU without referral → 80% × 40% = 32% effective."""
    claim = make_claim(
        items=(make_item(quantity=10, line_total_vnd=1_000_000),),
        care_level=CareLevel.TU,
        has_referral=False,
        same_province=True,
    )
    r = calculate(claim)
    assert r.coverage_rate_bps == 8_000
    assert r.referral_penalty_bps == 4_000
    assert r.insurer_pays_vnd == 320_000  # 32% of 1M
    assert r.patient_pays_vnd == 680_000


def test_calc_uu_tien_1_full_coverage_at_correct_tier():
    """Children at HUYEN → 100% coverage."""
    claim = make_claim(
        card_number="T10179012345678",  # T scheme + priority 1 = UU_TIEN_1
        items=(make_item(quantity=2, line_total_vnd=200_000),),
        care_level=CareLevel.HUYEN,
    )
    r = calculate(claim)
    assert r.insurer_pays_vnd == 200_000
    assert r.patient_pays_vnd == 0


def test_calc_emergency_waives_penalty():
    claim = make_claim(
        items=(make_item(quantity=10, line_total_vnd=1_000_000),),
        care_level=CareLevel.TU,
        has_referral=False,
        same_province=False,
    )
    r = calculate(claim, emergency=True)
    # 80% × 100% = 80%
    assert r.insurer_pays_vnd == 800_000


def test_calc_bad_card_format_skips_coverage():
    """A card with bad format pays 0 from insurer and notes the problem."""
    claim = make_claim(card_number="X90179012345678")  # priority 9 not allowed
    r = calculate(claim)
    assert r.insurer_pays_vnd == 0
    assert r.patient_pays_vnd == r.subtotal_vnd
    assert any("card_number" in note for note in r.notes)


def test_calc_flags_line_math_mismatch():
    """A line where line_total != qty × unit_price is noted."""
    bad_item = make_item(quantity=2, unit_price_vnd=100_000, line_total_vnd=200_001)
    claim = make_claim(items=(bad_item,), subtotal_vnd=200_001)
    r = calculate(claim)
    assert any("line_total" in note for note in r.notes)


def test_calc_flags_header_subtotal_mismatch():
    """Header total disagreeing with sum-of-items is flagged."""
    item = make_item(quantity=2, unit_price_vnd=100_000, line_total_vnd=200_000)
    claim = make_claim(items=(item,), subtotal_vnd=999_999)
    r = calculate(claim)
    assert any("subtotal" in note for note in r.notes)


def test_calc_zero_subtotal_zero_payouts():
    item = make_item(unit_price_vnd=0, line_total_vnd=0)
    claim = make_claim(items=(item,), subtotal_vnd=0)
    r = calculate(claim)
    assert r.insurer_pays_vnd == 0
    assert r.patient_pays_vnd == 0


def test_calc_cross_province_tu_with_referral_still_penalised():
    """Even with a referral, going to a TƯ hospital in another province takes penalty."""
    claim = make_claim(
        items=(make_item(quantity=10, line_total_vnd=1_000_000),),
        care_level=CareLevel.TU,
        has_referral=True,
        same_province=False,
    )
    r = calculate(claim)
    # 80% × 40% = 32%
    assert r.insurer_pays_vnd == 320_000


def test_make_card_default_passes():
    """Sanity — the fixture builds a legal default card."""
    card = make_card()
    assert card.card_number.startswith("D4")
