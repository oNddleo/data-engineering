"""Mobile-ad fraud detection — two classic attack patterns.

**Click-injection** (a.k.a. "click flooding") — a malicious source
fires a click event a fraction of a second before the install event,
claiming attribution for an organic install. The tell: the
attribution lag is implausibly short. Adjust's published threshold
is **20 seconds**; below that, the click was almost certainly fired
in response to the install-broadcast intent, not the other way
round.

**Install-spam** (a.k.a. "device farm") — a single source emits
many installs per unit time on devices that don't actually open the
app. The tell: the source's CTR (click → install) is normal, but
the **D1 retention rate** is collapsed (< 5% vs typical 20-40%).
We surface sources whose D1 retention is below ``min_d1_rate_pct``
and whose install volume exceeds ``min_installs``.

Both detectors are pure functions over (events, attributions) — no
clock dependencies, easy to test deterministically.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from mappev.schema import EventKind

if TYPE_CHECKING:
    from mappev.schema import Attribution, Event


class FraudKind(str, Enum):
    CLICK_INJECTION = "CLICK_INJECTION"
    INSTALL_SPAM = "INSTALL_SPAM"


@dataclass(frozen=True, slots=True)
class FraudFinding:
    """One ops-actionable fraud signal."""

    kind: FraudKind
    source: str  # the suspicious source name
    detail: str
    metric: int  # context-dependent: seconds for CLICK_INJECTION; pct×100 for INSTALL_SPAM
    devices_affected: int


def find_click_injection(
    attributions: list[Attribution],
    *,
    min_lag_seconds: int = 20,
) -> list[FraudFinding]:
    """Surface sources where many installs have attribution lag < ``min_lag_seconds``.

    Returns one finding per ``(source, campaign)`` with at least
    ``min_devices_affected=3`` suspicious attributions.
    """
    if min_lag_seconds <= 0:
        raise ValueError("min_lag_seconds must be > 0")
    suspicious_by_source: dict[tuple[str, str], list[str]] = defaultdict(list)
    for a in attributions:
        if a.attribution_event_id is None:
            continue  # organic
        if a.attribution_lag_seconds < min_lag_seconds:
            suspicious_by_source[(a.attributed_source, a.attributed_campaign)].append(a.device_id)
    out: list[FraudFinding] = []
    for (source, campaign), devices in suspicious_by_source.items():
        if len(devices) < 3:
            continue
        out.append(
            FraudFinding(
                kind=FraudKind.CLICK_INJECTION,
                source=f"{source}:{campaign}" if campaign else source,
                detail=(
                    f"{len(devices)} installs attributed with lag < {min_lag_seconds}s "
                    f"(median ~ {min_lag_seconds // 2}s)"
                ),
                metric=len(devices),
                devices_affected=len(devices),
            )
        )
    out.sort(key=lambda f: (-f.devices_affected, f.source))
    return out


def find_install_spam(
    events: list[Event],
    attributions: list[Attribution],
    *,
    min_installs: int = 10,
    min_d1_rate_pct: int = 5,
) -> list[FraudFinding]:
    """Surface sources whose D1 retention is implausibly low.

    Sources with fewer than ``min_installs`` are skipped (too small to
    judge). For the rest, if their D1 retention (any post-install
    OPEN/IN_APP/PURCHASE in 24h) is below ``min_d1_rate_pct`` per
    cent, we flag the source.
    """
    if min_installs < 1:
        raise ValueError("min_installs must be >= 1")
    if not 0 <= min_d1_rate_pct <= 100:
        raise ValueError("min_d1_rate_pct must be in [0, 100]")

    install_at_by_device: dict[str, datetime] = {}
    source_of_device: dict[str, tuple[str, str]] = {}
    for a in attributions:
        install_at_by_device[a.device_id] = a.install_at
        source_of_device[a.device_id] = (a.attributed_source, a.attributed_campaign)

    active_kinds = (EventKind.OPEN, EventKind.IN_APP, EventKind.PURCHASE)
    active_in_d1: set[str] = set()
    for e in events:
        if e.kind not in active_kinds:
            continue
        install_at = install_at_by_device.get(e.device_id)
        if install_at is None:
            continue
        delta = e.occurred_at - install_at
        if timedelta(0) < delta < timedelta(days=1):
            active_in_d1.add(e.device_id)

    by_source: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_source_d1: dict[tuple[str, str], int] = defaultdict(int)
    for device_id, source_pair in source_of_device.items():
        by_source[source_pair].append(device_id)
        if device_id in active_in_d1:
            by_source_d1[source_pair] += 1

    out: list[FraudFinding] = []
    for source_pair, devices in by_source.items():
        if len(devices) < min_installs:
            continue
        d1 = by_source_d1[source_pair]
        d1_pct = d1 / len(devices) * 100
        if d1_pct < min_d1_rate_pct:
            source, campaign = source_pair
            out.append(
                FraudFinding(
                    kind=FraudKind.INSTALL_SPAM,
                    source=f"{source}:{campaign}" if campaign else source,
                    detail=(
                        f"D1 retention {d1_pct:.1f}% (< threshold {min_d1_rate_pct}%); "
                        f"{len(devices)} installs"
                    ),
                    metric=int(d1_pct * 100),
                    devices_affected=len(devices),
                )
            )
    out.sort(key=lambda f: (f.metric, -f.devices_affected, f.source))
    return out


__all__ = [
    "FraudFinding",
    "FraudKind",
    "find_click_injection",
    "find_install_spam",
]
