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
    record_dispatch, submit_response, resume_cycle, read_terminal_packet,
    export_acceptance_receipt, verify_acceptance_receipt,
)
from alma.native_agents_v1 import execute_registered_query  # noqa: E402
from alma.operating_contracts import canonical_json  # noqa: E402


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
    for command in ("status", "verify", "resume", "packet"):
        subparser = commands.add_parser(command, help=f"{command} an existing private cycle")
        subparser.add_argument("--cycle", required=True, type=Path)
    record = commands.add_parser("record", help="validate and record parent native dispatch metadata")
    submit = commands.add_parser("submit", help="accept a recorded native response")
    for subparser in (record, submit):
        subparser.add_argument("--cycle", required=True, type=Path)
        subparser.add_argument("--role", required=True)
        subparser.add_argument("--response", required=True, type=Path)
        subparser.add_argument("--query-trace", required=True, type=Path)
    record.add_argument("--receipt-fields", required=True, type=Path)
    submit.add_argument("--receipt", required=True, type=Path)
    query = commands.add_parser("query", help="run one registered read-only frozen-metric lookup")
    query.add_argument("--request", required=True, type=Path)
    query.add_argument("--reconciliation-id", required=True)
    export = commands.add_parser("export-acceptance", help="project verified synthetic metadata only")
    export.add_argument("--cycle", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    acceptance = commands.add_parser("verify-acceptance", help="compare public receipt to private state")
    acceptance.add_argument("--receipt", required=True, type=Path)
    acceptance.add_argument("--output-root", type=Path,
                            default=ROOT / ".local" / "weekly-cycles")
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
        "accepted": {role: {key: item[key] for key in ("response_sha256",
                     "query_trace_sha256", "dispatch_sha256")}
                     for role, item in sorted(state["accepted_roles"].items())},
        "reviewer_request_sha256": state.get("reviewer_request_sha256"),
        "terminal_packet_sha256": state.get("packet_sha256"),
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
        elif args.command == "verify":
            state = verify_cycle(args.cycle)
        elif args.command == "resume":
            state = resume_cycle(args.cycle)
        elif args.command == "record":
            if (".." in args.receipt_fields.parts or args.receipt_fields.is_symlink() or
                args.receipt_fields.stat().st_size > 1024 * 1024):
                raise ValueError("invalid parent receipt fields path")
            fields_raw = args.receipt_fields.read_bytes()
            fields = json.loads(fields_raw)
            if fields_raw != canonical_json(fields):
                raise ValueError("noncanonical parent receipt fields")
            recorded = record_dispatch(args.cycle, args.role, args.response,
                                       args.query_trace, fields)
            print(json.dumps({"status": "RECORDED", "role": args.role,
                              "request_id": recorded["request_id"],
                              "response_sha256": recorded["response_sha256"],
                              "query_trace_sha256": recorded["query_trace_sha256"]},
                             sort_keys=True, separators=(",", ":")))
            return 0
        elif args.command == "submit":
            state = submit_response(args.cycle, args.role, args.response,
                                    args.query_trace, args.receipt)
        elif args.command == "packet":
            packet = read_terminal_packet(args.cycle)
            state = verify_cycle(args.cycle)
            print(json.dumps({"version": packet["version"], "status": packet["status"],
                              "cut_id": packet["cut_id"], "run_id": packet["run_id"],
                              "terminal_packet_sha256": state["packet_sha256"],
                              "packet_path": str(Path(args.cycle) / "decision-packet.json")},
                             sort_keys=True, separators=(",", ":")))
            return 0
        elif args.command == "query":
            request_path = args.request.resolve(strict=True)
            if request_path.parent.name != "tasks":
                raise ValueError("query requires a private cycle request")
            verify_cycle(request_path.parent.parent)
            request = json.loads(request_path.read_bytes())
            if request_path.name != f"{request['role']}.request.json" or \
                    request_path.read_bytes() != canonical_json(request):
                raise ValueError("query request differs from frozen bytes")
            print(json.dumps(execute_registered_query(request, args.reconciliation_id),
                             sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            return 0
        elif args.command == "export-acceptance":
            receipt = export_acceptance_receipt(args.cycle, args.output)
            print(json.dumps({"status": receipt["terminal_status"],
                              "cut_id": receipt["cut_id"], "run_id": receipt["run_id"],
                              "output": str(args.output)}, sort_keys=True, separators=(",", ":")))
            return 0
        else:
            print(json.dumps(verify_acceptance_receipt(args.receipt, args.output_root),
                             sort_keys=True, separators=(",", ":")))
            return 0
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
