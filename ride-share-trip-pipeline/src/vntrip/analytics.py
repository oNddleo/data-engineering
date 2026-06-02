"""ETA accuracy + surge-window detection + driver utilization.

These three roll-ups are what ops dashboards and supply-demand teams
actually look at every day at Grab/Gojek/Be VN:

* **ETA accuracy** — distribution of ``actual_pickup_seconds /
  estimated_pickup_seconds``. A platform is "well-calibrated" if the
  median is in [0.9, 1.1] and 90th percentile < 1.5. We expose the
  raw distribution.
* **Surge windows** — district × hour-of-day buckets where demand
  ran hot (avg surge ≥ 1.2× AND completion rate < 50%). These are
  the markets where supply needs reinforcement.
* **Driver utilization** — per-driver on-trip-time ÷ online-time.
  Healthy drivers sit at 50-70%; below 30% suggests under-dispatched;
  above 80% is unsustainable.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import TYPE_CHECKING

from vntrip.schema import VN_TZ, DriverShift, SurgeWindow, TripEventKind

if TYPE_CHECKING:
    from datetime import datetime

    from vntrip.schema import Trip, TripEvent


def eta_accuracy_pct(
    estimated_pickup_seconds_by_trip: dict[str, int],
    trips: list[Trip],
) -> dict[str, float]:
    """Return the actual-over-estimated ratio (×100) per trip,
    for trips that reached PICKUP."""
    out: dict[str, float] = {}
    for t in trips:
        if t.picked_up_at is None:
            continue
        estimated = estimated_pickup_seconds_by_trip.get(t.trip_id)
        if estimated is None or estimated <= 0:
            continue
        actual = int((t.picked_up_at - t.requested_at).total_seconds())
        out[t.trip_id] = actual / estimated * 100
    return out


def eta_accuracy_summary(ratios: dict[str, float]) -> dict[str, float]:
    """Compute median, p90, p99 of an ETA-ratio map."""
    if not ratios:
        return {"median": 0.0, "p90": 0.0, "p99": 0.0, "n": 0.0}
    sorted_vals = sorted(ratios.values())
    return {
        "median": round(median(sorted_vals), 1),
        "p90": round(_percentile(sorted_vals, 90), 1),
        "p99": round(_percentile(sorted_vals, 99), 1),
        "n": float(len(sorted_vals)),
    }


def _percentile(sorted_vals: list[float], p: int) -> float:
    """Nearest-rank percentile on a pre-sorted list."""
    if not sorted_vals:
        return 0.0
    rank = max(1, int(round(p / 100 * len(sorted_vals))))
    return sorted_vals[min(len(sorted_vals), rank) - 1]


def surge_windows(events: list[TripEvent]) -> list[SurgeWindow]:
    """Aggregate REQUEST events by (district, hour-of-VN-day) bucket
    and compute completion rate + avg surge."""
    bucket_requests: dict[tuple[str, str], list[TripEvent]] = defaultdict(list)
    completed_by_trip: set[str] = set()
    for e in events:
        if e.kind is TripEventKind.REQUEST:
            key = (e.district, _hour_bucket(e.occurred_at))
            bucket_requests[key].append(e)
        elif e.kind is TripEventKind.DROPOFF:
            completed_by_trip.add(e.trip_id)

    out: list[SurgeWindow] = []
    for (district, hour_bucket), reqs in bucket_requests.items():
        completed = sum(1 for r in reqs if r.trip_id in completed_by_trip)
        surge_sum = sum(r.surge_bps for r in reqs)
        avg_surge = surge_sum // len(reqs)
        completion_rate = completed / len(reqs) * 100
        out.append(
            SurgeWindow(
                district=district,
                hour_bucket=hour_bucket,
                requests=len(reqs),
                completed_trips=completed,
                completion_rate_pct=round(completion_rate, 1),
                avg_surge_bps=avg_surge,
            )
        )
    out.sort(key=lambda w: (w.hour_bucket, w.district))
    return out


def driver_shifts(trips: list[Trip]) -> list[DriverShift]:
    """Aggregate per-driver shifts from stitched trips."""
    # Group trips by (driver_id, shift_date).
    grouped: dict[tuple[str, str], list[Trip]] = defaultdict(list)
    for t in trips:
        if not t.driver_id:
            continue
        if t.accepted_at is None:
            continue  # no driver activity
        shift_date = t.accepted_at.astimezone(VN_TZ).date().isoformat()
        grouped[(t.driver_id, shift_date)].append(t)

    out: list[DriverShift] = []
    for (driver_id, shift_date), trips_in_shift in grouped.items():
        completed = sum(1 for t in trips_in_shift if t.is_completed)
        cancelled_by_driver = sum(
            1
            for t in trips_in_shift
            if t.is_cancelled and t.cancel_by is not None and t.cancel_by.value == "DRIVER"
        )
        accept_times = [t.accepted_at for t in trips_in_shift if t.accepted_at is not None]
        end_times = [
            (t.dropped_off_at or t.cancelled_at)
            for t in trips_in_shift
            if (t.dropped_off_at or t.cancelled_at) is not None
        ]
        if not accept_times or not end_times:
            continue
        online_start = min(accept_times)
        online_end = max(t for t in end_times if t is not None)
        online_seconds = max(0, int((online_end - online_start).total_seconds()))
        on_trip_seconds = 0
        revenue = 0
        for t in trips_in_shift:
            if t.accepted_at is None:
                continue
            end_at = t.dropped_off_at or t.cancelled_at
            if end_at is not None:
                on_trip_seconds += max(0, int((end_at - t.accepted_at).total_seconds()))
            if t.is_completed:
                revenue += t.fare_vnd
        out.append(
            DriverShift(
                driver_id=driver_id,
                shift_date=shift_date,
                trips_completed=completed,
                trips_cancelled_by_driver=cancelled_by_driver,
                online_seconds=online_seconds,
                on_trip_seconds=min(on_trip_seconds, online_seconds),
                revenue_vnd=revenue,
            )
        )
    out.sort(key=lambda s: (s.shift_date, s.driver_id))
    return out


def _hour_bucket(ts: datetime) -> str:
    """ISO datetime truncated to the hour in VN_TZ."""
    local = ts.astimezone(VN_TZ).replace(minute=0, second=0, microsecond=0)
    return local.isoformat()


__all__ = [
    "driver_shifts",
    "eta_accuracy_pct",
    "eta_accuracy_summary",
    "surge_windows",
]
