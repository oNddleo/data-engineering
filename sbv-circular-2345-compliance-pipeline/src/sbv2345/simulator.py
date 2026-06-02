"""Seeded synthetic TransactionEvent generator with controllable trigger mix."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sbv2345.schema import VN_TZ, AuthMethod, BiometricMethod, Channel, TransactionEvent

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


def _account(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(10))


def _small_amount(rng: random.Random) -> int:
    return rng.randint(50_000, 9_500_000)


def _medium_amount(rng: random.Random) -> int:
    """Just under the daily-cumulative trigger when summed twice."""
    return rng.randint(8_000_000, 9_900_000)


def _large_amount(rng: random.Random) -> int:
    return rng.randint(11_000_000, 100_000_000)


def _channel(rng: random.Random) -> Channel:
    return rng.choices(
        list(Channel),
        weights=[0.75, 0.18, 0.05, 0.02],
        k=1,
    )[0]


def _auth(rng: random.Random, biometric_ok: bool) -> tuple[AuthMethod, BiometricMethod | None]:
    if biometric_ok and rng.random() < 0.7:
        return AuthMethod.BIOMETRIC, rng.choice(list(BiometricMethod))
    return rng.choice([AuthMethod.PIN, AuthMethod.OTP]), None


def _make_txn(
    rng: random.Random,
    *,
    txn_id: str,
    initiator: str,
    beneficiary: str,
    amount: int,
    occurred_at: datetime,
    biometric_ok: bool,
    cross_border: bool = False,
) -> TransactionEvent:
    auth, bio = _auth(rng, biometric_ok)
    return TransactionEvent(
        txn_id=txn_id,
        initiator_account=initiator,
        beneficiary_account=beneficiary,
        amount_vnd=amount,
        channel=_channel(rng),
        occurred_at=occurred_at,
        auth_method=auth,
        biometric_method=bio,
        cross_border=cross_border,
    )


def generate(
    *,
    n_small: int = 50,
    n_large: int = 5,
    n_cumulative_pair: int = 2,
    n_cross_border: int = 2,
    n_high_risk_beneficiary: int = 1,
    high_risk_accounts: list[str] | None = None,
    seed: int = 0,
    base_time: datetime | None = None,
) -> list[TransactionEvent]:
    """Build a deterministic mix of transactions touching every trigger kind."""
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    out: list[TransactionEvent] = []
    serial = 0

    def next_id(prefix: str) -> str:
        nonlocal serial
        serial += 1
        return f"{prefix}-{serial:05d}"

    # n_small: nothing fires.
    for i in range(n_small):
        out.append(
            _make_txn(
                rng,
                txn_id=next_id("TXN"),
                initiator=_account(rng),
                beneficiary=_account(rng),
                amount=_small_amount(rng),
                occurred_at=base + timedelta(seconds=i),
                biometric_ok=False,
            )
        )

    # n_large: SINGLE_TXN_OVER_10M fires every time.
    for i in range(n_large):
        out.append(
            _make_txn(
                rng,
                txn_id=next_id("LRG"),
                initiator=_account(rng),
                beneficiary=_account(rng),
                amount=_large_amount(rng),
                occurred_at=base + timedelta(seconds=60 + i),
                biometric_ok=True,
            )
        )

    # n_cumulative_pair: 3 medium amounts (8–9.9M each) from the same
    # account on the same day. Each individual txn stays ≤ 10M so it
    # doesn't trip SINGLE_TXN_OVER_10M; together they sum to ~24M+ so
    # the *third* fires DAILY_CUMULATIVE_OVER_20M. (Two would only reach
    # ~19.8M max, which doesn't cross 20M — three is the smallest group
    # that reliably exercises the cumulative rule.)
    for i in range(n_cumulative_pair):
        acc = _account(rng)
        for j in range(3):
            out.append(
                _make_txn(
                    rng,
                    txn_id=next_id("CUM"),
                    initiator=acc,
                    beneficiary=_account(rng),
                    amount=_medium_amount(rng),
                    occurred_at=base + timedelta(seconds=120 + i * 30 + j * 5),
                    biometric_ok=False,
                )
            )

    # n_cross_border.
    for i in range(n_cross_border):
        out.append(
            _make_txn(
                rng,
                txn_id=next_id("XBR"),
                initiator=_account(rng),
                beneficiary=_account(rng),
                amount=_small_amount(rng),
                occurred_at=base + timedelta(seconds=240 + i),
                biometric_ok=False,
                cross_border=True,
            )
        )

    # n_high_risk_beneficiary: requires the caller-supplied blacklist.
    bl = list(high_risk_accounts or [])
    for i in range(n_high_risk_beneficiary):
        if not bl:
            break
        out.append(
            _make_txn(
                rng,
                txn_id=next_id("HRB"),
                initiator=_account(rng),
                beneficiary=bl[i % len(bl)],
                amount=_small_amount(rng),
                occurred_at=base + timedelta(seconds=300 + i),
                biometric_ok=False,
            )
        )

    out.sort(key=lambda t: t.occurred_at)
    return out


__all__ = ["generate"]
