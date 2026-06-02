"""Seeded synthetic CDR stream generator.

Generates a realistic per-subscriber telco-traffic mix over a month:

* **Voice calls** — duration drawn from a log-normal (median ~ 60s),
  peer chosen by carrier-market-share weighting, peak/off-peak skew
  matches business-hour weighting.
* **SMS** — 4-8 messages per subscriber per day at random hours.
* **Data** — 50-200 MB per day in bursts (modem usage pattern).

Three fraud-injection options:

* ``premium_fraction`` — share of voice CDRs that go to premium 1900
  numbers (default 0.1% in normal mode; 5% for fraud-positive subscribers).
* ``roaming_fraction`` — share of CDRs flagged as roaming.
* ``sim_swap_fraction`` — fraction of subscribers whose peer set
  abruptly changes mid-month.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from cdrpipe.carriers import all_profiles
from cdrpipe.schema import CDR, VN_TZ, CDRKind


def generate(
    *,
    n_subscribers: int = 50,
    n_days: int = 30,
    base_time: datetime | None = None,
    premium_fraction: float = 0.001,
    roaming_fraction: float = 0.005,
    sim_swap_fraction: float = 0.04,
    seed: int = 0,
) -> list[CDR]:
    """Generate a synthetic month of CDRs for ``n_subscribers``."""
    if n_subscribers < 0:
        raise ValueError("n_subscribers must be >= 0")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    if not 0 <= premium_fraction <= 1:
        raise ValueError("premium_fraction must be in [0, 1]")
    if not 0 <= roaming_fraction <= 1:
        raise ValueError("roaming_fraction must be in [0, 1]")
    if not 0 <= sim_swap_fraction <= 1:
        raise ValueError("sim_swap_fraction must be in [0, 1]")

    rng = random.Random(seed)
    base = base_time or datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
    subscribers = _allocate_subscribers(n_subscribers, rng)
    # Mark some subscribers as SIM-swap victims; they get a fresh peer set
    # halfway through the month.
    n_swap = max(1, int(n_subscribers * sim_swap_fraction)) if sim_swap_fraction > 0 else 0
    swap_targets = set(rng.sample(subscribers, k=min(n_swap, n_subscribers)))

    events: list[CDR] = []
    counter = 0

    def _eid() -> str:
        nonlocal counter
        eid = f"C-{counter:010d}"
        counter += 1
        return eid

    for sub in subscribers:
        baseline_peers = [_random_msisdn(rng) for _ in range(rng.randint(5, 15))]
        swap_peers = (
            [_random_msisdn(rng) for _ in range(rng.randint(5, 10))] if sub in swap_targets else []
        )
        for day in range(n_days):
            day_start = base + timedelta(days=day)
            n_voice = rng.randint(2, 8)
            n_sms = rng.randint(2, 6)
            n_data = rng.randint(3, 8)
            # SIM-swap victims: on the FINAL day, switch to a fresh peer set
            # so the detector's 24-hour window cleanly separates baseline
            # peers from suspect peers.
            using_peers = (
                swap_peers if (sub in swap_targets and day == n_days - 1) else baseline_peers
            )
            for _ in range(n_voice):
                peer = "19001234" if rng.random() < premium_fraction else rng.choice(using_peers)
                duration = max(6, int(rng.lognormvariate(4.0, 1.0)))  # median ~ 60s
                hour = rng.randint(0, 23)
                is_roaming = rng.random() < roaming_fraction
                events.append(
                    CDR(
                        cdr_id=_eid(),
                        subscriber_msisdn=sub,
                        peer_msisdn=peer,
                        kind=CDRKind.VOICE,
                        occurred_at=day_start + timedelta(hours=hour, minutes=rng.randint(0, 59)),
                        duration_seconds=duration,
                        is_premium=peer.startswith("1900"),
                        is_roaming=is_roaming,
                    )
                )
            for _ in range(n_sms):
                peer = rng.choice(using_peers)
                events.append(
                    CDR(
                        cdr_id=_eid(),
                        subscriber_msisdn=sub,
                        peer_msisdn=peer,
                        kind=CDRKind.SMS,
                        occurred_at=day_start
                        + timedelta(hours=rng.randint(8, 22), minutes=rng.randint(0, 59)),
                        n_messages=1,
                        is_roaming=rng.random() < roaming_fraction,
                    )
                )
            for _ in range(n_data):
                mb = rng.randint(5, 80)
                events.append(
                    CDR(
                        cdr_id=_eid(),
                        subscriber_msisdn=sub,
                        peer_msisdn="",
                        kind=CDRKind.DATA,
                        occurred_at=day_start
                        + timedelta(hours=rng.randint(0, 23), minutes=rng.randint(0, 59)),
                        bytes_used=mb * 1024 * 1024,
                        is_roaming=rng.random() < roaming_fraction,
                    )
                )
    events.sort(key=lambda e: (e.occurred_at, e.cdr_id))
    return events


def _allocate_subscribers(n: int, rng: random.Random) -> list[str]:
    """Allocate ``n`` MSISDNs across the 5 carriers by their market share."""
    profiles = all_profiles()
    weights = [p.market_share_pct for p in profiles]
    out: list[str] = []
    for i in range(n):
        prof = rng.choices(profiles, weights=weights, k=1)[0]
        prefix = rng.choice(prof.prefixes)
        # Generate a 7-digit subscriber number, seeded by index for uniqueness.
        subscriber_num = f"{(seed_for_index(i, rng)):07d}"
        out.append(prefix + subscriber_num)
    return out


def seed_for_index(i: int, rng: random.Random) -> int:
    """Generate a unique 7-digit subscriber number per index."""
    # Mix the rng with i to keep determinism while ensuring uniqueness.
    return (rng.randint(0, 9_999_999) + i * 7919) % 10_000_000


def _random_msisdn(rng: random.Random) -> str:
    """Generate one random 10-digit VN MSISDN."""
    prof = rng.choice(all_profiles())
    prefix = rng.choice(prof.prefixes)
    return prefix + f"{rng.randint(0, 9_999_999):07d}"


__all__ = ["generate"]
