"""NAPAS BIN registry tests."""

from __future__ import annotations

from n247mon.banks import BIN_TO_BANK, bank_name, is_valid_bin


def test_known_bins_resolve():
    assert bank_name("970418") == "BIDV"
    assert bank_name("970436") == "Vietcombank"
    assert bank_name("970432") == "VPBank"
    assert bank_name("970422") == "MB Bank"


def test_unknown_bin_returns_none():
    assert bank_name("999999") is None


def test_is_valid_bin_accepts_known():
    assert is_valid_bin("970418")


def test_is_valid_bin_rejects_wrong_length():
    assert not is_valid_bin("97041")
    assert not is_valid_bin("9704188")


def test_is_valid_bin_rejects_non_digit():
    assert not is_valid_bin("ABCDEF")


def test_is_valid_bin_rejects_unknown():
    assert not is_valid_bin("123456")


def test_registry_has_big_4_state_banks():
    # The big 4 partly-state-owned banks must be in the registry.
    names = set(BIN_TO_BANK.values())
    for n in ("BIDV", "Vietcombank", "VietinBank", "Agribank"):
        assert n in names, n


def test_all_bins_are_6_digits():
    assert all(len(b) == 6 and b.isdigit() for b in BIN_TO_BANK)
