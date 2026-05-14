"""Seeded synthetic transaction-graph generator.

Build a noisy "normal" graph and then optionally inject any of the
five AML topologies on top. Every injection is deterministic from
the seed + the per-injection serial counter.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from amlgraph.schema import VN_TZ, Account, AccountType, Channel, Transaction

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)
_BINS = ("970418", "970436", "970422", "970407", "970432", "970448", "970437")


def _acc_id(rng: random.Random) -> str:
    return "ACC-" + "".join(str(rng.randint(0, 9)) for _ in range(8))


def _bin(rng: random.Random) -> str:
    return rng.choice(_BINS)


def _make_account(rng: random.Random) -> Account:
    return Account(
        account_id=_acc_id(rng),
        bank_bin=_bin(rng),
        account_type=AccountType.PERSONAL,
    )


def _make_txn(
    rng: random.Random,
    *,
    txn_id: str,
    src: str,
    dst: str,
    amount: int,
    occurred_at: datetime,
) -> Transaction:
    return Transaction(
        txn_id=txn_id,
        from_account=src,
        to_account=dst,
        amount_vnd=amount,
        occurred_at=occurred_at,
        channel=rng.choice(list(Channel)),
    )


def _next_id(state: dict[str, int], prefix: str) -> str:
    state[prefix] = state.get(prefix, 0) + 1
    return f"{prefix}-{state[prefix]:06d}"


def generate(
    *,
    n_accounts: int = 30,
    n_normal_txns: int = 60,
    inject_fan_out: int = 0,
    inject_fan_in: int = 0,
    inject_layering: int = 0,
    inject_round_trip: int = 0,
    inject_structured: int = 0,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Account], list[Transaction]]:
    """Return ``(accounts, transactions)`` for a synthetic dataset.

    ``inject_*`` counts add **one full pattern instance per unit**:
    a fan-out injection adds 1 source + 6 destinations + 6 txns,
    a layering injection adds a 4-account chain + 3 txns, etc.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    state: dict[str, int] = {}

    accounts: list[Account] = [_make_account(rng) for _ in range(n_accounts)]
    acc_ids = [a.account_id for a in accounts]
    txns: list[Transaction] = []

    # ----- normal traffic — random small transfers between random accounts.
    for i in range(n_normal_txns):
        src, dst = rng.sample(acc_ids, 2)
        amount = rng.randint(50_000, 5_000_000)
        txns.append(
            _make_txn(
                rng,
                txn_id=_next_id(state, "N"),
                src=src,
                dst=dst,
                amount=amount,
                occurred_at=base + timedelta(seconds=i * 30),
            )
        )

    # ----- fan-out: one source → 6 distinct destinations within an hour.
    for k in range(inject_fan_out):
        src_acc = _make_account(rng)
        accounts.append(src_acc)
        dests = [_make_account(rng) for _ in range(6)]
        accounts.extend(dests)
        anchor = base + timedelta(hours=2 + k)
        for j, d in enumerate(dests):
            txns.append(
                _make_txn(
                    rng,
                    txn_id=_next_id(state, "FO"),
                    src=src_acc.account_id,
                    dst=d.account_id,
                    amount=rng.randint(1_000_000, 5_000_000),
                    occurred_at=anchor + timedelta(seconds=j * 60),
                )
            )

    # ----- fan-in: 6 distinct sources → 1 destination within an hour.
    for k in range(inject_fan_in):
        dst_acc = _make_account(rng)
        accounts.append(dst_acc)
        srcs = [_make_account(rng) for _ in range(6)]
        accounts.extend(srcs)
        anchor = base + timedelta(hours=4 + k)
        for j, s in enumerate(srcs):
            txns.append(
                _make_txn(
                    rng,
                    txn_id=_next_id(state, "FI"),
                    src=s.account_id,
                    dst=dst_acc.account_id,
                    amount=rng.randint(1_000_000, 5_000_000),
                    occurred_at=anchor + timedelta(seconds=j * 60),
                )
            )

    # ----- layering: 4-account chain (3 hops) within an hour.
    for k in range(inject_layering):
        chain = [_make_account(rng) for _ in range(4)]
        accounts.extend(chain)
        anchor = base + timedelta(hours=6 + k)
        for j in range(3):
            txns.append(
                _make_txn(
                    rng,
                    txn_id=_next_id(state, "LY"),
                    src=chain[j].account_id,
                    dst=chain[j + 1].account_id,
                    amount=rng.randint(1_000_000, 3_000_000),
                    occurred_at=anchor + timedelta(seconds=j * 600),
                )
            )

    # ----- round-trip: A → B → C → A within an hour.
    for k in range(inject_round_trip):
        ring = [_make_account(rng) for _ in range(3)]
        accounts.extend(ring)
        anchor = base + timedelta(hours=8 + k)
        for j in range(3):
            txns.append(
                _make_txn(
                    rng,
                    txn_id=_next_id(state, "RT"),
                    src=ring[j].account_id,
                    dst=ring[(j + 1) % 3].account_id,
                    amount=rng.randint(1_000_000, 3_000_000),
                    occurred_at=anchor + timedelta(seconds=j * 300),
                )
            )

    # ----- structured deposit: 4 sources → 1 dest, each in 9.6–9.9M range.
    for k in range(inject_structured):
        dst_acc = _make_account(rng)
        accounts.append(dst_acc)
        srcs = [_make_account(rng) for _ in range(4)]
        accounts.extend(srcs)
        anchor = base + timedelta(hours=10 + k)
        for j, s in enumerate(srcs):
            txns.append(
                _make_txn(
                    rng,
                    txn_id=_next_id(state, "SD"),
                    src=s.account_id,
                    dst=dst_acc.account_id,
                    amount=rng.randint(9_600_000, 9_950_000),
                    occurred_at=anchor + timedelta(seconds=j * 300),
                )
            )

    txns.sort(key=lambda t: t.occurred_at)
    return accounts, txns


__all__ = ["generate"]
