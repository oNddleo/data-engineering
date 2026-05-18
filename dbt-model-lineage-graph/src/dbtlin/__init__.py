"""dbt-model-lineage-graph — parse dbt SQL → DAG + cycles + impact."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from dbtlin.graph import (
        LineageGraph,
        build_graph,
        find_cycles,
        leaves,
        roots,
        topological_order,
    )
    from dbtlin.impact import downstream_of, impact, impact_by_name, upstream_of
    from dbtlin.io_jsonl import (
        dump_edges,
        dump_models,
        edge_from_dict,
        edge_to_dict,
        load_edges,
        load_models,
        model_from_dict,
        model_to_dict,
        node_from_dict,
        node_to_dict,
        project_from_json,
        project_to_json,
    )
    from dbtlin.parser import (
        extract_refs,
        extract_sources,
        parse_model,
        parse_project,
        strip_comments,
    )
    from dbtlin.schema import (
        CycleReport,
        Edge,
        ImpactReport,
        Model,
        NodeId,
        NodeKind,
    )
    from dbtlin.simulator import generate


_LAZY: dict[str, tuple[str, str]] = {
    "CycleReport": ("dbtlin.schema", "CycleReport"),
    "Edge": ("dbtlin.schema", "Edge"),
    "ImpactReport": ("dbtlin.schema", "ImpactReport"),
    "LineageGraph": ("dbtlin.graph", "LineageGraph"),
    "Model": ("dbtlin.schema", "Model"),
    "NodeId": ("dbtlin.schema", "NodeId"),
    "NodeKind": ("dbtlin.schema", "NodeKind"),
    "build_graph": ("dbtlin.graph", "build_graph"),
    "downstream_of": ("dbtlin.impact", "downstream_of"),
    "dump_edges": ("dbtlin.io_jsonl", "dump_edges"),
    "dump_models": ("dbtlin.io_jsonl", "dump_models"),
    "edge_from_dict": ("dbtlin.io_jsonl", "edge_from_dict"),
    "edge_to_dict": ("dbtlin.io_jsonl", "edge_to_dict"),
    "extract_refs": ("dbtlin.parser", "extract_refs"),
    "extract_sources": ("dbtlin.parser", "extract_sources"),
    "find_cycles": ("dbtlin.graph", "find_cycles"),
    "generate": ("dbtlin.simulator", "generate"),
    "impact": ("dbtlin.impact", "impact"),
    "impact_by_name": ("dbtlin.impact", "impact_by_name"),
    "leaves": ("dbtlin.graph", "leaves"),
    "load_edges": ("dbtlin.io_jsonl", "load_edges"),
    "load_models": ("dbtlin.io_jsonl", "load_models"),
    "model_from_dict": ("dbtlin.io_jsonl", "model_from_dict"),
    "model_to_dict": ("dbtlin.io_jsonl", "model_to_dict"),
    "node_from_dict": ("dbtlin.io_jsonl", "node_from_dict"),
    "node_to_dict": ("dbtlin.io_jsonl", "node_to_dict"),
    "parse_model": ("dbtlin.parser", "parse_model"),
    "parse_project": ("dbtlin.parser", "parse_project"),
    "project_from_json": ("dbtlin.io_jsonl", "project_from_json"),
    "project_to_json": ("dbtlin.io_jsonl", "project_to_json"),
    "roots": ("dbtlin.graph", "roots"),
    "strip_comments": ("dbtlin.parser", "strip_comments"),
    "topological_order": ("dbtlin.graph", "topological_order"),
    "upstream_of": ("dbtlin.impact", "upstream_of"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CycleReport",
    "Edge",
    "ImpactReport",
    "LineageGraph",
    "Model",
    "NodeId",
    "NodeKind",
    "__version__",
    "build_graph",
    "downstream_of",
    "dump_edges",
    "dump_models",
    "edge_from_dict",
    "edge_to_dict",
    "extract_refs",
    "extract_sources",
    "find_cycles",
    "generate",
    "impact",
    "impact_by_name",
    "leaves",
    "load_edges",
    "load_models",
    "model_from_dict",
    "model_to_dict",
    "node_from_dict",
    "node_to_dict",
    "parse_model",
    "parse_project",
    "project_from_json",
    "project_to_json",
    "roots",
    "strip_comments",
    "topological_order",
    "upstream_of",
]
