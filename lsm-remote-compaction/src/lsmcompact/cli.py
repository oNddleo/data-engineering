"""CLI entry point for lsmcompact.

Sub-commands
------------
put KEY VALUE   — insert / update a key
get KEY         — retrieve a value
scan START END  — list key/value pairs in range [START, END)
compact         — trigger immediate compaction
stats           — print level and MemTable statistics

The database directory defaults to ``./lsmdata`` and can be overridden with
``--db-dir``.

Examples::

    lsmcompact put hello world
    lsmcompact get hello
    lsmcompact scan a z
    lsmcompact compact
    lsmcompact stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lsmcompact.node import LSMNode


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lsmcompact",
        description="LSM-tree storage engine CLI",
    )
    parser.add_argument(
        "--db-dir",
        default="lsmdata",
        metavar="DIR",
        help="Path to the database directory (default: ./lsmdata)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # put
    p_put = sub.add_parser("put", help="Insert or update KEY with VALUE")
    p_put.add_argument("key", help="Key to insert")
    p_put.add_argument("value", help="Value to associate with KEY")

    # get
    p_get = sub.add_parser("get", help="Retrieve the value for KEY")
    p_get.add_argument("key", help="Key to look up")

    # scan
    p_scan = sub.add_parser("scan", help="List all key/value pairs in [START, END)")
    p_scan.add_argument("start", help="Start of range (inclusive)")
    p_scan.add_argument("end", help="End of range (exclusive)")

    # compact
    sub.add_parser("compact", help="Trigger an immediate L0 compaction")

    # stats
    sub.add_parser("stats", help="Print storage statistics")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns an exit code (0 = success)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    db_dir = Path(args.db_dir)

    with LSMNode(db_dir) as node:
        if args.command == "put":
            node.put(args.key, args.value)
            print(f"OK  {args.key!r} → {args.value!r}")

        elif args.command == "get":
            val = node.get(args.key)
            if val is None:
                print(f"NOT FOUND  {args.key!r}", file=sys.stderr)
                return 1
            print(val)

        elif args.command == "scan":
            pairs = node.scan(args.start, args.end)
            for k, v in pairs:
                print(f"{k}\t{v}")

        elif args.command == "compact":
            node.compact()
            print("Compaction complete.")

        elif args.command == "stats":
            data = node.stats()
            print(json.dumps(data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
