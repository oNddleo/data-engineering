"""
CLI entry-point for the column-encryption-pipeline.

Sub-commands:
  encrypt   Encrypt specified columns in a JSON record.
  decrypt   Decrypt an EncryptedRecord JSON file / stdin.
  rotate    Rotate the CMK for a customer (creates new CMK version).
  forget    Crypto-shred all data for a customer (delete CMKs).

All state (KMS + RecordStore) is held in-memory for this process; the CLI is
primarily useful for smoke-testing and demonstration purposes.

Usage examples::

    colenc encrypt --customer cust1 --columns ssn,email '{"ssn":"123","email":"a@b.c","id":1}'
    colenc decrypt --record-id <uuid>
    colenc rotate --customer cust1
    colenc forget --customer cust1
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace

from colenc.engine import EncryptionEngine
from colenc.kms import LocalKMS
from colenc.rtbf import CryptoShredder
from colenc.storage import RecordStore


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="colenc",
        description="Column-level encryption pipeline (stdlib-only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- encrypt --
    enc_p = sub.add_parser("encrypt", help="Encrypt PII columns in a JSON record.")
    enc_p.add_argument("--customer", required=True, help="Customer ID.")
    enc_p.add_argument(
        "--columns",
        default=None,
        help="Comma-separated column names to encrypt.  Defaults to built-in PII set.",
    )
    enc_p.add_argument(
        "record_json",
        nargs="?",
        default=None,
        help="JSON record string (or omit to read from stdin).",
    )

    # -- decrypt --
    dec_p = sub.add_parser("decrypt", help="Decrypt an EncryptedRecord JSON.")
    dec_p.add_argument(
        "record_json",
        nargs="?",
        default=None,
        help="EncryptedRecord JSON string (or omit to read from stdin).",
    )
    dec_p.add_argument(
        "--columns",
        default=None,
        help="Comma-separated columns to decrypt.  Defaults to all encrypted columns.",
    )

    # -- rotate --
    rot_p = sub.add_parser("rotate", help="Rotate CMK for a customer.")
    rot_p.add_argument("--customer", required=True, help="Customer ID.")

    # -- forget --
    frg_p = sub.add_parser("forget", help="Crypto-shred all data for a customer.")
    frg_p.add_argument("--customer", required=True, help="Customer ID.")
    frg_p.add_argument(
        "--delete-records",
        action="store_true",
        default=False,
        help="Also purge physical records from the in-memory store.",
    )

    return parser


# Shared process-level state (reset on each process start; tests use fresh instances).
_kms = LocalKMS()
_store = RecordStore()
_engine = EncryptionEngine(kms=_kms)
_shredder = CryptoShredder(kms=_kms, store=_store)


def _cmd_encrypt(args: Namespace) -> int:
    raw = args.record_json or sys.stdin.read()
    record: dict[str, object] = json.loads(raw)
    customer_id: str = args.customer

    # Ensure CMK exists for the customer.
    try:
        _kms.get_active_cmk(customer_id)
    except Exception:
        _kms.generate_cmk(customer_id)

    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None
    enc = _engine.encrypt_record(record, customer_id, columns)
    _store.put(enc)
    print(enc.to_json())
    return 0


def _cmd_decrypt(args: Namespace) -> int:
    raw = args.record_json or sys.stdin.read()
    from colenc.storage import EncryptedRecord

    enc = EncryptedRecord.from_json(raw)
    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None
    plain = _engine.decrypt_record(enc, columns)
    print(json.dumps(plain, indent=2))
    return 0


def _cmd_rotate(args: Namespace) -> int:
    customer_id: str = args.customer
    old_cmk_id, new_cmk_id = _kms.rotate_cmk(customer_id)
    # Re-wrap all in-memory records for this customer.
    records = _store.list_for_customer(customer_id)
    for rec in records:
        updated = _engine.re_encrypt_record(rec, new_cmk_id)
        _store.put(updated)
    result = {
        "customer_id": customer_id,
        "old_cmk_id": old_cmk_id,
        "new_cmk_id": new_cmk_id,
        "records_rotated": len(records),
    }
    print(json.dumps(result, indent=2))
    return 0


def _cmd_forget(args: Namespace) -> int:
    result = _shredder.forget_customer(
        args.customer,
        delete_records=args.delete_records,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


def main() -> None:
    """Entry-point registered in pyproject.toml as ``colenc``."""
    parser = _build_parser()
    args = parser.parse_args()
    dispatch = {
        "encrypt": _cmd_encrypt,
        "decrypt": _cmd_decrypt,
        "rotate": _cmd_rotate,
        "forget": _cmd_forget,
    }
    handler = dispatch[args.command]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
