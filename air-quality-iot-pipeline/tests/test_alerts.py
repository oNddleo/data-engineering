"""Alert detector behaviour."""

from __future__ import annotations

from datetime import datetime

import pytest

from aqipipe.alerts import (
    AlertKind,
    band_distribution,
    find_public_alerts,
    find_sensitive_alerts,
)
from aqipipe.qcvn import AQIBand, station_aqi
from aqipipe.schema import VN_TZ, Pollutant

NOW = datetime(2026, 5, 17, 9, 0, tzinfo=VN_TZ)


def _aqis_for(values: dict[str, int]) -> dict[str, object]:  # type: ignore[type-arg]
    """Helper — build a dict[station_id, StationAQI] from raw PM2.5 ×10 values."""
    out: dict[str, object] = {}
    for sid, value_x10 in values.items():
        out[sid] = station_aqi(sid, {Pollutant.PM25: value_x10})
    return out  # type: ignore[return-value]


def test_public_alerts_skip_good_and_moderate_by_default():
    # PM25=20 µg/m³ → GOOD; PM25=40 µg/m³ → MODERATE.
    aqis = _aqis_for({"S-1": 200, "S-2": 400})
    alerts = find_public_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert alerts == []


def test_public_alerts_fire_at_unhealthy_sensitive():
    # PM25=65 µg/m³ → ~UNHEALTHY_SENSITIVE.
    aqis = _aqis_for({"S-1": 650})
    alerts = find_public_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.PUBLIC
    assert alerts[0].band is AQIBand.UNHEALTHY_SENSITIVE


def test_public_alerts_sort_by_aqi_desc():
    """Worst air gets surfaced first."""
    aqis = _aqis_for({"S-LOW": 650, "S-HIGH": 1800})
    alerts = find_public_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert alerts[0].station_id == "S-HIGH"
    assert alerts[1].station_id == "S-LOW"


def test_public_alerts_threshold_tunable():
    """Raising min_band to HAZARDOUS suppresses everything below."""
    aqis = _aqis_for({"S-1": 1800})  # UNHEALTHY
    alerts = find_public_alerts(aqis, NOW, min_band=AQIBand.HAZARDOUS)  # type: ignore[arg-type]
    assert alerts == []


def test_public_alerts_rejects_naive_now():
    with pytest.raises(ValueError):
        find_public_alerts({}, datetime(2026, 5, 17, 9, 0))


def test_sensitive_alerts_fire_at_moderate():
    """Sensitive-group alerts escalate one band earlier."""
    aqis = _aqis_for({"S-1": 400})  # MODERATE
    alerts = find_sensitive_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert len(alerts) == 1
    assert alerts[0].kind is AlertKind.SENSITIVE
    assert alerts[0].band is AQIBand.MODERATE


def test_sensitive_alerts_skip_good():
    aqis = _aqis_for({"S-1": 200})  # GOOD
    assert find_sensitive_alerts(aqis, NOW) == []  # type: ignore[arg-type]


def test_sensitive_alerts_include_higher_bands():
    """Sensitive alerts include all bands ≥ MODERATE."""
    aqis = _aqis_for({"S-LOW": 400, "S-MID": 650, "S-HIGH": 1800})
    alerts = find_sensitive_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert len(alerts) == 3


def test_band_distribution_zero_fills():
    aqis = _aqis_for({"S-1": 200})  # GOOD
    dist = band_distribution(aqis)  # type: ignore[arg-type]
    assert dist[AQIBand.GOOD] == 1
    assert dist[AQIBand.HAZARDOUS] == 0
    assert set(dist) == set(AQIBand)


def test_band_distribution_counts_by_band():
    # PM25 value_x10: 200 → 20 µg/m³ (GOOD); 400 → 40 µg/m³ (MODERATE);
    #                 1000 → 100 µg/m³ (UNHEALTHY, in (801, 1500) band).
    aqis = _aqis_for({"A": 200, "B": 400, "C": 1000})
    dist = band_distribution(aqis)  # type: ignore[arg-type]
    assert dist[AQIBand.GOOD] == 1
    assert dist[AQIBand.MODERATE] == 1
    assert dist[AQIBand.UNHEALTHY] == 1


def test_public_alert_detail_mentions_dominant_pollutant():
    aqis = _aqis_for({"S-1": 650})
    [a] = find_public_alerts(aqis, NOW)  # type: ignore[arg-type]
    assert "PM25" in a.detail


def test_sensitive_alerts_rejects_naive_now():
    with pytest.raises(ValueError):
        find_sensitive_alerts({}, datetime(2026, 5, 17, 9, 0))
