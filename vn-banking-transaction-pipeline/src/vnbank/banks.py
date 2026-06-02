"""VN commercial-bank directory — BIN codes per NAPAS allocation.

Each bank is uniquely identified in the interbank network by a 6-digit
**BIN** (Bank Identification Number) assigned by NAPAS. The same BIN
appears on physical cards (positions 1-6 of the PAN) and in VietQR
payloads (field 38 sub-field 00 of the EMV TLV).

The 18 banks bundled below cover **> 95% of VN retail-banking deposits**
as of 2025 (source: SBV Annual Report 2024, NAPAS member directory).
Account number length varies by bank and product line; we encode the
canonical length used by the bank's *primary* personal-checking schema.

For account-number validation we accept any number of digits within
``[min_account_length, max_account_length]`` for the bank — banks often
issue multiple lengths for legacy vs current products.
"""

from __future__ import annotations

from dataclasses import dataclass

from vnbank.schema import Bank


@dataclass(frozen=True, slots=True)
class BankProfile:
    """Bundled bank metadata + account-number length range."""

    bank: Bank
    min_account_length: int
    max_account_length: int
    market_share_pct: float


# Ordered by deposit market share (SBV 2024 figures, rounded).
_PROFILES: tuple[BankProfile, ...] = (
    BankProfile(
        Bank(
            bin_code="970418",
            abbreviation="BIDV",
            name_vi="Ngân hàng TMCP Đầu tư và Phát triển Việt Nam",
            name_en="Bank for Investment and Development of Vietnam",
            swift="BIDVVNVX",
            account_length=14,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=14.5,
    ),
    BankProfile(
        Bank(
            bin_code="970405",
            abbreviation="AGRIBANK",
            name_vi="Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam",
            name_en="Vietnam Bank for Agriculture and Rural Development",
            swift="VBAAVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=13.8,
    ),
    BankProfile(
        Bank(
            bin_code="970436",
            abbreviation="VCB",
            name_vi="Ngân hàng TMCP Ngoại thương Việt Nam",
            name_en="Joint Stock Commercial Bank for Foreign Trade of Vietnam",
            swift="BFTVVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=11.4,
    ),
    BankProfile(
        Bank(
            bin_code="970415",
            abbreviation="VTB",
            name_vi="Ngân hàng TMCP Công thương Việt Nam",
            name_en="Vietnam Joint Stock Commercial Bank for Industry and Trade",
            swift="ICBVVNVX",
            account_length=15,
        ),
        min_account_length=10,
        max_account_length=16,
        market_share_pct=10.6,
    ),
    BankProfile(
        Bank(
            bin_code="970422",
            abbreviation="MB",
            name_vi="Ngân hàng TMCP Quân đội",
            name_en="Military Commercial Joint Stock Bank",
            swift="MSCBVNVX",
            account_length=12,
        ),
        min_account_length=8,
        max_account_length=14,
        market_share_pct=6.3,
    ),
    BankProfile(
        Bank(
            bin_code="970407",
            abbreviation="TCB",
            name_vi="Ngân hàng TMCP Kỹ Thương Việt Nam",
            name_en="Vietnam Technological and Commercial Joint Stock Bank",
            swift="VTCBVNVX",
            account_length=14,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=5.8,
    ),
    BankProfile(
        Bank(
            bin_code="970432",
            abbreviation="VPB",
            name_vi="Ngân hàng TMCP Việt Nam Thịnh Vượng",
            name_en="Vietnam Prosperity Joint-Stock Commercial Bank",
            swift="VPBKVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=5.1,
    ),
    BankProfile(
        Bank(
            bin_code="970416",
            abbreviation="ACB",
            name_vi="Ngân hàng TMCP Á Châu",
            name_en="Asia Commercial Joint Stock Bank",
            swift="ASCBVNVX",
            account_length=12,
        ),
        min_account_length=8,
        max_account_length=14,
        market_share_pct=4.3,
    ),
    BankProfile(
        Bank(
            bin_code="970403",
            abbreviation="STB",
            name_vi="Ngân hàng TMCP Sài Gòn Thương Tín",
            name_en="Saigon Thuong Tin Bank",
            swift="SGTTVNVX",
            account_length=12,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=3.5,
    ),
    BankProfile(
        Bank(
            bin_code="970443",
            abbreviation="SHB",
            name_vi="Ngân hàng TMCP Sài Gòn - Hà Nội",
            name_en="Saigon Hanoi Bank",
            swift="SHBAVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=3.2,
    ),
    BankProfile(
        Bank(
            bin_code="970423",
            abbreviation="TPB",
            name_vi="Ngân hàng TMCP Tiên Phong",
            name_en="Tien Phong Commercial Joint Stock Bank",
            swift="TPBVVNVX",
            account_length=14,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=2.7,
    ),
    BankProfile(
        Bank(
            bin_code="970437",
            abbreviation="HDB",
            name_vi="Ngân hàng TMCP Phát triển TP. HCM",
            name_en="Ho Chi Minh City Development Bank",
            swift="HDBCVNVX",
            account_length=14,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=2.3,
    ),
    BankProfile(
        Bank(
            bin_code="970441",
            abbreviation="VIB",
            name_vi="Ngân hàng TMCP Quốc Tế Việt Nam",
            name_en="Vietnam International Commercial Joint Stock Bank",
            swift="VNIBVNVX",
            account_length=14,
        ),
        min_account_length=10,
        max_account_length=15,
        market_share_pct=2.1,
    ),
    BankProfile(
        Bank(
            bin_code="970426",
            abbreviation="MSB",
            name_vi="Ngân hàng TMCP Hàng Hải Việt Nam",
            name_en="Vietnam Maritime Commercial Joint Stock Bank",
            swift="MCOBVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=1.9,
    ),
    BankProfile(
        Bank(
            bin_code="970448",
            abbreviation="OCB",
            name_vi="Ngân hàng TMCP Phương Đông",
            name_en="Orient Commercial Joint Stock Bank",
            swift="ORCOVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=1.6,
    ),
    BankProfile(
        Bank(
            bin_code="970440",
            abbreviation="SEAB",
            name_vi="Ngân hàng TMCP Đông Nam Á",
            name_en="Southeast Asia Commercial Joint Stock Bank",
            swift="SEAVVNVX",
            account_length=13,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=1.5,
    ),
    BankProfile(
        Bank(
            bin_code="970431",
            abbreviation="EIB",
            name_vi="Ngân hàng TMCP Xuất Nhập Khẩu Việt Nam",
            name_en="Vietnam Export Import Commercial Joint Stock Bank",
            swift="EBVIVNVX",
            account_length=12,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=1.3,
    ),
    BankProfile(
        Bank(
            bin_code="970454",
            abbreviation="VCCB",
            name_vi="Ngân hàng TMCP Bản Việt",
            name_en="Viet Capital Commercial Joint Stock Bank",
            swift="VCBCVNVX",
            account_length=12,
        ),
        min_account_length=10,
        max_account_length=14,
        market_share_pct=0.9,
    ),
)


# Flat indexes — BIN and abbreviation lookups.
_BY_BIN: dict[str, BankProfile] = {p.bank.bin_code: p for p in _PROFILES}
_BY_ABBR: dict[str, BankProfile] = {p.bank.abbreviation: p for p in _PROFILES}


def all_profiles() -> tuple[BankProfile, ...]:
    """Return every bundled bank, sorted by market share descending."""
    return _PROFILES


def profile_for_bin(bin_code: str) -> BankProfile | None:
    """Return the profile for a 6-digit BIN, or ``None`` if unknown."""
    return _BY_BIN.get(bin_code)


def profile_for_abbr(abbr: str) -> BankProfile | None:
    """Return the profile for a bank's short code (case-insensitive)."""
    return _BY_ABBR.get(abbr.upper())


def is_valid_account(account_number: str, bin_code: str) -> bool:
    """``True`` if ``account_number`` matches the bank's length range."""
    if not account_number.isdigit():
        return False
    profile = profile_for_bin(bin_code)
    if profile is None:
        return False
    return profile.min_account_length <= len(account_number) <= profile.max_account_length


__all__ = [
    "BankProfile",
    "all_profiles",
    "is_valid_account",
    "profile_for_abbr",
    "profile_for_bin",
]
