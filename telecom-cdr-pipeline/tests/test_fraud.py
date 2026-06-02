"""Fraud detection: premium-rate, foreign-roaming, SIM-swap."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cdrpipe.fraud import (
    FraudKind,
    find_foreign_roaming,
    find_premium_rate_spikes,
    find_sim_swap,
)
from cdrpipe.rating import rate
from cdrpipe.schema import CDR, VN_TZ, CDRKind

from ._fixtures import make_cdr, voice_cdr

# ---------- premium-rate spikes ---------------------------------------------


def test_find_premium_spike_fires_on_high_volume() -> None:
    """30 minutes of premium voice in one day fires."""
    cdrs = [
        make_cdr(
            cdr_id=f"P-{i}",
            peer_msisdn="19001234",
            kind=CDRKind.VOICE,
            duration_seconds=120,  # 2 min × 20 calls = 40 min
            is_premium=True,
            occurred_at=datetime(2026, 5, 18, i % 24, i // 24, tzinfo=VN_TZ),
        )
        for i in range(20)
    ]
    rated = [rate(c) for c in cdrs]
    findings = find_premium_rate_spikes(rated)
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.PREMIUM_RATE_SPIKE
    assert findings[0].metric == 40


def test_find_premium_spike_silent_on_low_volume() -> None:
    """A single 2-minute premium call must not fire (< 30 min threshold)."""
    c = make_cdr(
        peer_msisdn="19001234",
        kind=CDRKind.VOICE,
        duration_seconds=120,
        is_premium=True,
    )
    findings = find_premium_rate_spikes([rate(c)])
    assert findings == []


def test_find_premium_spike_ignores_non_premium_voice() -> None:
    """Regular high-volume voice doesn't trigger premium fraud."""
    cdrs = [voice_cdr(cdr_id=f"V-{i}", duration_seconds=600) for i in range(10)]
    rated = [rate(c) for c in cdrs]
    assert find_premium_rate_spikes(rated) == []


def test_find_premium_spike_threshold_validation() -> None:
    with pytest.raises(ValueError, match="min_premium_minutes_per_day"):
        find_premium_rate_spikes([], min_premium_minutes_per_day=0)


# ---------- foreign-roaming -------------------------------------------------


def test_find_roaming_fires_above_threshold() -> None:
    """A roaming voice call ≥ 100k VND fires."""
    # Roaming voice = 8,000 VND/min. 15 min = 120,000 VND > 100k threshold.
    c = make_cdr(
        kind=CDRKind.VOICE,
        duration_seconds=15 * 60,
        is_roaming=True,
        occurred_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
    )
    findings = find_foreign_roaming([rate(c)])
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.FOREIGN_ROAMING


def test_find_roaming_silent_below_threshold() -> None:
    c = make_cdr(
        kind=CDRKind.VOICE,
        duration_seconds=60,  # 8,000 VND → below 100k
        is_roaming=True,
    )
    findings = find_foreign_roaming([rate(c)])
    assert findings == []


def test_find_roaming_ignores_non_roaming() -> None:
    """Non-roaming CDRs never trigger roaming fraud."""
    c = voice_cdr(duration_seconds=600, is_roaming=False)
    findings = find_foreign_roaming([rate(c)])
    assert findings == []


def test_find_roaming_custom_threshold() -> None:
    """Caller can lower the threshold to surface smaller amounts."""
    c = make_cdr(
        kind=CDRKind.VOICE,
        duration_seconds=60,
        is_roaming=True,
    )
    findings = find_foreign_roaming([rate(c)], min_roaming_amount_vnd=1_000)
    assert len(findings) == 1


def test_find_roaming_validation() -> None:
    with pytest.raises(ValueError, match="min_roaming_amount_vnd"):
        find_foreign_roaming([], min_roaming_amount_vnd=-1)


# ---------- SIM swap --------------------------------------------------------


def _sim_swap_scenario() -> list[CDR]:
    """Build a CDR stream where the subscriber switches peer set in the last 24h.

    * Baseline 30 days: calls only to peers A/B/C/D/E.
    * Final day: calls only to peers X/Y/Z (no overlap → Jaccard 0).
    """
    base = datetime(2026, 5, 1, 9, 0, tzinfo=VN_TZ)
    sub = "0961234567"
    baseline_peers = [f"099000000{i}" for i in range(5)]
    swap_peers = ["0911111111", "0911111112", "0911111113"]
    cdrs: list[CDR] = []
    # Baseline calls on days 0..28 at noon — cycle through all 5 peers.
    for day in range(29):
        for j, peer in enumerate(baseline_peers):
            cdrs.append(
                make_cdr(
                    cdr_id=f"B-{day}-{j}",
                    subscriber_msisdn=sub,
                    peer_msisdn=peer,
                    kind=CDRKind.VOICE,
                    duration_seconds=60,
                    occurred_at=base + timedelta(days=day, hours=12, minutes=j * 5),
                )
            )
    # Swap day: day 30, brand-new peers (gap of >24h from last baseline).
    for j, peer in enumerate(swap_peers):
        cdrs.append(
            make_cdr(
                cdr_id=f"S-{j}",
                subscriber_msisdn=sub,
                peer_msisdn=peer,
                kind=CDRKind.VOICE,
                duration_seconds=60,
                occurred_at=base + timedelta(days=30, hours=j),
            )
        )
    return cdrs


def test_find_sim_swap_fires_on_peer_switch() -> None:
    findings = find_sim_swap(_sim_swap_scenario())
    assert len(findings) == 1
    assert findings[0].kind is FraudKind.SIM_SWAP
    assert findings[0].metric == 0  # Jaccard 0 → metric 0


def test_find_sim_swap_silent_on_stable_pattern() -> None:
    """Subscriber calling the same peers every day must not fire."""
    base = datetime(2026, 5, 1, 9, 0, tzinfo=VN_TZ)
    sub = "0961234567"
    peer = "0991234567"
    cdrs = [
        make_cdr(
            cdr_id=f"S-{i}",
            subscriber_msisdn=sub,
            peer_msisdn=peer,
            kind=CDRKind.VOICE,
            duration_seconds=60,
            occurred_at=base + timedelta(days=i),
        )
        for i in range(31)
    ]
    findings = find_sim_swap(cdrs)
    assert findings == []


def test_find_sim_swap_skips_short_baseline() -> None:
    """Subscribers with too few baseline calls are not judged."""
    base = datetime(2026, 5, 1, 9, 0, tzinfo=VN_TZ)
    cdrs = [
        make_cdr(
            cdr_id="A",
            subscriber_msisdn="0961234567",
            peer_msisdn="0991234567",
            kind=CDRKind.VOICE,
            duration_seconds=60,
            occurred_at=base,
        ),
        make_cdr(
            cdr_id="B",
            subscriber_msisdn="0961234567",
            peer_msisdn="0911111111",
            kind=CDRKind.VOICE,
            duration_seconds=60,
            occurred_at=base + timedelta(days=30),
        ),
    ]
    assert find_sim_swap(cdrs, min_baseline_calls=5) == []


def test_find_sim_swap_param_validation() -> None:
    with pytest.raises(ValueError, match="baseline_days"):
        find_sim_swap([], baseline_days=0)
    with pytest.raises(ValueError, match="suspect_window_hours"):
        find_sim_swap([], suspect_window_hours=0)
    with pytest.raises(ValueError, match="min_baseline_calls"):
        find_sim_swap([], min_baseline_calls=0)
    with pytest.raises(ValueError, match="min_jaccard"):
        find_sim_swap([], min_jaccard=1.5)
