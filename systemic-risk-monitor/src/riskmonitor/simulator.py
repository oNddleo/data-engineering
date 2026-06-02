"""TransactionSimulator: generates synthetic interbank transfer flows."""

from __future__ import annotations

import random
from dataclasses import dataclass

BANK_POOL: list[str] = [
    "BANK_A",
    "BANK_B",
    "BANK_C",
    "BANK_D",
    "BANK_E",
    "BANK_F",
    "BANK_G",
    "BANK_H",
    "BANK_I",
    "BANK_J",
]

_AMOUNT_MIN = 1_000_000.0  # 1 M
_AMOUNT_MAX = 50_000_000.0  # 50 M


@dataclass(frozen=True)
class Transfer:
    """A single synthetic interbank transfer."""

    from_id: str
    to_id: str
    amount: float


class TransactionSimulator:
    """Generates reproducible synthetic interbank flows from a seeded RNG.

    Parameters
    ----------
    seed:
        Seed for the internal :class:`random.Random` instance.  Defaults to
        ``42`` to give deterministic results across runs.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, n: int, seed: int | None = None) -> list[Transfer]:
        """Generate *n* synthetic transfers.

        Parameters
        ----------
        n:
            Number of transfers to generate.
        seed:
            Optional override seed.  If *None*, the instance seed is used.

        Returns
        -------
        list[Transfer]
            Deterministically generated transfers.
        """
        rng = random.Random(seed if seed is not None else self._seed)
        transfers: list[Transfer] = []
        pool = BANK_POOL

        for _ in range(n):
            from_id = rng.choice(pool)
            # Ensure from_id != to_id
            choices = [b for b in pool if b != from_id]
            to_id = rng.choice(choices)
            amount = round(rng.uniform(_AMOUNT_MIN, _AMOUNT_MAX), 2)
            transfers.append(Transfer(from_id=from_id, to_id=to_id, amount=amount))

        return transfers
