"""cdc-debezium-postgres-kafka — type-safe CDC event toolkit."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "Op": ("cdc.events.envelope", "Op"),
        "SourceInfo": ("cdc.events.envelope", "SourceInfo"),
        "DebeziumEnvelope": ("cdc.events.envelope", "DebeziumEnvelope"),
        "parse_envelope": ("cdc.events.parse", "parse_envelope"),
        "ParseError": ("cdc.events.parse", "ParseError"),
        "Transform": ("cdc.transforms.base", "Transform"),
        "FlattenAfter": ("cdc.transforms.flatten", "FlattenAfter"),
        "MaskPII": ("cdc.transforms.mask_pii", "MaskPII"),
        "RenameColumns": ("cdc.transforms.rename", "RenameColumns"),
        "DLQRouter": ("cdc.dlq.router", "DLQRouter"),
        "DLQReason": ("cdc.dlq.router", "DLQReason"),
        "DLQDecision": ("cdc.dlq.router", "DLQDecision"),
        "Pipeline": ("cdc.pipeline", "Pipeline"),
        "PipelineResult": ("cdc.pipeline", "PipelineResult"),
        "postgres_to_avro": ("cdc.schema.avro", "postgres_to_avro"),
        "generate_avro_schema": ("cdc.schema.avro", "generate_avro_schema"),
    }

    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DLQDecision",
    "DLQReason",
    "DLQRouter",
    "DebeziumEnvelope",
    "FlattenAfter",
    "MaskPII",
    "Op",
    "ParseError",
    "Pipeline",
    "PipelineResult",
    "RenameColumns",
    "SourceInfo",
    "Transform",
    "__version__",
    "generate_avro_schema",
    "parse_envelope",
    "postgres_to_avro",
]
