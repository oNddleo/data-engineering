"""Seeded synthetic column generator for testing + demos.

Produces realistic-looking columns of each ``ColumnKind``:

* **NUMERIC** — Gaussian, log-normal, or uniform draws.
* **CATEGORICAL** — Zipf-distributed picks from a fixed alphabet.
* **STRING** — random length-10 alphanumeric strings (unique).
* **DATE** — uniform random dates in a configured window.

Each generator returns ``list[str]`` (the raw, pre-parse format that
the profiler expects).
"""

from __future__ import annotations

import random
import string
from datetime import date, timedelta
from enum import Enum


class NumericShape(str, Enum):
    """Three numeric distributions."""

    UNIFORM = "UNIFORM"
    GAUSSIAN = "GAUSSIAN"
    LOGNORMAL = "LOGNORMAL"


def generate_numeric(
    *,
    n: int = 1_000,
    shape: NumericShape = NumericShape.GAUSSIAN,
    mean: float = 0.0,
    std: float = 1.0,
    low: float = 0.0,
    high: float = 100.0,
    null_fraction: float = 0.0,
    seed: int = 0,
) -> list[str]:
    """Generate a numeric column, returned as a list of stringified values."""
    _check_size(n)
    _check_null_fraction(null_fraction)
    rng = random.Random(seed)
    out: list[str] = []
    for _ in range(n):
        if rng.random() < null_fraction:
            out.append("")
            continue
        if shape is NumericShape.UNIFORM:
            v = rng.uniform(low, high)
        elif shape is NumericShape.GAUSSIAN:
            v = rng.gauss(mean, std)
        elif shape is NumericShape.LOGNORMAL:
            v = rng.lognormvariate(mean, std)
        else:
            raise ValueError(f"unknown shape: {shape}")
        out.append(f"{v:.4f}")
    return out


def generate_categorical(
    *,
    n: int = 1_000,
    n_categories: int = 5,
    skew: float = 1.0,  # Zipf exponent — 1 = strong head, 0 = uniform
    null_fraction: float = 0.0,
    seed: int = 0,
) -> list[str]:
    """Generate a categorical column with Zipf-weighted picks."""
    _check_size(n)
    _check_null_fraction(null_fraction)
    if n_categories < 1:
        raise ValueError(f"n_categories must be >= 1, got {n_categories}")
    if skew < 0:
        raise ValueError(f"skew must be >= 0, got {skew}")
    rng = random.Random(seed)
    categories = [f"cat_{i}" for i in range(n_categories)]
    weights = [1.0 / ((i + 1) ** skew) for i in range(n_categories)]
    out: list[str] = []
    for _ in range(n):
        if rng.random() < null_fraction:
            out.append("")
            continue
        out.append(rng.choices(categories, weights=weights, k=1)[0])
    return out


def generate_string(
    *,
    n: int = 1_000,
    length: int = 10,
    null_fraction: float = 0.0,
    seed: int = 0,
) -> list[str]:
    """Generate random alphanumeric strings."""
    _check_size(n)
    _check_null_fraction(null_fraction)
    if length < 1:
        raise ValueError(f"length must be >= 1, got {length}")
    rng = random.Random(seed)
    alphabet = string.ascii_lowercase + string.digits
    out: list[str] = []
    for _ in range(n):
        if rng.random() < null_fraction:
            out.append("")
            continue
        out.append("".join(rng.choices(alphabet, k=length)))
    return out


def generate_date(
    *,
    n: int = 1_000,
    start: date | None = None,
    span_days: int = 365,
    null_fraction: float = 0.0,
    seed: int = 0,
) -> list[str]:
    """Generate uniform random ISO dates in ``[start, start + span_days)``."""
    _check_size(n)
    _check_null_fraction(null_fraction)
    if span_days < 1:
        raise ValueError(f"span_days must be >= 1, got {span_days}")
    rng = random.Random(seed)
    base = start or date(2026, 1, 1)
    out: list[str] = []
    for _ in range(n):
        if rng.random() < null_fraction:
            out.append("")
            continue
        d = base + timedelta(days=rng.randint(0, span_days - 1))
        out.append(d.isoformat())
    return out


def _check_size(n: int) -> None:
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")


def _check_null_fraction(f: float) -> None:
    if not 0 <= f <= 1:
        raise ValueError(f"null_fraction must be in [0, 1], got {f}")


__all__ = [
    "NumericShape",
    "generate_categorical",
    "generate_date",
    "generate_numeric",
    "generate_string",
]
