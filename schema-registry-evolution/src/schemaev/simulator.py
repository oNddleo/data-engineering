"""Seeded synthetic schema pairs for testing.

Produces `(old, new)` schema pairs covering every change kind we
care about. The bundled example is a Shopee-style ``Order`` schema
to match the rest of the catalogue.
"""

from __future__ import annotations

import random

from schemaev.schema import Field, FieldType, Schema


def _base_order_schema(version: str) -> Schema:
    """The starting-point Order schema everyone in the catalogue uses."""
    return Schema(
        name="Order",
        version=version,
        fields=(
            Field(name="order_id", type=FieldType.STRING),
            Field(name="customer_id", type=FieldType.STRING),
            Field(name="gross_vnd", type=FieldType.LONG),
            Field(name="n_items", type=FieldType.INT),
            Field(name="placed_at", type=FieldType.STRING),  # ISO timestamp
        ),
    )


def generate_pair(
    *,
    mutation: str = "safe_add",
    seed: int = 0,
) -> tuple[Schema, Schema]:
    """Return ``(old, new)`` schemas exercising one of the named mutations.

    Recognised ``mutation`` values:

    * ``safe_add``       — adds an optional field with a default
    * ``required_add``   — adds a required field WITHOUT default (BACKWARD break)
    * ``remove_optional``— removes an optional field (FORWARD-safe, BACKWARD-safe)
    * ``remove_required``— removes a required field (BACKWARD break)
    * ``widen_type``     — int → long (BACKWARD-safe)
    * ``narrow_type``    — long → int (BACKWARD break)
    * ``rename_with_alias`` — renames with an alias (BACKWARD-safe)
    * ``required_to_optional`` — required → optional (BACKWARD-safe)
    * ``optional_to_required`` — optional → required (BACKWARD break)
    """
    rng = random.Random(seed)
    _ = rng  # reserved for future jitter
    old = _base_order_schema("1.0.0")

    if mutation == "safe_add":
        new = Schema(
            name="Order",
            version="1.1.0",
            fields=(
                *old.fields,
                Field(name="discount_code", type=FieldType.STRING, required=False, default=""),
            ),
        )
    elif mutation == "required_add":
        new = Schema(
            name="Order",
            version="2.0.0",
            fields=(
                *old.fields,
                Field(name="store_id", type=FieldType.STRING),
            ),  # required, no default
        )
    elif mutation == "remove_optional":
        with_opt = Schema(
            name="Order",
            version="1.0.0",
            fields=(
                *old.fields,
                Field(name="notes", type=FieldType.STRING, required=False, default=""),
            ),
        )
        old = with_opt
        new = Schema(name="Order", version="1.1.0", fields=old.fields[:-1])
    elif mutation == "remove_required":
        new = Schema(name="Order", version="2.0.0", fields=old.fields[:-1])
    elif mutation == "widen_type":
        new = Schema(
            name="Order",
            version="1.1.0",
            fields=tuple(
                Field(
                    name=f.name,
                    type=FieldType.LONG,
                    required=f.required,
                    default=f.default,
                    aliases=f.aliases,
                )
                if f.name == "n_items"
                else f
                for f in old.fields
            ),
        )
    elif mutation == "narrow_type":
        new = Schema(
            name="Order",
            version="2.0.0",
            fields=tuple(
                Field(
                    name=f.name,
                    type=FieldType.INT,
                    required=f.required,
                    default=f.default,
                    aliases=f.aliases,
                )
                if f.name == "gross_vnd"
                else f
                for f in old.fields
            ),
        )
    elif mutation == "rename_with_alias":
        new = Schema(
            name="Order",
            version="1.1.0",
            fields=tuple(
                Field(
                    name="buyer_id",
                    type=f.type,
                    required=f.required,
                    default=f.default,
                    aliases=("customer_id",),
                )
                if f.name == "customer_id"
                else f
                for f in old.fields
            ),
        )
    elif mutation == "required_to_optional":
        new = Schema(
            name="Order",
            version="1.1.0",
            fields=tuple(
                Field(
                    name=f.name,
                    type=f.type,
                    required=False,
                    default=f.default or "",
                    aliases=f.aliases,
                )
                if f.name == "n_items"
                else f
                for f in old.fields
            ),
        )
    elif mutation == "optional_to_required":
        with_opt = Schema(
            name="Order",
            version="1.0.0",
            fields=(
                *old.fields,
                Field(name="notes", type=FieldType.STRING, required=False, default=""),
            ),
        )
        old = with_opt
        new = Schema(
            name="Order",
            version="2.0.0",
            fields=tuple(
                Field(name=f.name, type=f.type, required=True, default=f.default, aliases=f.aliases)
                if f.name == "notes"
                else f
                for f in old.fields
            ),
        )
    else:
        raise ValueError(
            f"unknown mutation {mutation!r}; choose from safe_add / required_add / "
            f"remove_optional / remove_required / widen_type / narrow_type / "
            f"rename_with_alias / required_to_optional / optional_to_required"
        )
    return old, new


def all_mutations() -> tuple[str, ...]:
    """Names of every mutation the simulator supports."""
    return (
        "safe_add",
        "required_add",
        "remove_optional",
        "remove_required",
        "widen_type",
        "narrow_type",
        "rename_with_alias",
        "required_to_optional",
        "optional_to_required",
    )


__all__ = ["all_mutations", "generate_pair"]
