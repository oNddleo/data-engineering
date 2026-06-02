"""EVN customer code + provincial unit directory."""

from __future__ import annotations

import pytest

from evn.customer import (
    all_units,
    is_valid_customer_code,
    unit_for_abbr,
    unit_for_code,
    unit_for_prefix,
)


def test_directory_has_five_units() -> None:
    """One per EVN regional corporation (PA-PE)."""
    assert len(all_units()) == 5


@pytest.mark.parametrize(
    ("prefix", "abbr"),
    [
        ("PA", "EVNHANOI"),
        ("PB", "EVNNPC"),
        ("PC", "EVNCPC"),
        ("PD", "EVNSPC"),
        ("PE", "EVNHCMC"),
    ],
)
def test_prefix_to_abbr_mapping(prefix: str, abbr: str) -> None:
    u = unit_for_prefix(prefix)
    assert u is not None
    assert u.abbreviation == abbr


def test_unit_for_prefix_case_insensitive() -> None:
    assert unit_for_prefix("pa") is not None
    assert unit_for_prefix("Pa") is not None


def test_unit_for_prefix_unknown() -> None:
    assert unit_for_prefix("ZZ") is None


def test_unit_for_abbr_case_insensitive() -> None:
    assert unit_for_abbr("evnhanoi") is not None


def test_unit_for_abbr_unknown() -> None:
    assert unit_for_abbr("FAKE") is None


# ---------- is_valid_customer_code -----------------------------------------


def test_valid_code_pa() -> None:
    assert is_valid_customer_code("PA00000000001") is True


def test_valid_code_pe() -> None:
    assert is_valid_customer_code("PE99999999999") is True


def test_invalid_code_too_short() -> None:
    assert is_valid_customer_code("PA1234") is False


def test_invalid_code_too_long() -> None:
    assert is_valid_customer_code("PA0000000000001") is False


def test_invalid_code_unknown_prefix() -> None:
    assert is_valid_customer_code("ZZ00000000001") is False


def test_invalid_code_non_digit_body() -> None:
    assert is_valid_customer_code("PA0000ABCD001") is False


def test_invalid_code_empty() -> None:
    assert is_valid_customer_code("") is False


# ---------- unit_for_code --------------------------------------------------


def test_unit_for_code_resolves() -> None:
    u = unit_for_code("PE12345678901")
    assert u is not None
    assert u.abbreviation == "EVNHCMC"


def test_unit_for_code_invalid_returns_none() -> None:
    assert unit_for_code("nonsense") is None


# ---------- Bundled data integrity -----------------------------------------


def test_all_prefixes_unique() -> None:
    prefixes = [u.prefix for u in all_units()]
    assert len(prefixes) == len(set(prefixes))


def test_all_abbreviations_unique() -> None:
    abbrs = [u.abbreviation for u in all_units()]
    assert len(abbrs) == len(set(abbrs))


def test_all_prefixes_two_letters() -> None:
    for u in all_units():
        assert len(u.prefix) == 2
        assert u.prefix.isalpha()
        assert u.prefix.isupper()
