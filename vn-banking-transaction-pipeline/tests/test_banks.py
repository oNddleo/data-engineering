"""Bank directory: BIN/abbreviation lookups + account validation."""

from __future__ import annotations

import pytest

from vnbank.banks import (
    all_profiles,
    is_valid_account,
    profile_for_abbr,
    profile_for_bin,
)


def test_directory_has_18_banks() -> None:
    assert len(all_profiles()) == 18


def test_directory_sorted_by_share() -> None:
    shares = [p.market_share_pct for p in all_profiles()]
    assert shares == sorted(shares, reverse=True)


def test_market_shares_sum_reasonably() -> None:
    """Total bundled share should be 80-100% (we cover the top 18)."""
    total = sum(p.market_share_pct for p in all_profiles())
    assert 80.0 <= total <= 100.0


@pytest.mark.parametrize(
    ("bin_code", "abbr"),
    [
        ("970436", "VCB"),
        ("970418", "BIDV"),
        ("970405", "AGRIBANK"),
        ("970415", "VTB"),
        ("970407", "TCB"),
        ("970422", "MB"),
        ("970432", "VPB"),
        ("970416", "ACB"),
        ("970443", "SHB"),
        ("970423", "TPB"),
        ("970403", "STB"),
        ("970431", "EIB"),
    ],
)
def test_bin_to_abbr_mapping(bin_code: str, abbr: str) -> None:
    p = profile_for_bin(bin_code)
    assert p is not None
    assert p.bank.abbreviation == abbr


def test_profile_for_abbr_case_insensitive() -> None:
    assert profile_for_abbr("vcb") is not None
    assert profile_for_abbr("VCB") is not None
    assert profile_for_abbr("Vcb") is not None


def test_profile_for_bin_unknown() -> None:
    assert profile_for_bin("999999") is None


def test_profile_for_abbr_unknown() -> None:
    assert profile_for_abbr("XYZ") is None


def test_all_bins_are_unique() -> None:
    bins = [p.bank.bin_code for p in all_profiles()]
    assert len(bins) == len(set(bins))


def test_all_abbreviations_are_unique() -> None:
    abbrs = [p.bank.abbreviation for p in all_profiles()]
    assert len(abbrs) == len(set(abbrs))


# ---------- is_valid_account ------------------------------------------------


def test_is_valid_account_basic() -> None:
    assert is_valid_account("1234567890", "970436") is True  # 10 digits, in VCB range


def test_is_valid_account_too_short() -> None:
    assert is_valid_account("123", "970436") is False


def test_is_valid_account_too_long() -> None:
    assert is_valid_account("1" * 20, "970436") is False


def test_is_valid_account_unknown_bank() -> None:
    assert is_valid_account("1234567890", "999999") is False


def test_is_valid_account_non_digit() -> None:
    assert is_valid_account("ABC123XYZ0", "970436") is False
