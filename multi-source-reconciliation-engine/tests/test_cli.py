"""CLI smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from recon.cli import main
from recon.io_jsonl import dump_transactions
from recon.simulator import generate_sources


class TestCLI:
    def test_simulate_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["simulate", "--output-dir", tmp, "-n", "20", "--seed", "1"])
            files = list(Path(tmp).glob("*.jsonl"))
        assert len(files) >= 2

    def test_simulate_output_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["simulate", "--output-dir", tmp, "-n", "10", "--seed", "2"])
            out = capsys.readouterr().out
        data = json.loads(out)
        assert "sources" in data
        assert "output_dir" in data

    def test_reconcile_produces_jsonl(self, capsys: pytest.CaptureFixture[str]) -> None:
        sources = generate_sources(n_transactions=25, seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for name, txns in sources.items():
                dump_transactions(txns, tmp_path / f"{name}.jsonl")
            main(["reconcile", str(tmp_path)])
            out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) >= 1
        meta = json.loads(lines[0])
        assert "matched" in meta
        assert "discrepancies" in meta

    def test_reconcile_empty_dir_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(SystemExit) as exc:
                main(["reconcile", tmp])
            assert exc.value.code == 1

    def test_summary_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        sources = generate_sources(n_transactions=15, seed=4)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # run reconcile first to get report
            for name, txns in sources.items():
                dump_transactions(txns, tmp_path / f"{name}.jsonl")
            main(["reconcile", str(tmp_path)])
            report_lines = capsys.readouterr().out
            report_path = tmp_path / "report.jsonl"
            report_path.write_text(report_lines)
            # now summary
            main(["summary", str(report_path)])
            out = capsys.readouterr().out
        summary = json.loads(out)
        assert "match_rate" in summary
        assert "total_records" in summary

    def test_help_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_simulate_default_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["simulate", "--output-dir", tmp])
            files = list(Path(tmp).glob("*.jsonl"))
        assert len(files) >= 2
