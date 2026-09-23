#!/usr/bin/env python3
"""Verify, export, or restore one private operating-v1 cut."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.operating_archive import export_cut, verify_cut  # noqa: E402
from alma.operating_contracts import OperatingContractError  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Local commands: verify --cut CUT; export --cut CUT --output ARCHIVE; "
            "restore --archive ARCHIVE --destination CUT (available after restore support is installed)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="verify a live private cut")
    verify.add_argument("--cut", required=True, type=Path)
    verify.add_argument("--private-root", type=Path)
    export = subparsers.add_parser("export", help="verify and export a private cut")
    export.add_argument("--cut", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--private-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify":
            receipt = verify_cut(args.cut, private_root=args.private_root)
        else:
            receipt = export_cut(args.cut, args.output, private_root=args.private_root)
    except OperatingContractError as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "location": exc.location}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
