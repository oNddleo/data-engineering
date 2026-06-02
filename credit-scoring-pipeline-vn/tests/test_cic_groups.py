"""CIC group rule tests."""

from __future__ import annotations

import pytest

from cicscore.cic_groups import (
    PROVISION_RATE,
    VN_NAMES,
    CICGroup,
    group_from_days_past_due,
    provision_amount_vnd,
)


def test_cic_groups_are_intenum_ordered_low_to_high():
    assert (
        CICGroup.GROUP_1 < CICGroup.GROUP_2 < CICGroup.GROUP_3 < CICGroup.GROUP_4 < CICGroup.GROUP_5
    )


def test_group_from_days_zero_is_group_1():
    assert group_from_days_past_due(0) is CICGroup.GROUP_1


def test_group_from_days_negative_is_group_1():
    assert group_from_days_past_due(-5) is CICGroup.GROUP_1


def test_group_cutoff_at_10_days():
    assert group_from_days_past_due(9) is CICGroup.GROUP_1
    assert group_from_days_past_due(10) is CICGroup.GROUP_2


def test_group_cutoff_at_90_days():
    assert group_from_days_past_due(89) is CICGroup.GROUP_2
    assert group_from_days_past_due(90) is CICGroup.GROUP_3


def test_group_cutoff_at_180_days():
    assert group_from_days_past_due(179) is CICGroup.GROUP_3
    assert group_from_days_past_due(180) is CICGroup.GROUP_4


def test_group_cutoff_at_360_days():
    assert group_from_days_past_due(359) is CICGroup.GROUP_4
    assert group_from_days_past_due(360) is CICGroup.GROUP_5


def test_provision_rates_match_circular_11():
    assert PROVISION_RATE[CICGroup.GROUP_1] == 0.0
    assert PROVISION_RATE[CICGroup.GROUP_2] == 0.05
    assert PROVISION_RATE[CICGroup.GROUP_3] == 0.20
    assert PROVISION_RATE[CICGroup.GROUP_4] == 0.50
    assert PROVISION_RATE[CICGroup.GROUP_5] == 1.0


def test_provision_amount_simple_cases():
    assert provision_amount_vnd(CICGroup.GROUP_1, 1_000_000_000) == 0
    assert provision_amount_vnd(CICGroup.GROUP_2, 1_000_000_000) == 50_000_000
    assert provision_amount_vnd(CICGroup.GROUP_3, 1_000_000_000) == 200_000_000
    assert provision_amount_vnd(CICGroup.GROUP_4, 1_000_000_000) == 500_000_000
    assert provision_amount_vnd(CICGroup.GROUP_5, 1_000_000_000) == 1_000_000_000


def test_provision_rejects_negative_principal():
    with pytest.raises(ValueError):
        provision_amount_vnd(CICGroup.GROUP_2, -1)


def test_vn_names_cover_all_groups():
    for g in CICGroup:
        assert g in VN_NAMES
        assert VN_NAMES[g]  # non-empty


def test_vn_names_match_circular_wording():
    assert VN_NAMES[CICGroup.GROUP_1] == "Nợ đủ tiêu chuẩn"
    assert VN_NAMES[CICGroup.GROUP_5] == "Nợ có khả năng mất vốn"
