#!/usr/bin/env python3
"""Prepare or verify one private, evidence-bound weekly analyst cycle."""
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
from alma.weekly_cycle import (  # noqa: E402
    cycle_status, start_cycle, start_cycle_from_source_pack, verify_cycle,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="freeze verified evidence and analyst requests")
    start.add_argument("--source-pack", type=Path)
    start.add_argument("--workspace", type=Path)
    start.add_argument("--mart-bundle", type=Path)
    start.add_argument("--workbook", type=Path,
                       help="reserved for Phase 4; direct workbook intake is unavailable")
    start.add_argument("--operating-root", type=Path, default=ROOT / ".local")
    start.add_argument("--mart-root", type=Path, default=ROOT / ".local" / "operating-marts")
    start.add_argument("--output-root", type=Path, required=True)
    start.add_argument("--role", action="append", dest="roles")
    for command in ("status", "verify"):
        subparser = commands.add_parser(command, help=f"{command} an existing private cycle")
        subparser.add_argument("--cycle", required=True, type=Path)
    return parser


def _receipt(state: dict[str, object]) -> dict[str, object]:
    destination = Path(str(state["destination"]))
    roles = state["expected_roles"]
    assert isinstance(roles, dict)
    return {key: state[key] for key in ("version", "cut_id", "run_id", "status",
        "input_route", "current_cut_sha256", "manifest_sha256", "mart_bundle_sha256",
        "task_bundle_sha256")} | {
        "destination": str(destination),
        "requests": {role: str(destination / "tasks" / f"{role}.request.json")
                     for role in sorted(roles)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "start":
            if args.workbook is not None:
                raise ValueError("direct workbook preparation belongs to Phase 4")
            if args.source_pack is not None and args.workspace is None and args.mart_bundle is None:
                state = start_cycle_from_source_pack(args.source_pack, args.operating_root,
                    args.mart_root, args.output_root, args.roles)
            elif args.source_pack is None and args.workspace is not None and args.mart_bundle is not None:
                state = start_cycle(args.workspace, args.mart_bundle, args.output_root, args.roles)
            else:
                raise ValueError("select exactly one route: --source-pack or --workspace with --mart-bundle")
        elif args.command == "status":
            state = cycle_status(args.cycle)
        else:
            state = verify_cycle(args.cycle)
    except (OperatingContractError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # Verification failures can embed private evidence paths; expose a stable code only.
        code = (str(exc) if isinstance(exc, ValueError) and
                str(exc) in {"direct workbook preparation belongs to Phase 4",
                             "select exactly one route: --source-pack or --workspace with --mart-bundle"}
                else "cycle_verification_failed")
        print(json.dumps({"status": "ERROR", "code": code}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(_receipt(state), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
