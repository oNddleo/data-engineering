"""Generate synthetic transaction sets for benchmarking and testing."""

from __future__ import annotations

import random
import string
from datetime import date, timedelta

from recon.schema import Transaction

_DESCS = [
    "WIRE TRANSFER",
    "ACH PAYMENT",
    "CARD TRANSACTION",
    "FEE CHARGE",
    "INTEREST CREDIT",
    "DIVIDEND PAYMENT",
    "REFUND",
    "LOAN DISBURSEMENT",
]


def _rand_ref(rng: random.Random) -> str:
    prefix = rng.choice(["TXN", "REF", "PMT", "TRF"])
    digits = "".join(rng.choices(string.digits, k=8))
    return f"{prefix}{digits}"


def generate_sources(
    n_transactions: int = 200,
    source_names: list[str] | None = None,
    missing_rate: float = 0.05,
    amount_mismatch_rate: float = 0.03,
    timing_drift_days: int = 2,
    seed: int | None = None,
) -> dict[str, list[Transaction]]:
    """Generate a synthetic multi-source transaction set.

    Args:
        n_transactions: Number of base transactions to generate.
        source_names: Names of simulated data sources.
        missing_rate: Fraction of transactions absent from one source.
        amount_mismatch_rate: Fraction with small amount discrepancies.
        timing_drift_days: Max date drift between sources.
        seed: RNG seed for reproducibility.
    """
    if source_names is None:
        source_names = ["core_banking", "reporting", "aggregator", "manual"]
    rng = random.Random(seed)
    base_date = date(2024, 1, 1)

    # Build canonical transactions
    canonical: list[Transaction] = []
    for _ in range(n_transactions):
        days_offset = rng.randint(0, 364)
        canonical.append(
            Transaction(
                source="canonical",
                ref=_rand_ref(rng),
                amount=round(rng.uniform(10.0, 100_000.0), 2),
                txn_date=base_date + timedelta(days=days_offset),
                description=rng.choice(_DESCS),
                currency="USD",
            )
        )

    sources: dict[str, list[Transaction]] = {}
    for src in source_names:
        txns: list[Transaction] = []
        for txn in canonical:
            # Maybe skip (missing)
            if rng.random() < missing_rate:
                continue
            # Maybe drift amount
            amount = txn.amount
            if rng.random() < amount_mismatch_rate:
                amount = round(amount + rng.uniform(-0.05, 0.05), 4)
            # Maybe drift date
            drift = rng.randint(0, timing_drift_days)
            txn_date = txn.txn_date + timedelta(days=drift)
            txns.append(
                Transaction(
                    source=src,
                    ref=txn.ref,
                    amount=amount,
                    txn_date=txn_date,
                    description=txn.description,
                    currency=txn.currency,
                )
            )
        sources[src] = txns

    return sources
