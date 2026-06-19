"""IoT sensor simulator → Kafka topic iot.sensors.

Emits JSON-encoded sensor readings at a configurable rate from a fixed pool of
synthetic devices. Each sensor type has its own normal distribution; 1% of
readings are forced ±5σ outliers so the silver layer can prove its detector
works.

Usage:
    python iot-simulator.py --rate 50 --duration 60 \
        --bootstrap kafka:9092 --topic iot.sensors

Idempotency: every event carries a ULID `event_id`; the silver MERGE
deduplicates by it. Restarting the producer will not corrupt downstream.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from confluent_kafka import KafkaError, Producer  # type: ignore[import-untyped]
from ulid import ULID  # type: ignore[import-untyped]

LOG = logging.getLogger("iot-simulator")

# Hanoi bounding box — small geographic spread for realistic dashboards.
LAT_RANGE = (20.95, 21.10)
LON_RANGE = (105.75, 105.95)

# (sensor_type, unit, mean, stddev)
SENSOR_SPECS: list[tuple[str, str, float, float]] = [
    ("temperature", "C",     27.0,  3.5),
    ("humidity",    "%",     72.0,  8.0),
    ("pm25",        "ug/m3", 55.0, 20.0),
    ("vibration",   "mm/s",   1.2,  0.4),
]

OUTLIER_RATE = 0.01    # fraction forced to extreme values
OUTLIER_SIGMAS = 5.0   # how far out the outliers go


@dataclass(frozen=True)
class Device:
    device_id: str
    lat: float
    lon: float
    fw_version: str


def build_device_pool(n: int, rng: random.Random) -> list[Device]:
    fw_choices = ["1.0.0", "1.1.0", "1.2.3", "2.0.0"]
    return [
        Device(
            device_id=f"dev-{i:04d}",
            lat=rng.uniform(*LAT_RANGE),
            lon=rng.uniform(*LON_RANGE),
            fw_version=rng.choice(fw_choices),
        )
        for i in range(n)
    ]


def sample_value(spec: tuple[str, str, float, float], rng: random.Random) -> float:
    _name, _unit, mean, stddev = spec
    if rng.random() < OUTLIER_RATE:
        direction = rng.choice([-1, 1])
        return round(mean + direction * OUTLIER_SIGMAS * stddev, 4)
    return round(rng.gauss(mean, stddev), 4)


def build_event(device: Device, rng: random.Random) -> dict:
    spec = rng.choice(SENSOR_SPECS)
    sensor_type, unit, _, _ = spec
    return {
        "event_id": str(ULID()),
        "device_id": device.device_id,
        "sensor_type": sensor_type,
        "value": sample_value(spec, rng),
        "unit": unit,
        "lat": device.lat,
        "lon": device.lon,
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "fw_version": device.fw_version,
    }


def make_producer(bootstrap: str) -> Producer:
    return Producer(
        {
            "bootstrap.servers": bootstrap,
            "client.id": "iot-simulator",
            "acks": "all",
            "enable.idempotence": True,
            "compression.type": "zstd",
            "linger.ms": 50,
            "batch.size": 64 * 1024,
            "message.timeout.ms": 30000,
        }
    )


def delivery_callback(err: KafkaError | None, _msg) -> None:
    if err is not None:
        LOG.warning("delivery failed: %s", err)


def run(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    devices = build_device_pool(args.devices, rng)
    producer = make_producer(args.bootstrap)

    stop = {"flag": False}

    def _stop(signum, _frame) -> None:
        LOG.info("signal %s — draining and exiting", signum)
        stop["flag"] = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    interval = 1.0 / max(args.rate, 1)
    end_at = time.monotonic() + args.duration if args.duration > 0 else None
    sent = 0
    next_tick = time.monotonic()

    LOG.info(
        "producing to %s topic=%s rate=%d/s duration=%s devices=%d",
        args.bootstrap, args.topic, args.rate,
        f"{args.duration}s" if args.duration > 0 else "forever",
        args.devices,
    )

    while not stop["flag"]:
        if end_at is not None and time.monotonic() >= end_at:
            break

        event = build_event(rng.choice(devices), rng)
        producer.produce(
            args.topic,
            value=json.dumps(event).encode("utf-8"),
            key=event["device_id"].encode("utf-8"),
            on_delivery=delivery_callback,
        )
        sent += 1

        producer.poll(0)

        next_tick += interval
        sleep_for = next_tick - time.monotonic()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            # Behind schedule — reset cadence to avoid runaway catch-up bursts.
            next_tick = time.monotonic()

    LOG.info("flushing %d remaining messages", len(producer))
    undelivered = producer.flush(timeout=10)
    LOG.info("done. sent=%d undelivered=%d", sent, undelivered)
    if undelivered > 0:
        LOG.error("%d messages were not delivered before timeout", undelivered)
        return 2
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate IoT sensor events → Kafka.")
    p.add_argument("--bootstrap", default="kafka:9092", help="Kafka bootstrap servers.")
    p.add_argument("--topic", default="iot.sensors", help="Target Kafka topic.")
    p.add_argument("--rate", type=int, default=50, help="Events per second.")
    p.add_argument("--duration", type=int, default=60, help="Seconds to run; 0 = forever.")
    p.add_argument("--devices", type=int, default=100, help="Device pool size.")
    p.add_argument("--seed", type=int, default=42, help="RNG seed (Faker-style determinism).")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
