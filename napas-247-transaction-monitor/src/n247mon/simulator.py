"""Synthetic NAPAS 247 traffic generator for tests + local demos.

This is **not** a load generator — its job is to produce a realistic
spread of transactions, with optional anomalies seeded in, so the
rule logic can be exercised end-to-end without real settlement
files. Reproducibility is the priority, so it takes a ``seed``.

Anomalies you can inject (see :func:`generate`):

* ``"bio_single"``  — one transfer > 10M VND with ``biometric_verified=False``.
* ``"bio_cumulative"`` — three 8M-VND transfers from the same account
  on the same day without biometric (last one tips total > 20M).
* ``"velocity"`` — 15 transfers in 30 seconds from the same account.
* ``"structuring"`` — 3 transfers at 9,800,000 VND from the same
  account within an hour.
* ``"blacklist"`` — one transfer with beneficiary in ``blacklist``.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from n247mon.banks import BIN_TO_BANK
from n247mon.schema import VN_TZ, Channel, Transaction

if TYPE_CHECKING:
    from collections.abc import Iterable

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


def _rand_account(rng: random.Random) -> str:
    # 10-digit numeric, like a typical VN savings account number.
    return "".join(str(rng.randint(0, 9)) for _ in range(10))


def _rand_amount(rng: random.Random) -> int:
    # Bias towards "small retail" amounts — 100k to 5M, log-uniform-ish.
    bucket = rng.random()
    if bucket < 0.7:
        return rng.randint(50_000, 5_000_000)
    if bucket < 0.95:
        return rng.randint(5_000_000, 50_000_000)
    return rng.randint(50_000_000, 500_000_000)


def _rand_channel(rng: random.Random) -> Channel:
    # Mobile dominates retail transfers; ATM/BRANCH are rarer.
    return rng.choices(
        list(Channel),
        weights=[0.75, 0.18, 0.05, 0.02],
        k=1,
    )[0]


def _txn(
    rng: random.Random,
    *,
    occurred_at: datetime,
    initiator: str | None = None,
    beneficiary: str | None = None,
    amount: int | None = None,
    biometric: bool | None = None,
    txn_id: str,
) -> Transaction:
    bins = list(BIN_TO_BANK.keys())
    amt = amount if amount is not None else _rand_amount(rng)
    if biometric is None:
        # Random consumer flow — only ~30% of small transfers had bio capture
        # before Decision 2345; after July 2024 banks should set this on every
        # transfer above the threshold. We bias for "good citizens".
        biometric = rng.random() < 0.6 if amt > 10_000_000 else rng.random() < 0.1
    return Transaction(
        txn_id=txn_id,
        initiator_account=initiator or _rand_account(rng),
        initiator_bank_bin=rng.choice(bins),
        beneficiary_account=beneficiary or _rand_account(rng),
        beneficiary_bank_bin=rng.choice(bins),
        amount_vnd=amt,
        channel=_rand_channel(rng),
        occurred_at=occurred_at,
        biometric_verified=biometric,
        device_id=f"dev-{rng.randint(0, 999):03d}",
        geo_ip=None,
    )


def _inject_bio_single(rng: random.Random, base: datetime, n: int) -> list[Transaction]:
    return [
        _txn(
            rng,
            occurred_at=base + timedelta(seconds=n),
            amount=50_000_000,
            biometric=False,
            txn_id=f"ANOM-BIO-S-{n}",
        )
    ]


def _inject_bio_cumulative(rng: random.Random, base: datetime, n: int) -> list[Transaction]:
    account = _rand_account(rng)
    return [
        _txn(
            rng,
            occurred_at=base + timedelta(seconds=n + i),
            initiator=account,
            amount=8_000_000,
            biometric=False,
            txn_id=f"ANOM-BIO-C-{n}-{i}",
        )
        for i in range(3)
    ]


def _inject_velocity(rng: random.Random, base: datetime, n: int) -> list[Transaction]:
    account = _rand_account(rng)
    return [
        _txn(
            rng,
            occurred_at=base + timedelta(seconds=n) + timedelta(seconds=i * 2),
            initiator=account,
            amount=200_000,
            biometric=False,
            txn_id=f"ANOM-VEL-{n}-{i:02d}",
        )
        for i in range(15)
    ]


def _inject_structuring(rng: random.Random, base: datetime, n: int) -> list[Transaction]:
    account = _rand_account(rng)
    return [
        _txn(
            rng,
            occurred_at=base + timedelta(seconds=n) + timedelta(minutes=i * 5),
            initiator=account,
            amount=9_800_000,
            biometric=False,
            txn_id=f"ANOM-STR-{n}-{i}",
        )
        for i in range(3)
    ]


def _inject_blacklist(
    rng: random.Random, base: datetime, n: int, blacklist: list[str]
) -> list[Transaction]:
    if not blacklist:
        return []
    return [
        _txn(
            rng,
            occurred_at=base + timedelta(seconds=n),
            beneficiary=blacklist[n % len(blacklist)],
            amount=2_000_000,
            biometric=True,
            txn_id=f"ANOM-BL-{n}",
        )
    ]


def generate(
    *,
    n_txns: int,
    seed: int = 0,
    base_time: datetime | None = None,
    inject_anomalies: Iterable[str] = (),
    blacklist: Iterable[str] = (),
) -> list[Transaction]:
    """Return ``n_txns`` synthetic transactions sorted by ``occurred_at``.

    Anomalous transactions are added on top of the baseline count.
    The seed makes output exactly reproducible across runs.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    out: list[Transaction] = [
        _txn(rng, occurred_at=base + timedelta(seconds=i), txn_id=f"TXN-{i:06d}")
        for i in range(n_txns)
    ]
    bl = list(blacklist)
    for anomaly in inject_anomalies:
        n = len(out)
        if anomaly == "bio_single":
            out.extend(_inject_bio_single(rng, base, n))
        elif anomaly == "bio_cumulative":
            out.extend(_inject_bio_cumulative(rng, base, n))
        elif anomaly == "velocity":
            out.extend(_inject_velocity(rng, base, n))
        elif anomaly == "structuring":
            out.extend(_inject_structuring(rng, base, n))
        elif anomaly == "blacklist":
            out.extend(_inject_blacklist(rng, base, n, bl))
        else:
            raise ValueError(f"unknown anomaly kind: {anomaly!r}")
    out.sort(key=lambda t: t.occurred_at)
    return out


__all__ = ["generate"]
