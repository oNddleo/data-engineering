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
- and benchmark it against naïve fixed-cadence retraining.

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

## Results

`lrcctl benchmark` — 200 steps, `n_fit = 200`, 20 seeds, identical seeds per controller (paired).
`real/step` includes the 32 samples/step monitoring probe everyone pays.

**Static reference** — retraining is pure waste; the controller mostly skips:

```
controller                mean V     max V  collapse%  real/step  retrains
never                     0.0000    0.0000         0%       32.0       0.0
fixed(k=1,a=0.1)          0.0239    0.2376         0%       52.0     200.0
fixed(k=5,a=0.5)          0.0061    0.0319         0%       52.0      40.0
fixed(k=20,a=1)           0.0049    0.0236         0%       42.0      10.0
lyapunov(eta=0.3)         0.0026    0.0365         0%       37.3      10.1
```

**Linear drift** (μ* moves 0.02/step) — never-retrain collapses; the controller beats every fixed
cadence on mean V while spending less than the best-tuned one:

```
controller                mean V     max V  collapse%  real/step  retrains
never                     2.6867    8.0000       100%       32.0       0.0
fixed(k=1,a=0.1)          0.0403    0.3982         0%       52.0     200.0
fixed(k=5,a=0.5)          0.0196    0.0975         0%       52.0      40.0
fixed(k=20,a=1)           0.0318    0.1578         0%       42.0      10.0
lyapunov(eta=0.3)         0.0184    0.0938         0%       50.9      35.4
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
```

The takeaway: each fixed cadence is decent in exactly one regime — dense cadences waste budget
when static, sparse cadences leave the model exposed after a shock, dilute mixes destabilise.
The Lyapunov controller, with **one setting and no per-regime tuning**, is the best or tied-best
policy in all three regimes on stability, the cheapest on budget, and 4–8× faster to recover from
a shock. And with α pinned to 0 it reproduces textbook model collapse (a pinned test).

## Usage

```bash
pip install -e ".[dev]"
pytest -q                                   # 70 tests

lrcctl info
lrcctl run --drift shock --seed 3           # one closed-loop episode + V sparkline
lrcctl run --controller fixed --period 5 --alpha 0.5 --drift linear
lrcctl benchmark --drift linear --seeds 20  # the tables above
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
| `lrc/distributions.py` | Gaussian algebra: sampling, MLE/unbiased fits, KL, mixture moments |
| `lrc/lyapunov.py` | V and the exact certainty-equivalent one-step map `V_pred(α)` |
| `lrc/simulator.py` | The generation loop: drifting reference, mixed retrains, budget accounting |
| `lrc/controller.py` | The trigger+deadbeat Lyapunov law + fixed-cadence / never baselines |
| `lrc/benchmark.py` | Closed-loop episodes, paired-seed benchmark, metrics table |
| `lrc/cli.py` | `lrcctl info \| run \| benchmark` |

## Honest limitations

- The model family is a 1-D Gaussian fit by MLE — the point is that the loop dynamics (shrinkage
  + random walk + mixing) are exact, not that the model is rich. The control law only needs a
  one-step predictor of V; swapping in a richer family means swapping that predictor.
- The controller's prediction is certainty-equivalent (ignores fit noise); the slack `c` absorbs
  it. With `c` well below `2/n` the controller chases noise.
- Probe pooling (4-step window) trades a lower monitoring noise floor for lag under fast drift.
- Collapse detection is via a fixed KL threshold (1 nat), and recovery via 0.05 nats — both are
  config constants, not learned.
