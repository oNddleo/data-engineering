"""Simulator + CLI smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dbtlin.cli import main
from dbtlin.graph import build_graph, find_cycles
from dbtlin.parser import parse_project
from dbtlin.simulator import generate


def test_simulate_deterministic():
    a = generate(seed=42)
    b = generate(seed=42)
    assert a == b


def test_simulate_no_cycle_in_clean_project():
    project = generate(seed=0)
    models = parse_project(project)
    graph = build_graph(models)
    assert find_cycles(graph) == []


def test_simulate_cycle_injection_creates_cycle():
    project = generate(seed=0, inject_cycle=True)
    models = parse_project(project)
    graph = build_graph(models)
    cycles = find_cycles(graph)
    assert len(cycles) >= 1


def test_simulate_includes_expected_models():
    project = generate(seed=0)
    # Smoke check that the canonical staging / int / mart layers exist.
    assert "stg_orders" in project
    assert "int_order_items" in project
    assert "fact_revenue_daily" in project


def test_cli_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "dbt-model-lineage-graph" in out


def test_cli_full_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = tmp_path / "project.json"
    rc = main(["simulate", "--seed", "0", "--output", str(proj)])
    assert rc == 0
    assert proj.is_file()
    capsys.readouterr()

    parsed = tmp_path / "models.jsonl"
    rc = main(["parse", "--input", str(proj), "--output", str(parsed)])
    assert rc == 0
    capsys.readouterr()

    edges = tmp_path / "edges.jsonl"
    rc = main(["graph", "--input", str(proj), "--output", str(edges), "--show", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nodes" in out
    assert edges.is_file()

    rc = main(["topo", "--input", str(proj)])
    capsys.readouterr()
    assert rc == 0

    rc = main(["cycles", "--input", str(proj)])
    capsys.readouterr()
    assert rc == 0  # clean project = no cycles

    rc = main(["impact", "--input", str(proj), "--target", "stg_orders", "--show", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Upstream" in out
    assert "Downstream" in out

    rc = main(["summary", "--input", str(proj)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["n_models"] >= 10
    assert payload["n_cycles"] == 0


def test_cli_cycles_exits_2_on_cycle(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = tmp_path / "bad.json"
    rc = main(["simulate", "--cycle", "--seed", "0", "--output", str(proj)])
    capsys.readouterr()
    rc = main(["cycles", "--input", str(proj)])
    capsys.readouterr()
    assert rc == 2


def test_cli_topo_exits_2_on_cycle(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = tmp_path / "bad.json"
    rc = main(["simulate", "--cycle", "--seed", "0", "--output", str(proj)])
    capsys.readouterr()
    rc = main(["topo", "--input", str(proj)])
    capsys.readouterr()
    assert rc == 2
