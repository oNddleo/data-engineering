# Changelog

## [0.1.0] — 2026-05-17

### Added
- `NodeId` composite identifier `(kind, name)` where `kind` is
  `MODEL` or `SOURCE`; SOURCE names enforce `schema.table` form.
- `Model`, `Edge`, `CycleReport`, `ImpactReport` frozen-slots
  dataclasses with validation at construction.
- `strip_comments(sql)` removes SQL line (`--`), block (`/* */`),
  and dbt Jinja (`{# #}`) comments before ref/source extraction.
- `extract_refs(sql)` — regex parser for `{{ ref('name') }}` and
  `{{ ref("name") }}` with tolerance for whitespace + versioned-ref
  arguments (`ref('m', v=2)`). Deduplicates within a model.
- `extract_sources(sql)` — same for `{{ source('schema', 'table') }}`.
- `parse_model(name, sql)` + `parse_project({name: sql})` — bulk
  parsing returning populated `Model` records, sorted by name.
- `LineageGraph` adjacency-list container with `upstream_of` and
  `downstream_of` indexes for O(1) edge lookup in either direction.
- `build_graph(models)` constructs the DAG from parsed models;
  MODEL and SOURCE nodes are created on demand from refs.
- `find_cycles(graph)` — Tarjan's SCC algorithm. Reports every SCC
  of size ≥ 2 plus all self-edges as `CycleReport`s.
- `topological_order(graph)` — Kahn's algorithm. Sources first,
  leaves last, ties broken by `NodeId.label` for stable diffs.
  Raises `ValueError` if any cycle exists.
- `roots(graph)` + `leaves(graph)` — nodes with no upstream / no
  downstream respectively.
- `upstream_of(graph, target)` + `downstream_of(graph, target)` —
  BFS in each direction; both exclude the target itself.
- `impact(graph, target)` + `impact_by_name(graph, model_name)` —
  build an `ImpactReport` with both directions.
- Seeded synthetic dbt project (`simulator.generate`) producing
  realistic Vietnamese-themed staging → intermediate → mart layers
  (Shopee-context: raw_orders, raw_users, raw_returns sources;
  stg_*/int_*/fact_*/dim_* models). `inject_cycle=True` adds a
  deliberate loop for cycle-detection tests.
- Type-checked JSON codec for projects (`project_to_json` /
  `project_from_json`) + JSONL codec for models + edges.
- CLI `dbtlin info | simulate | parse | graph | topo | cycles |
  impact | summary` with CI-friendly exit codes (`cycles` and
  `topo` exit 2 when cycles exist, 0 otherwise).
- 77 tests + 8 Hypothesis properties:
  - acyclic models always yield no cycles
  - topo sort is total over the node set
  - topo sort respects every edge (upstream before downstream)
  - roots and leaves are disjoint except for isolated nodes
  - `upstream_of` is a subset of topo predecessors
  - `downstream_of` is a subset of topo successors
  - any self-ref produces exactly one detected cycle
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `dbtlin` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The regex parser tolerates `ref('m', v=2)` versioned refs (dbt
  1.6+) and extracts the model name only. The version doesn't
  affect lineage — same model, same downstream blast radius.
- Self-loops are surfaced as `CycleReport(cycle=(n, n))` — a
  two-element tuple even though it's one node. The schema validates
  that any `CycleReport` has at least 2 entries so this represents
  cleanly without a separate `SelfLoopReport` type.
- Comments inside string literals are still stripped (e.g.
  `'foo -- not a comment'` loses the trailing text). Documented
  limitation; production callers don't write SQL that depends on
  string-literal comment payloads.
