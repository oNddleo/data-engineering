"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fxagg.cli import main

from ._fixtures import BIDV_HTML, GENERIC_CSV, TCB_JSON, VCB_XML


def test_cli_info(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "fx-rate-aggregator" in out


def test_cli_parse_vcb_xml(tmp_path: Path, capsys):
    p = tmp_path / "vcb.xml"
    p.write_text(VCB_XML, encoding="utf-8")
    rc = main(["parse", "--format", "vcb-xml", "--file", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VCB @ 2026-05-14T09:30:00+07:00" in out
    assert "USD" in out


def test_cli_parse_bidv_html(tmp_path: Path, capsys):
    p = tmp_path / "bidv.html"
    p.write_text(BIDV_HTML, encoding="utf-8")
    rc = main(
        [
            "parse",
            "--format",
            "bidv-html",
            "--file",
            str(p),
            "--quoted-at",
            "2026-05-14T09:30:00+07:00",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "BIDV" in out
    assert "USD" in out


def test_cli_parse_tcb_json(tmp_path: Path, capsys):
    p = tmp_path / "tcb.json"
    p.write_text(TCB_JSON, encoding="utf-8")
    rc = main(["parse", "--format", "tcb-json", "--file", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TCB" in out


def test_cli_parse_generic_csv(tmp_path: Path, capsys):
    p = tmp_path / "data.csv"
    p.write_text(GENERIC_CSV, encoding="utf-8")
    rc = main(
        [
            "parse",
            "--format",
            "generic-csv",
            "--file",
            str(p),
            "--bank",
            "VPB",
            "--quoted-at",
            "2026-05-14T09:30:00+07:00",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "VPB" in out


def test_cli_parse_generic_csv_requires_bank(tmp_path: Path, capsys):
    p = tmp_path / "data.csv"
    p.write_text(GENERIC_CSV, encoding="utf-8")
    rc = main(["parse", "--format", "generic-csv", "--file", str(p)])
    assert rc == 2


def test_cli_simulate_and_analyze(tmp_path: Path, capsys):
    store_path = tmp_path / "store.jsonl"
    main(
        [
            "simulate",
            "--banks",
            "VCB,BIDV,TCB,MB,VPB",
            "--currencies",
            "USD",
            "--snapshots",
            "2",
            "--seed",
            "1",
            "--inject",
            "outlier_buy",
            "--output",
            str(store_path),
        ]
    )
    rc = main(
        [
            "analyze",
            "--store",
            str(store_path),
            "--currency",
            "USD",
            "--outlier-pct",
            "1.0",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "BUY_OUTLIER" in out


def test_cli_no_subcommand_errors():
    with pytest.raises(SystemExit):
        main([])
