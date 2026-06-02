"""Seeded synthetic transaction stream generator.

Produces a realistic month of VN retail-banking activity:

* Accounts are allocated across banks by deposit market share.
* Daily mix per account: 2-5 INTER/INTRA transfers, 1-3 VietQR
  receives, 0-2 cash events, 1 salary credit (mid-month), bill
  payments at month-end.
* Configurable AML-positive subscribers:
  - ``ctr_fraction`` — accounts that make ≥ 1 large cash deposit/day
  - ``structuring_fraction`` — accounts that split a single large
    cash deposit into 3-5 sub-threshold pieces
  - ``velocity_fraction`` — accounts that fire bursts of outbound
    debits (money-mule pattern)
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from vnbank.banks import all_profiles
from vnbank.schema import (
    CTR_THRESHOLD_VND,
    VN_TZ,
    Transaction,
    TxnDirection,
    TxnKind,
)


def generate(
    *,
    n_accounts: int = 30,
    n_days: int = 30,
    base_time: datetime | None = None,
    ctr_fraction: float = 0.02,
    structuring_fraction: float = 0.02,
    velocity_fraction: float = 0.02,
    seed: int = 0,
) -> list[Transaction]:
    """Generate a synthetic month of transactions for ``n_accounts`` accounts."""
    if n_accounts < 0:
        raise ValueError("n_accounts must be >= 0")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    for name, frac in (
        ("ctr_fraction", ctr_fraction),
        ("structuring_fraction", structuring_fraction),
        ("velocity_fraction", velocity_fraction),
    ):
        if not 0 <= frac <= 1:
            raise ValueError(f"{name} must be in [0, 1], got {frac}")

    rng = random.Random(seed)
    base = base_time or datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
    accounts = _allocate_accounts(n_accounts, rng)
    bins_pool = [p.bank.bin_code for p in all_profiles()]

    # Pick AML-positive cohorts (disjoint).
    targets = list(accounts)
    rng.shuffle(targets)
    n_ctr = int(n_accounts * ctr_fraction)
    n_struct = int(n_accounts * structuring_fraction)
    n_vel = int(n_accounts * velocity_fraction)
    ctr_accounts = set(targets[:n_ctr])
    struct_accounts = set(targets[n_ctr : n_ctr + n_struct])
    vel_accounts = set(targets[n_ctr + n_struct : n_ctr + n_struct + n_vel])

    events: list[Transaction] = []
    counter = 0

    def _tid() -> str:
        nonlocal counter
        tid = f"T-{counter:012d}"
        counter += 1
        return tid

    for account_num, bank_bin in accounts:
        for day in range(n_days):
            day_start = base + timedelta(days=day)
            # Normal mix.
            n_transfers = rng.randint(2, 5)
            for _ in range(n_transfers):
                amount = rng.choice([50_000, 100_000, 250_000, 500_000, 1_000_000])
                kind = rng.choice(
                    [
                        TxnKind.INTRA_BANK_TRANSFER,
                        TxnKind.INTERBANK_TRANSFER,
                        TxnKind.VIETQR_SEND,
                    ]
                )
                counterparty_bin = rng.choice(bins_pool)
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=kind,
                        direction=TxnDirection.DEBIT,
                        amount_vnd=amount,
                        occurred_at=day_start
                        + timedelta(hours=rng.randint(8, 22), minutes=rng.randint(0, 59)),
                        counterparty_bank_bin=counterparty_bin,
                    )
                )
            # VietQR receives.
            for _ in range(rng.randint(1, 3)):
                amount = rng.choice([20_000, 50_000, 100_000, 200_000, 500_000])
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=TxnKind.VIETQR_RECEIVE,
                        direction=TxnDirection.CREDIT,
                        amount_vnd=amount,
                        occurred_at=day_start
                        + timedelta(hours=rng.randint(9, 21), minutes=rng.randint(0, 59)),
                    )
                )
            # Mid-month salary credit.
            if day == 15:
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=TxnKind.SALARY_CREDIT,
                        direction=TxnDirection.CREDIT,
                        amount_vnd=rng.randint(8_000_000, 35_000_000),
                        occurred_at=day_start + timedelta(hours=9),
                        description="Salary",
                    )
                )
            # End-of-month bill payments.
            if day >= n_days - 3:
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=TxnKind.BILL_PAYMENT,
                        direction=TxnDirection.DEBIT,
                        amount_vnd=rng.randint(300_000, 1_500_000),
                        occurred_at=day_start + timedelta(hours=rng.randint(10, 20)),
                        description="EVN electricity",
                    )
                )

        # AML-positive injections.
        if (account_num, bank_bin) in ctr_accounts:
            # One large cash deposit on a random day.
            day = rng.randint(0, n_days - 1)
            day_start = base + timedelta(days=day)
            events.append(
                Transaction(
                    txn_id=_tid(),
                    account_number=account_num,
                    bank_bin=bank_bin,
                    kind=TxnKind.CASH_DEPOSIT,
                    direction=TxnDirection.CREDIT,
                    amount_vnd=rng.randint(
                        CTR_THRESHOLD_VND + 50_000_000,
                        CTR_THRESHOLD_VND + 500_000_000,
                    ),
                    occurred_at=day_start + timedelta(hours=11),
                    description="Cash deposit at branch",
                )
            )
        if (account_num, bank_bin) in struct_accounts:
            # Structuring: 4 deposits at 90M each, all on one day.
            day = rng.randint(0, n_days - 1)
            day_start = base + timedelta(days=day)
            for j in range(4):
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=TxnKind.CASH_DEPOSIT,
                        direction=TxnDirection.CREDIT,
                        amount_vnd=90_000_000,
                        occurred_at=day_start + timedelta(hours=10 + j, minutes=rng.randint(0, 59)),
                        description="Cash deposit",
                    )
                )
        if (account_num, bank_bin) in vel_accounts:
            # High-velocity burst: 60 outbound debits within 30 minutes.
            day = rng.randint(0, n_days - 1)
            burst_start = base + timedelta(days=day, hours=14)
            for j in range(60):
                events.append(
                    Transaction(
                        txn_id=_tid(),
                        account_number=account_num,
                        bank_bin=bank_bin,
                        kind=TxnKind.INTERBANK_TRANSFER,
                        direction=TxnDirection.DEBIT,
                        amount_vnd=rng.randint(500_000, 5_000_000),
                        occurred_at=burst_start + timedelta(seconds=j * 30),
                        counterparty_bank_bin=rng.choice(bins_pool),
                    )
                )

    events.sort(key=lambda e: (e.occurred_at, e.txn_id))
    return events


def _allocate_accounts(n: int, rng: random.Random) -> list[tuple[str, str]]:
    """Allocate ``n`` (account_number, bank_bin) pairs by market share."""
    profiles = all_profiles()
    weights = [p.market_share_pct for p in profiles]
    out: list[tuple[str, str]] = []
    for i in range(n):
        prof = rng.choices(profiles, weights=weights, k=1)[0]
        # Pick a length in the bank's valid range and emit that many digits.
        length = rng.randint(prof.min_account_length, prof.max_account_length)
        # Use index to keep account numbers unique within the simulation.
        base_num = (rng.randint(0, 10**length - 1) + i * 7919) % (10**length)
        account_number = f"{base_num:0{length}d}"
        out.append((account_number, prof.bank.bin_code))
    return out


__all__ = ["generate"]
