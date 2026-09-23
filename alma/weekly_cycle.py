"""Read-only Phase 1/2 boundary and immutable local native-task preparation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from alma.operating_archive import verify_cut
from alma.operating_contracts import canonical_json
from alma.operating_mart_contracts import MetricRow
from alma.operating_marts import (
    SEMANTIC_FORMULAS, _FACT_KEYS, _definitions, build_operating_marts,
)
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
VERSION = "operating-cycle-v1"
DEFAULT_ROLES = ("merchandiser", "finance_analyst", "commerce_analyst",
                 "returns_analyst", "growth_analyst", "market_researcher")
ROLE_MODELS = {"merchandiser": "terra", "finance_analyst": "terra",
               "commerce_analyst": "luna", "returns_analyst": "luna",
               "growth_analyst": "sol", "market_researcher": "sol"}
MAX_JSON_BYTES = 32 * 1024 * 1024
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        evidence = {"current_cut": report}
        body = {"version": VERSION, "cut_id": report["cut_id"], "run_id": run_id,
                "role": role, "expected_model_family": ROLE_MODELS[role],
                "execution_mode": "native-codex-task-bridge",
                "synthetic_business_data": report["synthetic_business_data"],
                "current_cut_sha256": current_hash,
                "manifest_sha256": report["manifest_sha256"],
                "mart_bundle_sha256": report["mart_bundle_sha256"],
                "metric_contract_sha256": report["metric_contract_sha256"],
                "evidence_hash": _digest(canonical_json(evidence)), "evidence": evidence,
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
                roles: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    """Freeze one verified canonical cut without invoking any native analyst."""
    root = _output_root(output_root)
    chosen = tuple(DEFAULT_ROLES if roles is None else roles)
    if not chosen or len(chosen) > len(DEFAULT_ROLES) or len(set(chosen)) != len(chosen) or \
            any(role not in ROLE_MODELS for role in chosen):
        raise ValueError("invalid analyst role set")
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
        "status": "WAITING_ANALYSTS", "input_route": "verified_boundary",
        "current_cut_sha256": report_hash, "manifest_sha256": manifest_hash,
        "mart_bundle_sha256": mart_hash, "task_bundle_sha256": _digest(bundle_bytes),
        "expected_roles": {role: {"model_family": ROLE_MODELS[role],
                                   "request_sha256": _digest(requests[role])} for role in chosen},
        "accepted_roles": {}, "workspace_path": str(_path(workspace, existing=True)),
        "mart_bundle_path": str(_path(mart_bundle, existing=True))}
    event = {"sequence": 1, "previous_hash": "GENESIS", "event_type": "TASKS_PREPARED",
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
    built = build_operating_workspace(pack, private_root=operating_root)
    verify_cut(built["destination"], private_root=operating_root)
    marts = build_operating_marts(built["destination"], mart_root,
                                  policy_path=POLICY, private_root=mart_root)
    state = start_cycle(built["destination"], marts["destination"], output_root, roles)
    # Input route is display metadata only; it cannot alter the frozen report.
    return {**state, "input_route": "source_pack"}


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
    tasks = folder / "tasks"
    if tasks.is_symlink() or {item.name for item in tasks.iterdir()} != {
            f"{role}.request.json" for role in state["expected_roles"]}:
        raise ValueError("task inventory changed")
    for role, info in bundle["requests"].items():
        if info.get("path") != f"tasks/{role}.request.json":
            raise ValueError("task path changed")
        request, raw = _read(tasks / f"{role}.request.json")
        if (_digest(raw) != info.get("sha256") or
            _digest(raw) != state["expected_roles"][role]["request_sha256"] or
            request.get("role") != role or request.get("cut_id") != state["cut_id"] or
            request.get("current_cut_sha256") != state["current_cut_sha256"] or
            request.get("evidence_hash") != _digest(canonical_json(request.get("evidence"))) or
            request.get("request_id") != _digest(canonical_json({
                key: value for key, value in request.items() if key != "request_id"}))):
            raise ValueError("task request changed")
    return {**state, "destination": str(folder)}


def cycle_status(cycle_dir: str | Path) -> dict[str, Any]:
    return verify_cycle(cycle_dir)


__all__ = ["DEFAULT_ROLES", "ROLE_MODELS", "start_cycle", "start_cycle_from_source_pack",
           "verify_cycle", "cycle_status"]
