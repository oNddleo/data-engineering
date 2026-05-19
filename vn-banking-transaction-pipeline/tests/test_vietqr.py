"""VietQR codec: build, parse, CRC, round-trips."""

from __future__ import annotations

import pytest

from vnbank.vietqr import build_vietqr, crc16_ccitt, parse_vietqr

# ---------- CRC-16-CCITT ----------------------------------------------------


def test_crc16_known_vector() -> None:
    """CRC16/CCITT-FALSE: '123456789' → 0x29B1 (RFC 1662 test vector)."""
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_crc16_empty() -> None:
    """CRC of empty bytes = init value (0xFFFF)."""
    assert crc16_ccitt(b"") == 0xFFFF


def test_crc16_deterministic() -> None:
    assert crc16_ccitt(b"hello") == crc16_ccitt(b"hello")


# ---------- build_vietqr ----------------------------------------------------


def test_build_static_qr() -> None:
    """No amount → static QR (POI method 11)."""
    qr = build_vietqr(bank_bin="970436", account_number="1234567890")
    # Should contain POI 11 → tag "0102" + "11"
    assert "010211" in qr
    # Currency must be VND (704).
    assert "5303704" in qr
    # Country VN.
    assert "5802VN" in qr


def test_build_dynamic_qr() -> None:
    """Amount > 0 → dynamic QR (POI method 12 + tag 54)."""
    qr = build_vietqr(
        bank_bin="970436",
        account_number="1234567890",
        amount_vnd=100_000,
    )
    assert "010212" in qr  # POI method 12
    assert "5406100000" in qr  # tag 54, length 06, value "100000"


def test_build_contains_bank_bin() -> None:
    qr = build_vietqr(bank_bin="970418", account_number="9999")
    assert "970418" in qr


def test_build_rejects_bad_bin() -> None:
    with pytest.raises(ValueError, match="bank_bin"):
        build_vietqr(bank_bin="ABC123", account_number="1234")


def test_build_rejects_bad_account() -> None:
    with pytest.raises(ValueError, match="account_number"):
        build_vietqr(bank_bin="970436", account_number="ABC")


def test_build_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount_vnd"):
        build_vietqr(
            bank_bin="970436",
            account_number="1234",
            amount_vnd=-1,
        )


# ---------- parse_vietqr ----------------------------------------------------


def test_parse_roundtrip_static() -> None:
    qr = build_vietqr(bank_bin="970436", account_number="1234567890")
    p = parse_vietqr(qr)
    assert p.bank_bin == "970436"
    assert p.account_number == "1234567890"
    assert p.amount_vnd == 0
    assert p.is_dynamic is False
    assert p.purpose == ""


def test_parse_roundtrip_dynamic() -> None:
    qr = build_vietqr(
        bank_bin="970418",
        account_number="9876543210",
        amount_vnd=250_000,
        purpose="Order 12345",
    )
    p = parse_vietqr(qr)
    assert p.bank_bin == "970418"
    assert p.account_number == "9876543210"
    assert p.amount_vnd == 250_000
    assert p.is_dynamic is True
    assert p.purpose == "Order 12345"


def test_parse_rejects_bad_crc() -> None:
    qr = build_vietqr(bank_bin="970436", account_number="1234567890")
    # Flip a CRC nibble.
    tampered = qr[:-1] + ("0" if qr[-1] != "0" else "1")
    with pytest.raises(ValueError, match="CRC"):
        parse_vietqr(tampered)


def test_parse_rejects_truncated() -> None:
    with pytest.raises(ValueError):
        parse_vietqr("00020101")


def test_parse_real_world_payload_shape() -> None:
    """The full payload must round-trip to the exact same string."""
    payloads = [
        build_vietqr("970436", "1234567890"),
        build_vietqr("970418", "9999", amount_vnd=50_000),
        build_vietqr("970422", "111222333", amount_vnd=1_000_000, purpose="HD001"),
    ]
    for payload in payloads:
        p = parse_vietqr(payload)
        rebuilt = build_vietqr(
            p.bank_bin,
            p.account_number,
            p.amount_vnd,
            p.purpose,
        )
        assert rebuilt == payload
