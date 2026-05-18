"""JSONL codec for rows, suites, and CheckResults."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dqkit.schema import CheckResult, CheckSpec, FailedRow, Severity, Suite

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from dqkit.schema import Row


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _dump_lines(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


# ---------- Rows -----------------------------------------------------------


def dump_rows(rows: Iterable[Row]) -> str:
    """Emit one row per JSONL line. Mixed scalar/null values supported."""
    return _dump_lines(dict(r) for r in rows)


def load_rows(text: str) -> list[Row]:
    """Decode JSONL into rows; coerces ``bool`` keys' values to int conservatively."""
    out: list[Row] = []
    for parsed in _iter_lines(text):
        row: Row = {}
        for k, v in parsed.items():
            if v is None or isinstance(v, str):
                row[k] = v
            elif isinstance(v, bool):
                # JSON has no separate bool — caller's hand-crafted file
                # might pass true/false. Reject explicitly so downstream
                # dtype_int catches the misuse.
                row[k] = int(v)
            elif isinstance(v, int):
                row[k] = v
            else:
                # Floats, lists, dicts — coerce to string for type-uniform storage.
                row[k] = json.dumps(v, ensure_ascii=False)
        out.append(row)
    return out


# ---------- Suite ----------------------------------------------------------


def suite_to_json(suite: Suite) -> str:
    """One JSON object with the suite name + list of specs."""
    payload = {
        "name": suite.name,
        "specs": [
            {
                "check": spec.check,
                "column": spec.column,
                "severity": spec.severity.value,
                "args": dict(spec.args),
            }
            for spec in suite.specs
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def suite_from_json(text: str) -> Suite:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError("suite must be a JSON object")
    name = parsed.get("name")
    if not isinstance(name, str) or not name:
        raise TypeError("suite.name must be a non-empty string")
    raw_specs = parsed.get("specs")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise TypeError("suite.specs must be a non-empty list")
    specs: list[CheckSpec] = []
    for s in raw_specs:
        if not isinstance(s, dict):
            raise TypeError("each spec must be an object")
        check = _require_str(s, "check")
        column = _require_str(s, "column")
        severity = Severity(_require_str(s, "severity"))
        raw_args = s.get("args", {})
        if not isinstance(raw_args, dict):
            raise TypeError("spec.args must be an object")
        args: dict[str, str] = {}
        for k, v in raw_args.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("spec.args must be str→str")
            args[k] = v
        specs.append(CheckSpec(check=check, column=column, severity=severity, args=args))
    return Suite(name=name, specs=tuple(specs))


# ---------- CheckResult ----------------------------------------------------


def result_to_dict(r: CheckResult) -> dict[str, object]:
    return {
        "check_name": r.check_name,
        "column": r.column,
        "severity": r.severity.value,
        "n_rows": r.n_rows,
        "n_passed": r.n_passed,
        "n_failed": r.n_failed,
        "passed": r.passed,
        "failures": [
            {
                "row_index": f.row_index,
                "column": f.column,
                "value": f.value,
                "reason": f.reason,
            }
            for f in r.failures
        ],
    }


def result_from_dict(d: dict[str, object]) -> CheckResult:
    raw_failures = d.get("failures", [])
    if not isinstance(raw_failures, list):
        raise TypeError("failures must be a list")
    failures: list[FailedRow] = []
    for f in raw_failures:
        if not isinstance(f, dict):
            raise TypeError("each failure must be an object")
        value = f.get("value")
        if not (value is None or isinstance(value, str | int)):
            raise TypeError("failure.value must be str | int | null")
        failures.append(
            FailedRow(
                row_index=_require_int(f, "row_index"),
                column=_require_str(f, "column"),
                value=value,
                reason=_require_str(f, "reason"),
            )
        )
    return CheckResult(
        check_name=_require_str(d, "check_name"),
        column=_require_str(d, "column"),
        severity=Severity(_require_str(d, "severity")),
        n_rows=_require_int(d, "n_rows"),
        n_passed=_require_int(d, "n_passed"),
        failures=tuple(failures),
    )


def dump_results(results: Iterable[CheckResult]) -> str:
    return _dump_lines(result_to_dict(r) for r in results)


def load_results(text: str) -> list[CheckResult]:
    return [result_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_results",
    "dump_rows",
    "load_results",
    "load_rows",
    "result_from_dict",
    "result_to_dict",
    "suite_from_json",
    "suite_to_json",
]
