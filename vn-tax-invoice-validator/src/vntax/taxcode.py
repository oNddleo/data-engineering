"""MST (Mã số thuế) checksum algorithm.

The Vietnamese tax ID's 10th digit is a checksum over the first 9
digits, computed as follows:

1. Multiply each of the first 9 digits by its position-weight from
   the GDT-published table ``[31, 29, 23, 19, 17, 13, 7, 5, 3]``.
2. Sum the products.
3. Compute ``mod = sum % 11``.
4. The check digit is ``10 - mod`` for ``mod ∈ [1, 10]``, with
   ``mod == 0`` special-cased to check digit ``0``. The output is
   always a single digit 0-9.

The 13-digit form appends a 3-digit branch suffix (e.g. ``001`` for
the head office, ``002`` for the first branch). The branch suffix is
**not** independently checksum-validated — GDT controls assignment.

Examples (real public MSTs from GDT registry):

| Tax code     | Entity                  | Valid?               |
| ------------ | ----------------------- | -------------------- |
| ``0100109106`` | Vietcombank             | ✓                    |
| ``0100109105`` | (mutated check digit)   | ✗                    |
| ``0301442379`` | FPT Corp                | ✓                    |
| ``0301442379001`` | FPT Corp - HQ branch | ✓ (13-digit form) |

The first cut of this algorithm had a ``mod == 1 → invalid`` carve-out
that rejected FPT Corp's real MST. There is no such carve-out — the
formula produces a valid digit for every mod value in ``[0, 10]``.
"""

from __future__ import annotations

_WEIGHTS: tuple[int, ...] = (31, 29, 23, 19, 17, 13, 7, 5, 3)


def compute_check_digit(first_nine: str) -> int:
    """Return the expected 10th-digit checksum.

    ``first_nine`` must be exactly 9 ASCII digits — caller's job to
    sanitise. Output is always a single digit 0-9.
    """
    if len(first_nine) != 9 or not first_nine.isascii() or not first_nine.isdigit():
        raise ValueError(f"first_nine must be 9 digits, got {first_nine!r}")
    total = sum(int(d) * w for d, w in zip(first_nine, _WEIGHTS, strict=True))
    mod = total % 11
    if mod == 0:
        return 0
    return 10 - mod


def is_valid(digits: str) -> bool:
    """``True`` if ``digits`` is a valid 10- or 13-digit MST.

    For 13-digit codes only the first 10 digits go through the
    checksum — the 3-digit suffix is GDT-assigned and not
    independently verifiable.
    """
    if not digits.isascii() or not digits.isdigit():
        return False
    if len(digits) not in (10, 13):
        return False
    primary = digits[:10]
    expected = compute_check_digit(primary[:9])
    return expected == int(primary[9])


def normalise(raw: str) -> str:
    """Strip whitespace and ``-`` separators commonly found in invoices.

    ``"0301442379-001"`` → ``"0301442379001"``. Doesn't validate;
    callers pair this with :func:`is_valid`.
    """
    return "".join(c for c in raw if c.isdigit())


__all__ = ["compute_check_digit", "is_valid", "normalise"]
