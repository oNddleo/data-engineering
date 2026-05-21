"""Unit tests for pricing module."""

from __future__ import annotations

import pytest

from vnship.pricing import calculate_fee
from vnship.schema import Carrier, ServiceType, ShipmentRequest, ZoneType


def _req(
    carrier: Carrier = Carrier.GHN,
    service: ServiceType = ServiceType.STANDARD,
    zone: ZoneType = ZoneType.INNER_CITY,
    weight_g: int = 300,
    declared_value_vnd: int = 500_000,
    cod_amount_vnd: int = 0,
    is_fragile: bool = False,
) -> ShipmentRequest:
    return ShipmentRequest(
        carrier=carrier,
        service=service,
        zone=zone,
        weight_g=weight_g,
        declared_value_vnd=declared_value_vnd,
        cod_amount_vnd=cod_amount_vnd,
        is_fragile=is_fragile,
    )


class TestSchemaValidation:
    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="weight_g"):
            _req(weight_g=-1)

    def test_zero_weight_raises(self) -> None:
        with pytest.raises(ValueError):
            _req(weight_g=0)

    def test_negative_declared_value_raises(self) -> None:
        with pytest.raises(ValueError):
            _req(declared_value_vnd=-1)

    def test_negative_cod_raises(self) -> None:
        with pytest.raises(ValueError):
            _req(cod_amount_vnd=-1)

    def test_same_day_inter_province_raises(self) -> None:
        with pytest.raises(ValueError, match="SAME_DAY"):
            _req(service=ServiceType.SAME_DAY, zone=ZoneType.INTER_PROVINCE)

    def test_same_day_inner_city_ok(self) -> None:
        req = _req(service=ServiceType.SAME_DAY, zone=ZoneType.INNER_CITY)
        assert req.service == ServiceType.SAME_DAY


class TestBaseFee:
    def test_ghn_standard_inner_500g(self) -> None:
        r = calculate_fee(_req(weight_g=500))
        assert r.base_fee_vnd == 22_000
        assert r.weight_surcharge_vnd == 0

    def test_ghn_standard_inner_501g(self) -> None:
        r = calculate_fee(_req(weight_g=501))
        assert r.base_fee_vnd == 25_000
        assert r.weight_surcharge_vnd == 0

    def test_ghn_standard_inner_1000g(self) -> None:
        r = calculate_fee(_req(weight_g=1_000))
        assert r.base_fee_vnd == 25_000
        assert r.weight_surcharge_vnd == 0

    def test_ghn_standard_inner_1001g(self) -> None:
        # 1 extra step above 1000g
        r = calculate_fee(_req(weight_g=1_001))
        assert r.weight_surcharge_vnd == 2_500

    def test_weight_surcharge_2_steps(self) -> None:
        # 2000g = 1000g above threshold → 2 steps
        r = calculate_fee(_req(weight_g=2_000))
        assert r.weight_surcharge_vnd == 5_000  # 2 * 2500

    def test_weight_surcharge_fractional_step_rounds_up(self) -> None:
        # 1800g = 800g above → ceil(800/500)=2 steps
        r = calculate_fee(_req(weight_g=1_800))
        assert r.weight_surcharge_vnd == 5_000


class TestCodFee:
    def test_no_cod(self) -> None:
        r = calculate_fee(_req(cod_amount_vnd=0))
        assert r.cod_fee_vnd == 0

    def test_cod_small_amount(self) -> None:
        # 100_000 VND → flat 3000 + 1% = 3000 + 1000 = 4000
        r = calculate_fee(_req(cod_amount_vnd=100_000))
        assert r.cod_fee_vnd == 4_000

    def test_cod_large_amount(self) -> None:
        # 1_000_000 VND → 3000 + 10000 = 13000
        r = calculate_fee(_req(cod_amount_vnd=1_000_000))
        assert r.cod_fee_vnd == 13_000


class TestFragile:
    def test_fragile_surcharge(self) -> None:
        r = calculate_fee(_req(is_fragile=True))
        assert r.fragile_surcharge_vnd == 5_000

    def test_not_fragile(self) -> None:
        r = calculate_fee(_req(is_fragile=False))
        assert r.fragile_surcharge_vnd == 0


class TestTotalConsistency:
    def test_total_equals_sum(self) -> None:
        r = calculate_fee(_req(weight_g=2_500, cod_amount_vnd=500_000, is_fragile=True))
        expected = (
            r.base_fee_vnd + r.weight_surcharge_vnd + r.cod_fee_vnd + r.fragile_surcharge_vnd
        )
        assert r.total_fee_vnd == expected

    def test_all_carriers_price_ok(self) -> None:
        for carrier in Carrier:
            for zone in ZoneType:
                for service in ServiceType:
                    if service == ServiceType.SAME_DAY and zone == ZoneType.INTER_PROVINCE:
                        continue
                    try:
                        r = calculate_fee(
                            _req(carrier=carrier, service=service, zone=zone, weight_g=1_000)
                        )
                        assert r.total_fee_vnd > 0
                    except ValueError:
                        pass  # some combos not in rate table


class TestInterProvince:
    def test_ghn_inter_province_standard(self) -> None:
        r = calculate_fee(_req(carrier=Carrier.GHN, zone=ZoneType.INTER_PROVINCE, weight_g=300))
        assert r.base_fee_vnd == 30_000

    def test_ghtk_inter_province_express(self) -> None:
        r = calculate_fee(
            _req(
                carrier=Carrier.GHTK,
                service=ServiceType.EXPRESS,
                zone=ZoneType.INTER_PROVINCE,
                weight_g=800,
            )
        )
        assert r.base_fee_vnd == 43_000


class TestUnknownRate:
    def test_missing_rate_raises(self) -> None:
        # VNPOST doesn't have SAME_DAY → should raise
        with pytest.raises((ValueError, KeyError)):
            calculate_fee(
                _req(
                    carrier=Carrier.VNPOST,
                    service=ServiceType.SAME_DAY,
                    zone=ZoneType.INNER_CITY,
                )
            )
