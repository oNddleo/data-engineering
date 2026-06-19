"""Synthetic image + video uploader → MinIO bucket `lakehouse/raw-media/`.

Generates PNG/JPG with valid EXIF (DateTimeOriginal + GPSInfo) and short MP4
clips via `ffmpeg -f lavfi -i testsrc`. Uploads concurrently using boto3 to
exercise the same code path Phase 4's batch metadata extractor will read.

Naming: raw-media/{type}/{yyyy}/{mm}/{dd}/{device_id}-{ulid}.{ext}

Idempotency: this script ACCUMULATES — every invocation writes new objects
with fresh ULID keys. To reset, run `make clean-hybrid` (drops the MinIO
volume) or clear the prefix manually with `mc rm --recursive --force
local/lakehouse/raw-media/`. Phase 4's bronze ingestion uses an anti-join on
(object_key, etag) so re-runs of this uploader will not double-count in the
catalog, but storage usage grows monotonically.

Usage:
    python media-uploader.py --count 60 --ratio 5:1 --endpoint http://minio:9000
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import random
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3  # type: ignore[import-untyped]
import piexif  # type: ignore[import-untyped]
from PIL import Image, ImageDraw  # type: ignore[import-untyped]
from ulid import ULID  # type: ignore[import-untyped]

LOG = logging.getLogger("media-uploader")

LAT_RANGE = (20.95, 21.10)
LON_RANGE = (105.75, 105.95)


def _decimal_to_dms_rational(value: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Convert decimal lat/lon to EXIF DMS rationals (degrees, minutes, seconds)."""
    value = abs(value)
    degrees = int(value)
    minutes_full = (value - degrees) * 60
    minutes = int(minutes_full)
    seconds = round((minutes_full - minutes) * 60 * 1000)  # 3-decimal precision
    return (degrees, 1), (minutes, 1), (seconds, 1000)


def _build_exif(taken_at: datetime, lat: float, lon: float) -> bytes:
    zeroth = {piexif.ImageIFD.Make: b"HybridPOC", piexif.ImageIFD.Model: b"sim-cam-v1"}
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: taken_at.strftime("%Y:%m:%d %H:%M:%S").encode("ascii"),
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: _decimal_to_dms_rational(lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: _decimal_to_dms_rational(lon),
    }
    return piexif.dump({"0th": zeroth, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None})


def make_image_bytes(rng: random.Random, taken_at: datetime, lat: float, lon: float, ext: str) -> bytes:
    img = Image.new("RGB", (320, 240), color=(rng.randint(0, 80), rng.randint(40, 120), rng.randint(80, 200)))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), taken_at.isoformat(timespec="seconds"), fill="white")
    buf = io.BytesIO()
    if ext == "png":
        # PNG doesn't carry EXIF the same way; keep metadata in JPG variant only.
        img.save(buf, format="PNG")
    else:
        exif_bytes = _build_exif(taken_at, lat, lon)
        img.save(buf, format="JPEG", quality=85, exif=exif_bytes)
    return buf.getvalue()


def make_video_bytes(seconds: int = 5) -> bytes:
    """Synthesize a tiny MP4 via ffmpeg lavfi testsrc; return its bytes."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH; install ffmpeg or run inside the Spark image.")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        out_path = tmp.name
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x240:rate=24",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                out_path,
            ],
            check=True,
        )
        return Path(out_path).read_bytes()
    finally:
        Path(out_path).unlink(missing_ok=True)


def build_s3_key(media_type: str, ext: str, device_id: str, taken_at: datetime) -> str:
    ulid = ULID()
    return (
        f"raw-media/{media_type}/{taken_at:%Y/%m/%d}/{device_id}-{ulid}.{ext}"
    )


def make_s3_client(endpoint: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )


def upload_one(client, bucket: str, key: str, body: bytes, content_type: str) -> str:
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    return key


def run(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    client = make_s3_client(args.endpoint, args.access_key, args.secret_key)

    img_per_block, vid_per_block = (int(p) for p in args.ratio.split(":"))
    blocks = max(1, args.count // (img_per_block + vid_per_block))
    plan: list[tuple[str, str]] = []   # (media_type, ext)
    for _ in range(blocks):
        for _ in range(img_per_block):
            plan.append(("image", rng.choice(["png", "jpg"])))
        for _ in range(vid_per_block):
            plan.append(("video", "mp4"))
    plan = plan[: args.count]
    rng.shuffle(plan)

    devices = [f"dev-{i:04d}" for i in range(args.devices)]
    now = datetime.now(timezone.utc)

    LOG.info("uploading %d objects to s3://%s (%s)", len(plan), args.bucket, args.endpoint)

    futures = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for media_type, ext in plan:
            device_id = rng.choice(devices)
            taken_at = now - timedelta(minutes=rng.randint(0, 120), seconds=rng.randint(0, 59))
            lat = rng.uniform(*LAT_RANGE)
            lon = rng.uniform(*LON_RANGE)

            if media_type == "image":
                body = make_image_bytes(rng, taken_at, lat, lon, ext)
                content_type = "image/png" if ext == "png" else "image/jpeg"
            else:
                body = make_video_bytes(seconds=5)
                content_type = "video/mp4"

            key = build_s3_key(media_type, ext, device_id, taken_at)
            futures.append(pool.submit(upload_one, client, args.bucket, key, body, content_type))

        for fut in as_completed(futures):
            LOG.debug("uploaded %s", fut.result())

    LOG.info("done. uploaded=%d", len(futures))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate + upload synthetic media to MinIO.")
    p.add_argument("--endpoint", default=os.environ.get("S3_ENDPOINT_URL", "http://minio:9000"))
    p.add_argument("--access-key", default=os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"))
    p.add_argument("--secret-key", default=os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"))
    p.add_argument("--bucket", default=os.environ.get("S3_BUCKET", "lakehouse"))
    p.add_argument("--count", type=int, default=60, help="Total number of objects to upload.")
    p.add_argument("--ratio", default="5:1", help="image:video block ratio.")
    p.add_argument("--devices", type=int, default=100, help="Device pool size for tagging.")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
