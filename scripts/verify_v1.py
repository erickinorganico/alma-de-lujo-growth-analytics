#!/usr/bin/env python3
"""Fail-closed v1 release checks and two-cut native evidence verification.

Preparation never dispatches a model. Live completion requires 6 distinct analyst
tasks and a subsequent distinct reviewer task for EACH cut: 14 tasks in all.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.operating_contracts import canonical_json  # noqa: E402
from alma.weekly_cycle import DEFAULT_ROLES, ROLE_MODELS, start_cycle, verify_cycle  # noqa: E402
from alma.native_agents_v1 import validate_dispatch  # noqa: E402
from alma.weekly import _extended, _normal  # noqa: E402
from alma.operating_workspace import build_operating_workspace  # noqa: E402
from alma.operating_archive import verify_cut  # noqa: E402
from alma.operating_marts import build_operating_marts  # noqa: E402

SCENARIO = ROOT / "tests/fixtures/release_v1/two_week_scenario.json"
ROLES = ROOT / "agents/native-cycle-v1.roles.json"
SOURCE = ROOT / "client/source-packs/v1/synthetic"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TASK_ID = re.compile(r"/root/[a-z0-9_/-]{1,120}\Z")
PRIVATE_MARKERS = ("fixture", "test_fixture", "mock", "fake", "sample", "decision_")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_json(value):
        raise ValueError("noncanonical verification artifact")
    return value, raw


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json(value)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".verify-v1-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _relative(path: Path) -> str:
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(ROOT):
        raise ValueError("release output outside repository")
    return resolved.relative_to(ROOT).as_posix()


def _routing() -> dict[str, Any]:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    roles = json.loads(ROLES.read_bytes())
    phase3 = (ROOT / "agents/RUN-NATIVE-CYCLE-v1.md").read_text(encoding="utf-8")
    required = {"agents/RUN-NATIVE-CYCLE-v1.md", "agents/native-cycle-v1.roles.json",
                "scripts/run_weekly_cycle.py", "agents/RUN-NATIVE-CYCLE.md"}
    if not all(name in instructions for name in required) or \
            "historical v0.2 regression-only" not in instructions or \
            "14 native tasks total" not in instructions or \
            "six independent native Codex tasks" not in phase3:
        raise ValueError("aggregate-v1 route is not explicit")
    role_map = roles["roles"]
    if (set(role_map) != set(DEFAULT_ROLES) | {"evidence_reviewer"} or
            any(role_map[role]["model_family"] != ROLE_MODELS[role] for role in DEFAULT_ROLES) or
            role_map["evidence_reviewer"]["model_family"] != "astra" or
            roles["business_execution"] != "PROHIBITED"):
        raise ValueError("native role contract drift")
    return {"status": "PASS", "agents_sha256": _sha((ROOT / "AGENTS.md").read_bytes()),
            "roles_sha256": _sha(ROLES.read_bytes()), "analysts_per_cut": 6,
            "independent_reviews_per_cut": 1, "cuts": 2, "required_native_tasks": 14}


def _gate(name: str, arguments: list[str], *, timeout: int, artifact: Path | None = None) -> dict[str, Any]:
    start = time.monotonic()
    try:
        result = subprocess.run(arguments, cwd=ROOT, capture_output=True, timeout=timeout,
                                check=False)
        status = "PASS" if result.returncode == 0 else "FAIL"
        code = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        status, code = "BLOCKED", None
        stdout, stderr = b"", type(exc).__name__.encode("ascii")
    if status == "PASS" and artifact is not None and not artifact.is_file():
        status = "BLOCKED"
    return {"gate": name, "status": status, "command": [_relative(Path(arguments[0])) if
            Path(arguments[0]).is_absolute() and Path(arguments[0]).is_relative_to(ROOT) else
            ("python" if i == 0 else argument) for i, argument in enumerate(arguments)],
            "exit_code": code, "elapsed_seconds": round(time.monotonic() - start, 3),
            "stdout_sha256": _sha(stdout), "stderr_sha256": _sha(stderr),
            "output_sha256": _sha(artifact.read_bytes()) if status == "PASS" and
                             artifact and artifact.is_file() else None,
            "diagnostic": status if status == "PASS" else f"{name}:{status}"}


def deterministic(output: Path) -> dict[str, Any]:
    _relative(output)
    python = sys.executable
    work = ROOT / ".local/v1-acceptance/deterministic"
    work.mkdir(parents=True, exist_ok=True)
    try:
        routing = _routing()
        route_status = "PASS"
    except (ValueError, KeyError, OSError, json.JSONDecodeError):
        routing, route_status = {}, "FAIL"
    gates: list[dict[str, Any]] = [{"gate": "aggregate-v1-routing", "status": route_status,
                                   "contract": routing}]
    specs = [
        ("v0.2-full-suite-and-scenarios", [python, "scripts/verify_v2.py", "--output",
          ".local/v1-acceptance/deterministic/v2"], 1800,
         work / "v2/verification.json"),
        ("v0.2-scope", [python, "scripts/check_scope_v2.py", "--workspace",
          "evidence/v0.2/workspace", "--verification",
          ".local/v1-acceptance/deterministic/v2/verification.json", "--output",
          ".local/v1-acceptance/deterministic/scope.json"], 240, work / "scope.json"),
        ("v0.3-workbooks", [python, "scripts/verify_client_v3.py", "check", "--directory",
          "client", "--engine-receipt", "evidence/v0.3/excel/excel-recalculation.json",
          "--output", ".local/v1-acceptance/deterministic/workbooks.json"], 240, work / "workbooks.json"),
        ("historical-client", [python, "-m", "unittest", "tests.test_client_system", "-q"], 300, None),
        ("v1-portal-and-package", [python, "-m", "unittest", "tests.test_offline_portal_v1",
          "tests.test_weekly_kit", "-q"], 600, None),
        ("v1-matrix", [python, "-m", "unittest", "tests.test_v1_release_acceptance", "-q"], 600, None),
        ("client-system", [python, "scripts/build_client_system.py", "--check"], 120, None),
        ("public-scope", [python, "scripts/audit_release.py"], 180, None),
    ]
    for name, command, timeout, artifact in specs:
        if name == "v0.2-scope" and gates[-1]["status"] != "PASS":
            gates.append({"gate": name, "status": "BLOCKED", "diagnostic": "v0.2 prerequisite failed"})
            continue
        if artifact is not None:
            artifact.unlink(missing_ok=True)
        gates.append(_gate(name, command, timeout=timeout, artifact=artifact))
    counts = {state: sum(item["status"] == state for item in gates)
              for state in ("PASS", "FAIL", "BLOCKED")}
    overall = "FAIL" if counts["FAIL"] else "BLOCKED" if counts["BLOCKED"] else "PASS"
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, check=False).stdout.strip()
    receipt = {"version": "v1.0-release-acceptance", "status": overall,
        "candidate_commit": commit if HEX64.fullmatch(commit) else None,
        "interpreter": platform.python_version(), "platform": platform.system(),
        "scenario_sha256": _sha(SCENARIO.read_bytes()), "roles_sha256": _sha(ROLES.read_bytes()),
        "counts": counts, "gates": gates,
        "external_gates": {"EXT-01": "UNKNOWN", "EXT-02": "UNKNOWN", "EXT-03": "REVIEW"},
        "native_execution": "NOT_RUN_BY_DETERMINISTIC_VERIFIER",
        "limits": "Synthetic release verification only. CI does not execute a model, prove owner adoption or authorize business action."}
    _atomic(output, receipt)
    return receipt


def _scenario_pack(base: Path, week: dict[str, Any]) -> Path:
    pack = base / "source-packs" / week["id"]
    shutil.copytree(SOURCE, pack)
    metadata = json.loads((pack / "metadata.json").read_bytes())
    metadata["cutoff_at"] = week["cutoff_at"]
    for item in metadata["coverage"].values():
        item["window_end"] = week["cutoff_at"][:10]
    _atomic(pack / "metadata.json", metadata)
    sales_path = pack / "sales_aggregates.csv"
    with sales_path.open(newline="", encoding="utf-8") as stream:
        sales = list(csv.DictReader(stream))
    sales[0].update({key: str(value) for key, value in week["sales"].items()})
    with sales_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(sales[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(sales)
    movements_path = pack / "inventory_movements.csv"
    with movements_path.open(newline="", encoding="utf-8") as stream:
        movements = list(csv.DictReader(stream))
    for row in movements:
        if row["movement_type"] == "SALE_OUT":
            row["units"] = str(week["sales"]["delivered_units"])
    with movements_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(movements[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(movements)
    return pack


def prepare_live(output: Path) -> dict[str, Any]:
    if output.exists() or ".local" not in output.parts or ".." in output.parts:
        raise ValueError("prepare-live requires a fresh ignored .local output")
    _relative(output)
    _routing()
    scenario = json.loads(SCENARIO.read_bytes())
    if scenario.get("evidence_class") != "TEST_FIXTURE" or len(scenario["weeks"]) != 2:
        raise ValueError("two-cut scenario contract missing")
    output.mkdir(parents=True)
    weeks = []
    for week in scenario["weeks"]:
        pack = _scenario_pack(output, week)
        stage = output / week["id"]
        cut = build_operating_workspace(pack, private_root=stage / "operating")
        verify_cut(cut["destination"], private_root=stage / "operating")
        mart_root = _extended(stage / ".local/operating-marts")
        mart = build_operating_marts(cut["destination"], mart_root,
            policy_path=ROOT / "policies/operating-metrics-synthetic-v1.json",
            private_root=mart_root)
        state = start_cycle(cut["destination"], mart["destination"],
            _extended(stage / ".local/weekly-cycles"), list(DEFAULT_ROLES))
        if state["status"] != "WAITING_ANALYSTS" or set(state["expected_roles"]) != set(DEFAULT_ROLES):
            raise ValueError("prepared task bundle incomplete")
        weeks.append({"id": week["id"], "cutoff_at": week["cutoff_at"],
            "source_pack": Path(pack).relative_to(output).as_posix(),
            "cycle": _normal(state["destination"]).relative_to(output).as_posix(),
            "cut_id": state["cut_id"], "run_id": state["run_id"],
            "current_cut_sha256": state["current_cut_sha256"],
            "task_bundle_sha256": state["task_bundle_sha256"]})
    if len({row["cut_id"] for row in weeks}) != 2 or \
            len({row["current_cut_sha256"] for row in weeks}) != 2:
        raise ValueError("second week is only a replay")
    index = {"version": "v1.0-native-preparation", "status": "WAITING_NATIVE_TASKS",
        "required_native_tasks": 14, "analysts_per_cut": 6, "reviewers_per_cut": 1,
        "roles_sha256": _sha(ROLES.read_bytes()), "scenario_sha256": _sha(SCENARIO.read_bytes()),
        "weeks": weeks, "native_execution": "NOT_YET_RUN"}
    _atomic(output / "run-index.json", index)
    return {"status": index["status"], "required_native_tasks": 14,
            "weeks": [{key: item[key] for key in ("id", "cut_id", "run_id", "cycle")}
                      for item in weeks]}


def _native_entry(cycle: Path, role: str, state: dict[str, Any]) -> dict[str, Any]:
    tasks = cycle / "tasks"
    request, request_raw = _read(tasks / f"{role}.request.json")
    response, response_raw = _read(tasks / f"{role}.response.json")
    trace, trace_raw = _read(tasks / f"{role}.query-trace.json")
    dispatch, dispatch_raw = _read(tasks / f"{role}.dispatch.json")
    validate_dispatch(request, response, trace, dispatch)
    identity = dispatch["agent_id"]
    if not TASK_ID.fullmatch(identity) or any(marker in identity.lower() for marker in PRIVATE_MARKERS) or \
            b"TEST_FIXTURE" in response_raw or b"TEST_FIXTURE" in trace_raw or \
            dispatch["mode"] != "live":
        raise ValueError("fixture or fabricated native task metadata")
    accepted = state["reviewer"] if role == "evidence_reviewer" else state["accepted_roles"][role]
    if (accepted["agent_id"] != identity or accepted["response_sha256"] != _sha(response_raw) or
            accepted["query_trace_sha256"] != _sha(trace_raw) or
            accepted["dispatch_sha256"] != _sha(dispatch_raw)):
        raise ValueError("accepted native artifact differs")
    return {"role": role, "agent_id": identity, "model": dispatch["model"],
        "started_at_utc": dispatch["started_at_utc"],
        "completed_at_utc": dispatch["completed_at_utc"],
        "request_sha256": _sha(request_raw), "response_sha256": _sha(response_raw),
        "query_trace_sha256": _sha(trace_raw), "dispatch_sha256": _sha(dispatch_raw)}


def finalize_live(run: Path, summary: Path) -> dict[str, Any]:
    if ".local" not in run.parts or ".." in run.parts:
        raise ValueError("live source must remain under .local")
    _relative(run)
    if _relative(summary) != "evidence/v1.0/two-week-native.json":
        raise ValueError("live public receipt must use the sanitized evidence path")
    index, _ = _read(run / "run-index.json")
    if (index.get("version") != "v1.0-native-preparation" or
            index.get("required_native_tasks") != 14 or len(index.get("weeks", [])) != 2 or
            index.get("roles_sha256") != _sha(ROLES.read_bytes()) or
            index.get("scenario_sha256") != _sha(SCENARIO.read_bytes())):
        raise ValueError("prepared run index changed")
    entries = []
    all_ids: set[str] = set()
    for week in index["weeks"]:
        cycle_path = (run / week["cycle"]).resolve(strict=True)
        if not cycle_path.is_relative_to(run.resolve(strict=True)):
            raise ValueError("cycle escaped private run")
        cycle = _extended(cycle_path)
        state = verify_cycle(cycle)
        if state["status"] != "READY_FOR_OWNER" or \
                set(state["expected_roles"]) != set(DEFAULT_ROLES) or \
                set(state["accepted_roles"]) != set(DEFAULT_ROLES) or \
                any(state[key] != week[key] for key in
                    ("cut_id", "run_id", "current_cut_sha256", "task_bundle_sha256")):
            raise ValueError("native week is incomplete or changed")
        analysts = [_native_entry(cycle, role, state) for role in DEFAULT_ROLES]
        reviewer = _native_entry(cycle, "evidence_reviewer", state)
        reviewer_start = datetime.fromisoformat(reviewer["started_at_utc"].replace("Z", "+00:00"))
        if any(reviewer_start < datetime.fromisoformat(item["completed_at_utc"].replace("Z", "+00:00"))
               for item in analysts):
            raise ValueError("reviewer started before accepted analysts completed")
        identities = {row["agent_id"] for row in [*analysts, reviewer]}
        if len(identities) != 7 or identities & all_ids:
            raise ValueError("native task identity reused")
        all_ids |= identities
        reviewer_request, reviewer_raw = _read(cycle / "tasks/evidence_reviewer.request.json")
        if _sha(reviewer_raw) != state["reviewer_request_sha256"] or \
                reviewer["request_sha256"] != state["reviewer_request_sha256"] or \
                reviewer_request["role"] != "evidence_reviewer":
            raise ValueError("frozen review request changed")
        packet, packet_raw = _read(cycle / "decision-packet.json")
        events, events_raw = _read(cycle / "events.json")
        if _sha(packet_raw) != state["packet_sha256"] or packet["status"] != "READY_FOR_OWNER" or \
                events[-1]["event_type"] != "REVIEW_ACCEPTED":
            raise ValueError("terminal packet or journal changed")
        entries.append({"id": week["id"], "cutoff_at": week["cutoff_at"],
            "cut_id": state["cut_id"], "run_id": state["run_id"],
            "status": state["status"], "current_cut_sha256": state["current_cut_sha256"],
            "manifest_sha256": state["manifest_sha256"],
            "mart_bundle_sha256": state["mart_bundle_sha256"],
            "task_bundle_sha256": state["task_bundle_sha256"],
            "analysts": analysts, "reviewer": reviewer,
            "reviewer_request_sha256": _sha(reviewer_raw),
            "terminal_packet_sha256": _sha(packet_raw), "journal_sha256": _sha(events_raw),
            "challenge_disposition": packet["status"]})
    if len({row["cut_id"] for row in entries}) != 2 or \
            len({row["current_cut_sha256"] for row in entries}) != 2:
        raise ValueError("second native cut is only a replay")
    # Decision continuity requires a separately verified register. A terminal
    # packet alone cannot claim a reviewed decision reached later-cut closure.
    from alma.decision_register import verify_register
    register = run / ".local/decision-register/weekly"
    checked = verify_register(register)
    decisions = checked["decisions"]
    def _is_later_closure(item: dict[str, Any]) -> bool:
        evidence = item.get("closure_evidence")
        return (item["status"] == "CLOSED" and item["cut_id"] == entries[0]["cut_id"] and
                isinstance(evidence, dict) and evidence.get("cut_id") == entries[1]["cut_id"] and
                evidence.get("current_cut_sha256") == entries[1]["current_cut_sha256"])
    if not any(_is_later_closure(item) for item in decisions):
        raise ValueError("week-one decision has no verified later-cut closure")
    receipt = {"version": "v1.0-native-acceptance", "status": "PASS",
        "synthetic_business_data": True, "required_native_tasks": 14,
        "verified_native_tasks": len(all_ids), "weeks": entries,
        "decision_register_anchor_sha256": _sha(canonical_json(checked["anchor"])),
        "closed_week_one_decisions": sum(_is_later_closure(item) for item in decisions),
        "external_gates": {"EXT-01": "UNKNOWN", "EXT-02": "UNKNOWN", "EXT-03": "REVIEW"},
        "limits": "Parent-runtime attestations and verified local hashes, not provider signatures; synthetic decisions do not prove owner adoption or authorize execution."}
    _atomic(summary, receipt)
    return {"status": "PASS", "verified_native_tasks": 14,
            "summary_sha256": _sha(summary.read_bytes())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    d = modes.add_parser("deterministic")
    d.add_argument("--output", type=Path, required=True)
    p = modes.add_parser("prepare-live")
    p.add_argument("--output", type=Path, required=True)
    f = modes.add_parser("finalize-live")
    f.add_argument("--run", type=Path, required=True)
    f.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "deterministic":
            result = deterministic(args.output)
        elif args.mode == "prepare-live":
            result = prepare_live(args.output)
        else:
            result = finalize_live(args.run, args.summary)
    except (ValueError, OSError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "code": type(exc).__name__}, sort_keys=True),
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] in {"PASS", "WAITING_NATIVE_TASKS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
