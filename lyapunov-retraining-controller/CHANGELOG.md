# Changelog

## [0.1.0] — 2026-06-10

### Added
- Gaussian algebra core (`distributions.py`): sampling, MLE and
  unbiased fits with a degenerate-variance floor, closed-form KL,
  mixture moment matching.
- Exact one-step expectation map (`lyapunov.py`) for a retrain on a
  deterministic real/synthetic split: E[μ̂] and E[σ̂²] including the
  (1 − 1/n) MLE shrinkage and the w(1−w)Δμ² cross term, verified
  against Monte Carlo in tests.
- Generation-loop simulator with static / linear-drift / shock
  reference trajectories, probe-based monitoring, and real-data
  budget accounting that charges probes and the real share of every
  retrain.
- `LyapunovController`: trigger + deadbeat control law — skip while
  V̂ ≤ c/η, otherwise the smallest α with predicted V ≤ c. Every
  action satisfies the Foster–Lyapunov drift condition
  V_pred ≤ (1−η)V̂ + c, giving lim sup E[V] ≤ c/η (+ drift).
- Baselines: `FixedCadenceController` (the naïve policy under test)
  and `NeverRetrainController`.
- Paired-seed benchmark harness with stability (mean/max V, collapse
  rate), cost (real samples, retrains), and responsiveness (shock
  recovery) metrics; plain-text results table.
- CLI `lrcctl info | run | benchmark` with a V sparkline per episode.
- 70 tests including 4 Hypothesis properties; mypy `--strict` clean
  over 7 source files; ruff clean; zero runtime dependencies;
  multi-stage slim Docker image with non-root `lrc` user.

### Notes
- The first controller draft was proportional — choose the smallest α
  with V_pred ≤ (1−η)V̂ + c every step. It retrained ~130 times in
  200 drift steps and still tracked worse than fixed(k=5, α=0.5),
  because every retrain pays an O(1/n) fit-noise tax regardless of α.
  Rewrote as trigger + deadbeat (rare, decisive corrections); the
  drift guarantee is preserved since c ≤ (1−η)V̂ + c, and the
  controller now beats or ties every fixed cadence in all three
  regimes at lower budget.
- A single 32-sample probe made V̂'s noise floor (~0.03 nats) exceed
  the controller's trigger, causing phantom retrains under a static
  reference. Fixed by pooling the last 4 probes into the reference
  estimate — 4× lower noise floor for 4 steps of lag.
