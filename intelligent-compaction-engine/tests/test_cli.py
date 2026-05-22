"""CLI smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from compact.cli import main
from compact.io_jsonl import dump_tablemeta
from compact.simulator import generate_query_patterns, generate_table


class TestCLI:
    def test_simulate_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["simulate", "--output-dir", tmp, "--partitions", "5", "--seed", "1"])
            files = list(Path(tmp).iterdir())
        assert len(files) >= 2

    def test_simulate_output_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["simulate", "--output-dir", tmp, "--partitions", "10", "--seed", "2"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "table_name" in data
        assert "output_dir" in data

    def test_plan_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        table = generate_table(n_partitions=10, seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            meta_path = tmp_path / "table_meta.json"
            with open(meta_path, "w") as fh:
                dump_tablemeta(table, fh)
            main(["plan", str(meta_path)])
        out = capsys.readouterr().out
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) >= 1
        meta = json.loads(lines[0])
        assert "table_name" in meta
        assert "task_count" in meta

    def test_plan_with_patterns(self, capsys: pytest.CaptureFixture[str]) -> None:
        table = generate_table(n_partitions=5, seed=4)
        patterns = generate_query_patterns(n_patterns=20, seed=4)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            meta_path = tmp_path / "table_meta.json"
            patt_path = tmp_path / "query_patterns.json"
            with open(meta_path, "w") as fh:
                dump_tablemeta(table, fh)
            with open(patt_path, "w") as fh:
                json.dump(
                    [
                        {
                            "query_id": p.query_id,
                            "filter_columns": p.filter_columns,
                            "join_columns": p.join_columns,
                            "group_by_columns": p.group_by_columns,
                            "frequency": p.frequency,
                        }
                        for p in patterns
                    ],
                    fh,
                )
            main(["plan", str(meta_path), "--patterns", str(patt_path)])
        out = capsys.readouterr().out
        assert "table_name" in out

    def test_summary_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        table = generate_table(n_partitions=8, seed=5)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            meta_path = tmp_path / "table_meta.json"
            plan_path = tmp_path / "plan.jsonl"
            with open(meta_path, "w") as fh:
                dump_tablemeta(table, fh)
            main(["plan", str(meta_path)])
            plan_text = capsys.readouterr().out
            plan_path.write_text(plan_text)
            main(["summary", str(plan_path)])
            out = capsys.readouterr().out
        summary = json.loads(out)
        assert "task_count" in summary
        assert "action_counts" in summary

    def test_help_exits_0(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
