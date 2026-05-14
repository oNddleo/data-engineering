# anti-money-laundering-graph

In-memory directed-multigraph engine + five classic AML pattern
detectors (fan-out, fan-in, layering chain, round-trip, structured
deposit) cho mạng lưới giao dịch liên ngân hàng Việt Nam.
Substitute Neo4j-style graph DB with zero deps — production swap
giữ nguyên contract.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Build a graph** — accounts are nodes, transactions are
   directed edges with `amount_vnd` + timestamp. Backed by two
   adjacency-list indexes (in / out) so both directions are O(1).
2. **Run 5 detectors** — each is a pure
   `(graph, **params) → list[AMLAlert]` function. Compose them in
   whatever order the pipeline wants.
3. **Score accounts** — aggregate alerts + a-priori `RiskFlag` bumps
   into a per-account risk score, then surface the top-N.

## The five patterns

| Pattern              | Topology                                                 | Severity |
| -------------------- | -------------------------------------------------------- | -------- |
| `FAN_OUT`            | One source → ≥N distinct destinations within a window     | WARN     |
| `FAN_IN`             | One destination ← ≥N distinct sources within a window     | WARN     |
| `LAYERING_CHAIN`     | Directed path of L hops where each step is ≤ τ apart      | CRIT     |
| `ROUND_TRIP`         | Cycle returning to origin after ≥1 intermediary           | CRIT     |
| `STRUCTURED_DEPOSIT` | ≥N just-under-threshold deposits to same destination     | WARN     |

`STRUCTURED_DEPOSIT` is the **per-recipient** view of structuring.
It's complementary to the per-initiator structuring rule in
[`napas-247-transaction-monitor`](../napas-247-transaction-monitor/)
— this one catches mule **collection** patterns where many small
deposits converge on a single account, whereas the real-time monitor
catches a single initiator splitting up one big transfer.

## Why in-memory and not Neo4j

This project is the *logic* of an AML pattern engine. The
`TransactionGraph` interface (`add_transaction`, `out_edges`,
`in_edges`, `window_out`, …) is narrow enough that every detector
in `patterns.py` works against any implementation of those methods.
Production deployments swap the in-memory backend for:

* **Neo4j** — same five Cypher queries express the same five
  patterns; the detector functions become `MATCH` queries.
* **Apache AGE** (Postgres extension) — for shops already running
  Postgres at scale.
* **TigerGraph / Amazon Neptune** — for very high-throughput
  workloads.

The pure-Python implementation in `graph.py` handles ~1M edges in
< 250 MB and answers per-account neighbor queries in O(1) — plenty
for educational use and small-bank pilots.

## Components

| Module              | Role                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| `amlgraph.schema`   | `Account`, `Transaction`, `RiskFlag`, `Channel`, `AccountType`              |
| `amlgraph.graph`    | `TransactionGraph` — in/out indexes + time-window helpers                  |
| `amlgraph.alerts`   | `AMLAlert`, `AlertKind`, `Severity`                                        |
| `amlgraph.patterns` | 5 detector functions (fan-out, fan-in, layering, round-trip, structured)   |
| `amlgraph.scoring`  | `score_accounts`, `top_n` — severity × kind multiplier + a-priori bumps    |
| `amlgraph.io_jsonl` | JSONL codec for accounts / txns / alerts                                   |
| `amlgraph.simulator`| Seeded synthetic graph with controllable pattern injection                 |
| `amlgraph.cli`      | `amlgraph info | simulate | detect | rank`                                 |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
amlgraph info

# 1) Generate a synthetic graph with one of each pattern injected.
amlgraph simulate \
  --accounts 30 --normal 60 \
  --fan-out 1 --fan-in 1 --layering 1 --round-trip 1 --structured 1 \
  --seed 42 \
  --output graph.json

# 2) Run all five detectors and emit alerts as JSONL.
amlgraph detect \
  --dataset graph.json \
  --output alerts.jsonl \
  --summary

# 3) Aggregate alerts into per-account scores and print the top-N.
amlgraph rank \
  --dataset graph.json \
  --alerts alerts.jsonl \
  --n 10
```

Sample end-to-end output on a graph with all five patterns injected:

```
$ amlgraph detect --dataset graph.json --output alerts.jsonl --summary
wrote 5 alerts to alerts.jsonl
Summary: 5 alerts — {'FAN_OUT': 1, 'FAN_IN': 1,
                     'LAYERING_CHAIN': 1, 'ROUND_TRIP': 1,
                     'STRUCTURED_DEPOSIT': 1}

$ amlgraph rank --dataset graph.json --alerts alerts.jsonl --n 5
ACC-37265167    112
ACC-54862057    112
ACC-00182633     56
ACC-07290222     56
ACC-12220297     56
```

(112 = primary in LAYERING_CHAIN + ROUND_TRIP, both CRIT.)

## Library

```python
from amlgraph import (
    TransactionGraph, generate, detect_fan_out, detect_fan_in,
    detect_layering_chains, detect_round_trips, detect_structured_deposits,
    score_accounts, top_n,
)

accounts, txns = generate(seed=42, inject_fan_out=2, inject_layering=1)
g = TransactionGraph()
for a in accounts: g.add_account(a)
for t in txns: g.add_transaction(t)

alerts = (
    detect_fan_out(g)
    + detect_fan_in(g)
    + detect_layering_chains(g)
    + detect_round_trips(g)
    + detect_structured_deposits(g)
)

scores = score_accounts(g, alerts)
for rank in top_n(scores, n=10):
    print(rank.account_id, rank.score)
```

## Detector knobs

Every detector is a pure function with tunable thresholds. The
defaults are tuned for **sensitivity on hand-crafted test cases**.
For production traffic at a bank's scale, raise the bars:

```python
detect_fan_out(g, min_distinct_dests=8, window_seconds=3600)
detect_fan_in(g, min_distinct_sources=8, window_seconds=3600)
detect_layering_chains(g, min_depth=5, hop_seconds=600, total_seconds=86_400)
detect_round_trips(g, max_depth=4, window_seconds=86_400)
detect_structured_deposits(g, threshold_vnd=10_000_000, margin_vnd=500_000,
                            min_count=4, min_distinct_sources=3)
```

## Risk scoring weights

```python
SEVERITY_POINTS = {INFO: 5, WARN: 25, CRIT: 75}
KIND_MULTIPLIER = {
    FAN_OUT: 1.0,    FAN_IN: 1.0,
    LAYERING_CHAIN: 1.5, ROUND_TRIP: 1.5,
    STRUCTURED_DEPOSIT: 1.2,
}
RISK_FLAG_POINTS = {
    PEP: 30,   SANCTIONED: 100,   MULE_SUSPECTED: 50,
    HIGH_RISK_JURISDICTION: 20,   PRIOR_SAR: 40,
}
```

Primary account gets full credit; related accounts get half credit
(they're implicated but not the centre). The whole formula is
deliberately transparent so analysts can debug why an account is
high-scoring.

## Quality

```bash
make test       # 98 tests, 4 Hypothesis properties
make type       # mypy --strict
make lint
```

- **98 tests** covering each pattern, the graph primitives, JSONL
  round-trips, the simulator, the CLI, and 4 Hypothesis properties
  (txn round-trips for any amount; account round-trips for any flag
  subset; graph add never raises for unique txn_ids; fan-out stays
  silent below threshold).
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `aml` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
