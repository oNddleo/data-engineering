# abandoned-cart-recovery-pipeline

Funnel-event sessionization + abandoned-cart detection + recovery-
campaign scheduling + conversion attribution for VN marketplaces
(Shopee / Lazada / Tiki / TikTok Shop). The pipeline turns raw
buyer events into ranked recovery opportunities and measures whether
the campaign worked.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates** funnel `Event` records at the boundary —
   tz-aware datetimes, item-ID + price required for ``ADD_TO_CART``
   and ``REMOVE_FROM_CART``, six legal event kinds.
2. **Sessionizes** events per buyer using a 30-min idle gap
   (industry standard). ``COMPLETE_CHECKOUT`` and
   ``ABANDON_CHECKOUT`` force an explicit session boundary — the
   buyer's next product view is a new shopping intent, not a
   continuation.
3. **Detects abandoned sessions**: cart had ≥ 1 ``ADD_TO_CART``,
   cart value ≥ ₫50k, no ``COMPLETE_CHECKOUT``. Each abandon is
   classified into one of three reasons:
   * `EXPLICIT` — buyer hit ABANDON_CHECKOUT (highest intent)
   * `CHECKOUT_DROPOFF` — started checkout but never completed
   * `IDLE_TIMEOUT` — had cart, never started checkout
4. **Schedules recovery touches** at industry-standard delays:
   1h EMAIL → 24h SMS → 72h PUSH per abandoned session.
5. **Attributes conversions** — for each touch, did the buyer
   ``COMPLETE_CHECKOUT`` within the attribution window? First-touch
   credit by default; last-touch via ``last_touch=True``.

## Components

| Module                | Role                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `cartrec.schema`      | `Event`, `EventKind`, `Session`, `CampaignTouch`, `TouchChannel`, `VN_TZ` |
| `cartrec.sessionize`  | `sessionize(events, idle_gap_minutes=30)`                             |
| `cartrec.detect`      | `find_abandoned`, `abandon_rate`, `AbandonReason`                     |
| `cartrec.campaign`    | `schedule`, `DEFAULT_CADENCE`, `filter_due`                           |
| `cartrec.attribute`   | `attribute`, `conversion_rate`, `conversion_by_channel`               |
| `cartrec.simulator`   | Seeded synthetic event stream across 5 buyer archetypes               |
| `cartrec.io_jsonl`    | Type-checked JSONL codec for all four record types                    |
| `cartrec.cli`         | `cartrec info \| simulate \| sessionize \| detect \| schedule \| attribute \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
cartrec info
cartrec simulate   --buyers 200 --recovery-fraction 0.15 --seed 7 --output ./events.jsonl
cartrec sessionize --input ./events.jsonl --output ./sessions.jsonl
cartrec detect     --input ./sessions.jsonl --show 10
cartrec schedule   --input ./sessions.jsonl --output ./touches.jsonl
cartrec attribute  --touches ./touches.jsonl --events ./events.jsonl --window-hours 24
cartrec summary    --input ./sessions.jsonl
```

Sample `detect` output:

```
session                                                      reason               cart_vnd
B-000000|2026-05-01T09:00:00+07:00                           IDLE_TIMEOUT          159,000
B-000003|2026-05-01T09:33:00+07:00                           IDLE_TIMEOUT          487,000
B-000004|2026-05-01T09:44:00+07:00                           EXPLICIT               89,000
B-000006|2026-05-01T10:06:00+07:00                           CHECKOUT_DROPOFF      797,000

Abandon rate: 69.3% (93/150 carting sessions)
```

Sample `attribute` output (first-touch attribution, 24h window):

```
Conversion rate: 3.94% (11/279)
  EMAIL  11.83%
  SMS    0.00%
  PUSH   0.00%
```

Sample `summary` JSON:

```json
{
  "n_sessions": 211,
  "n_carting_sessions": 150,
  "n_completed": 57,
  "n_abandoned": 93,
  "by_reason": {
    "IDLE_TIMEOUT": 23,
    "EXPLICIT": 28,
    "CHECKOUT_DROPOFF": 42
  },
  "total_recoverable_vnd": 71602000
}
```

## Library

```python
from cartrec.simulator   import generate
from cartrec.sessionize  import sessionize
from cartrec.detect      import find_abandoned
from cartrec.campaign    import schedule
from cartrec.attribute   import attribute, conversion_by_channel

events     = generate(n_buyers=1000, seed=42)
sessions   = sessionize(events, idle_gap_minutes=30)
abandoned  = find_abandoned(sessions, min_cart_vnd=50_000)
touches    = schedule(abandoned)
attributed = attribute(touches, events, attribution_window_hours=24)

print("Recoverable VND:", sum(a.session.cart_value_vnd for a in abandoned))
print("Conversion by channel:", conversion_by_channel(attributed))
```

## Key design decisions

- **30-min idle gap** is the industry-standard sessionization window.
  Both Shopee CRM and Lazada Retention Tools use this; the parameter
  is exposed so you can AB-test e.g. 45-min for power buyers.
- **Checkout-terminal events force a session boundary.** A buyer
  who completes checkout and immediately views another product is
  starting a *new* shopping intent — not continuing the previous
  cart. The same holds for ``ABANDON_CHECKOUT``: a buyer who closes
  the checkout drawer and resumes viewing in 5 minutes opened a
  fresh session.
- **`cart_value_vnd` clamped at zero.** Out-of-order webhook with
  REMOVE arriving before ADD shouldn't produce a negative cart —
  we cap at zero rather than letting the bug propagate.
- **Three abandon reasons** because they need different CRM
  treatments. EXPLICIT abandoners get personalised win-back offers
  (highest intent); IDLE_TIMEOUT buyers get the generic email blast.
- **Pure functions everywhere**, ``now`` and ``attribution_window``
  injected by the caller — tests pin time deterministically.
- **Min-cart filter at ₫50k.** VN marketplaces' average campaign cost
  per touch is ~₫500-1,500 (email + SMS combined); below ₫50k cart
  value the expected revenue doesn't justify the spend. The
  threshold is parametric so finance teams can re-tune.
- **First-touch attribution by default**, with last-touch available.
  First-touch gives credit to the channel that *re-engaged* the
  buyer; last-touch credits the channel that *closed* the sale.
  Both are useful — the function exposes both so analysts can run
  the comparison.

## Quality

```bash
make test       # 84 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **84 tests**, 0 failing; 6 Hypothesis properties (sum of session
  ``n_events`` equals input length; ``started_at ≤ ended_at`` always;
  cart value is always ≥ 0; abandon rate is always in [0, 1];
  abandoned sessions always have ``n_add ≥ 1``; attribution is
  consistent with the window — converted iff conversion falls in
  ``[touch_ts, touch_ts + window]``).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `cartrec` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
