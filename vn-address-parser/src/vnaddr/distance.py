"""Levenshtein edit distance + nearest-neighbour lookup.

Uses the classic two-row dynamic programming formulation
(Wagner-Fischer 1974) — O(n × m) time, O(min(n, m)) space.

For VN address tokens the input strings are short (≤ 30 chars
typically), so the asymptotic cost is dominated by Python overhead;
no need for the Hirschberg / DP-with-bitmasks variants.
"""

from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    """Return the Levenshtein edit distance between ``a`` and ``b``.

    Insertion, deletion, and substitution each cost 1.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Always make ``a`` the shorter — keeps memory at min(n, m).
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    cur = [0] * (len(a) + 1)
    for j, cb in enumerate(b, start=1):
        cur[0] = j
        for i, ca in enumerate(a, start=1):
            cost = 0 if ca == cb else 1
            cur[i] = min(
                prev[i] + 1,  # deletion
                cur[i - 1] + 1,  # insertion
                prev[i - 1] + cost,  # substitution
            )
        prev, cur = cur, prev
    return prev[len(a)]


def find_closest(
    needle: str,
    haystack: list[str],
    *,
    max_distance: int = 2,
) -> tuple[str, int] | None:
    """Return ``(closest_match, distance)`` from ``haystack``.

    Returns ``None`` if no candidate is within ``max_distance``.
    Ties broken by haystack order (first wins).
    """
    if max_distance < 0:
        raise ValueError(f"max_distance must be >= 0, got {max_distance}")
    best: tuple[str, int] | None = None
    for candidate in haystack:
        # Early-out: length-difference is a lower bound on edit distance.
        if abs(len(candidate) - len(needle)) > max_distance:
            continue
        d = levenshtein(needle, candidate)
        if d <= max_distance and (best is None or d < best[1]):
            best = (candidate, d)
            if d == 0:
                break
    return best


__all__ = ["find_closest", "levenshtein"]
