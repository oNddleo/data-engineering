"""Hypothesis properties — invariants of normalise + distance + parse."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnaddr.distance import find_closest, levenshtein
from vnaddr.normalize import fold_diacritics, normalise
from vnaddr.parser import parse
from vnaddr.simulator import NoiseLevel, generate

# ---------- normalize properties ---------------------------------------------


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=50)
def test_property_fold_idempotent(text: str) -> None:
    """fold_diacritics(fold_diacritics(x)) == fold_diacritics(x)."""
    once = fold_diacritics(text)
    twice = fold_diacritics(once)
    assert once == twice


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=50)
def test_property_fold_idempotent_lower(text: str) -> None:
    """Folding always returns lowercase output."""
    out = fold_diacritics(text)
    assert out == out.lower()


@given(st.text(min_size=0, max_size=100))
@settings(max_examples=50)
def test_property_normalise_idempotent(text: str) -> None:
    """normalise(normalise(x)) == normalise(x)."""
    once = normalise(text)
    twice = normalise(once)
    assert once == twice


# ---------- distance properties ----------------------------------------------


@given(st.text(min_size=0, max_size=20))
@settings(max_examples=40)
def test_property_levenshtein_self_zero(text: str) -> None:
    """levenshtein(s, s) == 0."""
    assert levenshtein(text, text) == 0


@given(
    a=st.text(min_size=0, max_size=20),
    b=st.text(min_size=0, max_size=20),
)
@settings(max_examples=40)
def test_property_levenshtein_symmetric(a: str, b: str) -> None:
    """levenshtein(a, b) == levenshtein(b, a)."""
    assert levenshtein(a, b) == levenshtein(b, a)


@given(
    a=st.text(min_size=0, max_size=20),
    b=st.text(min_size=0, max_size=20),
)
@settings(max_examples=40)
def test_property_levenshtein_bounded_by_max_length(a: str, b: str) -> None:
    """levenshtein(a, b) <= max(len(a), len(b))."""
    assert levenshtein(a, b) <= max(len(a), len(b))


@given(
    needle=st.text(alphabet="abcde", min_size=3, max_size=8),
    haystack=st.lists(
        st.text(alphabet="abcde", min_size=3, max_size=8),
        min_size=1,
        max_size=20,
    ),
)
@settings(max_examples=20)
def test_property_find_closest_returns_member(
    needle: str,
    haystack: list[str],
) -> None:
    """When a match exists, it's a member of haystack."""
    out = find_closest(needle, haystack, max_distance=10)
    if out is not None:
        assert out[0] in haystack


# ---------- parser properties ------------------------------------------------


@given(
    n=st.integers(min_value=1, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_clean_simulator_always_parses(n: int, seed: int) -> None:
    """Every CLEAN-noise address parses to is_complete=True."""
    for line in generate(n=n, noise=NoiseLevel.CLEAN, seed=seed):
        p = parse(line)
        assert p.is_complete, f"failed on: {line}"


@given(
    n=st.integers(min_value=1, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_folded_simulator_always_parses(n: int, seed: int) -> None:
    """Every FOLDED-noise address parses to is_complete=True."""
    for line in generate(n=n, noise=NoiseLevel.FOLDED, seed=seed):
        p = parse(line)
        assert p.is_complete, f"failed on: {line}"


@given(
    n=st.integers(min_value=1, max_value=30),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_property_abbrev_simulator_always_parses(n: int, seed: int) -> None:
    """Every ABBREV-noise address parses to is_complete=True."""
    for line in generate(n=n, noise=NoiseLevel.ABBREV, seed=seed):
        p = parse(line)
        assert p.is_complete, f"failed on: {line}"


@given(st.text(alphabet="zxqwjy", min_size=10, max_size=50))
@settings(max_examples=20)
def test_property_long_garbage_does_not_match(text: str) -> None:
    """Long consonant-only garbage never fuzzy-matches a VN admin unit.

    (Very short strings may fuzzy-match short codes; require min_size=10
    so the edit distance to any unit name exceeds the threshold.)
    """
    p = parse(text)
    assert not p.is_partial
