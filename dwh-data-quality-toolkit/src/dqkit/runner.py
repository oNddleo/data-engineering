"""Run a :class:`Suite` against a rowset → list of :class:`CheckResult`.

The runner is a registry-driven dispatcher:

1. The bundled checks are registered under their names (``not_null``,
   ``cccd``, etc.) at import time via :func:`_build_default_registry`.
2. ``run_suite(rows, suite)`` looks up each ``CheckSpec.check`` in the
   registry, instantiates the check with the spec's ``severity``
   + ``args``, and runs it against the column.
3. The output is one ``CheckResult`` per ``CheckSpec``.

The runner also offers a **quarantine mode**: rows that fail an
ERROR-severity check get split out of the loadable set, so dashboards
can still load the GOOD rows while flagging the bad ones. Quarantine
is row-level — failing one ERROR check moves the entire row out.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

from dqkit.checks_generic import (
    dtype_int,
    dtype_str,
    in_set,
    not_null,
    range_int,
    regex,
    unique,
)
from dqkit.checks_vn import cccd, mst, vn_bank_account, vn_phone, vn_postal_code
from dqkit.schema import CheckResult, Severity, Suite

if TYPE_CHECKING:
    from dqkit.schema import Row


# Factory protocol: ``(severity, args_dict) → Check``.
CheckFactory = Callable[[Severity, dict[str, str]], object]


def _wrap_no_args(factory: Callable[[Severity], object]) -> CheckFactory:
    """Wrap a check that takes only ``severity`` to match CheckFactory shape."""

    def _f(severity: Severity, _args: dict[str, str]) -> object:
        return factory(severity)

    return _f


def _wrap_in_set(severity: Severity, args: dict[str, str]) -> object:
    raw = args.get("allowed", "")
    if not raw:
        raise ValueError("in_set requires args.allowed (comma-separated)")
    allowed: set[str | int] = set(raw.split(","))
    return in_set(allowed, severity)


def _wrap_regex(severity: Severity, args: dict[str, str]) -> object:
    pattern = args.get("pattern")
    if not pattern:
        raise ValueError("regex requires args.pattern")
    return regex(pattern, severity)


def _wrap_range_int(severity: Severity, args: dict[str, str]) -> object:
    lo_s = args.get("lo")
    hi_s = args.get("hi")
    if lo_s is None or hi_s is None:
        raise ValueError("range_int requires args.lo and args.hi")
    return range_int(int(lo_s), int(hi_s), severity)


def _build_default_registry() -> dict[str, CheckFactory]:
    return {
        # Generic
        "not_null": _wrap_no_args(not_null),
        "unique": _wrap_no_args(unique),
        "in_set": _wrap_in_set,
        "regex": _wrap_regex,
        "range_int": _wrap_range_int,
        "dtype_int": _wrap_no_args(dtype_int),
        "dtype_str": _wrap_no_args(dtype_str),
        # VN-specific
        "cccd": _wrap_no_args(cccd),
        "mst": _wrap_no_args(mst),
        "vn_phone": _wrap_no_args(vn_phone),
        "vn_bank_account": _wrap_no_args(vn_bank_account),
        "vn_postal_code": _wrap_no_args(vn_postal_code),
    }


_DEFAULT_REGISTRY = _build_default_registry()


def list_checks() -> list[str]:
    """Names of all registered checks."""
    return sorted(_DEFAULT_REGISTRY)


def run_suite(
    rows: list[Row],
    suite: Suite,
    registry: dict[str, CheckFactory] | None = None,
) -> list[CheckResult]:
    """Run every spec in ``suite`` against ``rows`` and return results.

    Unknown check names raise immediately — surfacing a typo in the
    suite definition early is cheaper than running the whole batch
    and noticing zero results came back.
    """
    reg = registry if registry is not None else _DEFAULT_REGISTRY
    out: list[CheckResult] = []
    for spec in suite.specs:
        factory = reg.get(spec.check)
        if factory is None:
            raise KeyError(f"unknown check {spec.check!r} (registered: {sorted(reg)})")
        check_callable = factory(spec.severity, dict(spec.args))
        # The factories return callables we type as `object`; cast for invocation.
        # mypy --strict accepts this because the Check Protocol can't enforce
        # the call signature without runtime-checkable Protocol.
        result = check_callable(rows, spec.column)  # type: ignore[operator]
        if not isinstance(result, CheckResult):
            raise TypeError(
                f"check {spec.check!r} returned {type(result).__name__}, not CheckResult"
            )
        out.append(result)
    return out


def quarantine_rows(
    rows: list[Row],
    results: list[CheckResult],
) -> tuple[list[Row], list[Row]]:
    """Split rows into (good, quarantined) based on ERROR-severity failures.

    A row is quarantined if **any** ERROR-severity check flagged it.
    WARNING-severity failures don't quarantine — they just log.
    """
    bad_indices: set[int] = set()
    for r in results:
        if r.severity is not Severity.ERROR:
            continue
        for f in r.failures:
            bad_indices.add(f.row_index)
    good: list[Row] = []
    bad: list[Row] = []
    for i, row in enumerate(rows):
        if i in bad_indices:
            bad.append(row)
        else:
            good.append(row)
    return good, bad


def summarise(results: list[CheckResult]) -> dict[str, object]:
    """Roll up results into a JSON-friendly summary."""
    return {
        "n_checks": len(results),
        "n_passed": sum(1 for r in results if r.passed),
        "n_failed": sum(1 for r in results if not r.passed),
        "by_severity": {
            "ERROR": sum(1 for r in results if not r.passed and r.severity is Severity.ERROR),
            "WARNING": sum(1 for r in results if not r.passed and r.severity is Severity.WARNING),
        },
        "per_check": [
            {
                "check": r.check_name,
                "column": r.column,
                "severity": r.severity.value,
                "n_rows": r.n_rows,
                "n_failed": r.n_failed,
            }
            for r in results
        ],
    }


def render_summary(summary: dict[str, object]) -> str:
    """Indented JSON representation of :func:`summarise`'s output."""
    return json.dumps(summary, indent=2, ensure_ascii=False)


__all__ = [
    "CheckFactory",
    "list_checks",
    "quarantine_rows",
    "render_summary",
    "run_suite",
    "summarise",
]
