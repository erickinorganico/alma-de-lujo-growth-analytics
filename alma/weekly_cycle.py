"""Read-only Phase 1/2 boundary and immutable local native-task preparation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alma.operating_archive import verify_cut
from alma.operating_contracts import canonical_json
from alma.operating_interchange import parse_pack
from alma.operating_mart_contracts import MetricRow
from alma.operating_marts import (
    SEMANTIC_FORMULAS, _FACT_KEYS, _definitions, build_operating_marts,
)
from alma.operating_workspace import _cut_id, build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
VERSION = "operating-cycle-v1"
DEFAULT_ROLES = ("merchandiser", "finance_analyst", "commerce_analyst",
                 "returns_analyst", "growth_analyst", "market_researcher")
ROLE_MODELS = {"merchandiser": "terra", "finance_analyst": "terra",
               "commerce_analyst": "luna", "returns_analyst": "luna",
               "growth_analyst": "sol", "market_researcher": "sol"}
QUERY_REGISTRY = {"metric_rows.by_reconciliation_id": {
    "source": "metric_rows", "parameters": ["reconciliation_id"], "read_only": True}}
ROLE_FAMILIES = {
    "merchandiser": ("cost", "inventory", "purchases", "learning", "budgets"),
    "finance_analyst": ("economics", "obligations", "cash", "budgets"),
    "commerce_analyst": ("economics", "learning", "sales_readiness"),
    "returns_analyst": ("inventory", "learning", "exceptions"),
    "growth_analyst": ("economics", "learning", "sales_readiness"),
    "market_researcher": ("learning", "exceptions", "sales_readiness"),
}
ROLE_REQUIRED_SOURCES = {
    "merchandiser": ("sku_catalog", "inventory_counts", "cost_versions"),
    "finance_analyst": ("obligations", "obligation_payments", "cash_events",
                        "cash_balance_evidence", "budgets"),
    "commerce_analyst": ("sales_aggregates", "availability_daily"),
    "returns_analyst": ("quality_events", "inventory_movements"),
    "growth_analyst": ("sales_aggregates", "availability_daily", "unmet_demand"),
    "market_researcher": ("sales_aggregates", "availability_daily"),
}
STATIC_METRIC_FAMILY = {
    "complete_landed_cost_cents": "cost", "available_units": "inventory",
    "purchase_remaining_units": "purchases", "realized_contribution_cents": "economics",
    "recorded_unpaid_cents": "obligations", "authoritative_outstanding_cents": "obligations",
    "reconciled_cash_close_cents": "cash", "cash_layer_cents": "cash",
    "budget_headroom_cents": "budgets", "sell_through": "learning",
    "mature_return_rate": "learning", "quality_defect_rate": "learning",
    "recorded_unmet_units": "learning", "stockout_exposure": "learning",
    "variant_mix": "learning",
}
MAX_JSON_BYTES = 32 * 1024 * 1024
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_pointer(evidence: Any, pointer: str) -> Any:
    """Resolve a strict RFC 6901 pointer within frozen in-memory evidence only."""
    if not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 500:
        raise ValueError("evidence reference must be a local JSON Pointer")
    current = evidence
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            raise ValueError("invalid JSON Pointer escape")
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part) or int(part) >= len(current):
                raise ValueError("invalid JSON Pointer array index")
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError("evidence reference is absent")
    return current


def _metric_family(row: dict[str, Any]) -> str | None:
    path = row.get("dimensions", {}).get("family_path")
    if isinstance(path, str):
        return path.split(".", 1)[0].split("[", 1)[0]
    return STATIC_METRIC_FAMILY.get(row.get("metric_id"))


def _role_evidence(report: dict[str, Any], role: str) -> dict[str, Any]:
    families = ROLE_FAMILIES[role]
    metrics = [row for row in report["metric_rows"] if _metric_family(row) in families]
    if len(metrics) > 10_000:
        raise ValueError("role evidence exceeds metric row cap")
    definitions = {name: report["metric_definitions"][name]
                   for name in sorted({row["metric_id"] for row in metrics})}
    evidence = {"cut": {key: report[key] for key in ("cut_id", "cutoff_at", "timezone",
        "input_class", "synthetic_business_data", "manifest_sha256", "mart_bundle_sha256",
        "metric_contract_sha256")},
        "coverage": report["coverage"], "domain_coverage": report["domain_coverage"],
        "source_sha256": report["source_sha256"], "quality": report["quality"],
        "reconciliation": report["reconciliation"], "lineage": report["lineage"],
        "metric_definitions": definitions, "metric_rows": metrics,
        "families": {name: report["families"][name] for name in families
                     if name in report["families"]}}
    if "decision_register" in report:
        evidence["decision_register"] = report["decision_register"]
        evidence["carried_decisions"] = report["carried_decisions"]
    if len(canonical_json(evidence)) > MAX_JSON_BYTES:
        raise ValueError("role evidence exceeds byte cap")
    return evidence


def _role_gate(report: dict[str, Any], role: str) -> tuple[str, list[str]]:
    required = ROLE_REQUIRED_SOURCES[role]
    blocked = [name for name in required if report["coverage"][name]["status"]
               in {"MISSING", "ERROR", "NOT_APPLICABLE"}]
    if role == "finance_analyst" and report["quality"]["cash_evidence"] == "MISSING":
        blocked.append("cash_balance_evidence")
    if role == "returns_analyst" and report["quality"]["cohort_links"] != "PASS":
        blocked.append("cohort_links")
    if blocked:
        return "BLOCKED_EVIDENCE", sorted(set(blocked))
    if any(report["coverage"][name]["status"] in {"PARTIAL", "ESTIMATED"}
           for name in required):
        return "REVIEW", []
    if role == "finance_analyst" and report["quality"]["cash_evidence"] == "MIXED":
        return "REVIEW", []
    return "READY_FOR_ANALYSIS", []


def _read(path: Path, *, canonical: bool = True) -> tuple[dict[str, Any] | list[Any], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("missing, linked or oversized cycle evidence")
    raw = path.read_bytes()
    value = json.loads(raw)
    if canonical and raw != canonical_json(value):
        raise ValueError("noncanonical cycle evidence")
    return value, raw


def _path(value: str | Path, *, existing: bool = False) -> Path:
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("path traversal")
    if any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction())
           for part in (path, *path.parents)):
        raise ValueError("linked path")
    path = path.resolve(strict=existing)
    if existing and not path.is_dir():
        raise ValueError("expected evidence directory")
    return path


def _output_root(value: str | Path) -> Path:
    root = _path(value)
    if root.name != "weekly-cycles" or root.parent.name != ".local":
        raise ValueError("cycle output must be .local/weekly-cycles")
    return root


def _verified_report(workspace: str | Path, mart_bundle: str | Path) -> tuple[dict[str, Any], str, str]:
    cut = _path(workspace, existing=True)
    mart = _path(mart_bundle, existing=True)
    if cut.parent.name != "operating-cuts":
        raise ValueError("not a canonical operating cut")
    verified = verify_cut(cut, private_root=cut.parent.parent)
    if verified["status"] != "PASS":
        raise ValueError("workspace verification failed")
    manifest, manifest_bytes = _read(cut / "workspace.json", canonical=False)
    if manifest_bytes != canonical_json(manifest) + b"\n":
        raise ValueError("workspace manifest bytes differ")
    bundle, bundle_bytes = _read(mart / "manifest.json")
    if not isinstance(bundle, dict) or bundle.get("cut_id") != verified["cut_id"]:
        raise ValueError("mart cut mismatch")
    if (bundle.get("source_sha256") != manifest["source_sha256"] or
        bundle.get("coverage") != manifest["coverage"]):
        raise ValueError("mart source or coverage mismatch")
    artifacts = bundle.get("artifacts")
    artifact_hashes = bundle.get("artifact_sha256")
    if (not isinstance(artifacts, list) or not artifacts or
        artifacts != sorted(set(artifacts)) or not isinstance(artifact_hashes, dict) or
        set(artifact_hashes) != set(artifacts) or
        {path.name for path in mart.iterdir()} != {"manifest.json", *artifacts}):
        raise ValueError("mart artifact inventory mismatch")
    data: dict[str, Any] = {}
    for name in artifacts:
        if not isinstance(name, str) or not name.endswith((".json", ".csv")) or "/" in name or "\\" in name:
            raise ValueError("unsafe mart artifact name")
        item = mart / name
        if item.is_symlink() or not item.is_file() or item.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("missing, linked or oversized mart artifact")
        raw = item.read_bytes()
        if _digest(raw) != artifact_hashes[name]:
            raise ValueError("mart artifact hash mismatch")
        if name.endswith(".json"):
            parsed = json.loads(raw)
            if raw != canonical_json(parsed):
                raise ValueError("noncanonical mart artifact")
            data[name] = parsed
    required = {"registry.json", "semantic_catalog.json", "domain_coverage.json",
                "metric_rows.json", "controls.json", "families.json", "lineage.json",
                "exceptions.json", "sales_readiness.json"}
    if not required <= set(data):
        raise ValueError("incomplete mart report")
    registry = data["registry.json"]
    expected_registry = {name: asdict(definition) for name, definition in sorted(_definitions().items())}
    contract_hash = _digest(canonical_json({"registry": registry,
        "semantic_formulas": SEMANTIC_FORMULAS, "fact_keys": sorted(_FACT_KEYS)}))
    if (canonical_json(registry) != canonical_json(expected_registry) or
        contract_hash != bundle.get("metric_contract_sha256")):
        raise ValueError("stale metric contract")
    lineage = data["lineage.json"]
    for key, expected in (("cut_id", manifest["cut_id"]), ("cutoff_at", manifest["cutoff_at"]),
                          ("source_sha256", manifest["source_sha256"]),
                          ("coverage", manifest["coverage"]),
                          ("metric_contract_sha256", contract_hash),
                          ("policy_sha256", bundle["policy_sha256"])):
        if lineage.get(key) != expected:
            raise ValueError("mart lineage mismatch")
    if not isinstance(data["metric_rows.json"], list):
        raise ValueError("invalid metric rows")
    for raw in data["metric_rows.json"]:
        row = MetricRow(**raw)
        if row.metric_id not in registry or row.cut_id != manifest["cut_id"]:
            raise ValueError("unregistered or foreign metric")
    report = {"version": VERSION, "cut_id": manifest["cut_id"],
        "cutoff_at": manifest["cutoff_at"], "timezone": manifest["timezone"],
        "input_class": manifest["input_class"],
        "synthetic_business_data": manifest["input_class"] == "SYNTHETIC_EXAMPLE",
        "manifest_sha256": _digest(manifest_bytes), "mart_bundle_sha256": _digest(bundle_bytes),
        "metric_contract_sha256": contract_hash, "source_sha256": manifest["source_sha256"],
        "coverage": manifest["coverage"],
        "quality": {"workspace": manifest["quality_status"],
                    "cash_evidence": manifest["cash_evidence_status"],
                    "cohort_links": manifest["cohort_link_status"]},
        "reconciliation": {"relationship": manifest["relationship_check"],
                           "mart_controls": data["controls.json"]},
        "lineage": lineage, "manifest": manifest, "mart_manifest": bundle,
        "metric_definitions": registry, "semantic_catalog": data["semantic_catalog.json"],
        "domain_coverage": data["domain_coverage.json"],
        "metric_rows": data["metric_rows.json"], "families": data["families.json"],
        "exceptions": data["exceptions.json"], "sales_readiness": data["sales_readiness.json"],
        "task_scope": list(DEFAULT_ROLES)}
    return report, _digest(manifest_bytes), _digest(bundle_bytes)


def _initial_requests(report: dict[str, Any], run_id: str, roles: tuple[str, ...],
                      current_hash: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    request_bytes: dict[str, bytes] = {}
    for role in roles:
        evidence = _role_evidence(report, role)
        evidence_status, blocked_sources = _role_gate(report, role)
        refs = ["/cut/cut_id", "/quality/workspace"]
        if evidence["metric_rows"]:
            refs.append("/metric_rows/0/value")
        for pointer in refs:
            resolve_pointer(evidence, pointer)
        body = {"version": VERSION, "cut_id": report["cut_id"], "run_id": run_id,
                "role": role, "expected_model_family": ROLE_MODELS[role],
                "execution_mode": "native-codex-task-bridge",
                "synthetic_business_data": report["synthetic_business_data"],
                "evidence_status": evidence_status, "blocked_sources": blocked_sources,
                "current_cut_sha256": current_hash,
                "manifest_sha256": report["manifest_sha256"],
                "mart_bundle_sha256": report["mart_bundle_sha256"],
                "metric_contract_sha256": report["metric_contract_sha256"],
                "evidence_hash": _digest(canonical_json(evidence)), "evidence": evidence,
                "evidence_refs": refs,
                "registered_queries": QUERY_REGISTRY,
                "response_contract": "contracts/weekly-cycle-v1.schema.json#/$defs/response",
                "write_scope": [f"tasks/{role}.response.json", f"tasks/{role}.query-trace.json"]}
        body["request_id"] = _digest(canonical_json(body))
        request_bytes[role] = canonical_json(body)
    bundle = {"version": VERSION, "cut_id": report["cut_id"], "run_id": run_id,
              "current_cut_sha256": current_hash,
              "requests": {role: {"path": f"tasks/{role}.request.json",
                                  "sha256": _digest(raw)} for role, raw in sorted(request_bytes.items())}}
    return request_bytes, bundle


def start_cycle(workspace: str | Path, mart_bundle: str | Path, output_root: str | Path,
                roles: tuple[str, ...] | list[str] | None = None, *,
                _input_route: str = "verified_boundary",
                prior_register: str | Path | None = None,
                prior_anchor: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    """Freeze one verified canonical cut without invoking any native analyst."""
    root = _output_root(output_root)
    chosen = tuple(DEFAULT_ROLES if roles is None else roles)
    if not chosen or len(chosen) > len(DEFAULT_ROLES) or len(set(chosen)) != len(chosen) or \
            any(role not in ROLE_MODELS for role in chosen):
        raise ValueError("invalid analyst role set")
    if _input_route not in {"verified_boundary", "source_pack"}:
        raise ValueError("invalid cycle input route")
    chosen = tuple(sorted(chosen))
    report, manifest_hash, mart_hash = _verified_report(workspace, mart_bundle)
    report["task_scope"] = list(chosen)
    if (prior_register is None) != (prior_anchor is None):
        raise ValueError("prior register and anchor must be supplied together")
    decision_path = None
    decision_anchor = None
    if prior_register is not None:
        from .decision_register import carry_for_report

        binding = carry_for_report(prior_register, report, prior_anchor)
        report["decision_register"] = {key: binding[key] for key in
                                       ("version", "register_id", "prior_anchor", "anchor")}
        report["carried_decisions"] = binding["carried_decisions"]
        decision_path = str(Path(prior_register).resolve(strict=True))
        decision_anchor = binding["anchor"]
    report_bytes = canonical_json(report)
    report_hash = _digest(report_bytes)
    run_id = _digest(canonical_json({"cut_id": report["cut_id"],
        "manifest_sha256": manifest_hash, "mart_bundle_sha256": mart_hash,
        "current_cut_sha256": report_hash}))[:24]
    requests, bundle = _initial_requests(report, run_id, chosen, report_hash)
    bundle_bytes = canonical_json(bundle)
    state = {"version": VERSION, "cut_id": report["cut_id"], "run_id": run_id,
        "status": "WAITING_ANALYSTS", "input_route": _input_route,
        "current_cut_sha256": report_hash, "manifest_sha256": manifest_hash,
        "mart_bundle_sha256": mart_hash, "task_bundle_sha256": _digest(bundle_bytes),
        "expected_roles": {role: {"model_family": ROLE_MODELS[role],
                                   "evidence_status": _role_gate(report, role)[0],
                                   "request_sha256": _digest(requests[role])} for role in chosen},
        "accepted_roles": {}, "workspace_path": str(_path(workspace, existing=True)),
        "mart_bundle_path": str(_path(mart_bundle, existing=True)),
        "decision_register_path": decision_path, "decision_register_anchor": decision_anchor}
    event = {"sequence": 1, "previous_hash": "GENESIS", "event_type": "TASKS_PREPARED",
             "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
             "checkpoint": state, "details": {"request_count": len(chosen),
                                               "current_cut_sha256": report_hash}}
    event["hash"] = _digest(canonical_json(event))
    state = {**state, "event_hash": event["hash"]}
    destination = root / report["cut_id"] / run_id
    if destination.exists():
        verified = verify_cycle(destination)
        if (verified["current_cut_sha256"] != report_hash or
            verified["task_bundle_sha256"] != state["task_bundle_sha256"]):
            raise ValueError("existing cycle differs")
        return verified
    root.mkdir(parents=True, exist_ok=True)
    cut_root = root / report["cut_id"]
    if cut_root.exists() and (cut_root.is_symlink() or
       (hasattr(cut_root, "is_junction") and cut_root.is_junction())):
        raise ValueError("linked cycle cut directory")
    cut_root.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=cut_root))
    try:
        (stage / "tasks").mkdir()
        (stage / "current-cut.json").write_bytes(report_bytes)
        (stage / "task-bundle.json").write_bytes(bundle_bytes)
        (stage / "state.json").write_bytes(canonical_json(state))
        (stage / "events.json").write_bytes(canonical_json([event]))
        for role, raw in requests.items():
            (stage / "tasks" / f"{role}.request.json").write_bytes(raw)
        if destination.exists():
            raise ValueError("cycle published concurrently")
        os.replace(stage, destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {**state, "destination": str(destination)}


def start_cycle_from_source_pack(source_pack: str | Path, operating_root: str | Path,
                                 mart_root: str | Path, output_root: str | Path,
                                 roles: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    """Build both completed upstream layers before issuing any native request."""
    pack = _path(source_pack, existing=True)
    if pack.suffix.lower() == ".xlsx":
        raise ValueError("direct workbook preparation belongs to Phase 4")
    parsed = parse_pack(pack, private_root=operating_root)
    cut_id = _cut_id(parsed)
    cut_path = _path(operating_root) / "operating-cuts" / cut_id
    if not cut_path.exists():
        built = build_operating_workspace(pack, private_root=operating_root)
        cut_path = Path(built["destination"])
    verified = verify_cut(cut_path, private_root=operating_root)
    if verified["status"] != "PASS" or verified["cut_id"] != cut_id:
        raise ValueError("source pack workspace verification failed")
    registry = {name: asdict(definition) for name, definition in sorted(_definitions().items())}
    contract_hash = _digest(canonical_json({"registry": registry,
        "semantic_formulas": SEMANTIC_FORMULAS, "fact_keys": sorted(_FACT_KEYS)}))
    mart_path = _path(mart_root) / cut_id / contract_hash
    if not mart_path.exists():
        marts = build_operating_marts(cut_path, mart_root,
                                      policy_path=POLICY, private_root=mart_root)
        mart_path = Path(marts["destination"])
    _verified_report(cut_path, mart_path)
    return start_cycle(cut_path, mart_path, output_root, roles, _input_route="source_pack")


def _event_state(events: list[Any], state: dict[str, Any]) -> None:
    if not events or events[0].get("event_type") != "TASKS_PREPARED":
        raise ValueError("cycle journal lacks preparation event")
    previous = "GENESIS"
    prior: dict[str, Any] | None = None
    for index, event in enumerate(events):
        if (not isinstance(event, dict) or event.get("sequence") != index + 1 or
            event.get("previous_hash") != previous or
            _digest(canonical_json({key: value for key, value in event.items()
                                    if key != "hash"})) != event.get("hash") or
            not isinstance(event.get("checkpoint"), dict)):
            raise ValueError("cycle event chain changed")
        checkpoint = event["checkpoint"]
        if prior is not None:
            immutable = ("version", "cut_id", "run_id", "input_route", "current_cut_sha256",
                         "manifest_sha256", "mart_bundle_sha256", "task_bundle_sha256",
                         "expected_roles", "workspace_path", "mart_bundle_path",
                         "decision_register_path", "decision_register_anchor")
            if any(checkpoint.get(key) != prior.get(key) for key in immutable):
                raise ValueError("cycle identity changed in journal")
            before, after = prior["accepted_roles"], checkpoint["accepted_roles"]
            kind = event.get("event_type")
            if kind == "ANALYST_ACCEPTED":
                role = event.get("details", {}).get("role")
                if (prior["status"] != "WAITING_ANALYSTS" or
                    checkpoint["status"] != "WAITING_ANALYSTS" or
                    role not in prior["expected_roles"] or role in before or
                    set(after) != set(before) | {role} or
                    any(after[name] != entry for name, entry in before.items()) or
                    event["details"].get("response_sha256") != after[role].get("response_sha256")):
                    raise ValueError("invalid analyst acceptance transition")
            elif kind == "REVIEWER_PREPARED":
                if (prior["status"] != "WAITING_ANALYSTS" or
                    set(before) != set(prior["expected_roles"]) or after != before or
                    checkpoint["status"] != "WAITING_REVIEW" or
                    event.get("details", {}).get("request_sha256") !=
                        checkpoint.get("reviewer_request_sha256")):
                    raise ValueError("invalid reviewer preparation transition")
            elif kind == "REVIEW_ACCEPTED":
                if (prior["status"] != "WAITING_REVIEW" or after != before or
                    checkpoint["status"] not in {"READY_FOR_OWNER", "REVIEW", "BLOCKED"} or
                    event.get("details", {}).get("packet_sha256") !=
                        checkpoint.get("packet_sha256")):
                    raise ValueError("invalid terminal review transition")
            else:
                raise ValueError("unknown cycle event type")
        prior, previous = checkpoint, event["hash"]
    if (state.get("event_hash") != previous or
        {key: value for key, value in state.items() if key != "event_hash"} != prior):
        raise ValueError("cycle state differs from final event checkpoint")


def _accepted_artifact(tasks: Path, role: str, request: dict[str, Any],
                       expected: dict[str, Any] | None = None) -> dict[str, Any]:
    from .native_agents_v1 import validate_dispatch

    response, response_bytes = _read(tasks / f"{role}.response.json")
    trace, trace_bytes = _read(tasks / f"{role}.query-trace.json")
    receipt, receipt_bytes = _read(tasks / f"{role}.dispatch.json")
    validate_dispatch(request, response, trace, receipt)
    entry = {"request_id": request["request_id"],
        "response_sha256": _digest(response_bytes),
        "query_trace_sha256": _digest(trace_bytes),
        "dispatch_sha256": _digest(receipt_bytes),
        "agent_id": receipt["agent_id"], "model": receipt["model"],
        "verdict": response["verdict"]}
    if expected is not None and entry != expected:
        raise ValueError("accepted native artifact differs from checkpoint")
    return {"request": request, "response": response, "trace": trace,
            "receipt": receipt, "entry": entry}


def _verified_cycle_context(cycle_dir: str | Path) -> dict[str, Any]:
    """Read-only full replay against upstream evidence and native artifacts."""
    folder = _path(cycle_dir, existing=True)
    if folder.parent.parent.name != "weekly-cycles" or folder.parent.parent.parent.name != ".local":
        raise ValueError("cycle outside private root")
    required_files = {"current-cut.json", "task-bundle.json", "state.json",
                      "events.json", "tasks"}
    allowed_files = required_files | {"decision-packet.json", ".cycle-lock"}
    inventory = {item.name for item in folder.iterdir()}
    if not required_files <= inventory or not inventory <= allowed_files or \
            any(item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction())
                for item in folder.iterdir()):
        raise ValueError("cycle directory inventory changed")
    state, _ = _read(folder / "state.json")
    events, _ = _read(folder / "events.json")
    if not isinstance(state, dict) or not isinstance(events, list):
        raise ValueError("invalid cycle state or events")
    _event_state(events, state)
    report, _ = _read(folder / "current-cut.json")
    bundle, _ = _read(folder / "task-bundle.json")
    rebuilt, manifest_hash, mart_hash = _verified_report(state["workspace_path"], state["mart_bundle_path"])
    rebuilt["task_scope"] = list(state["expected_roles"])
    if state.get("decision_register_path") is not None:
        from .decision_register import projection_for_anchor

        projection = projection_for_anchor(state["decision_register_path"],
                                           state["decision_register_anchor"])
        active = {"OPEN", "IN_PROGRESS", "REVIEW", "STALE"}
        carried = [{key: row[key] for key in ("decision_id", "recommendation_id", "owner",
            "due_date", "status", "source_hash", "packet_hash", "event_count", "terminal_hash")}
            for row in projection["decisions"] if row["status"] in active]
        binding = report.get("decision_register")
        if (not isinstance(binding, dict) or binding.get("anchor") != state["decision_register_anchor"] or
                binding.get("register_id") != projection["register_id"] or
                report.get("carried_decisions") != carried):
            raise ValueError("decision register binding changed")
        rebuilt["decision_register"] = binding
        rebuilt["carried_decisions"] = carried
    if (report != rebuilt or _digest(canonical_json(report)) != state["current_cut_sha256"] or
        manifest_hash != state["manifest_sha256"] or mart_hash != state["mart_bundle_sha256"] or
        _digest(canonical_json(bundle)) != state["task_bundle_sha256"]):
        raise ValueError("cycle report or upstream evidence changed")
    if (bundle.get("cut_id") != state["cut_id"] or bundle.get("run_id") != state["run_id"] or
        bundle.get("current_cut_sha256") != state["current_cut_sha256"] or
        set(bundle.get("requests", {})) != set(state["expected_roles"])):
        raise ValueError("task bundle identity mismatch")
    expected_requests, expected_bundle = _initial_requests(rebuilt, state["run_id"],
        tuple(state["expected_roles"]), state["current_cut_sha256"])
    if bundle != expected_bundle:
        raise ValueError("task bundle differs from verified evidence")
    tasks = folder / "tasks"
    roles = set(state["expected_roles"])
    allowed = {f"{role}.request.json" for role in roles}
    for role in (*roles, "evidence_reviewer"):
        allowed.update({f"{role}.response.json", f"{role}.query-trace.json",
                        f"{role}.dispatch.json"})
    allowed.add("evidence_reviewer.request.json")
    inventory = {item.name for item in tasks.iterdir()}
    if (tasks.is_symlink() or not all(item.is_file() and not item.is_symlink()
                                     for item in tasks.iterdir()) or
        not {f"{role}.request.json" for role in roles} <= inventory or
        not inventory <= allowed):
        raise ValueError("task inventory changed")
    from .native_agents_v1 import make_reviewer_request, validate_request, build_terminal_packet

    requests: dict[str, dict[str, Any]] = {}
    for role, info in bundle["requests"].items():
        if info.get("path") != f"tasks/{role}.request.json":
            raise ValueError("task path changed")
        request, raw = _read(tasks / f"{role}.request.json")
        if (_digest(raw) != info.get("sha256") or
            raw != expected_requests[role] or
            _digest(raw) != state["expected_roles"][role]["request_sha256"] or
            request.get("role") != role or request.get("cut_id") != state["cut_id"] or
            request.get("current_cut_sha256") != state["current_cut_sha256"] or
            request.get("evidence_hash") != _digest(canonical_json(request.get("evidence"))) or
            request.get("request_id") != _digest(canonical_json({
                key: value for key, value in request.items() if key != "request_id"}))):
            raise ValueError("task request changed")
        if request.get("write_scope") != [f"tasks/{role}.response.json",
                                            f"tasks/{role}.query-trace.json"]:
            raise ValueError("task write scope changed")
        for pointer in request.get("evidence_refs", []):
            resolve_pointer(request["evidence"], pointer)
        validate_request(request)
        requests[role] = request
    if not set(state["accepted_roles"]) <= roles:
        raise ValueError("foreign accepted role")
    accepted = {role: _accepted_artifact(tasks, role, requests[role], entry)
                for role, entry in state["accepted_roles"].items()}
    if len({item["entry"]["agent_id"] for item in accepted.values()}) != len(accepted):
        raise ValueError("duplicate native analyst identity")
    for role in roles - set(accepted):
        if f"{role}.dispatch.json" in inventory:
            _accepted_artifact(tasks, role, requests[role])
    reviewer_request = None
    if "evidence_reviewer.request.json" in inventory:
        if set(accepted) != roles:
            raise ValueError("reviewer request before analyst completion")
        reviewer_request, reviewer_bytes = _read(tasks / "evidence_reviewer.request.json")
        expected_reviewer = make_reviewer_request({"state": state, "report": report}, accepted)
        if (reviewer_request != expected_reviewer or
            reviewer_bytes != canonical_json(expected_reviewer)):
            raise ValueError("reviewer request differs from accepted evidence")
        validate_request(reviewer_request)
        if state.get("reviewer_request_sha256") is not None and \
                _digest(reviewer_bytes) != state["reviewer_request_sha256"]:
            raise ValueError("reviewer request hash differs from checkpoint")
    if state["status"] in {"WAITING_REVIEW", "READY_FOR_OWNER", "REVIEW", "BLOCKED"} and \
            reviewer_request is None:
        raise ValueError("reviewer request missing")
    review = None
    if state.get("reviewer") is not None:
        if reviewer_request is None:
            raise ValueError("reviewer artifact without request")
        review = _accepted_artifact(tasks, "evidence_reviewer", reviewer_request,
                                    state["reviewer"])
        if review["entry"]["agent_id"] in {
                item["entry"]["agent_id"] for item in accepted.values()}:
            raise ValueError("reviewer shares analyst identity")
    elif "evidence_reviewer.dispatch.json" in inventory:
        if reviewer_request is None:
            raise ValueError("unrequested reviewer artifact")
        _accepted_artifact(tasks, "evidence_reviewer", reviewer_request)
    if state["status"] in {"READY_FOR_OWNER", "REVIEW", "BLOCKED"}:
        if review is None:
            raise ValueError("terminal cycle has no review")
        packet, packet_bytes = _read(folder / "decision-packet.json")
        expected_packet = build_terminal_packet({"state": state, "report": report},
                                                accepted, review)
        if (packet != expected_packet or packet_bytes != canonical_json(expected_packet) or
            _digest(packet_bytes) != state.get("packet_sha256") or
            packet["status"] != state["status"]):
            raise ValueError("terminal packet changed")
    elif (folder / "decision-packet.json").exists():
        raise ValueError("packet exists before terminal review")
    return {"folder": folder, "state": state, "events": events, "report": report,
            "accepted": accepted, "review": review, "reviewer_request": reviewer_request}


def verify_cycle(cycle_dir: str | Path) -> dict[str, Any]:
    context = _verified_cycle_context(cycle_dir)
    return {**context["state"], "destination": str(context["folder"])}


def cycle_status(cycle_dir: str | Path) -> dict[str, Any]:
    return verify_cycle(cycle_dir)


@contextmanager
def _locked(folder: Path):
    lock = folder / ".cycle-lock"
    if lock.is_symlink():
        raise ValueError("linked cycle lock")
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("cycle is locked") from None
    try:
        with handle:
            handle.write("exclusive cycle mutation")
        yield
    finally:
        lock.unlink(missing_ok=True)


def _atomic_bytes(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ValueError("linked cycle output")
    descriptor, name = tempfile.mkstemp(prefix=".cycle-write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _write_immutable(path: Path, data: bytes) -> None:
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError("existing native artifact differs")
        return
    _atomic_bytes(path, data)


def _transition(context: dict[str, Any], state: dict[str, Any],
                kind: str, details: dict[str, Any]) -> dict[str, Any]:
    folder = context["folder"]
    events = context["events"]
    checkpoint = {key: value for key, value in state.items() if key != "event_hash"}
    event = {"sequence": len(events) + 1, "previous_hash": events[-1]["hash"],
             "event_type": kind, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
             "checkpoint": checkpoint, "details": details}
    event["hash"] = _digest(canonical_json(event))
    _atomic_bytes(folder / "events.json", canonical_json([*events, event]))
    _atomic_bytes(folder / "state.json", canonical_json({**checkpoint, "event_hash": event["hash"]}))
    return verify_cycle(folder)


def _recover_last_checkpoint(folder: Path) -> None:
    events, _ = _read(folder / "events.json")
    state, _ = _read(folder / "state.json")
    if not isinstance(events, list) or len(events) < 2 or not isinstance(state, dict):
        return
    prior = {**events[-2]["checkpoint"], "event_hash": events[-2]["hash"]}
    if state == prior:
        projected = {**events[-1]["checkpoint"], "event_hash": events[-1]["hash"]}
        _event_state(events, projected)
        _atomic_bytes(folder / "state.json", canonical_json(projected))


def _prepare_reviewer(context: dict[str, Any]) -> dict[str, Any]:
    from .native_agents_v1 import make_reviewer_request

    state = context["state"]
    if state["status"] != "WAITING_ANALYSTS" or \
            set(state["accepted_roles"]) != set(state["expected_roles"]):
        raise ValueError("analysts are not complete")
    request = make_reviewer_request(context, context["accepted"])
    raw = canonical_json(request)
    _write_immutable(context["folder"] / "tasks" / "evidence_reviewer.request.json", raw)
    next_state = {**state, "status": "WAITING_REVIEW",
                  "reviewer_request_sha256": _digest(raw)}
    return _transition(context, next_state, "REVIEWER_PREPARED",
                       {"request_sha256": _digest(raw)})


def record_dispatch(cycle_dir: str | Path, role: str, response_path: str | Path,
                    query_trace_path: str | Path,
                    receipt_fields: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Validate parent-attested metadata and save only its immutable receipt."""
    from .native_agents_v1 import validate_dispatch

    folder = _path(cycle_dir, existing=True)
    with _locked(folder):
        context = _verified_cycle_context(folder)
        state, tasks = context["state"], folder / "tasks"
        if role not in state["expected_roles"] and role != "evidence_reviewer":
            raise ValueError("unknown cycle role")
        if role == "evidence_reviewer" and state["status"] != "WAITING_REVIEW":
            raise ValueError("review has not been requested")
        if role != "evidence_reviewer" and state["status"] != "WAITING_ANALYSTS" and \
                role not in state["accepted_roles"]:
            raise ValueError("analyst submission window closed")
        response_file = tasks / f"{role}.response.json"
        trace_file = tasks / f"{role}.query-trace.json"
        if _path_file(response_path) != response_file or \
                _path_file(query_trace_path) != trace_file:
            raise ValueError("native outputs outside task write scope")
        request, _ = _read(tasks / f"{role}.request.json")
        response, _ = _read(response_file)
        trace, _ = _read(trace_file)
        receipt = (receipt_fields if isinstance(receipt_fields, dict)
                   else _read(_path_file(receipt_fields))[0])
        validate_dispatch(request, response, trace, receipt)
        agents = {item["entry"]["agent_id"] for item in context["accepted"].values()}
        if role == "evidence_reviewer" and receipt["agent_id"] in agents:
            raise ValueError("reviewer must be a distinct native task")
        if role not in state["accepted_roles"] and role != "evidence_reviewer" and \
                receipt["agent_id"] in agents:
            raise ValueError("native analyst task identity reused")
        _write_immutable(tasks / f"{role}.dispatch.json", canonical_json(receipt))
        _verified_cycle_context(folder)
        return receipt


def _path_file(value: str | Path) -> Path:
    path = Path(value)
    if ".." in path.parts or any(part.is_symlink() or
            (hasattr(part, "is_junction") and part.is_junction())
            for part in (path, *path.parents)):
        raise ValueError("linked or traversing native artifact path")
    return path.resolve(strict=False)


def submit_response(cycle_dir: str | Path, role: str, response_path: str | Path,
                    query_trace_path: str | Path, receipt_path: str | Path) -> dict[str, Any]:
    """Accept exactly one verified native dispatch and advance the journal."""
    folder = _path(cycle_dir, existing=True)
    with _locked(folder):
        context = _verified_cycle_context(folder)
        state, tasks = context["state"], folder / "tasks"
        if role not in state["expected_roles"] and role != "evidence_reviewer":
            raise ValueError("unknown cycle role")
        if (_path_file(response_path) != tasks / f"{role}.response.json" or
            _path_file(query_trace_path) != tasks / f"{role}.query-trace.json" or
            _path_file(receipt_path) != tasks / f"{role}.dispatch.json"):
            raise ValueError("native artifact outside task scope")
        request, _ = _read(tasks / f"{role}.request.json")
        item = _accepted_artifact(tasks, role, request)
        if role in state["accepted_roles"]:
            if state["accepted_roles"][role] != item["entry"]:
                raise ValueError("accepted analyst differs")
            return {**state, "destination": str(folder)}
        if role == "evidence_reviewer":
            if state["status"] not in {"WAITING_REVIEW", "READY_FOR_OWNER", "REVIEW", "BLOCKED"}:
                raise ValueError("reviewer submission out of order")
            if state.get("reviewer") is not None:
                if state["reviewer"] != item["entry"]:
                    raise ValueError("accepted review differs")
                return {**state, "destination": str(folder)}
            if item["entry"]["agent_id"] in {
                    accepted["entry"]["agent_id"] for accepted in context["accepted"].values()}:
                raise ValueError("reviewer shares an analyst identity")
            from .native_agents_v1 import build_terminal_packet

            review = item
            packet = build_terminal_packet(context, context["accepted"], review)
            packet_bytes = canonical_json(packet)
            _write_immutable(folder / "decision-packet.json", packet_bytes)
            next_state = {**state, "status": packet["status"], "reviewer": item["entry"],
                          "packet_sha256": _digest(packet_bytes)}
            return _transition(context, next_state, "REVIEW_ACCEPTED",
                               {"packet_sha256": _digest(packet_bytes),
                                "dispatch_sha256": item["entry"]["dispatch_sha256"]})
        if state["status"] != "WAITING_ANALYSTS":
            raise ValueError("analyst submission out of order")
        if item["entry"]["agent_id"] in {
                accepted["entry"]["agent_id"] for accepted in context["accepted"].values()}:
            raise ValueError("native analyst task identity reused")
        next_state = {**state, "accepted_roles": {**state["accepted_roles"],
                                                 role: item["entry"]}}
        next_result = _transition(context, next_state, "ANALYST_ACCEPTED",
                                  {"role": role,
                                   "response_sha256": item["entry"]["response_sha256"],
                                   "query_trace_sha256": item["entry"]["query_trace_sha256"],
                                   "dispatch_sha256": item["entry"]["dispatch_sha256"]})
        if set(next_result["accepted_roles"]) == set(next_result["expected_roles"]):
            return _prepare_reviewer(_verified_cycle_context(folder))
        return next_result


def resume_cycle(cycle_dir: str | Path) -> dict[str, Any]:
    folder = _path(cycle_dir, existing=True)
    with _locked(folder):
        _recover_last_checkpoint(folder)
        context = _verified_cycle_context(folder)
        state = context["state"]
        if state["status"] == "WAITING_ANALYSTS" and \
                set(state["accepted_roles"]) == set(state["expected_roles"]):
            return _prepare_reviewer(context)
        return {**state, "destination": str(folder)}


def read_terminal_packet(cycle_dir: str | Path) -> dict[str, Any]:
    context = _verified_cycle_context(cycle_dir)
    if context["state"]["status"] not in {"READY_FOR_OWNER", "REVIEW", "BLOCKED"}:
        raise ValueError("cycle has no terminal packet")
    return _read(context["folder"] / "decision-packet.json")[0]


ACCEPTANCE_SCOPE = ("Synthetic operating-v1 cut; parent-runtime metadata and exact local hashes "
                    "are attestations, not provider signatures. Advisory only; external execution PROHIBITED.")


def build_acceptance_receipt(cycle_dir: str | Path, recorded_at_utc: str) -> dict[str, Any]:
    """Project a terminal synthetic run to an exact metadata-only public shape."""
    context = _verified_cycle_context(cycle_dir)
    state, report = context["state"], context["report"]
    if state["status"] != "READY_FOR_OWNER" or not report["synthetic_business_data"] or \
            report["input_class"] != "SYNTHETIC_EXAMPLE" or context["review"] is None:
        raise ValueError("acceptance requires verified owner-ready synthetic cycle")
    try:
        moment = datetime.fromisoformat(recorded_at_utc.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid acceptance timestamp") from exc
    if moment.tzinfo is None or moment.utcoffset() != timezone.utc.utcoffset(moment):
        raise ValueError("acceptance timestamp must be UTC")
    analysts = {role: {"agent_id": item["entry"]["agent_id"],
                        "model": item["entry"]["model"],
                        "request_sha256": state["expected_roles"][role]["request_sha256"],
                        "response_sha256": item["entry"]["response_sha256"],
                        "query_trace_sha256": item["entry"]["query_trace_sha256"],
                        "dispatch_sha256": item["entry"]["dispatch_sha256"]}
                for role, item in sorted(context["accepted"].items())}
    reviewer = context["review"]["entry"]
    return {"version": VERSION, "synthetic_business_data": True,
        "cut_id": state["cut_id"], "run_id": state["run_id"],
        "current_cut_sha256": state["current_cut_sha256"],
        "manifest_sha256": state["manifest_sha256"],
        "mart_bundle_sha256": state["mart_bundle_sha256"],
        "metric_contract_sha256": report["metric_contract_sha256"],
        "task_bundle_sha256": state["task_bundle_sha256"],
        "analysts": analysts,
        "reviewer": {"agent_id": reviewer["agent_id"], "model": reviewer["model"],
                     "request_sha256": state["reviewer_request_sha256"],
                     "response_sha256": reviewer["response_sha256"],
                     "query_trace_sha256": reviewer["query_trace_sha256"],
                     "dispatch_sha256": reviewer["dispatch_sha256"]},
        "terminal_status": state["status"], "terminal_packet_sha256": state["packet_sha256"],
        "recorded_at_utc": recorded_at_utc, "scope_limits": ACCEPTANCE_SCOPE}


def export_acceptance_receipt(cycle_dir: str | Path, output: str | Path) -> dict[str, Any]:
    """Write only the verified synthetic metadata projection to public evidence."""
    path = _path_file(output)
    if path.name != "native-cycle-acceptance.json" or path.parent.name != "v1" or \
            path.parent.parent.name != "evidence":
        raise ValueError("acceptance output must be evidence/v1/native-cycle-acceptance.json")
    receipt = build_acceptance_receipt(cycle_dir, datetime.now(timezone.utc).isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_immutable(path, canonical_json(receipt))
    return receipt


def verify_acceptance_receipt(receipt_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    """Resolve public IDs to a private cycle and compare the exact allowlisted receipt."""
    receipt, raw = _read(_path_file(receipt_path))
    if not isinstance(receipt, dict) or raw != canonical_json(receipt):
        raise ValueError("invalid public acceptance JSON")
    cut_id, run_id = receipt.get("cut_id"), receipt.get("run_id")
    if not isinstance(cut_id, str) or not re.fullmatch(r"[0-9a-f]{64}", cut_id) or \
            not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{24}", run_id):
        raise ValueError("invalid public cut/run identity")
    cycle = _output_root(output_root) / cut_id / run_id
    expected = build_acceptance_receipt(cycle, receipt.get("recorded_at_utc"))
    if receipt != expected:
        raise ValueError("public acceptance differs from private verified state")
    return {"version": VERSION, "status": "PASS", "cut_id": cut_id, "run_id": run_id,
            "terminal_status": expected["terminal_status"],
            "receipt_sha256": _digest(raw),
            "terminal_packet_sha256": expected["terminal_packet_sha256"]}


__all__ = ["DEFAULT_ROLES", "ROLE_MODELS", "resolve_pointer", "start_cycle", "start_cycle_from_source_pack",
           "verify_cycle", "cycle_status", "record_dispatch", "submit_response",
           "resume_cycle", "read_terminal_packet", "build_acceptance_receipt",
           "export_acceptance_receipt", "verify_acceptance_receipt"]
