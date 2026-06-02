# napas-247-transaction-monitor

Real-time anomaly monitor cho NAPAS 247 instant inter-bank
transfer — phát hiện vi phạm Quyết định 2345/QĐ-NHNN (xác thực sinh
trắc học) cùng các pattern bất thường (velocity spike, structuring,
beneficiary blacklist).

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

Một event-time stream processor đơn giản nhưng đầy đủ:

1. **Ingest** một stream `Transaction` (NAPAS 247-shaped) từ JSONL
   trên stdin / file. Trong production, replay từ Kafka topic
   `napas-247.transactions` cùng schema này.
2. **Áp 4 rule** stateful per-account, deterministic theo
   `txn.occurred_at` (không dùng wall-clock — replay back-dated
   không cần mock):

   | Rule                  | Trigger                                                  | Severity |
   | --------------------- | -------------------------------------------------------- | -------- |
   | `BiometricRule`       | Decision 2345: txn > 10M VND không có biometric, hoặc cumulative > 20M VND/ngày | CRIT |
   | `VelocityRule`        | > N txns/window từ cùng 1 initiator account              | WARN     |
   | `StructuringRule`     | ≥ K txns trong dải 9.5M–10M VND trong cùng window        | WARN     |
   | `BlacklistRule`       | Beneficiary nằm trong blacklist (mule/sanctioned)        | CRIT     |

3. **Emit** một stream `Alert` (JSONL) với 5 kind:
   `BIO_REQUIRED_SINGLE_TXN`, `BIO_REQUIRED_CUMULATIVE`,
   `VELOCITY_SPIKE`, `STRUCTURING_SUSPECTED`, `BLACKLIST_HIT`.

State backend hiện tại là in-memory dict — production sẽ swap sang
Redis (cùng API thông qua `Rule` Protocol). Window logic là
event-time sliding window per-account, eviction lazy on consume.

## Decision 2345/QĐ-NHNN — chi tiết logic

Có hiệu lực từ **2024-07-01**. Hai threshold:

* **10 triệu VND/lần** — bất kỳ chuyển khoản nào > 10M VND đều
  phải xác thực sinh trắc học. Encode trong `Transaction.biometric_verified=True`.
* **20 triệu VND/ngày** — khi tổng cộng trong ngày của initiator
  account vượt 20M VND, mọi giao dịch tiếp theo (dù dưới 10M) đều
  phải xác thực sinh trắc học.

`BiometricRule` ngầm guarantee **không bao giờ emit cả 2 alert cho
cùng 1 txn**:

```
if amount > 10M and not biometric:
    -> BIO_REQUIRED_SINGLE_TXN
elif amount <= 10M and (daily_total_before + amount) > 20M and not biometric:
    -> BIO_REQUIRED_CUMULATIVE
```

Daily counter reset theo `occurred_at.date()` — đúng theo timezone
UTC+7.

## Components

| Module               | Role                                                                     |
| -------------------- | ------------------------------------------------------------------------ |
| `n247mon.schema`     | `Transaction`, `Channel`, `VN_TZ` + invariants                            |
| `n247mon.banks`      | NAPAS 6-digit BIN registry (`970418` → BIDV, etc.) + lookup helpers       |
| `n247mon.alerts`     | `AlertKind`, `Severity`, `Alert` dataclass                                |
| `n247mon.rules`      | `BiometricRule`, `VelocityRule`, `StructuringRule`, `BlacklistRule`       |
| `n247mon.engine`     | `MonitorEngine.consume()` + `EngineStats`                                 |
| `n247mon.io_jsonl`   | JSONL codec (round-trippable, type-checked)                               |
| `n247mon.simulator`  | seeded synthetic generator + anomaly injection                            |
| `n247mon.cli`        | `n247mon info | simulate | monitor`                                       |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
n247mon info

# 1) Generate a synthetic stream with anomalies seeded in.
n247mon simulate \
  --txns 1000 \
  --seed 42 \
  --inject bio_single,bio_cumulative,velocity,structuring \
  --output stream.jsonl

# 2) Run the monitor with a beneficiary blacklist.
echo "BAD-ACCOUNT-001" > blacklist.txt
n247mon monitor \
  --input stream.jsonl \
  --blacklist blacklist.txt \
  --velocity-window 60 \
  --velocity-threshold 10 \
  --output alerts.jsonl \
  --summary

# 3) Or pipe directly:
n247mon simulate --txns 100 --inject velocity | n247mon monitor --summary
```

Sample summary (on synthetic 30-txn stream with all 4 anomaly kinds injected):

```
Summary: 52 txns -> 12 alerts
  by kind:     {'BIO_REQUIRED_SINGLE_TXN': 4, 'BIO_REQUIRED_CUMULATIVE': 2,
                'VELOCITY_SPIKE': 5, 'STRUCTURING_SUSPECTED': 1}
  by severity: {'CRIT': 6, 'WARN': 6}
```

## Library

```python
from n247mon import (
    BiometricRule, VelocityRule, StructuringRule, BlacklistRule,
    MonitorEngine, generate,
)

engine = MonitorEngine(rules=[
    BiometricRule(),
    VelocityRule(window_seconds=60, threshold=10),
    StructuringRule(window_seconds=3600, min_count=3),
    BlacklistRule({"BAD-ACCOUNT-001"}),
])

for alert in engine.consume_many(generate(n_txns=1000, seed=42, inject_anomalies=["velocity"])):
    print(alert.severity.value, alert.kind.value, alert.account, alert.detail)

print(engine.stats)
```

## NAPAS BIN registry

`n247mon.banks.BIN_TO_BANK` ships a curated subset of the official
6-digit NAPAS BIN list — the 30+ member banks that handle ~99 % of
247 retail volume (Vietcombank `970436`, BIDV `970418`, MB Bank
`970422`, Techcombank `970407`, VPBank `970432`, etc.). Use
`is_valid_bin()` to validate inbound messages.

## Production deployment

In production this becomes a Flink / Kafka Streams job. The pieces
that change:

* **Input** — `KafkaConsumer("napas-247.transactions")` instead of
  JSONL file. The `Transaction` schema stays the same; Avro/Protobuf
  is recommended for the wire format.
* **State** — replace each rule's `dict` with a Redis hash (for
  daily-cumulative counters) and a Redis sorted set per account
  (for sliding-window deques). The `Rule` Protocol stays the same.
* **Output** — `KafkaProducer("napas-247.alerts")` writing the
  same `Alert` JSON shape; downstream consumers route to PagerDuty,
  Slack, the fraud-review queue, or the data warehouse.

The reference impl is single-process Python because that keeps the
logic readable. Replace each I/O boundary with the real thing and the
core stays untouched.

## Quality

```bash
make test       # 93 tests, 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **93 tests** including 6 Hypothesis properties (any > 10M txn
  without bio fires SINGLE; ≤ 10M with bio never fires; blacklist
  fires iff member; velocity stays silent at-or-below threshold;
  JSONL round-trips; engine stats == alert count).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `n247` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
