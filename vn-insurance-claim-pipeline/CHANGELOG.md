# Changelog

## 0.1.0

Initial release.

* `CardClass` / `HospitalTier` / `CareType` enums for BHYT scheme.
* `Claim` frozen dataclass with loose ICD-10 shape validation.
* `payout.compute` — base coverage × out-of-network multiplier with
  emergency override.
* `simulator.generate` — deterministic synthetic claim generator
  with realistic tier / care-type weighting.
* `vnbhyt` CLI: `info | payout | simulate`.
* JSONL codec for `Claim` and `Payout`.
* Hypothesis property tests for payout+copay=billed conservation,
  in-network ≥ out-of-network, and emergency=in-network overrides.
