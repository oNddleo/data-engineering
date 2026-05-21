"""Core domain types for VN domestic shipping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Carrier(str, Enum):
    """Major Vietnam domestic carriers."""

    GHN = "GHN"  # Giao Hang Nhanh
    GHTK = "GHTK"  # Giao Hang Tiet Kiem
    JT = "JT"  # J&T Express
    VIETTEL = "VIETTEL"  # Viettel Post
    VNPOST = "VNPOST"  # Vietnam Post


class ServiceType(str, Enum):
    """Delivery speed tiers."""

    STANDARD = "STANDARD"  # 3-5 days
    EXPRESS = "EXPRESS"  # 1-2 days
    SAME_DAY = "SAME_DAY"  # within city, same day


class DeliveryStatus(str, Enum):
    """Shipment lifecycle states."""

    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED_ATTEMPT = "FAILED_ATTEMPT"
    RETURNED = "RETURNED"


class ZoneType(str, Enum):
    """Intra-city vs inter-province routing zone."""

    INNER_CITY = "INNER_CITY"  # same city/province
    INTER_PROVINCE = "INTER_PROVINCE"  # different province


@dataclass(frozen=True, slots=True)
class ShipmentRequest:
    """A single shipment to be priced."""

    carrier: Carrier
    service: ServiceType
    zone: ZoneType
    weight_g: int  # grams
    declared_value_vnd: int  # for COD / insurance
    cod_amount_vnd: int  # 0 = no COD
    is_fragile: bool = False

    def __post_init__(self) -> None:
        if self.weight_g <= 0:
            raise ValueError(f"weight_g must be positive, got {self.weight_g}")
        if self.declared_value_vnd < 0:
            raise ValueError("declared_value_vnd must be >= 0")
        if self.cod_amount_vnd < 0:
            raise ValueError("cod_amount_vnd must be >= 0")
        if self.service == ServiceType.SAME_DAY and self.zone == ZoneType.INTER_PROVINCE:
            raise ValueError("SAME_DAY service is only available for INNER_CITY zone")


@dataclass(frozen=True, slots=True)
class ShipmentResult:
    """Pricing breakdown for a shipment."""

    request: ShipmentRequest
    base_fee_vnd: int
    weight_surcharge_vnd: int
    cod_fee_vnd: int
    fragile_surcharge_vnd: int
    total_fee_vnd: int

    def __post_init__(self) -> None:
        expected = (
            self.base_fee_vnd
            + self.weight_surcharge_vnd
            + self.cod_fee_vnd
            + self.fragile_surcharge_vnd
        )
        if self.total_fee_vnd != expected:
            raise ValueError(f"total_fee_vnd {self.total_fee_vnd} != sum of components {expected}")
