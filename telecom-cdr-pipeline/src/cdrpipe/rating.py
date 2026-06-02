"""CDR rating engine — turns a raw CDR into a ``RatedCDR`` with VND amounts.

The published VN telco tariff structure (as of 2024-2026, post-MNP era):

| Resource     | On-net rate    | Off-net rate    | Peak window         |
| ------------ | -------------- | --------------- | ------------------- |
| Voice / min  | 1 580 VND/min  | 1 780 VND/min   | 06:00 – 22:00 daily |
| Voice off-peak| 1 280 VND/min | 1 480 VND/min  | 22:00 – 06:00       |
| SMS / msg    | 290 VND        | 390 VND         | flat                |
| Data / MB    | 50 VND         | (same)          | flat                |
| Premium voice| 8 000 VND/min  | 8 000 VND/min   | flat                |
| Roaming voice| 8 000 VND/min  | 8 000 VND/min   | flat (any direction)|
| Roaming SMS  | 2 500 VND      | 2 500 VND       | flat                |
| Roaming data | 200 VND/MB     | 200 VND/MB      | flat                |

**VAT** is 10% of the rated amount, per the 2008 VAT Law as amended
2024. The total billed = rated + VAT, both stored as integer VND.

Calls under 6 seconds (block 1) are not charged; calls 6-60s are
billed as 1 minute; beyond 60s, rounded up to the nearest 6-second
block (Block 6 + 6 rounding, per published Viettel tariffs).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cdrpipe.carriers import carrier_for
from cdrpipe.schema import CDR, Carrier, CDRKind, RatedCDR


@dataclass(frozen=True, slots=True)
class TariffTable:
    """Published rates per minute / message / MB in VND."""

    # On-net = same carrier; off-net = different carrier.
    voice_on_net_peak_per_min: int = 1_580
    voice_on_net_off_peak_per_min: int = 1_280
    voice_off_net_peak_per_min: int = 1_780
    voice_off_net_off_peak_per_min: int = 1_480

    sms_on_net: int = 290
    sms_off_net: int = 390

    data_per_mb: int = 50

    # Special tariffs (override everything else)
    premium_voice_per_min: int = 8_000
    roaming_voice_per_min: int = 8_000
    roaming_sms: int = 2_500
    roaming_data_per_mb: int = 200


DEFAULT_TARIFF = TariffTable()
PEAK_START_HOUR = 6
PEAK_END_HOUR = 22  # 22:00 inclusive → off-peak from 22:00 to 06:00
VAT_BPS = 1_000  # 10% in basis points (10000 = 100%)
BLOCK_MIN_SECONDS = 6  # First billable block (Block-6 rounding)


def is_peak(occurred_at_local_hour: int) -> bool:
    """``True`` for any hour in ``[06, 22)``."""
    return PEAK_START_HOUR <= occurred_at_local_hour < PEAK_END_HOUR


def billable_minutes(duration_seconds: int) -> int:
    """Block-6-rounded billable minutes for a voice call.

    * 0..5s → 0 (free)
    * 6..60s → 1 minute
    * 61..120s → 2 minutes (rounded up to next 6-second block, then
      converted to minutes for tariff lookup).

    Real billing keeps seconds but expresses tariff in VND/min; we
    round up to the nearest whole minute.
    """
    if duration_seconds < BLOCK_MIN_SECONDS:
        return 0
    return math.ceil(duration_seconds / 60)


def rate(cdr: CDR, tariff: TariffTable | None = None) -> RatedCDR:
    """Apply ``tariff`` to ``cdr``; returns a fully-rated record."""
    t = tariff or DEFAULT_TARIFF
    subscriber_carrier = carrier_for(cdr.subscriber_msisdn)
    peer_carrier = carrier_for(cdr.peer_msisdn) if cdr.peer_msisdn else Carrier.UNKNOWN
    on_net = subscriber_carrier == peer_carrier and subscriber_carrier is not Carrier.UNKNOWN
    peak = is_peak(cdr.occurred_at.hour)
    amount = _rate_one(cdr, t, on_net=on_net, peak=peak)
    vat = (amount * VAT_BPS) // 10_000
    return RatedCDR(
        cdr=cdr,
        subscriber_carrier=subscriber_carrier,
        peer_carrier=peer_carrier,
        rated_amount_vnd=amount,
        vat_amount_vnd=vat,
        is_peak=peak,
    )


def _rate_one(cdr: CDR, t: TariffTable, *, on_net: bool, peak: bool) -> int:
    """Compute the **pre-VAT** rated amount for one CDR."""
    if cdr.kind is CDRKind.VOICE:
        return _rate_voice(cdr, t, on_net=on_net, peak=peak)
    if cdr.kind is CDRKind.SMS:
        return _rate_sms(cdr, t, on_net=on_net)
    if cdr.kind is CDRKind.DATA:
        return _rate_data(cdr, t)
    raise ValueError(f"unknown CDR kind: {cdr.kind}")


def _rate_voice(cdr: CDR, t: TariffTable, *, on_net: bool, peak: bool) -> int:
    """Voice tariff — premium / roaming override peak/off-peak/on-net."""
    minutes = billable_minutes(cdr.duration_seconds)
    if minutes == 0:
        return 0
    if cdr.is_premium:
        return minutes * t.premium_voice_per_min
    if cdr.is_roaming:
        return minutes * t.roaming_voice_per_min
    if on_net:
        return minutes * (t.voice_on_net_peak_per_min if peak else t.voice_on_net_off_peak_per_min)
    return minutes * (t.voice_off_net_peak_per_min if peak else t.voice_off_net_off_peak_per_min)


def _rate_sms(cdr: CDR, t: TariffTable, *, on_net: bool) -> int:
    if cdr.is_roaming:
        return cdr.n_messages * t.roaming_sms
    rate_per = t.sms_on_net if on_net else t.sms_off_net
    return cdr.n_messages * rate_per


def _rate_data(cdr: CDR, t: TariffTable) -> int:
    """Data tariff — billed per MB, round up partial MB."""
    mb = math.ceil(cdr.bytes_used / (1024 * 1024))
    rate_per = t.roaming_data_per_mb if cdr.is_roaming else t.data_per_mb
    return mb * rate_per


__all__ = [
    "BLOCK_MIN_SECONDS",
    "DEFAULT_TARIFF",
    "PEAK_END_HOUR",
    "PEAK_START_HOUR",
    "TariffTable",
    "VAT_BPS",
    "billable_minutes",
    "is_peak",
    "rate",
]
