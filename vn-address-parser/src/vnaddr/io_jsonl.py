"""JSONL codec for AdminUnit / MatchedToken / ParsedAddress."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from vnaddr.schema import (
    AdminLevel,
    AdminUnit,
    MatchedToken,
    MatchKind,
    ParsedAddress,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


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


# ---------- AdminUnit --------------------------------------------------------


def unit_to_dict(u: AdminUnit) -> dict[str, object]:
    return {
        "code": u.code,
        "name_vi": u.name_vi,
        "name_en": u.name_en,
        "level": u.level.value,
        "parent_code": u.parent_code,
        "aliases": list(u.aliases),
    }


def unit_from_dict(d: dict[str, object]) -> AdminUnit:
    aliases_raw = d.get("aliases", [])
    if not isinstance(aliases_raw, list):
        raise TypeError("aliases must be list")
    return AdminUnit(
        code=_require_str(d, "code"),
        name_vi=_require_str(d, "name_vi"),
        name_en=_require_str(d, "name_en"),
        level=AdminLevel(_require_str(d, "level")),
        parent_code=_require_str(d, "parent_code") if "parent_code" in d else "",
        aliases=tuple(str(a) for a in aliases_raw),
    )


# ---------- MatchedToken -----------------------------------------------------


def token_to_dict(m: MatchedToken) -> dict[str, object]:
    return {
        "raw_token": m.raw_token,
        "matched_code": m.matched_code,
        "matched_name": m.matched_name,
        "kind": m.kind.value,
        "edit_distance": m.edit_distance,
    }


def token_from_dict(d: dict[str, object]) -> MatchedToken:
    return MatchedToken(
        raw_token=_require_str(d, "raw_token"),
        matched_code=_require_str(d, "matched_code"),
        matched_name=_require_str(d, "matched_name"),
        kind=MatchKind(_require_str(d, "kind")),
        edit_distance=_require_int(d, "edit_distance") if "edit_distance" in d else 0,
    )


# ---------- ParsedAddress ----------------------------------------------------


def parsed_to_dict(p: ParsedAddress) -> dict[str, object]:
    return {
        "raw_input": p.raw_input,
        "street": p.street,
        "ward": token_to_dict(p.ward) if p.ward is not None else None,
        "district": token_to_dict(p.district) if p.district is not None else None,
        "province": token_to_dict(p.province) if p.province is not None else None,
    }


def parsed_from_dict(d: dict[str, object]) -> ParsedAddress:
    def _maybe_token(key: str) -> MatchedToken | None:
        v = d.get(key)
        if v is None:
            return None
        if not isinstance(v, dict):
            raise TypeError(f"{key} must be dict | null")
        return token_from_dict(v)

    return ParsedAddress(
        raw_input=_require_str(d, "raw_input"),
        street=_require_str(d, "street") if "street" in d else "",
        ward=_maybe_token("ward"),
        district=_maybe_token("district"),
        province=_maybe_token("province"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_units(items: Iterable[AdminUnit]) -> str:
    return _dump(unit_to_dict(u) for u in items)


def dump_parsed(items: Iterable[ParsedAddress]) -> str:
    return _dump(parsed_to_dict(p) for p in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_units(text: str) -> list[AdminUnit]:
    return [unit_from_dict(d) for d in _iter_lines(text)]


def load_parsed(text: str) -> list[ParsedAddress]:
    return [parsed_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_parsed",
    "dump_units",
    "load_parsed",
    "load_units",
    "parsed_from_dict",
    "parsed_to_dict",
    "token_from_dict",
    "token_to_dict",
    "unit_from_dict",
    "unit_to_dict",
]
