"""Baseline rule-based credit score.

This is a transparent, hand-tuned scorecard — every penalty and bonus
is named and the contributing reasons are returned alongside the
score. It is **not** a substitute for a properly-trained model; it
exists so the feature pipeline can be exercised end-to-end and so
the order-of-magnitude of each feature's influence is obvious.

Range: 300–900, following the VN consumer-credit convention shared
by CIC and most internal bank cards.

Anchor points:

* 700 baseline (fresh borrower, group 1, no inquiries).
* Group-2 in the 24-month window: −50.
* Group-3: −150.
* Group-4: −250.
* Group-5: −400 (regulatory write-off).
* Every distinct group-2+ month: −5 (multi-month problems compound).
* Each inquiry in the last 6 months: −10.
* DTI > 50 %: −50.
* DTI > 70 %: extra −50 on top.
* ≥ 5 years of credit history: +30.
* ≥ 5 active lenders: −30 (over-lending risk).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cicscore.cic_groups import CICGroup

if TYPE_CHECKING:
    from cicscore.features import FeatureVector


MIN_SCORE = 300
MAX_SCORE = 900
BASE_SCORE = 700


@dataclass(frozen=True, slots=True)
class ScoreReason:
    """One scoring rule's contribution to the final score."""

    label: str
    delta: int


@dataclass(frozen=True, slots=True)
class Score:
    """Output of :func:`baseline_score` — final score + reason trail."""

    borrower_id: str
    score: int
    reasons: tuple[ScoreReason, ...]


_GROUP_PENALTIES: dict[CICGroup, int] = {
    CICGroup.GROUP_1: 0,
    CICGroup.GROUP_2: -50,
    CICGroup.GROUP_3: -150,
    CICGroup.GROUP_4: -250,
    CICGroup.GROUP_5: -400,
}


def baseline_score(features: FeatureVector) -> Score:
    reasons: list[ScoreReason] = []
    score = BASE_SCORE

    if features.max_group_24m is not None:
        delta = _GROUP_PENALTIES[features.max_group_24m]
        if delta != 0:
            reasons.append(ScoreReason(f"max_group_24m={features.max_group_24m.value}", delta))
            score += delta

    if features.months_in_group_2plus_24m > 0:
        delta = -5 * features.months_in_group_2plus_24m
        reasons.append(
            ScoreReason(f"months_in_group_2plus_24m={features.months_in_group_2plus_24m}", delta)
        )
        score += delta

    if features.inquiries_6m > 0:
        delta = -10 * features.inquiries_6m
        reasons.append(ScoreReason(f"inquiries_6m={features.inquiries_6m}", delta))
        score += delta

    if features.dti_ratio is not None:
        if features.dti_ratio > 0.7:
            reasons.append(ScoreReason(f"dti>{0.7:.2f} ({features.dti_ratio:.2f})", -100))
            score -= 100
        elif features.dti_ratio > 0.5:
            reasons.append(ScoreReason(f"dti>{0.5:.2f} ({features.dti_ratio:.2f})", -50))
            score -= 50

    if features.months_since_first_credit is not None and features.months_since_first_credit >= 60:
        reasons.append(ScoreReason("history_>=_5y", +30))
        score += 30

    if features.unique_lenders >= 5:
        reasons.append(ScoreReason(f"unique_lenders={features.unique_lenders}", -30))
        score -= 30

    score = max(MIN_SCORE, min(MAX_SCORE, score))
    return Score(borrower_id=features.borrower_id, score=score, reasons=tuple(reasons))


__all__ = ["BASE_SCORE", "MAX_SCORE", "MIN_SCORE", "Score", "ScoreReason", "baseline_score"]
