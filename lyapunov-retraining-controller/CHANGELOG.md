# Changelog

## [0.2.0] — 2026-06-10

### Added
- KL-regularization knob beta: `fit_regularized` treats the previous
  model as beta pseudo-samples (MAP with a conjugate prior); plumbed
  through `RetrainAction`, the simulator, and the one-step map.
- Noise-aware `expected_v`: certainty-equivalent KL plus the two
  leading noise terms (Var[mu_hat]/(2*sigma_r^2),
  Var[sigma2_hat]/(4*sigma_ce^4)). At calibration they sum to ~1/n,
  independently confirming the v0.1 slack default c = 2/n. Without
  this map a controller would never rationally choose beta > 0.
- `DriftPlusPenaltyController` (Neely-style): per-step argmin of
  [E[V_next] - V_hat] + lam * real-samples over an (alpha, beta)
  grid. lam sweeps the cost-stability Pareto frontier; every fixed
  cadence is strictly dominated by the dpp curve, and the deadbeat
  Lyapunov controller sits on it (~ the lam = 2e-4 point).
- `FixedCadenceController` gained a beta parameter for the ablation.
- CLI `lrcctl frontier` (lam sweep) plus `--lam` / `--beta` flags on
  run and benchmark; dpp row in the benchmark table.
- 27 new tests (97 total, 5 Hypothesis properties).

### Findings
- beta rescues the naive dense dilute cadence when static (mean V
  0.0239 -> 0.0074) and cripples it after a shock (recovery 20 -> 59
  steps): damping is regime-dependent, not a free win.
- The dpp optimizer discovers that boundary itself: at lam = 2e-4
  (rare decisive retrains) it never uses beta; at lam = 1e-5
  (frequent small corrections) almost every retrain is damped.
  Pinned as a test.
- dpp(lam=2e-4) ties or beats the deadbeat law in all three regimes
  and recovers from a shock in ~1 step.

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
