"""CIC group definitions per Thông tư 11/2021/TT-NHNN.

The State Bank of Vietnam (NHNN) classifies every outstanding loan
into one of five groups based on overdue duration. Each group carries
a mandatory loan-loss provision rate that lenders must hold against
the outstanding principal.

The five groups (with the Vietnamese names that appear on every CIC
report):

| Group | Vietnamese name              | Overdue (days) | Provision |
| ----- | ---------------------------- | -------------- | --------- |
| 1     | Nợ đủ tiêu chuẩn             | 0–9            | 0 %       |
| 2     | Nợ cần chú ý                 | 10–89          | 5 %       |
| 3     | Nợ dưới tiêu chuẩn           | 90–179         | 20 %      |
| 4     | Nợ nghi ngờ                  | 180–359        | 50 %      |
| 5     | Nợ có khả năng mất vốn       | ≥ 360          | 100 %     |

There is also a "downgrade cascade" rule: once a borrower has any
contract in group X, every other contract owned by the same borrower
is automatically reclassified to *at least* group X. We model that
explicitly in :mod:`cicscore.features` because it changes effective
group at every observation date.
"""

from __future__ import annotations

from enum import IntEnum


class CICGroup(IntEnum):
    """The five CIC classification groups."""

    GROUP_1 = 1
    GROUP_2 = 2
    GROUP_3 = 3
    GROUP_4 = 4
    GROUP_5 = 5


PROVISION_RATE: dict[CICGroup, float] = {
    CICGroup.GROUP_1: 0.0,
    CICGroup.GROUP_2: 0.05,
    CICGroup.GROUP_3: 0.20,
    CICGroup.GROUP_4: 0.50,
    CICGroup.GROUP_5: 1.0,
}
"""Loan-loss provision rate per Thông tư 11/2021/TT-NHNN Điều 12."""

VN_NAMES: dict[CICGroup, str] = {
    CICGroup.GROUP_1: "Nợ đủ tiêu chuẩn",
    CICGroup.GROUP_2: "Nợ cần chú ý",
    CICGroup.GROUP_3: "Nợ dưới tiêu chuẩn",
    CICGroup.GROUP_4: "Nợ nghi ngờ",
    CICGroup.GROUP_5: "Nợ có khả năng mất vốn",
}


def group_from_days_past_due(days: int) -> CICGroup:
    """Map days-past-due to CIC group per the cutoffs above.

    Negative input is treated as zero (not overdue).
    """
    if days <= 0:
        return CICGroup.GROUP_1
    if days < 10:
        return CICGroup.GROUP_1
    if days < 90:
        return CICGroup.GROUP_2
    if days < 180:
        return CICGroup.GROUP_3
    if days < 360:
        return CICGroup.GROUP_4
    return CICGroup.GROUP_5


def provision_amount_vnd(group: CICGroup, outstanding_principal_vnd: int) -> int:
    """Round-down provision in VND. Banks must hold this against the loan."""
    if outstanding_principal_vnd < 0:
        raise ValueError(f"outstanding_principal must be >= 0, got {outstanding_principal_vnd}")
    return int(outstanding_principal_vnd * PROVISION_RATE[group])


__all__ = [
    "PROVISION_RATE",
    "VN_NAMES",
    "CICGroup",
    "group_from_days_past_due",
    "provision_amount_vnd",
]
