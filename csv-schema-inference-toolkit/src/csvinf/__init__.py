"""csv-schema-inference-toolkit — infer CSV column types + emit downstream schemas."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "ColumnType": ("csvinf.schema", "ColumnType"),
        "InferredColumn": ("csvinf.schema", "InferredColumn"),
        "InferredSchema": ("csvinf.schema", "InferredSchema"),
        "MAX_CARDINALITY": ("csvinf.schema", "MAX_CARDINALITY"),
        "ReadResult": ("csvinf.reader", "ReadResult"),
        "column_from_dict": ("csvinf.io_jsonl", "column_from_dict"),
        "column_to_dict": ("csvinf.io_jsonl", "column_to_dict"),
        "detect_date_format": ("csvinf.parsers", "detect_date_format"),
        "detect_datetime_format": ("csvinf.parsers", "detect_datetime_format"),
        "dump_schemas": ("csvinf.io_jsonl", "dump_schemas"),
        "emit_avro": ("csvinf.emit", "emit_avro"),
        "emit_dataclass": ("csvinf.emit", "emit_dataclass"),
        "emit_json_schema": ("csvinf.emit", "emit_json_schema"),
        "generate": ("csvinf.simulator", "generate"),
        "infer_schema": ("csvinf.infer", "infer_schema"),
        "load_schemas": ("csvinf.io_jsonl", "load_schemas"),
        "read": ("csvinf.reader", "read"),
        "schema_from_dict": ("csvinf.io_jsonl", "schema_from_dict"),
        "schema_to_dict": ("csvinf.io_jsonl", "schema_to_dict"),
        "sniff_delimiter": ("csvinf.reader", "sniff_delimiter"),
        "sniff_has_header": ("csvinf.reader", "sniff_has_header"),
        "try_bool": ("csvinf.parsers", "try_bool"),
        "try_date": ("csvinf.parsers", "try_date"),
        "try_datetime": ("csvinf.parsers", "try_datetime"),
        "try_decimal": ("csvinf.parsers", "try_decimal"),
        "try_float": ("csvinf.parsers", "try_float"),
        "try_int": ("csvinf.parsers", "try_int"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ColumnType",
    "InferredColumn",
    "InferredSchema",
    "MAX_CARDINALITY",
    "ReadResult",
    "__version__",
    "column_from_dict",
    "column_to_dict",
    "detect_date_format",
    "detect_datetime_format",
    "dump_schemas",
    "emit_avro",
    "emit_dataclass",
    "emit_json_schema",
    "generate",
    "infer_schema",
    "load_schemas",
    "read",
    "schema_from_dict",
    "schema_to_dict",
    "sniff_delimiter",
    "sniff_has_header",
    "try_bool",
    "try_date",
    "try_datetime",
    "try_decimal",
    "try_float",
    "try_int",
]
