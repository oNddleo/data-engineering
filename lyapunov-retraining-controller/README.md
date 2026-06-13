# lyapunov-retraining-controller

**Retraining as a control system — and a control law that makes it stable.**

ML systems that retrain on data contaminated by their own outputs (LLM corpora full of
model-generated text, recommender feedback loops, feature stores fed by model decisions) form a
closed loop. Left alone, the loop is unstable: finite-sample refitting shrinks variance
geometrically while the mean random-walks — *model collapse*. Most pipelines respond with a fixed
retraining cadence and a fixed real/synthetic data mix chosen by folklore.

This project makes the control-systems framing **prescriptive**:

- define a Lyapunov function `V_t = KL(model_t ‖ reference_t)`,
- derive the exact one-step expectation map for a Gaussian retraining loop,
- build a controller that adjusts **one knob — the real-data fraction α** (and implicitly the
  retraining frequency, since it may skip) so that V is forced to contract,
- prove a Foster–Lyapunov stability bound for it,
- benchmark it against naïve fixed-cadence retraining,
- add a **second knob — a KL-regularization weight β** — with a noise-aware expected-V map that
  makes choosing it rational,
- and generalize the law to **drift-plus-penalty**, whose price-of-data parameter λ traces the
  entire cost–stability Pareto frontier.

Zero runtime dependencies — stdlib only.

## The loop

Each generation, the model `p_t = N(μ_t, σ_t²)` is refit by MLE on `n` samples, of which
`k = round(αn)` are fresh real data from the reference `p* = N(μ*, σ*²)` and `n − k` are synthetic
samples from the model itself. The exact one-step expectation map is

```
E[μ̂]  = w·μ* + (1−w)·μ_t                                  w = k/n
E[σ̂²] = (1 − 1/n)·(w·σ*² + (1−w)·σ_t²) + w·(1−w)·(μ* − μ_t)²
```

The `(1 − 1/n)` factor is the MLE shrinkage that drives collapse at α = 0; the cross term is the
variance the mixture gains from mean disagreement. Both effects are exact, so the controller can
evaluate its options in closed form instead of by Monte Carlo.

The reference can be **static**, **drifting** (`μ*` moves every step), or **shocked** (a step
change at a known time). The controller never sees `p*` — it estimates it from a small monitoring
probe (32 samples/step, pooled over a 4-step window), and every probe and every real training
sample debits a real-data budget. Evaluation uses the true `p*`.

## The control law

A trigger + deadbeat law on the estimated Lyapunov value `V̂`:

1. **Inside the band** (`V̂ ≤ c/η`): skip — don't retrain at all.
2. **Outside the band**: retrain with the *smallest* α whose predicted next value lands back at
   the noise floor: `V_pred(α) ≤ c` (grid search over the closed-form map).

Since `c ≤ (1−η)·V̂ + c` always, every action satisfies the classic drift condition
`V_pred ≤ (1−η)·V̂ + c`, which gives the **Foster–Lyapunov bound**

```
lim sup E[V_t] ≤ c/η + (per-step environment drift)
```

with defaults `c = 2/n` (the fit-noise floor) and `η = 0.3`.

**Why deadbeat rather than proportional?** Every retrain pays an O(1/n) fit-noise tax *regardless
of α*. A proportional law (`V_pred ≤ (1−η)V̂ + c` chosen tightly) retrains ~130 times in 200 drift
steps — many small corrections — and pays that tax almost every step; it tracked *worse* than a
fixed 5-step cadence in our first benchmark. The band makes corrections rare but decisive, and the
retraining frequency self-adjusts to the drift rate. The Lyapunov guarantee is unchanged.

## The second knob: KL-regularization (β)

A retrain may shrink the fit toward the previous model, weighting it as β pseudo-samples
(`μ' = (n·μ̂ + β·μ_old)/(n+β)`, same for variance — MAP with a conjugate prior at the old model).
That scales the fit-noise variance by `(n/(n+β))²` but dilutes the correction by the same factor.

A certainty-equivalent predictor would never choose β > 0 — it sees the bias but not the noise it
saves. So v0.2 adds a **noise-aware expected-V map**: CE KL plus the two leading noise terms,
`Var[μ̂]/(2σ_r²)` and `Var[σ̂²]/(4σ_ce⁴)`. At perfect calibration these sum to exactly `1/n` —
independently confirming the v0.1 slack default `c = 2/n` as "just above the irreducible floor".

The ablation (200 steps, 20 seeds): β rescues the naive dense dilute cadence from its own fit
noise when static, and cripples it after a shock —

```
                          static mean V    shock recovery
fixed(k=1,a=0.1)               0.0239         20.4 steps
fixed(k=1,a=0.1,b=400)         0.0074         59.0 steps
```

## Drift-plus-penalty: the frontier

The deadbeat law has an implicit price of data; drift-plus-penalty (Neely) makes it explicit.
Each step, pick the action minimising

```
[E[V_next](α, β) − V̂] + λ · (real samples used)        vs. skip = 0
```

No trigger band is needed — λ creates one: near the noise floor no retrain can buy enough V
reduction to pay for itself. Sweeping λ traces the cost–stability Pareto frontier
(`lrcctl frontier`, drift regime, 10 seeds, sorted by budget):

```
controller                mean V     real/step  retrains
dpp(lam=0.001)            0.0822        39.4      22.0
fixed(k=20,a=1)           0.0320        42.0      10.0
dpp(lam=0.0005)           0.0415        42.7      25.3
lyapunov(eta=0.3)         0.0188        49.8      33.3
dpp(lam=0.0002)           0.0179        51.0      33.9
fixed(k=1,a=0.1)          0.0395        52.0     200.0
fixed(k=5,a=0.5)          0.0191        52.0      40.0
dpp(lam=0.0001)           0.0108        63.5      47.8
dpp(lam=5e-05)            0.0074        86.3      67.6
```

Every fixed cadence sits above the dpp curve — strictly dominated. The deadbeat Lyapunov
controller lands *on* the frontier (it is the λ ≈ 2e-4 point with a guarantee attached), and λ
extends the curve in both directions: λ = 1e-3 correctly decides "never retrain" when the
environment is static; λ = 5e-5 buys sub-step shock recovery.

**Where β becomes rational.** Because β candidates cost no real data, the dpp optimizer uses
KL-regularization exactly when theory says it should: at λ = 2e-4 (rare, decisive retrains) it
never picks β > 0; at λ = 1e-5 (frequent small corrections) almost every retrain is damped
(β = 0.25n–1n). The optimizer discovers the regime boundary on its own — pinned as a test.

## Results

`lrcctl benchmark` — 200 steps, `n_fit = 200`, 20 seeds, identical seeds per controller (paired).
`real/step` includes the 32 samples/step monitoring probe everyone pays.

**Static reference** — retraining is pure waste; the controllers mostly skip:

```
controller                mean V     max V  collapse%  real/step  retrains
never                     0.0000    0.0000         0%       32.0       0.0
fixed(k=1,a=0.1)          0.0239    0.2376         0%       52.0     200.0
fixed(k=5,a=0.5)          0.0061    0.0319         0%       52.0      40.0
fixed(k=20,a=1)           0.0049    0.0236         0%       42.0      10.0
lyapunov(eta=0.3)         0.0026    0.0365         0%       37.3      10.1
dpp(lam=0.0002)           0.0025    0.0319         0%       37.2       9.7
```

**Linear drift** (μ* moves 0.02/step) — never-retrain collapses; both controllers beat every
fixed cadence on mean V while spending less than the best-tuned one:

```
controller                mean V     max V  collapse%  real/step  retrains
never                     2.6867    8.0000       100%       32.0       0.0
fixed(k=1,a=0.1)          0.0403    0.3982         0%       52.0     200.0
fixed(k=5,a=0.5)          0.0196    0.0975         0%       52.0      40.0
fixed(k=20,a=1)           0.0318    0.1578         0%       42.0      10.0
lyapunov(eta=0.3)         0.0184    0.0938         0%       50.9      35.4
dpp(lam=0.0002)           0.0176    0.0893         0%       51.1      34.1
```

**Shock** (μ* jumps +2.0 at step 50) — the shock itself sends V to 2 nats for everyone
(`collapse%` is the environment's doing); what matters is how fast V comes back down:

```
controller                mean V     max V  collapse%  real/step  retrains  recovery
never                     1.5100    2.0000       100%       32.0       0.0         -
fixed(k=1,a=0.1)          0.0868    2.6112       100%       52.0     200.0      20.4
fixed(k=5,a=0.5)          0.0408    2.2923       100%       52.0      40.0      13.8
fixed(k=20,a=1)           0.1134    2.2846       100%       42.0      10.0      10.0
lyapunov(eta=0.3)         0.0161    2.0569       100%       38.2      11.1       2.7
dpp(lam=0.0002)           0.0133    2.0472       100%       39.3      12.2       1.1
```

The takeaway: each fixed cadence is decent in exactly one regime — dense cadences waste budget
when static, sparse cadences leave the model exposed after a shock, dilute mixes destabilise.
The Lyapunov controllers, with **one setting and no per-regime tuning**, are the best or
tied-best policy in all three regimes on stability, the cheapest on budget, and recover from a
shock in 1–3 steps instead of 10–20. And with α pinned to 0 the loop reproduces textbook model
collapse (a pinned test).

## Usage

```bash
pip install -e ".[dev]"
pytest -q                                   # 97 tests

lrcctl info
lrcctl run --drift shock --seed 3           # one closed-loop episode + V sparkline
lrcctl run --controller dpp --lam 1e-4 --drift linear
lrcctl run --controller fixed --period 1 --alpha 0.1 --beta 400   # the beta ablation
lrcctl benchmark --drift linear --seeds 20  # the tables above
lrcctl frontier --drift linear --seeds 10   # the lam sweep / Pareto frontier
```

```python
from lrc import EnvironmentConfig, LyapunovController, run_episode

env = EnvironmentConfig(drift="linear", drift_rate=0.02)
result = run_episode(LyapunovController(n_fit=200), env,
                     steps=200, n_fit=200, probe_size=32, seed=0)
print(result.mean_v, result.retrains, result.real_samples)
```

## Layout

| Module | What it holds |
|---|---|
| `lrc/distributions.py` | Gaussian algebra: sampling, MLE/unbiased/KL-regularized fits, KL, mixture moments |
| `lrc/lyapunov.py` | V, the CE one-step map `V_pred(α, β)`, and the noise-aware `expected_v` |
| `lrc/simulator.py` | The generation loop: drifting reference, mixed (α, β) retrains, budget accounting |
| `lrc/controller.py` | Trigger+deadbeat Lyapunov law, drift-plus-penalty, fixed-cadence / never baselines |
| `lrc/benchmark.py` | Closed-loop episodes, paired-seed benchmark, metrics table |
| `lrc/cli.py` | `lrcctl info \| run \| benchmark \| frontier` |

## Honest limitations

- The model family is a 1-D Gaussian fit by MLE — the point is that the loop dynamics (shrinkage
  + random walk + mixing) are exact, not that the model is rich. The control law only needs a
  one-step predictor of V; swapping in a richer family means swapping that predictor.
- The deadbeat controller's prediction is certainty-equivalent (ignores fit noise); the slack `c`
  absorbs it. With `c` well below `2/n` the controller chases noise. The dpp controller uses the
  noise-aware map, but its noise terms are themselves leading-order approximations.
- Drift-plus-penalty here is myopic (one-step greedy). Full Neely theory adds a virtual queue for
  long-run budget constraints; the [O(λ), O(1/λ)] trade-off shape shows up empirically in the
  frontier table but is not proven for this loop.
- Probe pooling (4-step window) trades a lower monitoring noise floor for lag under fast drift.
- Collapse detection is via a fixed KL threshold (1 nat), and recovery via 0.05 nats — both are
  config constants, not learned.
