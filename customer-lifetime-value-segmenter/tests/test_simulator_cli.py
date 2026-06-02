"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clvseg.cli import main
from clvseg.rfm import score
from clvseg.simulator import generate


def test_simulate_deterministic():
    a = generate(n_customers=20, window_days=180, seed=42)
    b = generate(n_customers=20, window_days=180, seed=42)
    assert [c.customer_id for c in a[0]] == [c.customer_id for c in b[0]]
    assert len(a[1]) == len(b[1])


def test_simulate_emits_n_customers():
    customers, _, _ = generate(n_customers=50, window_days=180, seed=1)
    assert len(customers) == 50


def test_simulate_orders_reference_real_customers():
    customers, orders, _ = generate(n_customers=30, window_days=180, seed=2)
    customer_ids = {c.customer_id for c in customers}
    for o in orders:
        assert o.customer_id in customer_ids


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_customers=0)
    with pytest.raises(ValueError):
        generate(window_days=0)


def test_simulator_to_rfm_pipeline():
    customers, orders, as_of = generate(n_customers=50, window_days=180, seed=3)
    scores = score(customers, orders, as_of=as_of)
    assert len(scores) == 50
    # Every score has well-formed R/F/M.
    for s in scores:
        assert 1 <= s.r_score <= 5
        assert 1 <= s.f_score <= 5
        assert 1 <= s.m_score <= 5


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "customer-lifetime-value-segmenter" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(
        [
            "simulate",
            "--customers",
            "100",
            "--window-days",
            "180",
            "--seed",
            "0",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "customers.jsonl").is_file()
    assert (out_dir / "orders.jsonl").is_file()
    assert (out_dir / "as_of.txt").is_file()
    capsys.readouterr()

    scores_path = tmp_path / "scores.jsonl"
    rc = main(["score", "--in-dir", str(out_dir), "--output", str(scores_path)])
    assert rc == 0
    assert scores_path.is_file()
    capsys.readouterr()

    rc = main(["segment", "--scores", str(scores_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "segment" in out

    rc = main(["clv", "--scores", str(scores_path), "--window-days", "180", "--show-top", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "total_clv_vnd" in out

    rc = main(["top", "--scores", str(scores_path), "--segment", "CHAMPIONS", "--n", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "customer" in out

    rc = main(["summary", "--scores", str(scores_path)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_customers"] == 100
    assert "by_segment" in payload
