"""VietQR codec — encode/decode the NAPAS national QR payment standard.

VietQR (live since March 2022) extends the EMV Co. Merchant Presented
QR Code spec with a NAPAS-specific Merchant Account Information block.
The payload is a sequence of **TLV** (tag-length-value) fields where
both tag and length are ASCII 2-digit strings, value is ASCII text.

The complete field map (subset we implement):

| Tag | Name                          | Required | Notes                       |
| --- | ----------------------------- | -------- | --------------------------- |
| 00  | Payload Format Indicator      | yes      | always ``"01"``             |
| 01  | Point of Initiation Method    | no       | ``"11"`` static / ``"12"`` dynamic |
| 38  | Merchant Account Info (NAPAS) | yes      | nested TLV (see below)      |
| 53  | Transaction Currency          | yes      | ISO 4217 numeric — VND=``"704"`` |
| 54  | Transaction Amount            | no       | ASCII decimal, dynamic only |
| 58  | Country Code                  | yes      | ``"VN"``                    |
| 62  | Additional Data (purpose)     | no       | nested TLV; sub-tag 08 = purpose |
| 63  | CRC-16-CCITT (xmodem)         | yes      | 4 hex chars, uppercase      |

Tag 38 (Merchant Account Info) is itself a TLV:

| Sub-tag | Value                                                |
| ------- | ---------------------------------------------------- |
| 00      | AID — Application Identifier, ``"A000000727"`` for NAPAS |
| 01      | Beneficiary Org block (nested TLV):                  |
|         |   00 = Bank BIN (6 digits)                           |
|         |   01 = Beneficiary account number                    |
| 02      | Service code: QRIBFTTA (account) / QRIBFTTC (card)   |

We only validate / build the **account-transfer** flavour (QRIBFTTA),
which is the dominant case for retail VietQR.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VietQRPayload:
    """Parsed VietQR payload."""

    bank_bin: str
    account_number: str
    amount_vnd: int  # 0 for static QRs (no fixed amount)
    purpose: str  # tag 62 sub-tag 08, often empty
    is_dynamic: bool  # True if amount is fixed


def crc16_ccitt(data: bytes, *, poly: int = 0x1021, init: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE (xmodem variant used by EMV QR)."""
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poly) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc


def _tlv(tag: str, value: str) -> str:
    if len(tag) != 2:
        raise ValueError(f"tag must be 2 chars, got {tag!r}")
    if len(value) > 99:
        raise ValueError(f"value too long ({len(value)}) for 2-digit length")
    return f"{tag}{len(value):02d}{value}"


def build_vietqr(
    bank_bin: str,
    account_number: str,
    amount_vnd: int = 0,
    purpose: str = "",
) -> str:
    """Build a VietQR payload (account-transfer flavour, QRIBFTTA).

    ``amount_vnd > 0`` produces a *dynamic* QR (fixed amount); ``0``
    produces a *static* QR (payer enters the amount).
    """
    if not bank_bin.isdigit() or len(bank_bin) != 6:
        raise ValueError(f"bank_bin must be 6 digits, got {bank_bin!r}")
    if not account_number.isdigit():
        raise ValueError(f"account_number must be all digits, got {account_number!r}")
    if amount_vnd < 0:
        raise ValueError(f"amount_vnd must be >= 0, got {amount_vnd}")

    # Tag 38 sub-tag 01 = Beneficiary Org (nested TLV).
    beneficiary = _tlv("00", bank_bin) + _tlv("01", account_number)
    merchant_account = (
        _tlv("00", "A000000727")  # AID for NAPAS
        + _tlv("01", beneficiary)
        + _tlv("02", "QRIBFTTA")  # service code: account transfer
    )

    poi_method = "12" if amount_vnd > 0 else "11"

    fields = [
        _tlv("00", "01"),  # payload format indicator
        _tlv("01", poi_method),
        _tlv("38", merchant_account),
        _tlv("53", "704"),  # VND
    ]
    if amount_vnd > 0:
        fields.append(_tlv("54", str(amount_vnd)))
    fields.append(_tlv("58", "VN"))
    if purpose:
        fields.append(_tlv("62", _tlv("08", purpose)))
    # Append the CRC placeholder (tag 63 + length 04) then compute CRC over everything
    # including the placeholder header.
    payload_no_crc = "".join(fields) + "6304"
    crc = crc16_ccitt(payload_no_crc.encode("ascii"))
    return payload_no_crc + f"{crc:04X}"


def parse_vietqr(payload: str) -> VietQRPayload:
    """Parse a VietQR payload and verify the CRC."""
    if len(payload) < 10:
        raise ValueError("payload too short")
    crc_value = payload[-4:]
    crc_body = payload[:-4]
    expected = crc16_ccitt(crc_body.encode("ascii"))
    if int(crc_value, 16) != expected:
        raise ValueError(
            f"CRC mismatch: got {crc_value!r}, expected {expected:04X}",
        )
    fields = _parse_tlv(payload[:-8])  # exclude the trailing "6304" + CRC

    if fields.get("00") != "01":
        raise ValueError(f"unexpected payload format: {fields.get('00')!r}")
    if fields.get("58") != "VN":
        raise ValueError(f"country code is not VN: {fields.get('58')!r}")
    if fields.get("53") != "704":
        raise ValueError(f"currency is not VND (704): {fields.get('53')!r}")

    if "38" not in fields:
        raise ValueError("missing merchant account info (tag 38)")
    merchant = _parse_tlv(fields["38"])
    if merchant.get("00") != "A000000727":
        raise ValueError(f"unexpected AID: {merchant.get('00')!r}")
    beneficiary_raw = merchant.get("01", "")
    beneficiary = _parse_tlv(beneficiary_raw)
    bank_bin = beneficiary.get("00", "")
    account_number = beneficiary.get("01", "")
    if not bank_bin or not account_number:
        raise ValueError("missing bank_bin / account in beneficiary block")

    amount = int(fields["54"]) if "54" in fields else 0
    is_dynamic = fields.get("01") == "12"

    purpose = ""
    if "62" in fields:
        addl = _parse_tlv(fields["62"])
        purpose = addl.get("08", "")

    return VietQRPayload(
        bank_bin=bank_bin,
        account_number=account_number,
        amount_vnd=amount,
        purpose=purpose,
        is_dynamic=is_dynamic,
    )


def _parse_tlv(s: str) -> dict[str, str]:
    """Parse a flat sequence of ASCII 2-digit-tag / 2-digit-length / value triples."""
    out: dict[str, str] = {}
    i = 0
    while i < len(s):
        if i + 4 > len(s):
            raise ValueError(f"truncated TLV at offset {i}: {s[i:]!r}")
        tag = s[i : i + 2]
        try:
            length = int(s[i + 2 : i + 4])
        except ValueError as exc:
            raise ValueError(f"invalid length at offset {i + 2}") from exc
        if i + 4 + length > len(s):
            raise ValueError(f"TLV value runs past end at tag {tag!r}")
        out[tag] = s[i + 4 : i + 4 + length]
        i += 4 + length
    return out


__all__ = [
    "VietQRPayload",
    "build_vietqr",
    "crc16_ccitt",
    "parse_vietqr",
]
