# schema-registry-evolution

Schema evolution toolkit for JSON / Avro / Protobuf-shaped streaming
schemas. Diffs `(old, new)` pairs → list of typed `FieldChange`s →
**BACKWARD / FORWARD / FULL / NONE** compatibility verdicts per the
Confluent Schema Registry taxonomy → semver bump suggestion +
next-version computation.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Models a flat record schema** — a deliberately-minimal subset
   of JSON Schema + Avro that captures only what affects wire
   compatibility: field name, primitive type, required/optional,
   default value, aliases. (Nested records flatten before feeding
   in; logical types collapse to their wire primitives.)
2. **Diffs two schemas** — alias-aware so a field renamed via an
   alias is one `ALIAS_ADDED`, not a `REMOVED` + `ADDED` pair.
   Output sorted by `(kind, field_name)` for stable PR diffs.
3. **Classifies each change** as safe or breaking under each
   compatibility mode:
   - **BACKWARD** — new schema can read data written by old.
   - **FORWARD** — old schema can read data written by new.
   - **FULL** — both BACKWARD and FORWARD.
   - **NONE** — no check.
4. **Suggests a semver bump** — `MAJOR` for any BACKWARD-breaking
   change, `MINOR` for safe additions / type widenings, `PATCH` for
   default-only tweaks. `next_version("1.2.3", BumpKind.MINOR) →
   "1.3.0"`.
5. **CI-friendly exit codes** — `schemaev compat` exits 2 when
   incompatible, 0 otherwise. Drop into a CI step on every schema PR.

## Confluent compatibility taxonomy

| Mode      | Meaning                                                       |
| --------- | ------------------------------------------------------------- |
| NONE      | No checks.                                                    |
| BACKWARD  | New schema can read data written by old schema. Default for most consumers. |
| FORWARD   | Old schema can read data written by new schema. Use for producers updated ahead of consumers. |
| FULL      | Both BACKWARD and FORWARD compatible.                         |

### Type promotion graph (per Avro 1.11 spec)

Safe widenings (BACKWARD compatible):
- `int → long, float, double`
- `long → float, double`
- `float → double`
- `string ↔ bytes` (bidirectional)

Any other type transition is BACKWARD-breaking.

### Field-change classification

| Change             | BACKWARD safe?           | FORWARD safe?             |
| ------------------ | ------------------------ | ------------------------- |
| ADDED required, no default | ✗                | ✓ (old ignores it)        |
| ADDED with default | ✓                        | ✓                         |
| REMOVED            | ✓ (new ignores leftover) | only if had default       |
| TYPE widened       | ✓                        | ✗                         |
| TYPE narrowed      | ✗                        | ✓                         |
| TYPE incompatible  | ✗                        | ✗                         |
| required → optional| ✓                        | ✓ if originally required  |
| optional → required| ✗                        | ✓                         |
| DEFAULT changed    | ✓                        | ✓                         |
| ALIAS added        | ✓                        | ✓                         |

## Components

| Module                | Role                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `schemaev.schema`     | `Schema`, `Field`, `FieldType`, `FieldChange`, `Compatibility`, `CompatibilityReport` |
| `schemaev.diff`       | `diff(old, new) → list[FieldChange]` — alias-aware                  |
| `schemaev.compat`     | `check_backward`, `check_forward`, `check_full`, `check(mode)`      |
| `schemaev.versioning` | `suggest_bump(changes) → BumpKind`, `next_version(current, bump)`   |
| `schemaev.simulator`  | Seeded `(old, new)` pairs covering 9 named mutations                |
| `schemaev.io_json`    | JSON codec for Schema + CompatibilityReport                          |
| `schemaev.cli`        | `schemaev info \| simulate \| diff \| compat \| bump \| summary`     |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
schemaev info
schemaev simulate --mutation safe_add --out-dir ./pair
schemaev diff     --old ./pair/old.json --new ./pair/new.json
schemaev compat   --old ./pair/old.json --new ./pair/new.json --mode BACKWARD
schemaev compat   --old ./pair/old.json --new ./pair/new.json --mode FULL --json
schemaev bump     --old ./pair/old.json --new ./pair/new.json
schemaev summary  --old ./pair/old.json --new ./pair/new.json
```

Mutations the simulator supports (for testing your own pipeline):

```
safe_add  required_add  remove_optional  remove_required  widen_type
narrow_type  rename_with_alias  required_to_optional  optional_to_required
```

Sample `summary` for a `safe_add` mutation:

```json
{
  "old_version": "1.0.0",
  "new_version": "1.1.0",
  "n_changes": 1,
  "kinds": {"ADDED": 1},
  "compatibility": {
    "BACKWARD": true,
    "FORWARD": true,
    "FULL": true
  },
  "suggested_bump": "minor",
  "suggested_next_version": "1.1.0"
}
```

Sample `compat` on a BACKWARD-breaking change (exits 2):

```
✗ INCOMPATIBLE under BACKWARD

Breaking (1):
  [ADDED] store_id: field 'store_id' added

Safe (0):
```

## Library

```python
from schemaev.compat     import check_backward, check_full
from schemaev.diff       import diff
from schemaev.schema     import Compatibility, Field, FieldType, Schema
from schemaev.versioning import next_version, suggest_bump

old = Schema(name="Order", version="1.0.0", fields=(
    Field(name="order_id", type=FieldType.STRING),
    Field(name="amount", type=FieldType.INT),
))
new = Schema(name="Order", version="1.0.0", fields=(
    Field(name="order_id", type=FieldType.STRING),
    Field(name="amount", type=FieldType.LONG),   # widened
))

changes = diff(old, new)                          # [TYPE_CHANGED]
print(check_backward(old, new).is_compatible)     # True (widening)
print(check_full(old, new).is_compatible)         # False (forward broken)

bump = suggest_bump(changes)                      # BumpKind.MINOR
print(next_version(old.version, bump))            # "1.1.0"
```

## Key design decisions

- **Flat schema model**, not full JSON Schema. Nested records, refs,
  oneOf — none of them affect wire compatibility at the field level
  the way primitive type promotions do. Production callers flatten
  before feeding in.
- **Alias-aware diffing.** A field renamed via an alias is `ALIAS_ADDED`,
  not `REMOVED + ADDED`. Catches the most common Avro rename pattern.
- **Conservative compatibility classification.** Anything whose
  safety depends on data values (e.g. long → int when "data fits")
  is treated as breaking. Production callers who know their data
  override on a case-by-case basis.
- **MAJOR is escalated by ANY BACKWARD-breaking change.** A mixed
  diff with one MAJOR + one MINOR change becomes MAJOR — the spirit
  of semver. We never silently downgrade a breaking change to a
  warning.
- **NONE mode always returns compatible.** Matches Confluent's
  behaviour — useful for greenfield schemas that haven't stabilised.
- **CompatibilityReport carries both breaking and safe changes** —
  dashboards can show the full picture without re-running the diff.

## Quality

```bash
make test       # 87 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **87 tests**, 0 failing; 6 Hypothesis properties (self-diff is
  always empty; a schema is always self-compatible; self-bump is
  always NONE; parse/render semver round-trips; MAJOR/MINOR/PATCH
  bumps reset lower components correctly; diff output is always
  sorted).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `schemaev` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
