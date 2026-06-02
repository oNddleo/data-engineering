# dbt-model-lineage-graph

Parse dbt SQL files for `{{ ref() }}` and `{{ source() }}` calls →
directed lineage graph → cycle detection (Tarjan) + topological sort
(Kahn) + upstream/downstream impact analysis. No sqlglot, no graphviz
— pure-Python regex parsing + stdlib graph algorithms.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Parses SQL** — strips line / block / Jinja comments, then
   extracts every `{{ ref('name') }}` and
   `{{ source('schema', 'table') }}` call. Versioned refs
   (`ref('m', v=2)`) are tolerated; the version is ignored for
   lineage purposes.
2. **Builds a DAG** — models become MODEL nodes, sources become
   SOURCE nodes, refs and source calls become directed edges
   (`downstream → upstream`).
3. **Detects cycles** via Tarjan's SCC algorithm. Reports each SCC
   of size ≥ 2 plus any self-edges as a `CycleReport`.
4. **Topological sort** via Kahn's algorithm — sources first,
   leaves last, ties broken by `NodeId.label`. Raises if the graph
   has cycles.
5. **Impact analysis** — BFS upstream / downstream from a target
   model. Answers "if I change `raw_orders`, what breaks?" and
   "what feeds into `fact_revenue`?"

## Why no sqlglot?

The toolkit is **zero runtime dependencies** like every other repo
in this catalogue. A regex parser for `ref()` / `source()` is enough
because that's what dbt itself uses to discover dependencies at
compile time — the calls are Jinja templating, not SQL.

Edge cases the regex parser handles:

* Single OR double quotes inside the call (`ref('x')` and `ref("x")`).
* Arbitrary whitespace between the braces, `ref`, `(`, name, `)`.
* Versioned refs (`ref('m', v=2)`) — extract the name only.
* Comments — line (`--`), block (`/* */`), and Jinja (`{# #}`)
  comments are stripped before parsing.
* Deduplication — three `{{ ref('orders') }}` calls in the same
  model produce one edge, not three.

What it deliberately doesn't handle:

* Macros that wrap `ref()` (e.g. `{{ my_macro('x') }}` expanding to
  `ref(x)`) — production callers preprocess via dbt's `parse` step
  if they use macro wrappers.
* Strings literally containing `{{ ref(...) }}` text — caught by
  the parser as a false positive. Production callers don't do this.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `dbtlin.schema`    | `Model`, `NodeId`, `NodeKind`, `Edge`, `CycleReport`, `ImpactReport`|
| `dbtlin.parser`    | `strip_comments`, `extract_refs`, `extract_sources`, `parse_project`|
| `dbtlin.graph`     | `build_graph`, `find_cycles`, `topological_order`, `roots`, `leaves`|
| `dbtlin.impact`    | `upstream_of`, `downstream_of`, `impact`, `impact_by_name`          |
| `dbtlin.simulator` | Seeded synthetic dbt project (Vietnamese-themed staging/int/mart)    |
| `dbtlin.io_jsonl`  | JSON codec for projects; JSONL codec for models + edges              |
| `dbtlin.cli`       | `dbtlin info \| simulate \| parse \| graph \| topo \| cycles \| impact \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
dbtlin info
dbtlin simulate  --seed 7 --output ./project.json    # synthetic Shopee-themed project
dbtlin simulate  --cycle --seed 7 --output ./bad.json # with cycle injected for testing
dbtlin parse     --input ./project.json --output ./models.jsonl
dbtlin graph     --input ./project.json --output ./edges.jsonl --show 5
dbtlin topo      --input ./project.json               # sources first → leaves last
dbtlin cycles    --input ./project.json               # exits 2 if any cycle
dbtlin impact    --input ./project.json --target stg_orders
dbtlin summary   --input ./project.json               # JSON roll-up
```

Sample `graph` output:

```
15 nodes, 15 edges

Roots (4):
  SOURCE:shopee.raw_inventory
  SOURCE:shopee.raw_orders
  SOURCE:shopee.raw_returns
  SOURCE:shopee.raw_users

Leaves (4):
  MODEL:dim_customer
  MODEL:dim_customer_extras
  MODEL:fact_returns_daily
  MODEL:fact_revenue_daily
```

Sample `impact --target stg_orders`:

```
Target: MODEL:stg_orders

Upstream (1):
  SOURCE:shopee.raw_orders

Downstream (6):
  MODEL:dim_customer
  MODEL:fact_returns_daily
  MODEL:fact_revenue_daily
  MODEL:int_order_items
  MODEL:int_return_summary
  MODEL:int_user_first_buy

Total affected: 7
```

Sample `cycles` on a cycle-injected project (exits 2):

```
Cycles found: 1
  MODEL:fact_revenue_daily → MODEL:int_revenue_loop
```

## Library

```python
from dbtlin.parser     import parse_project
from dbtlin.graph      import build_graph, find_cycles, topological_order
from dbtlin.impact     import impact_by_name

project = {
    "stg_orders":      "select * from {{ source('shopee', 'raw_orders') }}",
    "fact_revenue":    "select * from {{ ref('stg_orders') }}",
}
models = parse_project(project)
graph  = build_graph(models)

assert find_cycles(graph) == []
order  = topological_order(graph)          # sources → staging → marts
report = impact_by_name(graph, "stg_orders")  # who breaks if I change it
```

## Key design decisions

- **Regex parser for `ref()` / `source()`**, not a full SQL parser.
  dbt itself does the same at compile time — the calls are Jinja
  templating, not SQL syntax. Zero deps, ~50 lines of code, handles
  every edge case the toolkit needs.
- **`NodeId` is a composite `(kind, name)`** — MODEL nodes can
  coexist with SOURCE nodes of the same name without collision.
- **Tarjan SCC for cycle detection**, not naive DFS. Reports all
  cycles in one pass; produces stable component lists.
- **Kahn topological sort**, not DFS-postorder. Easier to make
  tie-breaking deterministic — we sort the frontier alphabetically
  by label.
- **`downstream → upstream` edge direction** — matches dbt's
  `depends_on` convention. `roots()` returns no-upstream nodes
  (typically SOURCEs); `leaves()` returns no-downstream (mart-layer).
- **Impact analysis excludes the target itself** — answering "what
  else is affected" rather than "what's involved including X".
- **CI-friendly exit codes**: `cycles` and `topo` exit 2 when cycles
  exist, 0 otherwise. Pipelines consume this directly.

## Quality

```bash
make test       # 77 tests + 8 Hypothesis properties
make type       # mypy --strict
make lint
```

- **77 tests**, 0 failing; 8 Hypothesis properties (acyclic models
  yield no cycles, topo sort is total over nodes, topo sort respects
  every edge, roots and leaves are disjoint except for isolated
  nodes, `upstream_of` is a subset of topo predecessors,
  `downstream_of` is a subset of topo successors, self-refs always
  produce a cycle).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `dbtlin` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
