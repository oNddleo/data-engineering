"""NAPAS bank identifier numbers (BIN) for the 247 instant transfer network.

Subset of the official NAPAS BIN registry. These are the codes that
prefix every NAPAS 247 message and identify which member bank
originated or received the transfer. A handful of high-volume banks
are enough for synthetic-data realism; expand the table as needed.

Source format: 6-digit BIN string, kept as ``str`` because some BINs
have leading zeros that an ``int`` would silently lose.
"""

from __future__ import annotations

BIN_TO_BANK: dict[str, str] = {
    "970403": "Sacombank",
    "970405": "Agribank",
    "970406": "DongA Bank",
    "970407": "Techcombank",
    "970409": "BacABank",
    "970412": "PVcomBank",
    "970414": "Oceanbank",
    "970415": "VietinBank",
    "970416": "ACB",
    "970418": "BIDV",
    "970419": "NCB",
    "970421": "VRB",
    "970422": "MB Bank",
    "970423": "TPBank",
    "970424": "Shinhan Bank",
    "970425": "ABBank",
    "970426": "MaritimeBank",
    "970427": "VietABank",
    "970428": "NamABank",
    "970429": "SCB",
    "970430": "PG Bank",
    "970431": "Eximbank",
    "970432": "VPBank",
    "970433": "VietBank",
    "970434": "IndovinaBank",
    "970436": "Vietcombank",
    "970437": "HDBank",
    "970438": "BaoVietBank",
    "970440": "SeABank",
    "970441": "VietCapital Bank",
    "970442": "HongLeong Bank",
    "970443": "SHB",
    "970444": "CBBank",
    "970448": "OCB",
    "970449": "LienVietPostBank",
    "970452": "KienLongBank",
    "970454": "BanVietBank",
}
"""Mapping of NAPAS 6-digit BIN → bank short name."""


def bank_name(bin_code: str) -> str | None:
    """Look up a bank short name by BIN code; returns ``None`` if unknown."""
    return BIN_TO_BANK.get(bin_code)


def is_valid_bin(bin_code: str) -> bool:
    """Return True iff ``bin_code`` is a 6-digit numeric string we recognise."""
    return len(bin_code) == 6 and bin_code.isdigit() and bin_code in BIN_TO_BANK


__all__ = ["BIN_TO_BANK", "bank_name", "is_valid_bin"]
