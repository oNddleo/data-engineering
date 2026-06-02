# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Schema`, `Field`, `FieldType`, `FieldChange`, `CompatibilityReport`
  frozen-slots dataclasses modelling a flat record schema (subset
  of JSON Schema + Avro that captures only wire-compatibility-affecting
  attributes).
- `FieldType` enum with the seven primitive wire types: STRING,
  INT, LONG, FLOAT, DOUBLE, BOOL, BYTES.
- `Compatibility` enum mirroring Confluent's taxonomy: NONE,
  BACKWARD, FORWARD, FULL.
- Field-name validation: alphanumeric + underscore only (rejects
  spaces / dashes / unicode).
- Alias support on `Field` — multiple historical names per field,
  enables alias-aware diffing.
- `Schema.field_named(name_or_alias)` looks up by current name or
  any alias.
- `diff(old, new)` — alias-aware. Output sorted by `(kind, field_name)`
  for stable PR diffs. Six change kinds: ADDED, REMOVED,
  TYPE_CHANGED, REQUIRED_CHANGED, DEFAULT_CHANGED, ALIAS_ADDED.
- Type-promotion table per Avro 1.11 spec: int → long, float, double;
  long → float, double; float → double; string ↔ bytes (bidirectional).
- `check_backward(old, new)` — "new schema can read old data".
  Adding required field without default ⇒ BACKWARD-breaking;
  type narrowing ⇒ BACKWARD-breaking; optional→required ⇒
  BACKWARD-breaking.
- `check_forward(old, new)` — "old schema can read new data".
  Removing required field without default ⇒ FORWARD-breaking;
  type widening ⇒ FORWARD-breaking.
- `check_full(old, new)` — both directions must pass.
- `check(old, new, mode)` dispatcher with `Compatibility.NONE` as
  the always-compatible escape hatch.
- `suggest_bump(changes) → BumpKind` — MAJOR for any BACKWARD-breaking
  change; MINOR for safe additions / widenings; PATCH for default-only
  changes; NONE for no changes.
- `parse_semver` + `render_semver` + `next_version(current, bump)`.
- `BumpKind.MAJOR` dominates: any combination of changes that includes
  a BACKWARD-breaking one produces MAJOR even if other changes are
  trivial.
- Seeded `simulator.generate_pair(mutation)` producing `(old, new)`
  pairs for 9 named mutations: safe_add, required_add, remove_optional,
  remove_required, widen_type, narrow_type, rename_with_alias,
  required_to_optional, optional_to_required.
- Hand-editable JSON codec (`schema_to_json` / `schema_from_json`)
  with pretty-printed `indent=2` output for clean PR diffs.
- `parse_compatibility(name)` — case-insensitive mode parser for CLI args.
- CLI `schemaev info | simulate | diff | compat | bump | summary`
  with CI-friendly exit codes (`compat` exits 2 when incompatible,
  0 otherwise).
- 87 tests + 6 Hypothesis properties:
  - self-diff is always empty
  - self-compatibility is always true (BACKWARD + FORWARD)
  - self-bump is always NONE
  - parse_semver / render_semver round-trip
  - MAJOR/MINOR/PATCH bumps reset lower components correctly
  - diff output is always sorted by (kind, field_name)
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `schemaev` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The type-promotion graph follows the **Avro spec**, not the JSON
  Schema spec. JSON Schema treats integers as numbers (no width
  distinction); Avro's int/long/float/double distinction matches how
  Kafka/Pulsar consumers actually deserialize. Production callers
  using pure JSON Schema can override the graph or simply treat all
  numerics as the widest type.
- `suggest_bump` for a removed required field is **MINOR**, not MAJOR
  — because removing a field is BACKWARD-safe (the new reader just
  ignores the extra column). Production teams who treat any field
  removal as a major version bump can layer their own rule on top.
- An earlier Hypothesis strategy generated all-underscore field names
  (e.g. `"_"`, `"__"`) which the `Field.name` validator correctly
  rejected. Tightened the strategy to require the first character
  be a letter — the validator behaviour stays unchanged, just the
  test generator got smarter.
