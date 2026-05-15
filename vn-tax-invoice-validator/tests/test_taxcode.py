"""MST checksum algorithm."""

from __future__ import annotations

import pytest

from vntax.taxcode import compute_check_digit, is_valid, normalise


# Real public MSTs from the GDT registry.
def test_vietcombank_mst_valid():
    assert is_valid("0100109106") is True


def test_fpt_mst_valid():
    """FPT Corp — caught the original ``mod == 1 → invalid`` bug."""
    assert is_valid("0301442379") is True


def test_mobile_world_mst_valid():
    assert is_valid("0301448243") is True


def test_vietjet_mst_valid():
    assert is_valid("0309532909") is True


def test_mutated_check_digit_invalid():
    # Vietcombank's MST with last digit + 1.
    assert is_valid("0100109107") is False


def test_mutated_middle_digit_invalid():
    # Vietcombank's MST with a body digit flipped.
    assert is_valid("0100109006") is False


def test_branch_suffix_accepted():
    # FPT primary 0301442379 + arbitrary 3-digit branch suffix.
    assert is_valid("0301442379001") is True
    assert is_valid("0301442379999") is True  # any branch suffix is fine


def test_branch_suffix_doesnt_revalidate_primary():
    """A bad primary checksum can't be saved by a branch suffix."""
    assert is_valid("0100109107001") is False


def test_wrong_length_rejected():
    assert is_valid("123") is False
    assert is_valid("12345678901") is False  # 11 digits — not a legal length
    assert is_valid("0100109106001234") is False  # 16 digits


def test_non_digits_rejected():
    assert is_valid("01001091AB") is False
    assert is_valid("01001091-6") is False  # raw form must be sanitised first


def test_normalise_strips_dashes_and_spaces():
    assert normalise("0301442379-001") == "0301442379001"
    assert normalise("0100 1091 06") == "0100109106"


def test_normalise_idempotent():
    """``normalise(normalise(x)) == normalise(x)`` for any input."""
    raw = "0301-442379 001"
    once = normalise(raw)
    twice = normalise(once)
    assert once == twice == "0301442379001"


def test_compute_check_digit_known_vectors():
    # Vietcombank: first 9 = "010010910" → check digit 6.
    assert compute_check_digit("010010910") == 6
    # FPT: first 9 = "030144237" → check digit 9.
    assert compute_check_digit("030144237") == 9


def test_compute_check_digit_validates_input():
    with pytest.raises(ValueError):
        compute_check_digit("12345")
    with pytest.raises(ValueError):
        compute_check_digit("01001091X")


def test_compute_check_digit_zero_mod():
    """The ``mod == 0 → check digit 0`` special case is reachable."""
    # Construct a 9-digit prefix whose weighted sum is a multiple of 11.
    # weights = [31, 29, 23, 19, 17, 13, 7, 5, 3]. We need a vector whose
    # dot product is 0 mod 11. The all-zeros vector trivially works
    # (sum = 0, mod = 0, check = 0).
    assert compute_check_digit("000000000") == 0
    assert is_valid("0000000000") is True


def test_all_legal_branch_suffixes_pass():
    """Any 3-digit suffix on a valid primary is legal."""
    for branch in ("000", "001", "010", "123", "999"):
        assert is_valid("0301442379" + branch) is True
