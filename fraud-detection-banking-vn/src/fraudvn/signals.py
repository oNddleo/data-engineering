"""Individual fraud-signal detectors.

Each detector is a function
``(req, src_state, dst_state, blacklist) → list[SignalHit]``. The
engine flattens the results and sums points.

The signals here are the ones we believe are *both* (a) reasonably
unambiguous indicators of fraud and (b) cheap to compute under a
200 ms real-time budget. We deliberately do not bundle anything
that needs an ML-model call — every signal is a deterministic
arithmetic rule.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from fraudvn.keywords import KEYWORD_CATEGORY_WEIGHTS, find_scam_keywords
from fraudvn.schema import SignalHit

if TYPE_CHECKING:
    from fraudvn.schema import TransactionRequest
    from fraudvn.state import AccountState


# Default weights & thresholds. Callers can override on the engine.

NEW_BENEFICIARY_AMOUNT_THRESHOLD = 5_000_000
NEW_BENEFICIARY_POINTS = 25

NIGHT_HOUR_START = 23  # inclusive
NIGHT_HOUR_END = 5  # exclusive
NIGHT_TRANSFER_POINTS = 10

OTP_RACE_SECONDS = 10
OTP_RACE_POINTS = 35

ROUND_AMOUNT_BAND_LOW = 9_500_000
ROUND_AMOUNT_BAND_HIGH = 10_000_000
ROUND_AMOUNT_POINTS = 15

VELOCITY_BURST_WINDOW_SECONDS = 300
VELOCITY_BURST_THRESHOLD = 5
VELOCITY_BURST_POINTS = 25

BENEFICIARY_HOT_WINDOW_SECONDS = 3600
BENEFICIARY_HOT_THRESHOLD = 5
BENEFICIARY_HOT_POINTS = 35

BLACKLIST_POINTS = 100


# ---------------------------------------------------------------------------
# Keyword signal — fires multiple hits, one per matched category.


def signal_keyword(req: TransactionRequest) -> list[SignalHit]:
    matches = find_scam_keywords(req.narrative)
    out: list[SignalHit] = []
    for cat, hits in matches.items():
        out.append(
            SignalHit(
                name=f"KEYWORD_{cat}",
                points=KEYWORD_CATEGORY_WEIGHTS[cat],
                detail=f"narrative matches {cat}: " + ", ".join(hits[:3]),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Blacklist beneficiary — instant block.


def signal_blacklist_beneficiary(
    req: TransactionRequest, *, blacklist: frozenset[str]
) -> list[SignalHit]:
    if req.beneficiary_account in blacklist:
        return [
            SignalHit(
                name="BLACKLIST_BENEFICIARY",
                points=BLACKLIST_POINTS,
                detail=f"beneficiary {req.beneficiary_account} is blacklisted",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# New beneficiary + large amount.


def signal_new_beneficiary_large(
    req: TransactionRequest, *, src_state: AccountState
) -> list[SignalHit]:
    if req.beneficiary_account in src_state.prior_beneficiaries:
        return []
    if req.amount_vnd < NEW_BENEFICIARY_AMOUNT_THRESHOLD:
        return []
    return [
        SignalHit(
            name="NEW_BENEFICIARY_LARGE",
            points=NEW_BENEFICIARY_POINTS,
            detail=(
                f"first-time transfer to {req.beneficiary_account} for "
                f"{req.amount_vnd:,} VND (threshold {NEW_BENEFICIARY_AMOUNT_THRESHOLD:,})"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Night-time transfer.


def signal_night_transfer(req: TransactionRequest) -> list[SignalHit]:
    hour = req.occurred_at.hour
    in_window = hour >= NIGHT_HOUR_START or hour < NIGHT_HOUR_END
    if not in_window:
        return []
    return [
        SignalHit(
            name="NIGHT_TRANSFER",
            points=NIGHT_TRANSFER_POINTS,
            detail=f"transfer at {hour:02d}:xx local — outside business hours",
        )
    ]


# ---------------------------------------------------------------------------
# OTP race — verified within seconds of issuance.


def signal_otp_race(req: TransactionRequest) -> list[SignalHit]:
    if req.otp_issued_at is None or req.otp_verified_at is None:
        return []
    delta = (req.otp_verified_at - req.otp_issued_at).total_seconds()
    if delta >= OTP_RACE_SECONDS:
        return []
    return [
        SignalHit(
            name="OTP_RACE",
            points=OTP_RACE_POINTS,
            detail=(
                f"OTP verified {delta:.1f}s after issuance (threshold {OTP_RACE_SECONDS}s) — "
                "may indicate phone handover or SIM-swap attacker"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Just-below-threshold amount (structuring signature).


def signal_round_amount_below(req: TransactionRequest) -> list[SignalHit]:
    if not (ROUND_AMOUNT_BAND_LOW < req.amount_vnd <= ROUND_AMOUNT_BAND_HIGH):
        return []
    return [
        SignalHit(
            name="ROUND_AMOUNT_BELOW_10M",
            points=ROUND_AMOUNT_POINTS,
            detail=(
                f"amount {req.amount_vnd:,} VND is in the just-below-10M structuring band "
                f"({ROUND_AMOUNT_BAND_LOW:,} < x <= {ROUND_AMOUNT_BAND_HIGH:,})"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Velocity burst — many outgoing in a short window.


def signal_velocity_burst(req: TransactionRequest, *, src_state: AccountState) -> list[SignalHit]:
    cutoff = req.occurred_at - timedelta(seconds=VELOCITY_BURST_WINDOW_SECONDS)
    recent = sum(1 for _, ts in src_state.recent_outgoing if ts >= cutoff)
    if recent < VELOCITY_BURST_THRESHOLD:
        return []
    return [
        SignalHit(
            name="VELOCITY_BURST",
            points=VELOCITY_BURST_POINTS,
            detail=(
                f"{recent} outgoing in last {VELOCITY_BURST_WINDOW_SECONDS}s "
                f"(threshold {VELOCITY_BURST_THRESHOLD})"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Beneficiary "hot" — receives from many distinct sources in a window.


def signal_beneficiary_hot(req: TransactionRequest, *, dst_state: AccountState) -> list[SignalHit]:
    cutoff = req.occurred_at - timedelta(seconds=BENEFICIARY_HOT_WINDOW_SECONDS)
    distinct_sources = {src for src, ts in dst_state.recent_incoming_sources if ts >= cutoff}
    if len(distinct_sources) < BENEFICIARY_HOT_THRESHOLD:
        return []
    return [
        SignalHit(
            name="BENEFICIARY_HOT",
            points=BENEFICIARY_HOT_POINTS,
            detail=(
                f"beneficiary received from {len(distinct_sources)} distinct sources "
                f"in last {BENEFICIARY_HOT_WINDOW_SECONDS}s "
                f"(threshold {BENEFICIARY_HOT_THRESHOLD})"
            ),
        )
    ]


__all__ = [
    "BENEFICIARY_HOT_POINTS",
    "BENEFICIARY_HOT_THRESHOLD",
    "BENEFICIARY_HOT_WINDOW_SECONDS",
    "BLACKLIST_POINTS",
    "NEW_BENEFICIARY_AMOUNT_THRESHOLD",
    "NEW_BENEFICIARY_POINTS",
    "NIGHT_HOUR_END",
    "NIGHT_HOUR_START",
    "NIGHT_TRANSFER_POINTS",
    "OTP_RACE_POINTS",
    "OTP_RACE_SECONDS",
    "ROUND_AMOUNT_BAND_HIGH",
    "ROUND_AMOUNT_BAND_LOW",
    "ROUND_AMOUNT_POINTS",
    "VELOCITY_BURST_POINTS",
    "VELOCITY_BURST_THRESHOLD",
    "VELOCITY_BURST_WINDOW_SECONDS",
    "signal_beneficiary_hot",
    "signal_blacklist_beneficiary",
    "signal_keyword",
    "signal_new_beneficiary_large",
    "signal_night_transfer",
    "signal_otp_race",
    "signal_round_amount_below",
    "signal_velocity_burst",
]
