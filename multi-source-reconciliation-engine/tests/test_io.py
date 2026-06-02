"""Tests for JSONL I/O round-trip."""

from __future__ import annotations

import io
import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from recon.engine import reconcile
from recon.io_jsonl import (
    dump_transactions,
    load_transactions,
    report_from_jsonl,
    report_to_jsonl,
    txn_from_dict,
    txn_to_dict,
)
from recon.schema import Transaction
from recon.simulator import generate_sources


def _sample_txn() -> Transaction:
    return Transaction(
        source="core_banking",
        ref="TXN12345678",
        amount=9999.99,
        txn_date=date(2024, 6, 15),
        description="ACH PAYMENT",
        currency="USD",
    )


class TestTransactionIO:
    def test_roundtrip_dict(self) -> None:
        t = _sample_txn()
        d = txn_to_dict(t)
        t2 = txn_from_dict(d)
        assert t == t2

    def test_roundtrip_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)
        txns = [_sample_txn()]
        dump_transactions(txns, path)
        loaded = load_transactions(path)
        assert loaded == txns

    def test_multiple_txns_file(self) -> None:
        sources = generate_sources(n_transactions=20, seed=99)
        with tempfile.TemporaryDirectory() as tmp:
            for src, txns in sources.items():
                dump_transactions(txns, Path(tmp) / f"{src}.jsonl")
            loaded: list[Transaction] = []
            for f in Path(tmp).glob("*.jsonl"):
                loaded.extend(load_transactions(f))
        total = sum(len(v) for v in sources.values())
        assert len(loaded) == total

    def test_missing_currency_defaults(self) -> None:
        d: dict[str, object] = {
            "source": "A",
            "ref": "R1",
            "amount": 1.0,
            "txn_date": "2024-01-01",
            "description": "X",
        }
        t = txn_from_dict(d)
        assert t.currency == "USD"

    def test_bad_type_raises(self) -> None:
        d: dict[str, object] = {
            "source": 123,
            "ref": "R1",
            "amount": 1.0,
            "txn_date": "2024-01-01",
            "description": "X",
        }
        with pytest.raises(TypeError):
            txn_from_dict(d)


class TestReportIO:
    def _sample_report(self) -> object:
        sources = generate_sources(n_transactions=30, seed=7)

        return reconcile(sources)

    def test_roundtrip_report(self) -> None:
        report = self._sample_report()
        buf = io.StringIO()
        report_to_jsonl(report, buf)
        buf.seek(0)
        report2 = report_from_jsonl(buf)
        assert report.matched == report2.matched
        assert report.discrepancies == report2.discrepancies
        assert report.run_date == report2.run_date

    def test_report_first_line_is_meta(self) -> None:
        report = self._sample_report()
        buf = io.StringIO()
        report_to_jsonl(report, buf)
        buf.seek(0)
        first = json.loads(buf.readline())
        assert "run_date" in first
        assert "match_rate" in first

    def test_empty_raises(self) -> None:
        buf = io.StringIO()
        with pytest.raises(ValueError):
            report_from_jsonl(buf)
