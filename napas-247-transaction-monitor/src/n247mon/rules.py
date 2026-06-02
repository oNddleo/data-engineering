"""The four bundled monitoring rules.

Each rule is a tiny state machine that consumes one
:class:`Transaction` at a time and returns zero-or-more
:class:`Alert` records. They share a common ``consume(txn)`` shape
(see :class:`Rule`) so the engine can iterate over a heterogeneous
list of them with no special-casing.

State is kept in plain dicts keyed by account. For a production
deployment the dict would be swapped for a Redis hash or a
RocksDB-backed state backend (look at the engine's pluggable
state protocol in ``engine.py``). The in-memory implementation here
is deliberately simple so the rule logic stays readable.

All windowing is **event-time** based — the rule uses
``txn.occurred_at`` for cutoffs, never wall-clock — which means tests
are fully deterministic and back-dated replays work without any
clock-mocking ceremony.
"""

from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from n247mon.alerts import Alert, AlertKind, Severity

if TYPE_CHECKING:
    from collections.abc import Iterable

    from n247mon.schema import Transaction


class Rule(Protocol):
    """A monitoring rule. Stateful; consumed in transaction order."""

    def consume(self, txn: Transaction) -> list[Alert]: ...


# ---------------------------------------------------------------------------
# Decision 2345/QĐ-NHNN biometric rule


class BiometricRule:
    """Decision 2345/QĐ-NHNN (in force 2024-07-01).

    Two sub-rules, encoded so that exactly one alert fires per
    transaction at most:

    1. **Single-txn trigger** — ``amount > 10_000_000`` and not
       ``biometric_verified`` → :attr:`AlertKind.BIO_REQUIRED_SINGLE_TXN`.
    2. **Cumulative trigger** — ``amount <= 10_000_000`` (so sub-rule
       1 didn't fire) and (``daily_total_before + amount > 20_000_000``)
       and not ``biometric_verified`` →
       :attr:`AlertKind.BIO_REQUIRED_CUMULATIVE`.

    Either way the rule **updates** its per-account daily total
    after the check so subsequent transfers see the new total.
    """

    SINGLE_THRESHOLD = 10_000_000
    DAILY_THRESHOLD = 20_000_000

    def __init__(self) -> None:
        self._daily_total: dict[tuple[str, date], int] = {}

    def consume(self, txn: Transaction) -> list[Alert]:
        day = txn.occurred_at.date()
        key = (txn.initiator_account, day)
        prior = self._daily_total.get(key, 0)
        self._daily_total[key] = prior + txn.amount_vnd

        if txn.biometric_verified:
            return []

        if txn.amount_vnd > self.SINGLE_THRESHOLD:
            return [
                Alert(
                    kind=AlertKind.BIO_REQUIRED_SINGLE_TXN,
                    severity=Severity.CRIT,
                    txn_id=txn.txn_id,
                    account=txn.initiator_account,
                    detail=(
                        f"transfer of {txn.amount_vnd:,} VND exceeds single-txn "
                        f"biometric threshold ({self.SINGLE_THRESHOLD:,} VND)"
                    ),
                    amount_vnd=txn.amount_vnd,
                )
            ]
        if prior + txn.amount_vnd > self.DAILY_THRESHOLD:
            return [
                Alert(
                    kind=AlertKind.BIO_REQUIRED_CUMULATIVE,
                    severity=Severity.CRIT,
                    txn_id=txn.txn_id,
                    account=txn.initiator_account,
                    detail=(
                        f"this transfer would push daily cumulative to "
                        f"{prior + txn.amount_vnd:,} VND (> {self.DAILY_THRESHOLD:,}) "
                        "without biometric auth"
                    ),
                    amount_vnd=txn.amount_vnd,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Velocity rule — sliding-window count


class VelocityRule:
    """Fire when an account exceeds ``threshold`` transfers in ``window_seconds``.

    Default settings are tuned for the retail consumer profile —
    > 10 transfers per minute is unusual and worth a WARN.
    """

    def __init__(self, *, window_seconds: int = 60, threshold: int = 10) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if threshold <= 0:
            raise ValueError("threshold must be > 0")
        self._window_seconds = window_seconds
        self._threshold = threshold
        self._windows: dict[str, deque[datetime]] = {}

    def consume(self, txn: Transaction) -> list[Alert]:
        window = self._windows.setdefault(txn.initiator_account, deque())
        cutoff = txn.occurred_at - timedelta(seconds=self._window_seconds)
        while window and window[0] < cutoff:
            window.popleft()
        window.append(txn.occurred_at)
        if len(window) > self._threshold:
            return [
                Alert(
                    kind=AlertKind.VELOCITY_SPIKE,
                    severity=Severity.WARN,
                    txn_id=txn.txn_id,
                    account=txn.initiator_account,
                    detail=(
                        f"{len(window)} transfers in {self._window_seconds}s window "
                        f"(threshold {self._threshold})"
                    ),
                    amount_vnd=txn.amount_vnd,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Structuring (smurfing) rule


class StructuringRule:
    """Detect a smurfing pattern that dodges the single-txn biometric trigger.

    "Structuring" = breaking one large transfer into several small
    ones, each just under the threshold. We track every transfer
    where ``threshold - margin < amount <= threshold`` and fire when
    at least ``min_count`` of them happen for the same initiator
    within ``window_seconds``.

    With defaults: ≥ 3 transfers in the 9.5M–10M VND range within an
    hour from the same account → alert.
    """

    def __init__(
        self,
        *,
        window_seconds: int = 3600,
        min_count: int = 3,
        threshold_vnd: int = 10_000_000,
        margin_vnd: int = 500_000,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if min_count < 2:
            raise ValueError("min_count must be >= 2 (need at least 2 txns to call it structuring)")
        if margin_vnd <= 0 or margin_vnd >= threshold_vnd:
            raise ValueError("margin_vnd must be in (0, threshold_vnd)")
        self._window_seconds = window_seconds
        self._min_count = min_count
        self._threshold = threshold_vnd
        self._margin = margin_vnd
        self._hits: dict[str, deque[datetime]] = {}

    def _is_near_threshold(self, amount: int) -> bool:
        return self._threshold - self._margin < amount <= self._threshold

    def consume(self, txn: Transaction) -> list[Alert]:
        if not self._is_near_threshold(txn.amount_vnd):
            return []
        window = self._hits.setdefault(txn.initiator_account, deque())
        cutoff = txn.occurred_at - timedelta(seconds=self._window_seconds)
        while window and window[0] < cutoff:
            window.popleft()
        window.append(txn.occurred_at)
        if len(window) >= self._min_count:
            return [
                Alert(
                    kind=AlertKind.STRUCTURING_SUSPECTED,
                    severity=Severity.WARN,
                    txn_id=txn.txn_id,
                    account=txn.initiator_account,
                    detail=(
                        f"{len(window)} near-threshold transfers "
                        f"(>{self._threshold - self._margin:,}, <={self._threshold:,}) "
                        f"in {self._window_seconds}s window"
                    ),
                    amount_vnd=txn.amount_vnd,
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Blacklist rule


class BlacklistRule:
    """Fire when the beneficiary account is on the supplied blacklist.

    Blacklists arrive from upstream sources: criminal-investigation
    freeze orders from the State Bank, internal fraud-team curation,
    or shared mule-account intel from NAPAS. The rule does not care
    where the list came from — just that membership is O(1).
    """

    def __init__(self, accounts: Iterable[str]) -> None:
        self._accounts: frozenset[str] = frozenset(a.strip() for a in accounts if a.strip())

    @property
    def size(self) -> int:
        return len(self._accounts)

    def consume(self, txn: Transaction) -> list[Alert]:
        if txn.beneficiary_account in self._accounts:
            return [
                Alert(
                    kind=AlertKind.BLACKLIST_HIT,
                    severity=Severity.CRIT,
                    txn_id=txn.txn_id,
                    account=txn.initiator_account,
                    detail=(
                        f"beneficiary account {txn.beneficiary_account} "
                        f"(bank BIN {txn.beneficiary_bank_bin}) is on the blacklist"
                    ),
                    amount_vnd=txn.amount_vnd,
                )
            ]
        return []


__all__ = [
    "BiometricRule",
    "BlacklistRule",
    "Rule",
    "StructuringRule",
    "VelocityRule",
]
