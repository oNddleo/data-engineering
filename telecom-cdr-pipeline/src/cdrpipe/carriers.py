"""VN telco carrier directory — prefix-based resolution.

Each VN mobile carrier was allocated a fixed set of 3-digit prefixes
in the 2018 numbering plan (Decision 2730/QĐ-BTTTT, Bộ TT&TT). All
mobile MSISDNs are 10 digits, starting with one of these prefixes:

| Carrier      | Prefixes                                                    |
| ------------ | ----------------------------------------------------------- |
| Viettel      | 086, 096, 097, 098, 032-039                                 |
| VinaPhone    | 081, 082, 083, 084, 085, 088, 091, 094                      |
| MobiFone     | 070, 076-079, 089, 090, 093                                 |
| Vietnamobile | 056, 058, 092                                                |
| Reddi        | 055, 059                                                     |

The MSISDN may be written with leading ``+84`` (E.164), ``84``, or
``0`` — ``carrier_for()`` normalises all three forms.

Premium-rate prefixes (1900xxxxxx, 1800xxxxxx) and short codes
(8XXX) bypass the carrier-prefix table and use ``is_premium_msisdn``.
"""

from __future__ import annotations

from dataclasses import dataclass

from cdrpipe.schema import Carrier


@dataclass(frozen=True, slots=True)
class CarrierProfile:
    """One carrier's name + prefix set + market share."""

    code: Carrier
    name_vi: str
    name_en: str
    prefixes: tuple[str, ...]
    market_share_pct: float


_PROFILES: tuple[CarrierProfile, ...] = (
    CarrierProfile(
        code=Carrier.VIETTEL,
        name_vi="Viettel Mobile",
        name_en="Viettel Mobile",
        prefixes=(
            "086",
            "096",
            "097",
            "098",
            "032",
            "033",
            "034",
            "035",
            "036",
            "037",
            "038",
            "039",
        ),
        market_share_pct=53.0,
    ),
    CarrierProfile(
        code=Carrier.VINAPHONE,
        name_vi="VinaPhone",
        name_en="VNPT-VinaPhone",
        prefixes=("081", "082", "083", "084", "085", "088", "091", "094"),
        market_share_pct=24.0,
    ),
    CarrierProfile(
        code=Carrier.MOBIFONE,
        name_vi="MobiFone",
        name_en="MobiFone",
        prefixes=("070", "076", "077", "078", "079", "089", "090", "093"),
        market_share_pct=17.0,
    ),
    CarrierProfile(
        code=Carrier.VIETNAMOBILE,
        name_vi="Vietnamobile",
        name_en="Vietnamobile",
        prefixes=("056", "058", "092"),
        market_share_pct=3.0,
    ),
    CarrierProfile(
        code=Carrier.REDDI,
        name_vi="Reddi",
        name_en="Mobicast (Reddi)",
        prefixes=("055", "059"),
        market_share_pct=1.0,
    ),
)


# Build a flat prefix → carrier index.
_PREFIX_TO_CARRIER: dict[str, Carrier] = {}
for _profile in _PROFILES:
    for _pfx in _profile.prefixes:
        _PREFIX_TO_CARRIER[_pfx] = _profile.code


def normalise_msisdn(raw: str) -> str:
    """Normalise an MSISDN to ``0X...`` (10-digit) VN form.

    Accepts ``+84961234567``, ``84961234567``, ``0961234567``,
    ``961234567``. Output is always 10 chars starting with ``0``.
    Returns the input unchanged if it doesn't look like a VN mobile.
    """
    s = raw.strip().replace(" ", "").replace("-", "")
    if s.startswith("+84"):
        s = "0" + s[3:]
    elif s.startswith("84") and len(s) >= 11:
        s = "0" + s[2:]
    elif not s.startswith("0") and len(s) == 9:
        s = "0" + s
    return s


def carrier_for(msisdn: str) -> Carrier:
    """Return the carrier owning ``msisdn``'s prefix (or ``UNKNOWN``)."""
    n = normalise_msisdn(msisdn)
    if len(n) != 10 or not n.startswith("0"):
        return Carrier.UNKNOWN
    return _PREFIX_TO_CARRIER.get(n[:3], Carrier.UNKNOWN)


def is_premium_msisdn(msisdn: str) -> bool:
    """``True`` if ``msisdn`` is a premium-rate or short-code number.

    Premium-rate (1900XXXXXX, 1800XXXXXX) and short codes (8XXX)
    bypass the carrier table — they're billed at fixed premium tariffs
    per Circular 14/2012/TT-BTTTT.
    """
    s = msisdn.strip().replace(" ", "")
    return s.startswith("1900") or s.startswith("1800") or (s.startswith("8") and len(s) <= 5)


def all_profiles() -> tuple[CarrierProfile, ...]:
    return _PROFILES


def profile_for(code: Carrier) -> CarrierProfile | None:
    """Return the bundled profile for a carrier code (``None`` for UNKNOWN)."""
    for p in _PROFILES:
        if p.code is code:
            return p
    return None


__all__ = [
    "CarrierProfile",
    "all_profiles",
    "carrier_for",
    "is_premium_msisdn",
    "normalise_msisdn",
    "profile_for",
]
