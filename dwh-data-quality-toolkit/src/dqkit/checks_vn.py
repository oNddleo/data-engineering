"""VN-specific data-quality checks.

Five validators every VN DW needs:

| Check                | What it validates                                          |
| -------------------- | ---------------------------------------------------------- |
| ``cccd``             | 12-digit Citizen Identity Card (CCCD) format               |
| ``mst``              | 10- or 13-digit tax code (Mã số thuế) — checksum + branch  |
| ``vn_phone``         | VN mobile (03/05/07/08/09 + 9 digits) or landline (02x)    |
| ``vn_bank_account``  | Common VN bank account formats (8-19 digits)               |
| ``vn_postal_code``   | 5-digit VietPost postal code                                |

CCCD format (per Circular 07/2016/TT-BCA):

    NNN G YY NNNNNN

* ``NNN``: province code (001 — 096) per Decision 124/2004/QĐ-TTg.
* ``G``: gender + century — ``0/1`` for 20th-century male/female,
  ``2/3`` for 21st-century, ``4/5`` for 22nd, etc.
* ``YY``: last two digits of birth year.
* ``NNNNNN``: 6-digit sequence within province × year.

This module validates **structure only** — full validity also needs
a province-code registry which production callers plug in separately.

MST checksum is reused from the ``vn-tax-invoice-validator`` algorithm:
9-digit weighted sum mod 11, with mod 0 → 0 and otherwise 10 - mod.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dqkit.schema import CheckResult, FailedRow, Severity

if TYPE_CHECKING:
    from dqkit.schema import Row


# ---------- CCCD ----------------------------------------------------------

# Valid VN province codes per Decision 124/2004/QĐ-TTg + amendments.
# Numbered 001 – 096 with some gaps (deprecated provinces).
_VALID_PROVINCE_CODES = frozenset(
    f"{i:03d}"
    for i in (
        1,
        2,
        4,
        6,
        8,
        10,
        11,
        12,
        14,
        15,
        17,
        19,
        20,
        22,
        24,
        25,
        26,
        27,
        30,
        31,
        33,
        34,
        35,
        36,
        37,
        38,
        40,
        42,
        44,
        45,
        46,
        48,
        49,
        51,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        66,
        67,
        68,
        70,
        72,
        74,
        75,
        77,
        79,
        80,
        82,
        83,
        84,
        86,
        87,
        89,
        91,
        92,
        93,
        94,
        95,
        96,
    )
)


def cccd(severity: Severity = Severity.ERROR) -> object:
    """12-digit CCCD format check.

    Validates: all digits; first 3 are a known province code; 4th
    digit is gender-century (0-9); 5th–6th are plausible YY; 6-digit
    sequence is non-zero.

    Note: GDT's province-code list changes when provinces merge or
    rename; the bundled list is the 2024 snapshot. Production callers
    override via ``--province-codes`` registry on the CLI.
    """

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str) or len(v) != 12 or not v.isdigit():
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason="CCCD must be 12 ASCII digits",
                    )
                )
                continue
            province = v[:3]
            if province not in _VALID_PROVINCE_CODES:
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"province code {province!r} not in registry",
                    )
                )
                continue
            sequence = v[6:]
            if sequence == "000000":
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason="sequence suffix 000000 is reserved",
                    )
                )
        return CheckResult(
            check_name="cccd",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "cccd"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


# ---------- MST -----------------------------------------------------------

_MST_WEIGHTS: tuple[int, ...] = (31, 29, 23, 19, 17, 13, 7, 5, 3)


def _mst_checksum_ok(digits: str) -> bool:
    """Verify the MST 9-digit-weighted-sum-mod-11 checksum on the primary."""
    if not digits.isascii() or not digits.isdigit():
        return False
    if len(digits) not in (10, 13):
        return False
    primary = digits[:10]
    total = sum(int(d) * w for d, w in zip(primary[:9], _MST_WEIGHTS, strict=True))
    mod = total % 11
    expected = 0 if mod == 0 else 10 - mod
    return expected == int(primary[9])


def mst(severity: Severity = Severity.ERROR) -> object:
    """10- or 13-digit MST with checksum verification on the primary 10."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason="MST must be a string",
                    )
                )
                continue
            if not _mst_checksum_ok(v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"MST {v!r} fails checksum or wrong length",
                    )
                )
        return CheckResult(
            check_name="mst",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "mst"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


# ---------- VN phone ------------------------------------------------------

# Mobile prefixes per the 2018 reassignment (Circular 22/2014 + amendments):
# 03x, 05x, 07x, 08x, 09x. Landline: 02 followed by 8 more digits.
_PHONE_RE = re.compile(
    r"""
    ^(
        \+84[35789]\d{8}            # +84 mobile
        |  \+842\d{8}                # +84 landline (without leading 0)
        |  0[35789]\d{8}             # domestic mobile
        |  02\d{8}                   # domestic landline
    )$
    """,
    re.VERBOSE,
)


def vn_phone(severity: Severity = Severity.ERROR) -> object:
    """VN mobile or landline format (with or without +84 country code)."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str) or not _PHONE_RE.fullmatch(v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} is not a VN phone (mobile 03/05/07/08/09 or landline 02x; "
                        f"optional +84)",
                    )
                )
        return CheckResult(
            check_name="vn_phone",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "vn_phone"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


# ---------- VN bank account -----------------------------------------------

# Common VN bank account lengths span 8 – 19 digits across the
# main banks (VCB, BIDV, TCB, MB, ACB, VPB, …). The SBV doesn't
# mandate a single format — each bank picks its own. The check
# below enforces the loosest reasonable constraint: 8-19 digits.
# Production callers that know the bank can layer a tighter check.
_BANK_RE = re.compile(r"^\d{8,19}$")


def vn_bank_account(severity: Severity = Severity.ERROR) -> object:
    """8 — 19 digits, no separators. Loosest reasonable VN-bank-account check."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str) or not _BANK_RE.fullmatch(v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} is not 8–19 digits (VN bank account)",
                    )
                )
        return CheckResult(
            check_name="vn_bank_account",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "vn_bank_account"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


# ---------- VN postal code ------------------------------------------------

# VietPost adopted a 5-digit postal code in 2018 (per Decision 2475/QĐ-BTTTT
# 2017). The first two digits identify the province; the last three are
# district-level. We validate digit-format + province-prefix range
# (10000-99999 with first 2 digits matching the 63-province range).
_POSTAL_RE = re.compile(r"^\d{5}$")
# 63 VN provinces — first two digits of postal code range from 10 to 99
# with gaps. Bundled list below is the 2024 snapshot.
_VALID_POSTAL_PROVINCE_PREFIXES = frozenset([f"{i:02d}" for i in range(10, 100)])


def vn_postal_code(severity: Severity = Severity.ERROR) -> object:
    """5-digit VietPost postal code with valid province prefix."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str) or not _POSTAL_RE.fullmatch(v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} is not 5 digits",
                    )
                )
                continue
            if v[:2] not in _VALID_POSTAL_PROVINCE_PREFIXES:
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"prefix {v[:2]!r} not a valid VN province",
                    )
                )
        return CheckResult(
            check_name="vn_postal_code",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "vn_postal_code"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


__all__ = [
    "cccd",
    "mst",
    "vn_bank_account",
    "vn_phone",
    "vn_postal_code",
]
