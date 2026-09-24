#!/usr/bin/env python3
"""Manage one private Alma de Lujo owner decision register."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.decision_register import (  # noqa: E402
    append_status, carry_forward, close_decision, create_register, export_csv,
    extend_decision, import_proposals, register_decision, verify_register,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--register", type=Path, required=True)
    init.add_argument("--register-id", required=True)
    init.add_argument("--owner-role", action="append", required=True)
    register = commands.add_parser("register")
    register.add_argument("--register", type=Path, required=True)
    register.add_argument("--cycle", type=Path, required=True)
    register.add_argument("--recommendation-id", required=True)
    register.add_argument("--owner-role", required=True)
    register.add_argument("--due-date", required=True)
    register.add_argument("--choice", required=True)
    register.add_argument("--closure-check", type=Path, required=True)
    advance = commands.add_parser("advance")
    advance.add_argument("--register", type=Path, required=True)
    advance.add_argument("--decision-id", required=True)
    advance.add_argument("--status", required=True)
    advance.add_argument("--owner-role", required=True)
    advance.add_argument("--note-code")
    extend = commands.add_parser("extend")
    extend.add_argument("--register", type=Path, required=True)
    extend.add_argument("--decision-id", required=True)
    extend.add_argument("--new-due-date", required=True)
    extend.add_argument("--owner-role", required=True)
    extend.add_argument("--note-code", required=True)
    carry = commands.add_parser("carry")
    carry.add_argument("--register", type=Path, required=True)
    carry.add_argument("--cycle", type=Path, required=True)
    carry.add_argument("--prior-anchor", type=Path, required=True)
    close = commands.add_parser("close")
    close.add_argument("--register", type=Path, required=True)
    close.add_argument("--decision-id", required=True)
    close.add_argument("--cycle", type=Path, required=True)
    close.add_argument("--closure-evidence", type=Path, required=True)
    close.add_argument("--owner-attestation", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("--register", type=Path, required=True)
    verify.add_argument("--expected-anchor", type=Path)
    export = commands.add_parser("export-csv")
    export.add_argument("--register", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    proposals = commands.add_parser("import-proposals")
    proposals.add_argument("--register", type=Path, required=True)
    proposals.add_argument("--csv", type=Path, required=True)
    return parser


def _json_file(path: Path) -> dict:
    if ".." in path.parts or path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("invalid private JSON input")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("private JSON input must be an object")
    return value


def _register_file(path: Path, register: Path, expected_name: str | None = None) -> Path:
    if ".." in path.parts or path.is_symlink():
        raise ValueError("invalid private register file")
    resolved = path.resolve(strict=False)
    if resolved.parent != register.resolve(strict=True) or (expected_name and resolved.name != expected_name):
        raise ValueError("file must remain inside the private register")
    return resolved


def _safe(result: dict) -> dict:
    anchor = result.get("anchor", result)
    output = {key: result[key] for key in ("decision_id", "event_id", "status") if key in result}
    if isinstance(anchor, dict):
        output.update({key: anchor[key] for key in
                       ("register_id", "event_count", "terminal_hash") if key in anchor})
    return output


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            register = create_register(args.register, args.register_id, args.owner_role)
            result = verify_register(register)
        elif args.command == "register":
            check_path = _register_file(args.closure_check, args.register)
            result = register_decision(args.register, args.cycle, args.recommendation_id,
                args.owner_role, args.due_date, args.choice, _json_file(check_path))
        elif args.command == "advance":
            result = append_status(args.register, args.decision_id, args.status,
                                   args.owner_role, args.note_code)
        elif args.command == "extend":
            result = extend_decision(args.register, args.decision_id, args.new_due_date,
                                     args.owner_role, args.note_code)
        elif args.command == "carry":
            result = carry_forward(args.register, args.cycle, args.prior_anchor)
        elif args.command == "close":
            evidence_path = _register_file(args.closure_evidence, args.register)
            attestation_path = (_register_file(args.owner_attestation, args.register)
                                if args.owner_attestation else None)
            result = close_decision(args.register, args.decision_id, args.cycle,
                _json_file(evidence_path), _json_file(attestation_path) if attestation_path else None)
        elif args.command == "verify":
            result = verify_register(args.register, args.expected_anchor)
        elif args.command == "export-csv":
            result = export_csv(args.register,
                _register_file(args.output, args.register, "REGISTRO_DECISIONES.csv"))
            result = {"status": result["status"], "rows": result["rows"],
                      "sha256": result["sha256"], "anchor": result["anchor"]}
        else:
            rows = import_proposals(args.register,
                _register_file(args.csv, args.register, "DECISION_PROPOSALS.csv"))
            result = {"status": "PROPOSALS_VALID", "rows": len(rows),
                      "anchor": verify_register(args.register)["anchor"]}
        print(json.dumps(_safe(result) | ({"rows": result["rows"]} if "rows" in result else {}),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        print(json.dumps({"status": "ERROR", "code": "decision_register_verification_failed"},
                         sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
