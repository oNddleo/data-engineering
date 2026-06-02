"""CLI: schemreg."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_info(_args: argparse.Namespace) -> None:
    from schemreg.registry import CompatibilityMode

    print(
        json.dumps(
            {
                "name": "schema-registry-lite",
                "version": "0.1.0",
                "compatibility_modes": [m.value for m in CompatibilityMode],
            }
        )
    )


def _cmd_check(args: argparse.Namespace) -> None:
    from schemreg.registry import CompatibilityMode, check_compatibility

    old = json.loads(args.old_schema)
    new = json.loads(args.new_schema)
    mode = CompatibilityMode(args.mode)
    errors = check_compatibility(old, new, mode)
    print(json.dumps({"compatible": not errors, "mode": mode.value, "violations": errors}))


def _cmd_demo(_args: argparse.Namespace) -> None:
    from schemreg.registry import CompatibilityMode, SchemaRegistry

    reg = SchemaRegistry(mode=CompatibilityMode.BACKWARD)
    v1 = reg.register("orders", {"id": "int", "amount": "float"}, now_ms=1000)
    v2 = reg.register("orders", {"id": "int", "amount": "float", "?note": "str"}, now_ms=2000)
    print(
        json.dumps(
            {
                "subject": "orders",
                "versions": reg.list_versions("orders"),
                "v1_fields": list(v1.schema),
                "v2_fields": list(v2.schema),
            }
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="schemreg")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info")
    sub.add_parser("demo")

    cp = sub.add_parser("check", help="Check schema compatibility")
    cp.add_argument("--old-schema", required=True, dest="old_schema")
    cp.add_argument("--new-schema", required=True, dest="new_schema")
    cp.add_argument("--mode", default="BACKWARD")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "info":
            _cmd_info(args)
        elif args.cmd == "demo":
            _cmd_demo(args)
        elif args.cmd == "check":
            _cmd_check(args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
