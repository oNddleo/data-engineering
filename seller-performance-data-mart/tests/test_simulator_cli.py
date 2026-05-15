"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sellermart.cli import main
from sellermart.etl import build_fact_seller_day
from sellermart.simulator import generate


def test_simulate_returns_three_coherent_streams():
    orders, returns, reviews = generate(n_days=7, n_sellers=4, n_buyers=20, seed=1)
    assert len(orders) > 0
    order_ids = {o.order_id for o in orders}
    # Every return / review references a real order.
    for r in returns:
        assert r.order_id in order_ids
    for rv in reviews:
        assert rv.order_id in order_ids


def test_simulate_is_deterministic():
    a = generate(n_days=5, n_sellers=3, seed=42)
    b = generate(n_days=5, n_sellers=3, seed=42)
    assert [o.order_id for o in a[0]] == [o.order_id for o in b[0]]
    assert [r.refund_vnd for r in a[1]] == [r.refund_vnd for r in b[1]]


def test_simulate_validates_inputs():
    with pytest.raises(ValueError):
        generate(n_days=0)
    with pytest.raises(ValueError):
        generate(n_sellers=0)
    with pytest.raises(ValueError):
        generate(return_rate=1.5)
    with pytest.raises(ValueError):
        generate(review_rate=-0.1)


def test_etl_runs_over_simulated_data():
    orders, returns, reviews = generate(n_days=7, n_sellers=4, n_buyers=20, seed=2)
    facts = build_fact_seller_day(orders, returns, reviews)
    assert len(facts) > 0
    # Sum invariant: total orders in the fact table == len(orders).
    assert sum(f.n_orders for f in facts) == len(orders)
    # Return counter never exceeds order counter per row.
    assert all(f.n_returns <= f.n_orders for f in facts)


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "seller-performance-data-mart" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "raw"
    rc = main(
        [
            "simulate",
            "--days",
            "5",
            "--sellers",
            "3",
            "--buyers",
            "10",
            "--seed",
            "0",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "orders.jsonl").is_file()
    assert (out_dir / "returns.jsonl").is_file()
    assert (out_dir / "reviews.jsonl").is_file()
    capsys.readouterr()

    facts_path = tmp_path / "facts.jsonl"
    rc = main(["build", "--in-dir", str(out_dir), "--output", str(facts_path)])
    assert rc == 0
    assert facts_path.is_file()
    capsys.readouterr()

    rc = main(["top", "--facts", str(facts_path), "--n", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "seller" in out

    rc = main(["worst", "--facts", str(facts_path), "--n", "3", "--min-orders", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "orders" in out

    rc = main(["trend", "--facts", str(facts_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "date" in out

    rc = main(["summary", "--facts", str(facts_path)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_fact_rows"] > 0
    assert payload["n_sellers"] > 0
