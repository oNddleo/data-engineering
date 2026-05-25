"""CLI smoke tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from datacatalog.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_demo_default(self, capsys: object) -> None:
        main(["demo"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "PII" in out or "Sources" in out

    def test_demo_quiet(self, capsys: object) -> None:
        main(["demo", "--quiet"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert out == ""

    def test_demo_writes_catalog(self, tmp_path: Path) -> None:
        out_file = tmp_path / "catalog.jsonl"
        main(["demo", "--quiet", "--output", str(out_file)])
        rows = [json.loads(ln) for ln in out_file.read_text().splitlines() if ln.strip()]
        assert len(rows) >= 2
        assert all("source_id" in r for r in rows)

    def test_pii_email(self, capsys: object) -> None:
        main(["pii", "email"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "EMAIL" in out

    def test_pii_non_pii(self, capsys: object) -> None:
        main(["pii", "order_id"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "NONE" in out

    def test_lineage_command(self, capsys: object) -> None:
        main(["lineage", "raw.raw.customers.email"])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "Upstream" in out or "Downstream" in out

    def test_summary_from_file(self, tmp_path: Path, capsys: object) -> None:
        out_file = tmp_path / "catalog.jsonl"
        main(["demo", "--quiet", "--output", str(out_file)])
        main(["summary", str(out_file)])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "sources" in out

    def test_summary_missing_file(self, tmp_path: Path, capsys: object) -> None:
        try:
            main(["summary", str(tmp_path / "missing.jsonl")])
        except SystemExit as exc:
            assert exc.code == 1
        err = capsys.readouterr().err  # type: ignore[attr-defined]
        assert "not found" in err

    def test_no_command_prints_help(self, capsys: object) -> None:
        main([])
        out = capsys.readouterr().out  # type: ignore[attr-defined]
        assert "datacatalog" in out or "usage" in out.lower()
