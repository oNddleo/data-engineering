"""Synthetic meter-reading stream generator.

Produces 12 monthly meter readings for a population of EVN customers
spanning all five provincial units and all five categories.

* Customers are allocated across the 5 provincial units (PA-PE) by
  population weights.
* Category mix: 70% HOUSEHOLD, 15% BUSINESS, 5% ADMIN_PUBLIC,
  5% PRODUCTION, 5% AGRICULTURE.
* HOUSEHOLD baselines are log-normal in [40, 600] kWh/month (the
  bulk of the 6-tier curve).
* Business / production baselines scale roughly 3-5× higher.
* Configurable anomaly-positive cohorts:
  - ``tampering_fraction`` — customers whose latest month drops > 90%
  - ``spike_fraction``     — customers whose latest month spikes > 5×
"""

from __future__ import annotations

import math
import random
from datetime import date

from evn.customer import all_units
from evn.schema import CustomerCategory, MeterReading


def generate(
    *,
    n_customers: int = 50,
    n_months: int = 12,
    start_year: int = 2025,
    tampering_fraction: float = 0.03,
    spike_fraction: float = 0.02,
    seed: int = 0,
) -> list[MeterReading]:
    """Generate one year of monthly meter readings for ``n_customers``."""
    if n_customers < 0:
        raise ValueError("n_customers must be >= 0")
    if n_months < 1 or n_months > 12:
        raise ValueError("n_months must be in [1, 12]")
    for name, frac in (
        ("tampering_fraction", tampering_fraction),
        ("spike_fraction", spike_fraction),
    ):
        if not 0 <= frac <= 1:
            raise ValueError(f"{name} must be in [0, 1], got {frac}")

    rng = random.Random(seed)
    units = all_units()
    customers = _allocate_customers(n_customers, units, rng)

    # Anomaly cohorts (disjoint).
    targets = list(customers)
    rng.shuffle(targets)
    n_tamper = int(n_customers * tampering_fraction)
    n_spike = int(n_customers * spike_fraction)
    tamper_set = {c[0] for c in targets[:n_tamper]}
    spike_set = {c[0] for c in targets[n_tamper : n_tamper + n_spike]}

    out: list[MeterReading] = []
    for customer_code, category in customers:
        baseline = _baseline_kwh(category, rng)
        for month in range(n_months):
            period_start = date(start_year, month + 1, 1)
            # End-of-month: day 28 is safe across all months.
            period_end = date(start_year, month + 1, 28)
            jitter = rng.uniform(0.85, 1.15)
            kwh = max(0, int(baseline * jitter))

            # Inject anomalies in the *latest* month only.
            if month == n_months - 1:
                if customer_code in tamper_set:
                    kwh = max(0, int(baseline * 0.05))  # 95% drop
                elif customer_code in spike_set:
                    kwh = int(baseline * rng.uniform(6.0, 10.0))

            out.append(
                MeterReading(
                    customer_code=customer_code,
                    category=category,
                    period_start=period_start,
                    period_end=period_end,
                    kwh_used=kwh,
                )
            )

    out.sort(key=lambda r: (r.period_start, r.customer_code))
    return out


def _allocate_customers(
    n: int,
    units: tuple,  # type: ignore[type-arg]
    rng: random.Random,
) -> list[tuple[str, CustomerCategory]]:
    """Allocate ``n`` (customer_code, category) pairs."""
    # Population-weighted provincial-unit pick.
    unit_weights = (35, 25, 15, 20, 5)  # PA, PB, PC, PD, PE rough share
    out: list[tuple[str, CustomerCategory]] = []
    for i in range(n):
        unit = rng.choices(units, weights=unit_weights, k=1)[0]
        suffix = rng.randrange(10**11)
        customer_code = f"{unit.prefix}{suffix:011d}"
        category = rng.choices(
            list(CustomerCategory),
            weights=[70, 15, 5, 5, 5],
            k=1,
        )[0]
        # Make the suffix unique by mixing in i.
        unique = (suffix + i * 7919) % (10**11)
        customer_code = f"{unit.prefix}{unique:011d}"
        out.append((customer_code, category))
    return out


def _baseline_kwh(category: CustomerCategory, rng: random.Random) -> float:
    """Sample a plausible monthly baseline for the given category."""
    if category is CustomerCategory.HOUSEHOLD:
        # Log-normal centred around ~150 kWh/month (median VN household).
        return math.exp(rng.normalvariate(5.0, 0.6))
    if category is CustomerCategory.BUSINESS:
        return math.exp(rng.normalvariate(6.5, 0.7))
    if category is CustomerCategory.ADMIN_PUBLIC:
        return math.exp(rng.normalvariate(6.2, 0.5))
    if category is CustomerCategory.PRODUCTION:
        return math.exp(rng.normalvariate(7.5, 0.9))
    # AGRICULTURE — lowest baseline; irrigation pumps run seasonally.
    return math.exp(rng.normalvariate(5.5, 0.8))


__all__ = ["generate"]
