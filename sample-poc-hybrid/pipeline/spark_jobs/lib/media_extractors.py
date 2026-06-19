"""Pure-function metadata + thumbnail extractors for the media bronze job.

Pulled out of the Spark job script so they can be unit-tested without a
SparkSession. Each function takes bytes in, returns bytes / dict out.

Extractors:
    extract_image_meta(content)  -> dict
    extract_video_meta(content)  -> dict
    make_thumbnail(content, kind) -> bytes (PNG, 256x256)
"""

from __future__ import annotations

import io
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps  # type: ignore[import-untyped]

LOG = logging.getLogger(__name__)

THUMB_SIZE = (256, 256)
PIEXIF_IMPORT_ERROR: Exception | None
try:
    import piexif  # type: ignore[import-untyped]
except ImportError as e:  # noqa: BLE001
    piexif = None  # type: ignore[assignment]
    PIEXIF_IMPORT_ERROR = e
else:
    PIEXIF_IMPORT_ERROR = None


def _dms_to_decimal(dms: tuple, ref: bytes) -> float | None:
    """Convert EXIF DMS rational ((d,1), (m,1), (s,1000)) → decimal degrees."""
    try:
        deg = dms[0][0] / dms[0][1]
        minutes = dms[1][0] / dms[1][1]
        seconds = dms[2][0] / dms[2][1]
        value = deg + minutes / 60 + seconds / 3600
        if ref in (b"S", b"W"):
            value = -value
        return round(value, 6)
    except (IndexError, ZeroDivisionError, TypeError):
        return None


def extract_image_meta(content: bytes) -> dict:
    """Return width/height/exif/taken_at/gps from raw image bytes."""
    out: dict = {"width": None, "height": None, "exif_json": None, "taken_at": None, "gps_lat": None, "gps_lon": None}
    try:
        img = Image.open(io.BytesIO(content))
        out["width"], out["height"] = img.size
    except Exception as e:  # noqa: BLE001
        LOG.warning("image open failed: %s", e)
        return out

    if piexif is None:
        return out

    try:
        exif_dict = piexif.load(content)
    except Exception as e:  # noqa: BLE001
        LOG.debug("piexif.load failed (no EXIF, e.g. PNG): %s", e)
        return out

    # DateTimeOriginal — bytes like b"2026:06:19 05:11:11"
    exif_ifd = exif_dict.get("Exif", {})
    dto = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal)
    if dto:
        try:
            out["taken_at"] = dto.decode("ascii")
        except (AttributeError, UnicodeDecodeError):
            out["taken_at"] = None

    gps_ifd = exif_dict.get("GPS", {})
    lat_dms = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
    lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, b"N")
    lon_dms = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
    lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, b"E")
    if lat_dms and lon_dms:
        out["gps_lat"] = _dms_to_decimal(lat_dms, lat_ref)
        out["gps_lon"] = _dms_to_decimal(lon_dms, lon_ref)

    # Serialize a compact, JSON-friendly EXIF blob (bytes → str).
    try:
        flat = {
            section: {str(tag): _coerce_json(value) for tag, value in tags.items()}
            for section, tags in exif_dict.items() if isinstance(tags, dict)
        }
        out["exif_json"] = json.dumps(flat, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        LOG.debug("exif json serialize failed: %s", e)

    return out


def _coerce_json(value):
    if isinstance(value, bytes):
        try:
            return value.decode("ascii", errors="replace")
        except Exception:  # noqa: BLE001
            return None
    if isinstance(value, tuple):
        return list(value)
    return value


def extract_video_meta(content: bytes) -> dict:
    """Run ffprobe on a temp file, return duration/codec/bitrate/fps/dims."""
    out: dict = {
        "duration_sec": None, "codec": None, "bitrate": None,
        "fps": None, "width": None, "height": None, "ffprobe_json": None,
    }
    if shutil.which("ffprobe") is None:
        LOG.warning("ffprobe not in PATH; install ffmpeg in the spark image")
        return out
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(tmp_path)],
            check=True, capture_output=True, text=True, timeout=15,
        )
        probe = json.loads(proc.stdout)
        out["ffprobe_json"] = proc.stdout

        v_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
        if v_streams:
            v = v_streams[0]
            out["codec"] = v.get("codec_name")
            out["width"] = v.get("width")
            out["height"] = v.get("height")
            fps_str = v.get("avg_frame_rate", "0/0")
            try:
                num, den = (int(p) for p in fps_str.split("/"))
                out["fps"] = round(num / den, 3) if den else None
            except (ValueError, ZeroDivisionError):
                out["fps"] = None

        fmt = probe.get("format", {})
        try:
            out["duration_sec"] = round(float(fmt["duration"]), 3)
        except (KeyError, TypeError, ValueError):
            pass
        try:
            out["bitrate"] = int(fmt["bit_rate"])
        except (KeyError, TypeError, ValueError):
            pass
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        LOG.warning("ffprobe failed: %s", e)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    return out


def make_thumbnail(content: bytes, *, kind: str) -> bytes | None:
    """Generate a 256x256 PNG thumbnail. Returns None on failure (caller decides)."""
    if kind == "image":
        return _image_thumbnail(content)
    if kind == "video":
        return _video_thumbnail(content)
    return None


def _image_thumbnail(content: bytes) -> bytes | None:
    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img)
        img.thumbnail(THUMB_SIZE)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:  # noqa: BLE001
        LOG.warning("image thumbnail failed: %s", e)
        return None


def _video_thumbnail(content: bytes) -> bytes | None:
    if shutil.which("ffmpeg") is None:
        LOG.warning("ffmpeg not in PATH; cannot thumbnail video")
        return None
    src: Path | None = None
    dst: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as s:
            s.write(content)
            src = Path(s.name)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as d:
            dst = Path(d.name)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-ss", "1", "-i", str(src),
             "-vframes", "1",
             "-vf", f"scale={THUMB_SIZE[0]}:{THUMB_SIZE[1]}:force_original_aspect_ratio=decrease",
             str(dst)],
            check=True, timeout=20,
        )
        return dst.read_bytes()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        LOG.warning("video thumbnail failed: %s", e)
        return None
    finally:
        for p in (src, dst):
            if p is not None:
                p.unlink(missing_ok=True)
