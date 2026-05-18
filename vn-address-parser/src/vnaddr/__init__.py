"""vn-address-parser — parse VN postal addresses into 3-level admin hierarchy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnaddr.distance import find_closest, levenshtein
    from vnaddr.io_jsonl import (
        dump_parsed,
        dump_units,
        load_parsed,
        load_units,
        parsed_from_dict,
        parsed_to_dict,
        token_from_dict,
        token_to_dict,
        unit_from_dict,
        unit_to_dict,
    )
    from vnaddr.normalize import (
        expand_abbreviations,
        fold_diacritics,
        normalise,
        tokens,
    )
    from vnaddr.parser import list_units, parse
    from vnaddr.schema import (
        AdminLevel,
        AdminUnit,
        MatchedToken,
        MatchKind,
        ParsedAddress,
    )
    from vnaddr.simulator import NoiseLevel, generate
    from vnaddr.units import all_units, by_code, by_level, by_parent, n_provinces


_LAZY: dict[str, tuple[str, str]] = {
    "AdminLevel": ("vnaddr.schema", "AdminLevel"),
    "AdminUnit": ("vnaddr.schema", "AdminUnit"),
    "MatchKind": ("vnaddr.schema", "MatchKind"),
    "MatchedToken": ("vnaddr.schema", "MatchedToken"),
    "NoiseLevel": ("vnaddr.simulator", "NoiseLevel"),
    "ParsedAddress": ("vnaddr.schema", "ParsedAddress"),
    "all_units": ("vnaddr.units", "all_units"),
    "by_code": ("vnaddr.units", "by_code"),
    "by_level": ("vnaddr.units", "by_level"),
    "by_parent": ("vnaddr.units", "by_parent"),
    "dump_parsed": ("vnaddr.io_jsonl", "dump_parsed"),
    "dump_units": ("vnaddr.io_jsonl", "dump_units"),
    "expand_abbreviations": ("vnaddr.normalize", "expand_abbreviations"),
    "find_closest": ("vnaddr.distance", "find_closest"),
    "fold_diacritics": ("vnaddr.normalize", "fold_diacritics"),
    "generate": ("vnaddr.simulator", "generate"),
    "levenshtein": ("vnaddr.distance", "levenshtein"),
    "list_units": ("vnaddr.parser", "list_units"),
    "load_parsed": ("vnaddr.io_jsonl", "load_parsed"),
    "load_units": ("vnaddr.io_jsonl", "load_units"),
    "n_provinces": ("vnaddr.units", "n_provinces"),
    "normalise": ("vnaddr.normalize", "normalise"),
    "parse": ("vnaddr.parser", "parse"),
    "parsed_from_dict": ("vnaddr.io_jsonl", "parsed_from_dict"),
    "parsed_to_dict": ("vnaddr.io_jsonl", "parsed_to_dict"),
    "token_from_dict": ("vnaddr.io_jsonl", "token_from_dict"),
    "token_to_dict": ("vnaddr.io_jsonl", "token_to_dict"),
    "tokens": ("vnaddr.normalize", "tokens"),
    "unit_from_dict": ("vnaddr.io_jsonl", "unit_from_dict"),
    "unit_to_dict": ("vnaddr.io_jsonl", "unit_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AdminLevel",
    "AdminUnit",
    "MatchKind",
    "MatchedToken",
    "NoiseLevel",
    "ParsedAddress",
    "__version__",
    "all_units",
    "by_code",
    "by_level",
    "by_parent",
    "dump_parsed",
    "dump_units",
    "expand_abbreviations",
    "find_closest",
    "fold_diacritics",
    "generate",
    "levenshtein",
    "list_units",
    "load_parsed",
    "load_units",
    "n_provinces",
    "normalise",
    "parse",
    "parsed_from_dict",
    "parsed_to_dict",
    "token_from_dict",
    "token_to_dict",
    "tokens",
    "unit_from_dict",
    "unit_to_dict",
]
