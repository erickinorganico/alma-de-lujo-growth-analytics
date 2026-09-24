#!/usr/bin/env python3
"""Validate or build a private operating-v1 analytical source workspace."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.operating_contracts import OperatingContractError  # noqa: E402
from alma.operating_interchange import parse_pack  # noqa: E402
from alma.operating_workspace import build_operating_workspace  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "build"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True, type=Path)
        subparser.add_argument("--private-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            parsed = parse_pack(args.input, private_root=args.private_root)
            receipt = {
                "status": "PASS",
                "contract_version": parsed["metadata"]["contract_version"],
                "sources": len(parsed["tables"]),
                "normalized_rows_digest": parsed["normalized_rows_digest"],
            }
        else:
            built = build_operating_workspace(args.input, private_root=args.private_root)
            receipt = {
                "status": built["status"],
                "cut_id": built["cut_id"],
                "destination": built["destination"],
            }
    except OperatingContractError as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "location": exc.location}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
