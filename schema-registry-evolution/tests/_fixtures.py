"""Canonical schema builders for tests."""

from __future__ import annotations

from schemaev.schema import Field, FieldType, Schema


def make_field(
    name: str = "x",
    type: FieldType = FieldType.STRING,
    required: bool = True,
    default: str | None = None,
    aliases: tuple[str, ...] = (),
) -> Field:
    return Field(name=name, type=type, required=required, default=default, aliases=aliases)


def make_schema(
    name: str = "Order",
    version: str = "1.0.0",
    fields: tuple[Field, ...] = (),
) -> Schema:
    if not fields:
        fields = (
            Field(name="order_id", type=FieldType.STRING),
            Field(name="amount", type=FieldType.LONG),
        )
    return Schema(name=name, version=version, fields=fields)


__all__ = ["make_field", "make_schema"]
