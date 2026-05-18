"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vnaddr.parser import parse
from vnaddr.simulator import NoiseLevel, generate


def test_simulator_deterministic():
    a = generate(n=30, seed=42)
    b = generate(n=30, seed=42)
    assert a == b


def test_simulator_different_seeds_differ():
    a = generate(n=30, seed=1)
    b = generate(n=30, seed=2)
    assert a != b


def test_simulator_count():
    out = generate(n=50, seed=0)
    assert len(out) == 50


def test_simulator_clean_parses_completely():
    """All CLEAN-noise outputs parse to is_complete=True."""
    for line in generate(n=20, noise=NoiseLevel.CLEAN, seed=0):
        p = parse(line)
        assert p.is_complete, f"failed to fully parse: {line}"


def test_simulator_abbrev_parses_completely():
    """ABBREV-noise outputs should still fully parse via abbreviation expansion."""
    for line in generate(n=20, noise=NoiseLevel.ABBREV, seed=0):
        p = parse(line)
        assert p.is_complete, f"failed to fully parse: {line}"


def test_simulator_folded_parses_completely():
    """FOLDED-noise (no diacritics) outputs still fully parse."""
    for line in generate(n=20, noise=NoiseLevel.FOLDED, seed=0):
        p = parse(line)
        assert p.is_complete, f"failed to fully parse: {line}"


def test_simulator_rejects_negative_n():
    with pytest.raises(ValueError):
        generate(n=-1)


def test_simulator_zero_count_returns_empty():
    assert generate(n=0) == []


# ---------- CLI --------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vnaddr.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    r = _run_cli("info")
    assert r.returncode == 0
    assert "vn-address-parser" in r.stdout


def test_cli_parse_complete():
    r = _run_cli("parse", "--text", "123 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
    assert r.returncode == 0
    assert "complete:  True" in r.stdout


def test_cli_parse_partial_returns_2():
    r = _run_cli("parse", "--text", "TP.HCM")
    # Only province → not complete → exit 2.
    assert r.returncode == 2


def test_cli_parse_json_output():
    r = _run_cli("parse", "--text", "Phường Bến Nghé, Quận 1, TP.HCM", "--json")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert "ward" in payload
    assert payload["province"]["matched_code"] == "HCM"


def test_cli_normalize():
    r = _run_cli("normalize", "--text", "TP.HCM, Q.1")
    assert r.returncode == 0
    assert "thanh pho ho chi minh" in r.stdout


def test_cli_list_units_provinces():
    r = _run_cli("list-units", "--level", "PROVINCE")
    assert r.returncode == 0
    assert "HCM" in r.stdout
    assert "63 province(s)" in r.stderr


def test_cli_simulate_then_batch(tmp_path: Path) -> None:
    addrs_path = tmp_path / "addrs.txt"
    parsed_path = tmp_path / "parsed.jsonl"
    r = _run_cli("simulate", "--n", "20", "--seed", "1", "--output", str(addrs_path))
    assert r.returncode == 0
    r = _run_cli("batch", "--input", str(addrs_path), "--output", str(parsed_path))
    assert r.returncode == 0
    assert parsed_path.exists()


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    addrs_path = tmp_path / "addrs.txt"
    _run_cli("simulate", "--n", "20", "--seed", "1", "--output", str(addrs_path))
    r = _run_cli("summary", "--input", str(addrs_path))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["n_inputs"] == 20
    assert payload["completion_rate_pct"] >= 0.0
