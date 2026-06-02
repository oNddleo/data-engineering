"""Coverage rates per (exemption_category, care_level) — encoded in basis points.

The rates come from **Nghị định 146/2018/NĐ-CP Article 14 + 22** and
later amendments. They're the *base* rates before any referral penalty
or service-specific caps.

| Category   | Base rate (correct referral) |
| ---------- | ---------------------------- |
| UU_TIEN_1  | 100%                         |
| UU_TIEN_2  | 100%                         |
| UU_TIEN_3  | 100% (poor) / 95% (near-poor — modelled as 95) |
| UU_TIEN_4  | 80%                          |
| UU_TIEN_5  | 80%                          |

### Referral penalty (Article 22 §3)

When a patient bypasses the referral chain and presents directly at
a higher-tier facility **without a referral**, BHYT pays a reduced
share of what it would otherwise:

| Visited level | Without referral pays |
| ------------- | --------------------- |
| TU            | 40% of base coverage  |
| TINH          | 60% of base coverage  |
| HUYEN         | 100% (no penalty)     |
| XA            | 100% (no penalty)     |
| OTHER         | 100% (no penalty)     |

In addition, if the facility is **outside the patient's home province**
(``same_province=False``), the multiplier from the table above
applies even *with* a referral, with one exception: emergency cases
restore the 100% rate (we expose ``emergency=True`` on the
calculator).

The function below returns base + penalty as separate basis-point
multipliers so the calculator composes them.
"""

from __future__ import annotations

from bhyt.schema import CareLevel, ExemptionCategory

# Base coverage rate in basis points.
_BASE_BPS: dict[ExemptionCategory, int] = {
    ExemptionCategory.UU_TIEN_1: 10_000,
    ExemptionCategory.UU_TIEN_2: 10_000,
    ExemptionCategory.UU_TIEN_3: 9_500,  # 95% (near-poor); 100% for strict poor uses 1 instead
    ExemptionCategory.UU_TIEN_4: 8_000,
    ExemptionCategory.UU_TIEN_5: 8_000,
}


# Referral-penalty multiplier (applied multiplicatively on top of base).
_PENALTY_BPS: dict[CareLevel, int] = {
    CareLevel.TU: 4_000,  # 40%
    CareLevel.TINH: 6_000,  # 60%
    CareLevel.HUYEN: 10_000,  # no penalty
    CareLevel.XA: 10_000,
    CareLevel.OTHER: 10_000,
}


def base_rate_bps(category: ExemptionCategory) -> int:
    """Return the base coverage rate (in basis points) for one category."""
    return _BASE_BPS[category]


def referral_penalty_bps(
    visited_level: CareLevel,
    has_referral: bool,
    same_province: bool,
    emergency: bool = False,
) -> int:
    """Penalty multiplier in basis points (10_000 = no penalty).

    Rules:
    * Emergency restores 100% regardless of referral status.
    * District / commune / other facilities have no penalty even without referral.
    * No-referral or cross-province visits at TU / TINH take the penalty.
    """
    if emergency:
        return 10_000
    if visited_level in (CareLevel.HUYEN, CareLevel.XA, CareLevel.OTHER):
        return 10_000
    if has_referral and same_province:
        return 10_000
    # No referral OR cross-province at TU/TINH → penalty applies.
    return _PENALTY_BPS[visited_level]


def effective_rate_bps(
    category: ExemptionCategory,
    visited_level: CareLevel,
    has_referral: bool,
    same_province: bool,
    emergency: bool = False,
) -> tuple[int, int]:
    """Convenience: return ``(base_bps, penalty_bps)``.

    The calculator multiplies them: ``insurer_pays = subtotal × base × penalty / 10000²``.
    """
    return (
        base_rate_bps(category),
        referral_penalty_bps(
            visited_level=visited_level,
            has_referral=has_referral,
            same_province=same_province,
            emergency=emergency,
        ),
    )


__all__ = [
    "base_rate_bps",
    "effective_rate_bps",
    "referral_penalty_bps",
]
