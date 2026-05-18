"""Simulator + CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mappev.io_jsonl import load_events
from mappev.schema import EventKind
from mappev.simulator import generate


def test_simulator_deterministic():
    """Same seed -> identical event stream."""
    a = generate(n_devices=40, n_days=10, seed=42)
    b = generate(n_devices=40, n_days=10, seed=42)
    assert len(a) == len(b)
    assert all(x == y for x, y in zip(a, b))


def test_simulator_different_seeds_differ():
    """Different seeds produce different streams."""
    a = generate(n_devices=40, n_days=10, seed=1)
    b = generate(n_devices=40, n_days=10, seed=2)
    assert a != b


def test_simulator_emits_expected_install_count():
    """``n_devices`` installs come out, one per device."""
    events = generate(n_devices=50, n_days=7, seed=7)
    installs = [e for e in events if e.kind is EventKind.INSTALL]
    assert len(installs) == 50
    # All device IDs unique.
    assert len({i.device_id for i in installs}) == 50


def test_simulator_emits_clicks_for_attributed_devices():
    """Roughly the click + injection + spam fractions emit CLICK events."""
    events = generate(n_devices=200, n_days=20, seed=0)
    clicks = [e for e in events if e.kind is EventKind.CLICK]
    # 45% click + 5% injection + 5% spam = ~55% of devices have a click.
    assert 80 <= len(clicks) <= 130


def test_simulator_rejects_invalid_fractions():
    with pytest.raises(ValueError):
        generate(organic_fraction=2.0)
    with pytest.raises(ValueError):
        generate(organic_fraction=0.5, click_fraction=0.6, view_fraction=0.5)


def test_simulator_rejects_invalid_size():
    with pytest.raises(ValueError, match="n_devices"):
        generate(n_devices=0)
    with pytest.raises(ValueError, match="n_days"):
        generate(n_days=0)


def test_simulator_purchase_revenue_positive():
    """Generated PURCHASE events have revenue > 0."""
    events = generate(n_devices=100, n_days=10, seed=3)
    purchases = [e for e in events if e.kind is EventKind.PURCHASE]
    assert all(p.revenue_vnd > 0 for p in purchases)


def test_simulator_in_app_has_name():
    """Generated IN_APP events all have a non-empty in_app_event_name."""
    events = generate(n_devices=100, n_days=10, seed=3)
    in_app = [e for e in events if e.kind is EventKind.IN_APP]
    assert all(e.in_app_event_name for e in in_app)


# ---------- CLI ---------------------------------------------------------------


_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "mappev.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_info():
    out = _run_cli("info")
    assert out.returncode == 0
    assert "mobile-app-event-pipeline" in out.stdout


def test_cli_pipeline_simulate_attribute_cohort(tmp_path: Path) -> None:
    """Full pipeline: simulate -> attribute -> cohort -> ltv."""
    events_path = tmp_path / "events.jsonl"
    attr_path = tmp_path / "attr.jsonl"
    r = _run_cli(
        "simulate", "--devices", "100", "--days", "14", "--seed", "1", "--output", str(events_path)
    )
    assert r.returncode == 0, r.stderr
    assert events_path.exists()
    events = load_events(events_path.read_text(encoding="utf-8"))
    assert len(events) > 0

    r = _run_cli(
        "attribute", "--input", str(events_path), "--output", str(attr_path), "--show", "5"
    )
    assert r.returncode == 0, r.stderr
    assert attr_path.exists()

    r = _run_cli("cohort", "--input", str(events_path), "--show", "5")
    assert r.returncode == 0, r.stderr
    assert "D1%" in r.stdout

    r = _run_cli("ltv", "--input", str(events_path), "--show", "5")
    assert r.returncode == 0, r.stderr
    assert "LTV_D1" in r.stdout


def test_cli_fraud_exit_code_2_on_findings(tmp_path: Path) -> None:
    """``fraud`` exits 2 when there's at least one finding."""
    events_path = tmp_path / "events.jsonl"
    _run_cli(
        "simulate", "--devices", "200", "--days", "20", "--seed", "11", "--output", str(events_path)
    )
    r = _run_cli("fraud", "--input", str(events_path), "--show", "5")
    assert r.returncode == 2
    assert "CLICK_INJECTION" in r.stdout


def test_cli_summary_outputs_json(tmp_path: Path) -> None:
    """``summary`` writes valid JSON with expected keys."""
    events_path = tmp_path / "events.jsonl"
    _run_cli(
        "simulate", "--devices", "50", "--days", "10", "--seed", "5", "--output", str(events_path)
    )
    r = _run_cli("summary", "--input", str(events_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "n_events" in payload
    assert "events_by_kind" in payload
    assert "installs_by_source" in payload
    assert payload["n_devices_attributed"] == 50
