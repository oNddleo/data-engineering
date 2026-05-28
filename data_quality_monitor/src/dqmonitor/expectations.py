"""ExpectationSuite: named, serialisable collection of rules."""

from __future__ import annotations

import json
from typing import Any

from dqmonitor.rules import (
    CustomPredicateRule,
    NotNullRule,
    RangeCheckRule,
    ReferentialIntegrityRule,
    RegexMatchRule,
    Rule,
    UniqueRule,
)

# Maps type tag → constructor
_RULE_TYPES: dict[str, type[Rule]] = {
    "NotNullRule": NotNullRule,
    "UniqueRule": UniqueRule,
    "RangeCheckRule": RangeCheckRule,
    "RegexMatchRule": RegexMatchRule,
    "ReferentialIntegrityRule": ReferentialIntegrityRule,
}


def _rule_to_dict(rule: Rule) -> dict[str, object]:
    """Serialise a rule to a plain dict.  CustomPredicateRule is skipped."""
    type_name = type(rule).__name__
    if isinstance(rule, NotNullRule):
        return {"type": type_name, "column": rule.column}
    if isinstance(rule, UniqueRule):
        return {"type": type_name, "column": rule.column}
    if isinstance(rule, RangeCheckRule):
        return {
            "type": type_name,
            "column": rule.column,
            "min_val": rule.min_val,
            "max_val": rule.max_val,
        }
    if isinstance(rule, RegexMatchRule):
        return {"type": type_name, "column": rule.column, "pattern": rule.pattern}
    if isinstance(rule, ReferentialIntegrityRule):
        return {
            "type": type_name,
            "column": rule.column,
            "allowed_values": list(rule.allowed_values),
        }
    if isinstance(rule, CustomPredicateRule):
        # Cannot serialise the callable; store metadata only.
        return {
            "type": "CustomPredicateRule",
            "name": rule.name,
            "description": rule.description,
        }
    raise ValueError(f"Unknown rule type: {type_name}")


def _dict_to_rule(data: dict[str, Any]) -> Rule:
    """Reconstruct a Rule from a serialised dict."""
    type_name: str = data["type"]
    if type_name == "NotNullRule":
        return NotNullRule(column=data["column"])
    if type_name == "UniqueRule":
        return UniqueRule(column=data["column"])
    if type_name == "RangeCheckRule":
        return RangeCheckRule(
            column=data["column"],
            min_val=float(data["min_val"]),
            max_val=float(data["max_val"]),
        )
    if type_name == "RegexMatchRule":
        return RegexMatchRule(column=data["column"], pattern=data["pattern"])
    if type_name == "ReferentialIntegrityRule":
        return ReferentialIntegrityRule(
            column=data["column"],
            allowed_values=set(data["allowed_values"]),
        )
    if type_name == "CustomPredicateRule":
        # Predicate cannot be restored from JSON; use a no-op that always passes.
        return CustomPredicateRule(
            rule_name=data["name"],
            predicate=lambda _r: True,
            rule_description=data.get("description", ""),
        )
    raise ValueError(f"Unknown rule type in JSON: {type_name!r}")


class ExpectationSuite:
    """A named, ordered collection of Rules that can be serialised to JSON."""

    def __init__(self, name: str = "default") -> None:
        self._name = name
        self._rules: list[Rule] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def to_json(self) -> str:
        payload: dict[str, object] = {
            "name": self._name,
            "rules": [_rule_to_dict(r) for r in self._rules],
        }
        return json.dumps(payload, indent=2)

    @classmethod
    def from_json(cls, s: str) -> ExpectationSuite:
        payload: dict[str, Any] = json.loads(s)
        suite = cls(name=payload.get("name", "default"))
        for rule_data in payload.get("rules", []):
            suite.add_rule(_dict_to_rule(rule_data))
        return suite
