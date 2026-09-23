"""Read-only Phase 1/2 boundary and immutable local native-task preparation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
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
                _input_route: str = "verified_boundary") -> dict[str, Any]:
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
        "mart_bundle_path": str(_path(mart_bundle, existing=True))}
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


def verify_cycle(cycle_dir: str | Path) -> dict[str, Any]:
    """Revalidate frozen bytes, upstream cuts, requests and the event checkpoint."""
    folder = _path(cycle_dir, existing=True)
    if folder.parent.parent.name != "weekly-cycles" or folder.parent.parent.parent.name != ".local":
        raise ValueError("cycle outside private root")
    state, _ = _read(folder / "state.json")
    events, _ = _read(folder / "events.json")
    if not isinstance(state, dict) or not isinstance(events, list) or len(events) != 1:
        raise ValueError("invalid cycle state or events")
    event = events[0]
    if (event.get("sequence") != 1 or event.get("previous_hash") != "GENESIS" or
        _digest(canonical_json({key: value for key, value in event.items() if key != "hash"})) != event.get("hash") or
        state.get("event_hash") != event["hash"] or
        {key: value for key, value in state.items() if key != "event_hash"} != event.get("checkpoint")):
        raise ValueError("cycle event chain or state changed")
    report, _ = _read(folder / "current-cut.json")
    bundle, _ = _read(folder / "task-bundle.json")
    rebuilt, manifest_hash, mart_hash = _verified_report(state["workspace_path"], state["mart_bundle_path"])
    rebuilt["task_scope"] = list(state["expected_roles"])
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
    if tasks.is_symlink() or {item.name for item in tasks.iterdir()} != {
            f"{role}.request.json" for role in state["expected_roles"]}:
        raise ValueError("task inventory changed")
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
    return {**state, "destination": str(folder)}


def cycle_status(cycle_dir: str | Path) -> dict[str, Any]:
    return verify_cycle(cycle_dir)


__all__ = ["DEFAULT_ROLES", "ROLE_MODELS", "resolve_pointer", "start_cycle", "start_cycle_from_source_pack",
           "verify_cycle", "cycle_status"]
