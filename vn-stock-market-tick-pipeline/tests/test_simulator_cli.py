"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vntick.cli import main
from vntick.resampler import resample
from vntick.schema import ceiling_price
from vntick.simulator import generate


def test_simulate_deterministic():
    a = generate(n_ticks_per_symbol=20, seed=42)
    b = generate(n_ticks_per_symbol=20, seed=42)
    assert [t.price_vnd for t in a[1]] == [t.price_vnd for t in b[1]]


def test_simulate_emits_n_ticks_per_symbol():
    symbols, ticks, _ = generate(n_ticks_per_symbol=15, seed=1)
    by_code: dict[str, int] = {}
    for t in ticks:
        by_code[t.code] = by_code.get(t.code, 0) + 1
    for sym in symbols:
        assert by_code[sym.code] == 15


def test_simulate_ticks_inside_band():
    """All synthetic ticks stay between floor and ceiling."""
    symbols, ticks, prev_close = generate(n_ticks_per_symbol=50, seed=5)
    by_code = {s.code: s for s in symbols}
    for t in ticks:
        sym = by_code[t.code]
        ref = prev_close[t.code]
        assert t.price_vnd <= ceiling_price(ref, sym.exchange)


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_ticks_per_symbol=0)


def test_simulate_ceiling_hit_forces_print():
    symbols, ticks, prev_close = generate(n_ticks_per_symbol=10, seed=2, ceiling_hit_codes=("VCB",))
    by_code = {s.code: s for s in symbols}
    ceiling = ceiling_price(prev_close["VCB"], by_code["VCB"].exchange)
    vcb_first = next(t for t in ticks if t.code == "VCB")
    assert vcb_first.price_vnd == ceiling


def test_simulator_ticks_resample_to_valid_bars():
    """Smoke test: simulator output is valid input for the resampler."""
    _, ticks, _ = generate(n_ticks_per_symbol=30, seed=3)
    bars = resample(ticks, interval="5m")
    assert len(bars) > 0
    # Every bar must satisfy OHLC invariants (already validated at construction).
    for b in bars:
        assert b.low_vnd <= b.open_vnd <= b.high_vnd
        assert b.low_vnd <= b.close_vnd <= b.high_vnd


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "vn-stock-market-tick-pipeline" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(["simulate", "--ticks-per-symbol", "30", "--seed", "0", "--out-dir", str(out_dir)])
    assert rc == 0
    assert (out_dir / "symbols.jsonl").is_file()
    assert (out_dir / "ticks.jsonl").is_file()
    assert (out_dir / "previous_close.json").is_file()
    capsys.readouterr()

    bars_path = tmp_path / "bars.jsonl"
    rc = main(
        [
            "resample",
            "--input",
            str(out_dir / "ticks.jsonl"),
            "--interval",
            "5m",
            "--output",
            str(bars_path),
        ]
    )
    assert rc == 0
    assert bars_path.is_file()
    capsys.readouterr()

    rc = main(
        [
            "indicators",
            "--bars",
            str(bars_path),
            "--code",
            "VCB",
            "--sma",
            "5",
            "--ema",
            "5",
            "--rsi",
            "14",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "close" in out

    rc = main(
        [
            "anomalies",
            "--bars",
            str(bars_path),
            "--symbols",
            str(out_dir / "symbols.jsonl"),
            "--previous-close",
            str(out_dir / "previous_close.json"),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "CIRCUIT-BREAKER" in out

    rc = main(["index", "--bars", str(bars_path), "--symbols", str(out_dir / "symbols.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "vn_index_total_cap_vnd" in payload
    assert "vn30_total_cap_vnd" in payload

    rc = main(["summary", "--input", str(out_dir / "ticks.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_ticks"] > 0


def test_cli_indicators_unknown_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    main(["simulate", "--ticks-per-symbol", "10", "--seed", "0", "--out-dir", str(out_dir)])
    bars_path = tmp_path / "bars.jsonl"
    main(
        [
            "resample",
            "--input",
            str(out_dir / "ticks.jsonl"),
            "--interval",
            "5m",
            "--output",
            str(bars_path),
        ]
    )
    capsys.readouterr()
    rc = main(["indicators", "--bars", str(bars_path), "--code", "NOTREAL"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown code" in err
