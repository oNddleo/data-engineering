"""VN AQI math per QĐ 1459/QĐ-TCMT."""

from __future__ import annotations

import pytest

from aqipipe.qcvn import AQIBand, aqi_for, band_for_aqi, station_aqi
from aqipipe.schema import Pollutant


def test_pm25_breakpoint_25_ug_m3_yields_aqi_50():
    """PM2.5 = 25 µg/m³ → top of the GOOD band → AQI 50."""
    out = aqi_for(Pollutant.PM25, 250)  # 25.0 × 10
    assert out.aqi == 50
    assert out.band is AQIBand.GOOD


def test_pm25_breakpoint_50_ug_m3_yields_aqi_100():
    """PM2.5 = 50 µg/m³ → top of MODERATE → AQI 100."""
    out = aqi_for(Pollutant.PM25, 500)
    assert out.aqi == 100
    assert out.band is AQIBand.MODERATE


def test_pm25_150_ug_m3_yields_aqi_200():
    """PM2.5 = 150 µg/m³ → top of UNHEALTHY → AQI 200."""
    out = aqi_for(Pollutant.PM25, 1500)
    assert out.aqi == 200
    assert out.band is AQIBand.UNHEALTHY


def test_pm25_zero_is_aqi_zero():
    out = aqi_for(Pollutant.PM25, 0)
    assert out.aqi == 0
    assert out.band is AQIBand.GOOD


def test_pm10_50_ug_m3_yields_aqi_50():
    """PM10 = 50 µg/m³ → top of GOOD."""
    out = aqi_for(Pollutant.PM10, 500)
    assert out.aqi == 50
    assert out.band is AQIBand.GOOD


def test_no2_200_ug_m3_yields_aqi_100():
    """NO2 = 200 µg/m³ → top of MODERATE."""
    out = aqi_for(Pollutant.NO2, 2000)
    assert out.aqi == 100
    assert out.band is AQIBand.MODERATE


def test_so2_125_ug_m3_yields_aqi_50():
    """SO2 = 125 µg/m³ → top of GOOD."""
    out = aqi_for(Pollutant.SO2, 1250)
    assert out.aqi == 50
    assert out.band is AQIBand.GOOD


def test_o3_160_ug_m3_yields_aqi_50():
    """O3 = 160 µg/m³ → top of GOOD."""
    out = aqi_for(Pollutant.O3, 1600)
    assert out.aqi == 50
    assert out.band is AQIBand.GOOD


def test_co_10_mg_m3_yields_aqi_50():
    """CO = 10 mg/m³ → top of GOOD."""
    out = aqi_for(Pollutant.CO, 100)
    assert out.aqi == 50
    assert out.band is AQIBand.GOOD


def test_above_top_breakpoint_clamps_to_500():
    """Concentration far above hazardous clamps at 500."""
    out = aqi_for(Pollutant.PM25, 999_999)
    assert out.aqi == 500
    assert out.band is AQIBand.HAZARDOUS


def test_aqi_for_rejects_negative():
    with pytest.raises(ValueError):
        aqi_for(Pollutant.PM25, -1)


def test_aqi_is_piecewise_linear():
    """Halfway through a band gives roughly halfway between I_lo and I_hi."""
    # PM2.5 (50.1, 80) maps to AQI (101, 150). Midpoint ~ 65 µg/m³ ⇒ AQI ~ 125.
    out = aqi_for(Pollutant.PM25, 650)
    assert 120 <= out.aqi <= 130


def test_station_aqi_picks_max():
    """Composite AQI = max over pollutants; dominant points to that one."""
    sa = station_aqi(
        "S-1",
        {
            Pollutant.PM25: 600,  # AQI ~ 115 (UNHEALTHY_SENSITIVE)
            Pollutant.NO2: 500,  # AQI ~ 25 (GOOD)
            Pollutant.SO2: 100,  # AQI ~ 4 (GOOD)
        },
    )
    assert sa.dominant_pollutant is Pollutant.PM25
    assert sa.band is AQIBand.UNHEALTHY_SENSITIVE


def test_station_aqi_rejects_empty():
    with pytest.raises(ValueError):
        station_aqi("S-1", {})


def test_station_aqi_contributions_match_input():
    sa = station_aqi("S-1", {Pollutant.PM25: 500, Pollutant.NO2: 1000})
    contributed_pollutants = {c.pollutant for c in sa.contributions}
    assert contributed_pollutants == {Pollutant.PM25, Pollutant.NO2}


def test_band_for_aqi_known_breaks():
    assert band_for_aqi(0) is AQIBand.GOOD
    assert band_for_aqi(50) is AQIBand.GOOD
    assert band_for_aqi(51) is AQIBand.MODERATE
    assert band_for_aqi(100) is AQIBand.MODERATE
    assert band_for_aqi(101) is AQIBand.UNHEALTHY_SENSITIVE
    assert band_for_aqi(150) is AQIBand.UNHEALTHY_SENSITIVE
    assert band_for_aqi(151) is AQIBand.UNHEALTHY
    assert band_for_aqi(200) is AQIBand.UNHEALTHY
    assert band_for_aqi(201) is AQIBand.VERY_UNHEALTHY
    assert band_for_aqi(300) is AQIBand.VERY_UNHEALTHY
    assert band_for_aqi(301) is AQIBand.HAZARDOUS
    assert band_for_aqi(500) is AQIBand.HAZARDOUS


def test_band_for_aqi_rejects_negative():
    with pytest.raises(ValueError):
        band_for_aqi(-1)
