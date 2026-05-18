"""VN-specific check behaviour."""

from __future__ import annotations

from dqkit.checks_vn import cccd, mst, vn_bank_account, vn_phone, vn_postal_code


def _run(check, rows, column):  # type: ignore[no-untyped-def]
    return check(rows, column)


# ---------- CCCD -----------------------------------------------------------


def test_cccd_accepts_valid_12_digit():
    """Valid province (001 = Hà Nội) + plausible sequence."""
    rows = [{"cccd": "001201123456"}]
    r = _run(cccd(), rows, "cccd")
    assert r.passed is True


def test_cccd_rejects_short():
    rows = [{"cccd": "0012011234"}]
    r = _run(cccd(), rows, "cccd")
    assert r.n_failed == 1
    assert "12 ASCII digits" in r.failures[0].reason


def test_cccd_rejects_unknown_province():
    rows = [{"cccd": "999201123456"}]
    r = _run(cccd(), rows, "cccd")
    assert r.n_failed == 1
    assert "province" in r.failures[0].reason


def test_cccd_rejects_reserved_zero_sequence():
    """000000 sequence is reserved."""
    rows = [{"cccd": "001201000000"}]
    r = _run(cccd(), rows, "cccd")
    assert r.n_failed == 1


def test_cccd_rejects_non_digit():
    rows = [{"cccd": "001A01123456"}]
    r = _run(cccd(), rows, "cccd")
    assert r.n_failed == 1


def test_cccd_skips_none():
    """``None`` doesn't fail — pair with ``not_null`` for required CCCD."""
    rows = [{"cccd": None}]
    r = _run(cccd(), rows, "cccd")
    assert r.passed is True


# ---------- MST -----------------------------------------------------------


def test_mst_accepts_real_vietcombank():
    """Vietcombank's published MST."""
    rows = [{"mst": "0100109106"}]
    r = _run(mst(), rows, "mst")
    assert r.passed is True


def test_mst_accepts_real_fpt():
    """FPT Corp — the value that broke an earlier algorithm draft."""
    rows = [{"mst": "0301442379"}]
    r = _run(mst(), rows, "mst")
    assert r.passed is True


def test_mst_accepts_13_digit_branch():
    rows = [{"mst": "0301442379999"}]
    r = _run(mst(), rows, "mst")
    assert r.passed is True


def test_mst_rejects_mutated_checksum():
    rows = [{"mst": "0100109107"}]  # last digit + 1
    r = _run(mst(), rows, "mst")
    assert r.n_failed == 1


def test_mst_rejects_wrong_length():
    rows = [{"mst": "12345"}]
    r = _run(mst(), rows, "mst")
    assert r.n_failed == 1


# ---------- VN phone ------------------------------------------------------


def test_vn_phone_accepts_mobile():
    rows = [
        {"phone": "0901234567"},
        {"phone": "0312345678"},
        {"phone": "0512345678"},
        {"phone": "0712345678"},
        {"phone": "0812345678"},
    ]
    r = _run(vn_phone(), rows, "phone")
    assert r.passed is True


def test_vn_phone_accepts_landline():
    rows = [{"phone": "0241234567"}]
    r = _run(vn_phone(), rows, "phone")
    assert r.passed is True


def test_vn_phone_accepts_plus84():
    rows = [{"phone": "+84901234567"}]
    r = _run(vn_phone(), rows, "phone")
    assert r.passed is True


def test_vn_phone_rejects_wrong_prefix():
    rows = [{"phone": "0112345678"}]  # 011 isn't assigned
    r = _run(vn_phone(), rows, "phone")
    assert r.n_failed == 1


def test_vn_phone_rejects_short():
    rows = [{"phone": "09012345"}]  # too short
    r = _run(vn_phone(), rows, "phone")
    assert r.n_failed == 1


# ---------- VN bank account ----------------------------------------------


def test_vn_bank_accepts_common_lengths():
    rows = [
        {"x": "12345678"},  # 8 — min
        {"x": "1234567890"},  # 10 — typical
        {"x": "1234567890123456789"},  # 19 — max
    ]
    r = _run(vn_bank_account(), rows, "x")
    assert r.passed is True


def test_vn_bank_rejects_too_short():
    rows = [{"x": "12345"}]
    r = _run(vn_bank_account(), rows, "x")
    assert r.n_failed == 1


def test_vn_bank_rejects_too_long():
    rows = [{"x": "1" * 20}]
    r = _run(vn_bank_account(), rows, "x")
    assert r.n_failed == 1


def test_vn_bank_rejects_non_digits():
    rows = [{"x": "12345-6789"}]
    r = _run(vn_bank_account(), rows, "x")
    assert r.n_failed == 1


# ---------- VN postal code -----------------------------------------------


def test_vn_postal_accepts_5_digits():
    rows = [{"x": "10000"}, {"x": "70000"}]
    r = _run(vn_postal_code(), rows, "x")
    assert r.passed is True


def test_vn_postal_rejects_short():
    rows = [{"x": "1234"}]
    r = _run(vn_postal_code(), rows, "x")
    assert r.n_failed == 1


def test_vn_postal_rejects_invalid_province_prefix():
    """Province prefix < 10 isn't assigned."""
    rows = [{"x": "05000"}]
    r = _run(vn_postal_code(), rows, "x")
    assert r.n_failed == 1
