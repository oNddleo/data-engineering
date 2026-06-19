"""Unit tests for media bronze extractors that don't require Spark.

We construct synthetic PNGs/JPGs in-memory with Pillow and exercise the
EXIF parse + thumbnail paths. The ffprobe-based video paths are mocked
because the test runner shouldn't need ffmpeg on the host.
"""

from __future__ import annotations

import io
from unittest import mock

import piexif
from PIL import Image

from lib.media_extractors import (
    _dms_to_decimal,
    extract_image_meta,
    extract_video_meta,
    make_thumbnail,
)


def _make_jpeg_with_exif(taken_at: str, lat: float, lon: float) -> bytes:
    """Build a small JPEG with DateTimeOriginal + GPS rationals."""
    img = Image.new("RGB", (16, 16), (10, 10, 10))
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: (
            (int(abs(lat)), 1),
            (int((abs(lat) - int(abs(lat))) * 60), 1),
            (0, 1000),
        ),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: (
            (int(abs(lon)), 1),
            (int((abs(lon) - int(abs(lon))) * 60), 1),
            (0, 1000),
        ),
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: taken_at.encode("ascii"),
    }
    exif_bytes = piexif.dump({"0th": {}, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None})

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=85)
    return buf.getvalue()


def test_dms_to_decimal_north_east():
    # 21°1' = 21.016666..°
    dms = ((21, 1), (1, 1), (0, 1000))
    assert _dms_to_decimal(dms, b"N") == 21.016667


def test_dms_to_decimal_handles_south_west_sign_flip():
    dms = ((10, 1), (30, 1), (0, 1000))
    assert _dms_to_decimal(dms, b"S") == -10.5


def test_extract_image_meta_round_trips_exif_gps_and_taken_at():
    content = _make_jpeg_with_exif("2026:06:19 05:11:11", 21.0, 105.0)
    meta = extract_image_meta(content)
    assert meta["width"] == 16 and meta["height"] == 16
    assert meta["taken_at"] == "2026:06:19 05:11:11"
    assert meta["gps_lat"] == 21.0
    assert meta["gps_lon"] == 105.0


def test_extract_image_meta_handles_png_without_exif():
    img = Image.new("RGB", (8, 8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    meta = extract_image_meta(buf.getvalue())
    assert meta["width"] == 8 and meta["height"] == 8
    assert meta["taken_at"] is None
    assert meta["gps_lat"] is None


def test_make_thumbnail_returns_png_bytes_for_image():
    img = Image.new("RGB", (400, 300), (128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    thumb = make_thumbnail(buf.getvalue(), kind="image")
    assert thumb is not None
    head = thumb[:8]
    # PNG magic header.
    assert head[:4] == b"\x89PNG"


def test_extract_video_meta_returns_empty_when_ffprobe_missing():
    with mock.patch("lib.media_extractors.shutil.which", return_value=None):
        out = extract_video_meta(b"fake-mp4-bytes")
    assert out["duration_sec"] is None
    assert out["codec"] is None
