"""JSONL I/O for Transaction and ReconReport objects."""

from __future__ import annotations

import json
from datetime import date
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from recon.schema import DiscrepancyType, MatchResult, ReconReport, Transaction

# ── helpers ──────────────────────────────────────────────────────────────────


def _req_str(obj: dict[str, object], key: str) -> str:
    v = obj[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str")
    return v


def _req_float(obj: dict[str, object], key: str) -> float:
    v = obj[key]
    if isinstance(v, int | float):
        return float(v)
    raise TypeError(f"{key} must be numeric")


def _req_date(obj: dict[str, object], key: str) -> date:
    v = obj[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be a date string")
    return date.fromisoformat(v)


# ── Transaction I/O ───────────────────────────────────────────────────────────


def txn_to_dict(t: Transaction) -> dict[str, object]:
    return {
        "source": t.source,
        "ref": t.ref,
        "amount": t.amount,
        "txn_date": t.txn_date.isoformat(),
        "description": t.description,
        "currency": t.currency,
    }


def txn_from_dict(obj: dict[str, object]) -> Transaction:
    return Transaction(
        source=_req_str(obj, "source"),
        ref=_req_str(obj, "ref"),
        amount=_req_float(obj, "amount"),
        txn_date=_req_date(obj, "txn_date"),
        description=_req_str(obj, "description"),
        currency=_req_str(obj, "currency") if "currency" in obj else "USD",
    )


def load_transactions(path: str | Path) -> list[Transaction]:
    txns: list[Transaction] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                txns.append(txn_from_dict(json.loads(line)))
    return txns


def dump_transactions(txns: list[Transaction], path: str | Path) -> None:
    with open(path, "w") as fh:
        for t in txns:
            fh.write(json.dumps(txn_to_dict(t)) + "\n")


def write_transactions(txns: list[Transaction], fh: IO[str]) -> None:
    for t in txns:
        fh.write(json.dumps(txn_to_dict(t)) + "\n")


# ── ReconReport I/O ───────────────────────────────────────────────────────────


def _match_to_dict(m: MatchResult) -> dict[str, object]:
    return {
        "ref": m.ref,
        "status": m.status.value,
        "sources_present": m.sources_present,
        "amount_delta": m.amount_delta,
        "confidence": m.confidence,
        "notes": m.notes,
        "transactions": [txn_to_dict(t) for t in m.transactions],
    }


def report_to_jsonl(report: ReconReport, fh: IO[str]) -> None:
    meta = {
        "run_date": report.run_date.isoformat(),
        "sources": report.sources,
        "total_records": report.total_records,
        "matched": report.matched,
        "discrepancies": report.discrepancies,
        "match_rate": round(report.match_rate, 4),
    }
    fh.write(json.dumps(meta) + "\n")
    for m in report.results:
        fh.write(json.dumps(_match_to_dict(m)) + "\n")


def report_from_jsonl(fh: IO[str]) -> ReconReport:
    lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        raise ValueError("empty input")
    meta = json.loads(lines[0])
    results: list[MatchResult] = []
    for line in lines[1:]:
        obj = json.loads(line)
        txns = [txn_from_dict(t) for t in obj.get("transactions", [])]
        results.append(
            MatchResult(
                ref=obj["ref"],
                status=DiscrepancyType(obj["status"]),
                sources_present=obj["sources_present"],
                transactions=txns,
                amount_delta=float(obj.get("amount_delta", 0.0)),
                confidence=float(obj.get("confidence", 1.0)),
                notes=str(obj.get("notes", "")),
            )
        )
    return ReconReport(
        run_date=date.fromisoformat(meta["run_date"]),
        sources=meta["sources"],
        total_records=int(meta["total_records"]),
        matched=int(meta["matched"]),
        discrepancies=int(meta["discrepancies"]),
        results=results,
    )
