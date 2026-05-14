"""``ekycpipe`` command-line interface."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ekycpipe.bca import BCARecord
    from ekycpipe.schema import OCRResult


def cmd_info(_args: argparse.Namespace) -> int:
    from ekycpipe import __version__

    print(f"ekyc-document-pipeline {__version__}")
    return 0


def cmd_parse_cccd(args: argparse.Namespace) -> int:
    from ekycpipe.cccd import CCCDFormatError, parse_cccd
    from ekycpipe.provinces import province_name

    try:
        f = parse_cccd(args.cccd)
    except CCCDFormatError as e:
        print(f"invalid CCCD: {e}", file=sys.stderr)
        return 2
    print(f"province     = {f.province_code} ({province_name(f.province_code)})")
    print(f"gender       = {f.gender.value}")
    print(f"century      = {f.century}xx")
    print(f"birth_year   = {f.birth_year}")
    print(f"serial       = {f.serial}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from ekycpipe.simulator import generate

    anomalies = [a.strip() for a in (args.anomalies or "").split(",") if a.strip()]
    image_to_ocr, bca = generate(n_citizens=args.citizens, seed=args.seed, anomalies=anomalies)
    payload = {
        "images": [
            {"image": image.decode("latin-1"), "ocr": _ocr_to_dict(ocr)}
            for image, ocr in image_to_ocr.items()
        ],
        "bca": [_bca_to_dict(r) for r in bca],
    }
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(
            f"wrote {len(image_to_ocr)} OCR rows + {len(bca)} BCA records to {args.output}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from ekycpipe.bca import BCADatabase
    from ekycpipe.encryption import SENSITIVE_COLUMNS, KeyManager
    from ekycpipe.ocr import MockOCREngine
    from ekycpipe.pipeline import process_image

    payload = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    image_to_ocr = {
        item["image"].encode("latin-1"): _ocr_from_dict(item["ocr"]) for item in payload["images"]
    }
    bca = BCADatabase([_bca_from_dict(r) for r in payload["bca"]])
    ocr_engine = MockOCREngine(image_to_ocr)

    km: KeyManager | None = None
    policies: dict[str, str] | None = None
    if args.with_encryption:
        # Per-column keys derived deterministically from a seed for demo purposes.
        seed = args.encryption_seed.encode("utf-8")
        keys = {col: _derive_demo_key(seed, col) for col in SENSITIVE_COLUMNS}
        km = KeyManager(keys)
        policies = {col: col for col in SENSITIVE_COLUMNS}

    processed = 0
    valid = 0
    encrypted_count = 0
    errors: list[dict[str, object]] = []
    for image in image_to_ocr:
        result = process_image(image, ocr=ocr_engine, bca=bca, key_manager=km, policies=policies)
        processed += 1
        if result.validation.is_valid:
            valid += 1
        if result.encrypted is not None:
            encrypted_count += 1
        for err in result.validation.errors:
            errors.append({"cccd": result.ocr.cccd, "error": err})
    summary: dict[str, object] = {
        "processed": processed,
        "valid": valid,
        "encrypted": encrypted_count,
        "errors": errors,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_demo_keygen(args: argparse.Namespace) -> int:
    """Print one fresh 32-byte hex key — for ad-hoc encryption demos."""
    print(secrets.token_hex(32))
    return 0


# ---------------------------------------------------------------------------
# Helpers


def _ocr_to_dict(ocr: OCRResult) -> dict[str, object]:
    return {
        "cccd": ocr.cccd,
        "full_name": ocr.full_name,
        "date_of_birth": ocr.date_of_birth,
        "gender": ocr.gender,
        "hometown": ocr.hometown,
        "place_of_residence": ocr.place_of_residence,
        "issued_at": ocr.issued_at,
        "expires_at": ocr.expires_at,
        "confidence": ocr.confidence,
    }


def _ocr_from_dict(d: dict[str, Any]) -> OCRResult:
    from ekycpipe.schema import OCRResult

    raw_conf = d.get("confidence")
    confidence: float | None = (
        float(raw_conf)
        if isinstance(raw_conf, int | float) and not isinstance(raw_conf, bool)
        else None
    )
    return OCRResult(
        cccd=_s_or_none(d.get("cccd")),
        full_name=_s_or_none(d.get("full_name")),
        date_of_birth=_s_or_none(d.get("date_of_birth")),
        gender=_s_or_none(d.get("gender")),
        hometown=_s_or_none(d.get("hometown")),
        place_of_residence=_s_or_none(d.get("place_of_residence")),
        issued_at=_s_or_none(d.get("issued_at")),
        expires_at=_s_or_none(d.get("expires_at")),
        confidence=confidence,
    )


def _s_or_none(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return str(v)


def _bca_to_dict(r: BCARecord) -> dict[str, object]:
    return {
        "cccd": r.cccd,
        "full_name": r.full_name,
        "date_of_birth": r.date_of_birth.isoformat(),
        "gender": r.gender.value,
        "hometown_province_code": r.hometown_province_code,
    }


def _bca_from_dict(d: dict[str, Any]) -> BCARecord:
    from datetime import date

    from ekycpipe.bca import BCARecord
    from ekycpipe.schema import Gender

    return BCARecord(
        cccd=str(d["cccd"]),
        full_name=str(d["full_name"]),
        date_of_birth=date.fromisoformat(str(d["date_of_birth"])),
        gender=Gender(str(d["gender"])),
        hometown_province_code=str(d["hometown_province_code"]),
    )


def _derive_demo_key(seed: bytes, column: str) -> bytes:
    import hashlib

    return hashlib.sha256(seed + b"|" + column.encode("utf-8")).digest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="ekycpipe",
        description="eKYC pipeline for Vietnamese CCCD documents with BCA cross-check + column-level encryption.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(func=cmd_info)

    pc = sub.add_parser("parse-cccd", help="decode the fields embedded in a CCCD number")
    pc.add_argument("cccd")
    pc.set_defaults(func=cmd_parse_cccd)

    sim = sub.add_parser("simulate", help="emit a synthetic OCR + BCA dataset")
    sim.add_argument("--citizens", type=int, default=20)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument(
        "--anomalies",
        default="",
        help="comma list: name_mismatch,dob_mismatch,gender_mismatch,not_in_bca,bad_cccd",
    )
    sim.add_argument("--output", default=None)
    sim.set_defaults(func=cmd_simulate)

    rn = sub.add_parser("run", help="run the pipeline over a dataset and summarise outcomes")
    rn.add_argument("--dataset", required=True)
    rn.add_argument("--with-encryption", dest="with_encryption", action="store_true")
    rn.add_argument(
        "--encryption-seed",
        dest="encryption_seed",
        default="demo-key-seed",
        help="passphrase from which per-column demo keys are derived (development only)",
    )
    rn.set_defaults(func=cmd_run)

    kg = sub.add_parser("demo-keygen", help="print one fresh 32-byte hex key")
    kg.set_defaults(func=cmd_demo_keygen)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
