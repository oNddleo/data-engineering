"""JSONL serialisation for catalog assets and audit log entries."""

from __future__ import annotations

import json
from typing import IO

from dpbudget.schema import (
    Analyst,
    BudgetAllocation,
    Dataset,
    ExhaustionPolicy,
    Mechanism,
    QueryLogEntry,
    QueryStatus,
)

# ── Dataset ───────────────────────────────────────────────────────────────────


def dataset_to_dict(d: Dataset) -> dict[str, object]:
    return {
        "dataset_id": d.dataset_id,
        "name": d.name,
        "sensitivity": d.sensitivity,
        "description": d.description,
    }


def dataset_from_dict(obj: dict[str, object]) -> Dataset:
    return Dataset(
        dataset_id=str(obj["dataset_id"]),
        name=str(obj["name"]),
        sensitivity=float(obj.get("sensitivity", 1.0)),  # type: ignore[arg-type]
        description=str(obj.get("description", "")),
    )


# ── Analyst ───────────────────────────────────────────────name──────────────


def analyst_to_dict(a: Analyst) -> dict[str, object]:
    return {"analyst_id": a.analyst_id, "name": a.name, "email": a.email}


def analyst_from_dict(obj: dict[str, object]) -> Analyst:
    return Analyst(
        analyst_id=str(obj["analyst_id"]),
        name=str(obj["name"]),
        email=str(obj.get("email", "")),
    )


# ── BudgetAllocation ──────────────────────────────────────────────────────────


def budget_to_dict(b: BudgetAllocation) -> dict[str, object]:
    return {
        "dataset_id": b.dataset_id,
        "analyst_id": b.analyst_id,
        "epsilon_total": b.epsilon_total,
        "delta_total": b.delta_total,
        "consumed_epsilon": b.consumed_epsilon,
        "consumed_delta": b.consumed_delta,
        "exhaustion_policy": b.exhaustion_policy.value,
        "default_mechanism": b.default_mechanism.value,
    }


def budget_from_dict(obj: dict[str, object]) -> BudgetAllocation:
    return BudgetAllocation(
        dataset_id=str(obj["dataset_id"]),
        analyst_id=str(obj["analyst_id"]),
        epsilon_total=float(obj.get("epsilon_total", 1.0)),  # type: ignore[arg-type]
        delta_total=float(obj.get("delta_total", 0.0)),  # type: ignore[arg-type]
        consumed_epsilon=float(obj.get("consumed_epsilon", 0.0)),  # type: ignore[arg-type]
        consumed_delta=float(obj.get("consumed_delta", 0.0)),  # type: ignore[arg-type]
        exhaustion_policy=ExhaustionPolicy(str(obj.get("exhaustion_policy", "block"))),
        default_mechanism=Mechanism(str(obj.get("default_mechanism", "laplace"))),
    )


# ── QueryLogEntry ─────────────────────────────────────────────────────────────


def log_to_dict(e: QueryLogEntry) -> dict[str, object]:
    return {
        "query_id": e.query_id,
        "dataset_id": e.dataset_id,
        "analyst_id": e.analyst_id,
        "query_text": e.query_text,
        "true_result": e.true_result,
        "noisy_result": e.noisy_result,
        "noise_added": e.noise_added,
        "epsilon_requested": e.epsilon_requested,
        "delta_requested": e.delta_requested,
        "epsilon_consumed": e.epsilon_consumed,
        "delta_consumed": e.delta_consumed,
        "sensitivity": e.sensitivity,
        "mechanism_used": e.mechanism_used.value,
        "status": e.status.value,
        "budget_remaining_after": e.budget_remaining_after,
        "tags": e.tags,
    }


def log_from_dict(obj: dict[str, object]) -> QueryLogEntry:
    nr = obj.get("noisy_result")
    na = obj.get("noise_added")
    tags_raw = obj.get("tags", [])
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    return QueryLogEntry(
        query_id=str(obj["query_id"]),
        dataset_id=str(obj["dataset_id"]),
        analyst_id=str(obj["analyst_id"]),
        query_text=str(obj.get("query_text", "")),
        true_result=float(obj.get("true_result", 0.0)),  # type: ignore[arg-type]
        noisy_result=float(nr) if nr is not None else None,  # type: ignore[arg-type]
        noise_added=float(na) if na is not None else None,  # type: ignore[arg-type]
        epsilon_requested=float(obj.get("epsilon_requested", 0.0)),  # type: ignore[arg-type]
        delta_requested=float(obj.get("delta_requested", 0.0)),  # type: ignore[arg-type]
        epsilon_consumed=float(obj.get("epsilon_consumed", 0.0)),  # type: ignore[arg-type]
        delta_consumed=float(obj.get("delta_consumed", 0.0)),  # type: ignore[arg-type]
        sensitivity=float(obj.get("sensitivity", 1.0)),  # type: ignore[arg-type]
        mechanism_used=Mechanism(str(obj.get("mechanism_used", "laplace"))),
        status=QueryStatus(str(obj.get("status", "allowed"))),
        budget_remaining_after=float(obj.get("budget_remaining_after", 0.0)),  # type: ignore[arg-type]
        tags=tags,
    )


# ── JSONL I/O helpers ─────────────────────────────────────────────────────────


def write_log(entries: list[QueryLogEntry], fh: IO[str]) -> None:
    for e in entries:
        fh.write(json.dumps(log_to_dict(e)) + "\n")


def read_log(fh: IO[str]) -> list[QueryLogEntry]:
    out: list[QueryLogEntry] = []
    for line in fh:
        line = line.strip()
        if line:
            out.append(log_from_dict(json.loads(line)))
    return out
