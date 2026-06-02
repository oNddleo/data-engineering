"""Telecom-fraud detection — three classic VN-context patterns.

* **Premium-rate spike** — a subscriber suddenly makes many calls
  to 1900XXX premium numbers, often after their SIM is compromised.
  Triggered when ``premium_voice_minutes > min_minutes`` (default 30
  min/day, where typical legitimate usage is < 2 min/day).

* **Foreign-roaming anomaly** — roaming charges arrive for a
  subscriber whose recent history shows no foreign travel pattern.
  Surfaces any roaming CDR over ``min_roaming_amount`` VND.

* **SIM-swap signal** — the subscriber's MSISDN suddenly shows
  a markedly different calling pattern (many calls to new peers,
  no calls to historical peers). Heuristic: in a 24-hour window,
  the Jaccard similarity of the peer set against the prior 30-day
  baseline drops below ``min_jaccard`` (default 0.10).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING

from cdrpipe.schema import CDRKind

if TYPE_CHECKING:
    from cdrpipe.schema import CDR, Carrier, RatedCDR


class FraudKind(str, Enum):
    """Three telecom-fraud signal types."""

    PREMIUM_RATE_SPIKE = "PREMIUM_RATE_SPIKE"
    FOREIGN_ROAMING = "FOREIGN_ROAMING"
    SIM_SWAP = "SIM_SWAP"


@dataclass(frozen=True, slots=True)
class FraudFinding:
    """One ops-actionable fraud signal."""

    kind: FraudKind
    subscriber_msisdn: str
    carrier: Carrier
    detail: str
    metric: int


def find_premium_rate_spikes(
    rated_cdrs: list[RatedCDR],
    *,
    min_premium_minutes_per_day: int = 30,
) -> list[FraudFinding]:
    """Surface subscribers with > ``min_premium_minutes_per_day`` of
    premium-voice usage in a single day."""
    if min_premium_minutes_per_day < 1:
        raise ValueError("min_premium_minutes_per_day must be >= 1")
    per_day: dict[tuple[str, str], int] = defaultdict(int)
    carrier_by_msisdn: dict[str, Carrier] = {}
    for rc in rated_cdrs:
        if rc.cdr.kind is not CDRKind.VOICE or not rc.cdr.is_premium:
            continue
        day = rc.cdr.occurred_at.date().isoformat()
        per_day[(rc.cdr.subscriber_msisdn, day)] += rc.cdr.duration_seconds
        carrier_by_msisdn[rc.cdr.subscriber_msisdn] = rc.subscriber_carrier
    out: list[FraudFinding] = []
    for (msisdn, day), secs in per_day.items():
        minutes = secs // 60
        if minutes >= min_premium_minutes_per_day:
            out.append(
                FraudFinding(
                    kind=FraudKind.PREMIUM_RATE_SPIKE,
                    subscriber_msisdn=msisdn,
                    carrier=carrier_by_msisdn[msisdn],
                    detail=f"{minutes} min of premium voice on {day}",
                    metric=minutes,
                )
            )
    out.sort(key=lambda f: (-f.metric, f.subscriber_msisdn))
    return out


def find_foreign_roaming(
    rated_cdrs: list[RatedCDR],
    *,
    min_roaming_amount_vnd: int = 100_000,
) -> list[FraudFinding]:
    """Surface subscribers whose roaming charges exceed a threshold."""
    if min_roaming_amount_vnd < 0:
        raise ValueError("min_roaming_amount_vnd must be >= 0")
    per_msisdn: dict[str, int] = defaultdict(int)
    carrier_by_msisdn: dict[str, Carrier] = {}
    for rc in rated_cdrs:
        if not rc.cdr.is_roaming:
            continue
        per_msisdn[rc.cdr.subscriber_msisdn] += rc.rated_amount_vnd
        carrier_by_msisdn[rc.cdr.subscriber_msisdn] = rc.subscriber_carrier
    out: list[FraudFinding] = []
    for msisdn, amount in per_msisdn.items():
        if amount >= min_roaming_amount_vnd:
            out.append(
                FraudFinding(
                    kind=FraudKind.FOREIGN_ROAMING,
                    subscriber_msisdn=msisdn,
                    carrier=carrier_by_msisdn[msisdn],
                    detail=f"roaming charges {amount:,} VND",
                    metric=amount,
                )
            )
    out.sort(key=lambda f: (-f.metric, f.subscriber_msisdn))
    return out


def find_sim_swap(
    cdrs: list[CDR],
    *,
    baseline_days: int = 30,
    suspect_window_hours: int = 24,
    min_baseline_calls: int = 5,
    min_jaccard: float = 0.10,
) -> list[FraudFinding]:
    """Detect SIM-swap by comparing recent peer-set vs historical baseline.

    For each subscriber:

    1. Define the **suspect window** = last ``suspect_window_hours``
       of activity in the input.
    2. Define the **baseline** = the prior ``baseline_days`` of activity.
    3. Skip subscribers with < ``min_baseline_calls`` in baseline
       (too small to judge).
    4. Compute Jaccard similarity of suspect-window peer set vs
       baseline peer set.
    5. If similarity < ``min_jaccard``, flag as SIM_SWAP.
    """
    if baseline_days < 1:
        raise ValueError("baseline_days must be >= 1")
    if suspect_window_hours < 1:
        raise ValueError("suspect_window_hours must be >= 1")
    if min_baseline_calls < 1:
        raise ValueError("min_baseline_calls must be >= 1")
    if not 0 <= min_jaccard <= 1:
        raise ValueError("min_jaccard must be in [0, 1]")

    # Group CDRs by subscriber, sorted by time.
    per_subscriber: dict[str, list[CDR]] = defaultdict(list)
    for c in cdrs:
        if c.kind is CDRKind.VOICE and c.peer_msisdn:
            per_subscriber[c.subscriber_msisdn].append(c)
    for group in per_subscriber.values():
        group.sort(key=lambda c: c.occurred_at)

    from cdrpipe.carriers import carrier_for

    out: list[FraudFinding] = []
    for msisdn, group in per_subscriber.items():
        if not group:
            continue
        latest = group[-1].occurred_at
        suspect_start = latest - timedelta(hours=suspect_window_hours)
        baseline_start = suspect_start - timedelta(days=baseline_days)
        baseline_peers = {
            c.peer_msisdn for c in group if baseline_start <= c.occurred_at < suspect_start
        }
        suspect_peers = {c.peer_msisdn for c in group if c.occurred_at >= suspect_start}
        if len(baseline_peers) < min_baseline_calls or not suspect_peers:
            continue
        union = baseline_peers | suspect_peers
        intersection = baseline_peers & suspect_peers
        jaccard = len(intersection) / len(union) if union else 1.0
        if jaccard < min_jaccard:
            out.append(
                FraudFinding(
                    kind=FraudKind.SIM_SWAP,
                    subscriber_msisdn=msisdn,
                    carrier=carrier_for(msisdn),
                    detail=(
                        f"Jaccard {jaccard:.2f} vs baseline of " f"{len(baseline_peers)} peers"
                    ),
                    metric=int(jaccard * 100),
                )
            )
    out.sort(key=lambda f: (f.metric, f.subscriber_msisdn))
    return out


__all__ = [
    "FraudFinding",
    "FraudKind",
    "find_foreign_roaming",
    "find_premium_rate_spikes",
    "find_sim_swap",
]
