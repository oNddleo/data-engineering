"""Validator: runs a list of Rules against a batch of records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqmonitor.rules import Rule


@dataclass(frozen=True)
class Violation:
    """Describes a single rule failure."""

    rule_name: str
    record_index: int
    value: object


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate result of validating a batch of records."""

    total: int
    passed: int
    failed: int
    pass_rate: float
    violations: list[Violation] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ValueError("total must be >= 0")
        if self.passed + self.failed != self.total:
            raise ValueError("passed + failed must equal total")


class Validator:
    """Runs a collection of rules against every record in a batch.

    Stateful rules (e.g. UniqueRule) are reset before each call.
    """

    def __init__(self, rules: list[Rule]) -> None:
        self._rules: list[Rule] = list(rules)

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def validate(self, batch: list[dict[str, object]]) -> ValidationResult:
        """Validate every record in *batch* against all rules.

        Each rule's ``reset()`` is called once before iteration begins.
        """
        for rule in self._rules:
            rule.reset()

        violations: list[Violation] = []
        failed_indices: set[int] = set()

        for idx, record in enumerate(batch):
            for rule in self._rules:
                if not rule.check(record):
                    violations.append(
                        Violation(
                            rule_name=rule.name,
                            record_index=idx,
                            value=record.get(_extract_column(rule), "<unknown>"),
                        )
                    )
                    failed_indices.add(idx)

        total = len(batch)
        failed = len(failed_indices)
        passed = total - failed
        pass_rate = passed / total if total > 0 else 1.0

        return ValidationResult(
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            violations=violations,
        )


def _extract_column(rule: Rule) -> str:
    """Try to extract a column name from a rule for violation reporting."""
    return getattr(rule, "column", rule.name)
