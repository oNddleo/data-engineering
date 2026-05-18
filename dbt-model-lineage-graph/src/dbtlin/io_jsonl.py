"""JSONL codec for project + parsed models + edges."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dbtlin.schema import Edge, Model, NodeId, NodeKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def model_to_dict(m: Model) -> dict[str, object]:
    return {
        "name": m.name,
        "sql": m.sql,
        "refs": list(m.refs),
        "sources": [[s, t] for s, t in m.sources],
        "path": m.path,
    }


def model_from_dict(d: dict[str, object]) -> Model:
    raw_refs = d.get("refs", [])
    if not isinstance(raw_refs, list):
        raise TypeError("refs must be a list")
    refs = tuple(str(r) for r in raw_refs if isinstance(r, str))
    raw_sources = d.get("sources", [])
    if not isinstance(raw_sources, list):
        raise TypeError("sources must be a list")
    sources: list[tuple[str, str]] = []
    for entry in raw_sources:
        if not isinstance(entry, list) or len(entry) != 2:
            raise TypeError("each source must be a 2-element list [schema, table]")
        s, t = entry
        if not isinstance(s, str) or not isinstance(t, str):
            raise TypeError("source elements must be strings")
        sources.append((s, t))
    return Model(
        name=_require_str(d, "name"),
        sql=_require_str(d, "sql"),
        refs=refs,
        sources=tuple(sources),
        path=str(d["path"]) if isinstance(d.get("path"), str) else "",
    )


def node_to_dict(n: NodeId) -> dict[str, object]:
    return {"kind": n.kind.value, "name": n.name}


def node_from_dict(d: dict[str, object]) -> NodeId:
    return NodeId(kind=NodeKind(_require_str(d, "kind")), name=_require_str(d, "name"))


def edge_to_dict(e: Edge) -> dict[str, object]:
    return {
        "downstream": node_to_dict(e.downstream),
        "upstream": node_to_dict(e.upstream),
    }


def edge_from_dict(d: dict[str, object]) -> Edge:
    raw_d = d.get("downstream")
    raw_u = d.get("upstream")
    if not isinstance(raw_d, dict) or not isinstance(raw_u, dict):
        raise TypeError("edge must have downstream + upstream objects")
    return Edge(downstream=node_from_dict(raw_d), upstream=node_from_dict(raw_u))


# ---------- bulk codecs ---------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_models(models: Iterable[Model]) -> str:
    return _dump(model_to_dict(m) for m in models)


def dump_edges(edges: Iterable[Edge]) -> str:
    return _dump(edge_to_dict(e) for e in edges)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_models(text: str) -> list[Model]:
    return [model_from_dict(d) for d in _iter_lines(text)]


def load_edges(text: str) -> list[Edge]:
    return [edge_from_dict(d) for d in _iter_lines(text)]


# ---------- project (model_name → sql) ----------------------------------


def project_to_json(project: dict[str, str]) -> str:
    """Round-trippable JSON dump of ``{model_name: sql_text}``."""
    return json.dumps(
        {"models": {k: project[k] for k in sorted(project)}},
        indent=2,
        ensure_ascii=False,
    )


def project_from_json(text: str) -> dict[str, str]:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError("project must be a JSON object")
    raw_models = parsed.get("models")
    if not isinstance(raw_models, dict):
        raise TypeError("project.models must be an object")
    out: dict[str, str] = {}
    for name, sql in raw_models.items():
        if not isinstance(name, str) or not isinstance(sql, str):
            raise TypeError("project.models entries must be str→str")
        out[name] = sql
    return out


__all__ = [
    "dump_edges",
    "dump_models",
    "edge_from_dict",
    "edge_to_dict",
    "load_edges",
    "load_models",
    "model_from_dict",
    "model_to_dict",
    "node_from_dict",
    "node_to_dict",
    "project_from_json",
    "project_to_json",
]
