"""Extract ``ref()`` / ``source()`` calls from raw SQL files.

The parser is a **deliberately simple regex pass**:

* ``{{ ref('model_name') }}`` → model dependency
* ``{{ ref("model_name") }}`` → same (double quotes ok)
* ``{{ source('schema', 'table') }}`` → source dependency
* ``{{ ref('m1', v=2) }}`` → ignored (dbt versioned refs not modelled)

Comment handling:

* ``-- ... \\n``  — line comment; stripped before parsing.
* ``/* ... */``  — block comment; stripped before parsing.
* ``{# ... #}``  — dbt-Jinja comment; stripped before parsing.

This is enough for the lineage analysis we care about — the toolkit
isn't a full SQL parser. We don't try to handle quoting inside
comments inside strings; production callers either keep their
``ref()`` calls in plain code or layer sqlglot on top.

The parser **deduplicates** refs and sources per model — three
``{{ ref('orders') }}`` calls in a model produce one ``"orders"``
entry, not three. Edge multiplicity in lineage is meaningless.
"""

from __future__ import annotations

import re

from dbtlin.schema import Model

# ---------- comment stripping ---------------------------------------------

_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


def strip_comments(sql: str) -> str:
    """Strip SQL line / block / Jinja comments. Stable round-trip not guaranteed."""
    sql = _JINJA_COMMENT_RE.sub("", sql)
    sql = _BLOCK_COMMENT_RE.sub("", sql)
    sql = _LINE_COMMENT_RE.sub("", sql)
    return sql


# ---------- ref / source extraction --------------------------------------

# Matches: {{ ref('name') }}  or  {{ ref("name") }}
# Also tolerates extra whitespace + optional version arg (dbt >= 1.6),
# which we ignore for lineage purposes.
_REF_RE = re.compile(
    r"""
    \{\{                          # opening
        \s* ref \s* \(
            \s* (?P<q>['"]) (?P<name>[^'"]+) (?P=q)
            \s* (?: , [^)]* )?    # optional extra args, e.g. v=2
        \s* \)
    \s* \}\}                      # closing
    """,
    re.VERBOSE | re.MULTILINE,
)

# Matches: {{ source('schema', 'table') }}
_SOURCE_RE = re.compile(
    r"""
    \{\{
        \s* source \s* \(
            \s* (?P<q1>['"]) (?P<schema>[^'"]+) (?P=q1)
            \s* , \s*
            (?P<q2>['"]) (?P<table>[^'"]+) (?P=q2)
        \s* \)
    \s* \}\}
    """,
    re.VERBOSE | re.MULTILINE,
)


def extract_refs(sql: str) -> tuple[str, ...]:
    """Deduplicated ordered tuple of model names referenced by this SQL."""
    cleaned = strip_comments(sql)
    seen: dict[str, None] = {}
    for m in _REF_RE.finditer(cleaned):
        seen[m.group("name")] = None
    return tuple(seen)


def extract_sources(sql: str) -> tuple[tuple[str, str], ...]:
    """Deduplicated ordered tuple of ``(schema, table)`` source pairs."""
    cleaned = strip_comments(sql)
    seen: dict[tuple[str, str], None] = {}
    for m in _SOURCE_RE.finditer(cleaned):
        seen[(m.group("schema"), m.group("table"))] = None
    return tuple(seen)


def parse_model(name: str, sql: str, path: str = "") -> Model:
    """Build a populated ``Model`` from one SQL file."""
    return Model(
        name=name,
        sql=sql,
        refs=extract_refs(sql),
        sources=extract_sources(sql),
        path=path,
    )


def parse_project(models: dict[str, str]) -> list[Model]:
    """Parse a whole project: ``{model_name: sql_text}`` → list of populated Models.

    Output is sorted by model name for stable diffs.
    """
    return [parse_model(name, sql) for name, sql in sorted(models.items())]


__all__ = [
    "extract_refs",
    "extract_sources",
    "parse_model",
    "parse_project",
    "strip_comments",
]
