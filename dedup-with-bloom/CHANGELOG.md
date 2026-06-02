# Changelog

## 0.1.0

Initial release.

* `BloomParams.for_capacity(n, fpr)` — optimal sizing calculator
  (rounded to byte boundary).
* `BloomFilter` — bit array with SHA-256/MD5 double hashing,
  byte-level storage, `add`/`__contains__`/`update`, `to_bytes`/
  `from_bytes` serialisation, `fill_ratio` saturation indicator.
* `dedup_stream` / `dedup_iter` — eager and lazy stream
  deduplicators with `DedupStats` accounting.
* `simulator.generate` — deterministic stream with controllable
  duplication rate.
* `bloomdedup` CLI: `info | params | dedup | simulate`.
* Hypothesis property tests: no false negatives, kept-records-unique,
  kept-subset-of-input, stats consistency.
