"""Seeded synthetic event stream.

Generates a realistic mix:

* **Organic users** — install with no preceding click/impression.
* **Click-attributed users** — click 1h - 5d before install.
* **View-attributed users** — impression < 24h before install.
* **Click-injection sources** — click fires 1-15s before install
  on devices that would otherwise be organic. Exercises the fraud
  detector.
* **Install-spam sources** — high-volume installs with near-zero
  D1 retention.
* **Genuine users emit OPEN / IN_APP / PURCHASE post-install** with
  realistic decay (lots of D1, less of D7, less still of D30).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from mappev.schema import VN_TZ, Event, EventKind

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)


# Real-ish source/campaign pairs in the VN market.
_LEGIT_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("facebook", ("vn_promo", "vn_signup", "vn_purchase_lookalike")),
    ("google_ads", ("uac_app_install", "search_competitor")),
    ("tiktok", ("vn_videoview", "vn_branded_hashtag")),
    ("zalo", ("vn_zalo_oa", "vn_messenger_ad")),
)

_FRAUD_SOURCES: tuple[tuple[str, str], ...] = (
    ("dodgy_network", "shady_campaign"),
    ("spam_dsp", "device_farm_a"),
)


def _make_install(rng: random.Random, eid: str, did: str, ts: datetime) -> Event:
    return Event(
        event_id=eid,
        device_id=did,
        kind=EventKind.INSTALL,
        occurred_at=ts,
        source="organic",
        campaign="",
    )


def _make_click(
    rng: random.Random, eid: str, did: str, ts: datetime, source: str, campaign: str
) -> Event:
    return Event(
        event_id=eid,
        device_id=did,
        kind=EventKind.CLICK,
        occurred_at=ts,
        source=source,
        campaign=campaign,
    )


def _make_open(rng: random.Random, eid: str, did: str, ts: datetime) -> Event:
    return Event(
        event_id=eid,
        device_id=did,
        kind=EventKind.OPEN,
        occurred_at=ts,
        source="organic",
        campaign="",
    )


def _make_in_app(rng: random.Random, eid: str, did: str, ts: datetime, name: str) -> Event:
    return Event(
        event_id=eid,
        device_id=did,
        kind=EventKind.IN_APP,
        occurred_at=ts,
        source="organic",
        campaign="",
        in_app_event_name=name,
    )


def _make_purchase(rng: random.Random, eid: str, did: str, ts: datetime, amount_vnd: int) -> Event:
    return Event(
        event_id=eid,
        device_id=did,
        kind=EventKind.PURCHASE,
        occurred_at=ts,
        source="organic",
        campaign="",
        revenue_vnd=amount_vnd,
    )


def generate(
    *,
    n_devices: int = 200,
    n_days: int = 30,
    organic_fraction: float = 0.35,
    click_fraction: float = 0.45,
    view_fraction: float = 0.10,
    click_injection_fraction: float = 0.05,
    install_spam_fraction: float = 0.05,
    seed: int = 0,
    base_time: datetime | None = None,
) -> list[Event]:
    """Generate a mixed event stream over ``n_days`` days.

    The five fractions must sum to <= 1.0 (the remainder is treated
    as additional organic devices).
    """
    fractions = (
        organic_fraction,
        click_fraction,
        view_fraction,
        click_injection_fraction,
        install_spam_fraction,
    )
    if any(not 0 <= f <= 1 for f in fractions):
        raise ValueError("each fraction must be in [0, 1]")
    if sum(fractions) > 1.0 + 1e-9:
        raise ValueError(f"fractions sum to {sum(fractions)}, must be <= 1.0")
    if n_devices < 1:
        raise ValueError("n_devices must be >= 1")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    n_organic = int(n_devices * organic_fraction)
    n_click = int(n_devices * click_fraction)
    n_view = int(n_devices * view_fraction)
    n_injection = int(n_devices * click_injection_fraction)
    n_spam = int(n_devices * install_spam_fraction)
    # Remainder becomes additional organic.
    n_organic += n_devices - (n_organic + n_click + n_view + n_injection + n_spam)

    events: list[Event] = []
    event_counter = 0

    def _next_id() -> str:
        nonlocal event_counter
        eid = f"E-{event_counter:08d}"
        event_counter += 1
        return eid

    def _post_install_activity(did: str, install_at: datetime, is_spam: bool) -> None:
        """Generate D1/D7/D30 activity. Spam devices get ~zero activity."""
        if is_spam:
            return
        # Diurnal activity over 30 days with decay.
        for day in range(n_days):
            survival = max(0.05, 0.85**day)
            if rng.random() > survival:
                continue
            day_start = install_at + timedelta(days=day, hours=rng.randint(0, 23))
            events.append(_make_open(rng, _next_id(), did, day_start))
            if rng.random() < 0.4:
                events.append(
                    _make_in_app(
                        rng,
                        _next_id(),
                        did,
                        day_start + timedelta(minutes=2),
                        rng.choice(("level_up", "share", "view_item")),
                    )
                )
            if rng.random() < 0.10:
                events.append(
                    _make_purchase(
                        rng,
                        _next_id(),
                        did,
                        day_start + timedelta(minutes=5),
                        rng.choice((49_000, 99_000, 199_000, 499_000)),
                    )
                )

    device_counter = 0

    def _next_device_id(prefix: str = "D") -> str:
        nonlocal device_counter
        did = f"{prefix}-{device_counter:08d}"
        device_counter += 1
        return did

    # 1. Organic
    for _ in range(n_organic):
        did = _next_device_id()
        install_at = base + timedelta(days=rng.randint(0, n_days - 1), hours=rng.randint(0, 23))
        events.append(_make_install(rng, _next_id(), did, install_at))
        _post_install_activity(did, install_at, is_spam=False)

    # 2. Click-attributed
    for _ in range(n_click):
        did = _next_device_id()
        source, campaigns = rng.choice(_LEGIT_SOURCES)
        campaign = rng.choice(campaigns)
        install_at = base + timedelta(days=rng.randint(0, n_days - 1), hours=rng.randint(0, 23))
        # Click 1h-5d before install.
        click_lag = timedelta(hours=rng.randint(1, 24 * 5))
        events.append(_make_click(rng, _next_id(), did, install_at - click_lag, source, campaign))
        events.append(_make_install(rng, _next_id(), did, install_at))
        _post_install_activity(did, install_at, is_spam=False)

    # 3. View-attributed (impression < 24h before install).
    for _ in range(n_view):
        did = _next_device_id()
        source, campaigns = rng.choice(_LEGIT_SOURCES)
        campaign = rng.choice(campaigns)
        install_at = base + timedelta(days=rng.randint(0, n_days - 1), hours=rng.randint(0, 23))
        impr_lag = timedelta(hours=rng.randint(1, 23))
        events.append(
            Event(
                event_id=_next_id(),
                device_id=did,
                kind=EventKind.IMPRESSION,
                occurred_at=install_at - impr_lag,
                source=source,
                campaign=campaign,
            )
        )
        events.append(_make_install(rng, _next_id(), did, install_at))
        _post_install_activity(did, install_at, is_spam=False)

    # 4. Click-injection — click fires 1-15s before install
    for _ in range(n_injection):
        did = _next_device_id("DI")
        source, campaign = rng.choice(_FRAUD_SOURCES)
        install_at = base + timedelta(days=rng.randint(0, n_days - 1), hours=rng.randint(0, 23))
        injection_lag = timedelta(seconds=rng.randint(1, 15))
        events.append(
            _make_click(rng, _next_id(), did, install_at - injection_lag, source, campaign)
        )
        events.append(_make_install(rng, _next_id(), did, install_at))
        # These users behave like real organic — they activate normally.
        _post_install_activity(did, install_at, is_spam=False)

    # 5. Install-spam — many devices on a single source, no D1 activity
    for _ in range(n_spam):
        did = _next_device_id("DS")
        source, campaign = rng.choice(_FRAUD_SOURCES)
        install_at = base + timedelta(days=rng.randint(0, n_days - 1), hours=rng.randint(0, 23))
        # Normal-looking click lag (1h-3d).
        click_lag = timedelta(hours=rng.randint(1, 24 * 3))
        events.append(_make_click(rng, _next_id(), did, install_at - click_lag, source, campaign))
        events.append(_make_install(rng, _next_id(), did, install_at))
        # No post-install activity — device farms don't open the app.
        _post_install_activity(did, install_at, is_spam=True)

    return events


__all__ = ["generate"]
