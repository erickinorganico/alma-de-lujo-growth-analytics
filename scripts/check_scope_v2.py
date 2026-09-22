"""Evaluate every v0.2 PRD acceptance ID against concrete release evidence.

This runner is read-only except for its requested output artifact and disposable
temporary lifecycle probes. Missing native-agent responses are BLOCKED, never
treated as successful deterministic analysis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alma.lifecycle import apply_event, definitions as lifecycle_definitions, verify_hash_chains
from alma.native_agents import digest, validate_dispatch, validate_response, verify_request
from alma.process_engine import definitions as process_definitions, status as process_status, verify_events
from alma.storage import canonical
from alma.warehouse import FOREIGN_KEYS, MARTS, TABLE_COLUMNS, inspect_schema, query_mart


class Blocked(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise Blocked("missing artifact: " + str(path))
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def compact(value: Any) -> Any:
    """Keep observations machine-readable without copying large source rows."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(encoded) <= 8000:
        return value
    if isinstance(value, dict):
        return {"keys": sorted(value), "serialized_chars": len(encoded), "sha256": hashlib.sha256(encoded.encode()).hexdigest()}
    if isinstance(value, list):
        return {"items": len(value), "serialized_chars": len(encoded), "sha256": hashlib.sha256(encoded.encode()).hexdigest()}
    return {"serialized_chars": len(encoded), "sha256": hashlib.sha256(encoded.encode()).hexdigest()}


class ScopeRunner:
    def __init__(self, workspace: Path, verification: Path):
        self.workspace = workspace.resolve()
        self.verification_path = (verification / "verification.json" if verification.is_dir() else verification).resolve()
        self.results: list[dict[str, Any]] = []
        self.checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._cache: dict[str, Any] = {}

    def ref(self, path: Path, suffix: str = "") -> str:
        return relative(path) + suffix

    def evaluate(
        self,
        acceptance_id: str,
        check_type: str,
        command_or_query: str,
        expected: Any,
        evidence_refs: list[str],
        check: Callable[[], tuple[bool, Any]],
    ) -> None:
        try:
            passed, observed = check()
            status = "PASS" if passed else "FAIL"
        except Blocked as exc:
            status, observed = "BLOCKED", {"reason": str(exc)}
        except Exception as exc:  # A broken check is a release failure, not a silent skip.
            status, observed = "FAIL", {"exception": type(exc).__name__, "message": str(exc)}
        self.results.append({
            "acceptance_id": acceptance_id,
            "status": status,
            "check_type": check_type,
            "command_or_query": command_or_query,
            "evidence_refs": evidence_refs,
            "observed": compact(observed),
            "expected": expected,
            "checked_at_utc": self.checked_at,
        })

    def workspace_json(self, name: str) -> Any:
        key = "workspace:" + name
        if key not in self._cache:
            self._cache[key] = read_json(self.workspace / name)
        return self._cache[key]

    def verification(self) -> dict[str, Any]:
        if "verification" not in self._cache:
            self._cache["verification"] = read_json(self.verification_path)
        return self._cache["verification"]

    def schema(self) -> dict[str, Any]:
        if "schema" not in self._cache:
            database = self.workspace / "warehouse.sqlite3"
            if not database.is_file():
                raise Blocked("missing warehouse.sqlite3")
            self._cache["schema"] = inspect_schema(database)
        return self._cache["schema"]

    def lifecycle_probe(self) -> dict[str, Any]:
        if "lifecycle_probe" in self._cache:
            return self._cache["lifecycle_probe"]
        with tempfile.TemporaryDirectory(prefix="alma-scope-lifecycle-") as temp:
            database = Path(temp) / "lifecycle.sqlite3"
            sequence = 0

            def emit(instance: str, event: str, payload: dict[str, Any], key: str | None = None, event_id: str | None = None):
                nonlocal sequence
                sequence += 1
                return apply_event(
                    database,
                    process_id="procure-to-stock",
                    instance_id=instance,
                    event_id=event_id or f"probe-{sequence}",
                    event_type=event,
                    payload=payload,
                    idempotency_key=key or f"probe:{instance}:{sequence}",
                    occurred_at_utc=f"2026-04-{sequence:02d}T00:00:00Z",
                    recorded_at_utc=f"2026-04-{sequence:02d}T00:00:00Z",
                    source_refs=[f"synthetic://scope-probe/{instance}/{event}/{sequence}"],
                )

            first = emit("idempotency", "po_drafted", {"quantity": 5, "unit_cost_cents": 100, "currency": "MXN"}, key="same-key", event_id="same-event")
            request = dict(
                database=database,
                process_id="procure-to-stock",
                instance_id="idempotency",
                event_id="same-event",
                event_type="po_drafted",
                payload={"quantity": 5, "unit_cost_cents": 100, "currency": "MXN"},
                idempotency_key="same-key",
                occurred_at_utc="2026-04-01T00:00:00Z",
                recorded_at_utc="2026-04-01T00:00:00Z",
                source_refs=["synthetic://scope-probe/idempotency/po_drafted/1"],
            )
            replay = apply_event(**request)
            request["payload"] = {"quantity": 6, "unit_cost_cents": 100, "currency": "MXN"}
            conflict = apply_event(**request)

            emit("approval", "po_drafted", {"quantity": 5, "unit_cost_cents": 100, "currency": "MXN"})
            emit("approval", "po_submitted", {"total_cents": 500})
            waiting = emit("approval", "po_approved", {})

            unsafe_rejected = False
            try:
                apply_event(
                    database,
                    process_id="procure-to-stock",
                    instance_id="unsafe",
                    event_id="unsafe-event",
                    event_type="po_drafted",
                    payload={"quantity": 1, "unit_cost_cents": 1, "currency": "MXN", "external_action": "BUY"},
                    idempotency_key="unsafe-key",
                    occurred_at_utc="2026-04-20T00:00:00Z",
                    source_refs=["synthetic://scope-probe/unsafe"],
                )
            except ValueError:
                unsafe_rejected = True

            connection = sqlite3.connect(database)
            try:
                events = connection.execute("SELECT count(*) FROM lifecycle_events WHERE process_id='procure-to-stock' AND instance_id='idempotency'").fetchone()[0]
                approval_state = connection.execute("SELECT current_state FROM lifecycle_instances WHERE process_id='procure-to-stock' AND instance_id='approval'").fetchone()[0]
            finally:
                connection.close()
            probe = {
                "first": first["status"],
                "replay": replay["status"],
                "conflict": conflict["status"],
                "conflict_code": conflict["exception_code"],
                "idempotency_business_events": events,
                "approval_attempt": waiting["status"],
                "approval_code": waiting["exception_code"],
                "approval_state": approval_state,
                "unsafe_payload_rejected": unsafe_rejected,
                "hash_chain": verify_hash_chains(database),
            }
        self._cache["lifecycle_probe"] = probe
        return probe

    def native_bundle(self) -> dict[str, Any]:
        if "native_bundle" in self._cache:
            value = self._cache["native_bundle"]
            if isinstance(value, Exception):
                raise value
            return value
        definitions = process_definitions()
        missing: list[str] = []
        processes: dict[str, Any] = {}
        models: list[str] = []
        analyst_ids: list[str] = []
        reviewer_ids: list[str] = []
        accepted_runs: list[dict[str, Any]] = []
        try:
            status_rows = process_status(self.workspace)
        except (OSError, ValueError, KeyError) as exc:
            blocked = Blocked("process status unavailable or invalid: " + str(exc))
            self._cache["native_bundle"] = blocked
            raise blocked
        statuses = {row["process_id"]: row["status"] for row in status_rows}
        for process_id, definition in definitions.items():
            folder = self.workspace / "processes" / process_id
            analyst_role = definition["agent"]
            tasks = folder / "tasks"
            paths = {
                "analyst_request": tasks / f"{analyst_role}.request.json",
                "analyst_response": tasks / f"{analyst_role}.response.json",
                "analyst_dispatch": tasks / f"{analyst_role}.dispatch.json",
                "reviewer_request": tasks / "evidence_reviewer.request.json",
                "reviewer_response": tasks / "evidence_reviewer.response.json",
                "reviewer_dispatch": tasks / "evidence_reviewer.dispatch.json",
                "packet": folder / "decision-packet.json",
            }
            absent = [relative(path) for path in paths.values() if not path.is_file()]
            if absent:
                missing.extend(absent)
                continue
            analyst_request = read_json(paths["analyst_request"])
            analyst_response = read_json(paths["analyst_response"])
            analyst_dispatch = read_json(paths["analyst_dispatch"])
            reviewer_request = read_json(paths["reviewer_request"])
            reviewer_response = read_json(paths["reviewer_response"])
            reviewer_dispatch = read_json(paths["reviewer_dispatch"])
            packet = read_json(paths["packet"])
            verify_request(analyst_request)
            validate_response(analyst_request, analyst_response)
            validate_dispatch(analyst_dispatch, analyst_request)
            verify_request(reviewer_request)
            validate_response(reviewer_request, reviewer_response)
            validate_dispatch(reviewer_dispatch, reviewer_request)
            if digest(analyst_response) != analyst_dispatch["response_sha256"] or digest(reviewer_response) != reviewer_dispatch["response_sha256"]:
                raise ValueError("native response hash mismatch: " + process_id)
            if analyst_dispatch["agent_id"] == reviewer_dispatch["agent_id"]:
                raise ValueError("analyst and reviewer identity are equal: " + process_id)
            if packet.get("external_execution") != "PROHIBITED" or packet.get("synthetic") is not True:
                raise ValueError("unsafe decision packet: " + process_id)
            if packet.get("facts") != analyst_response["facts"] or packet.get("review") != reviewer_response:
                raise ValueError("packet does not contain the validated native outputs: " + process_id)
            verify_events(folder)
            processes[process_id] = {
                "status": statuses.get(process_id),
                "analyst_role": analyst_role,
                "analyst_model": analyst_dispatch["model"],
                "analyst_agent_id": analyst_dispatch["agent_id"],
                "reviewer_model": reviewer_dispatch["model"],
                "reviewer_agent_id": reviewer_dispatch["agent_id"],
                "recommendations": len(packet["recommendations"]),
                "facts": len(packet["facts"]),
                "packet_hash": digest(packet),
            }
            models.extend((analyst_dispatch["model"], reviewer_dispatch["model"]))
            analyst_ids.append(analyst_dispatch["agent_id"])
            reviewer_ids.append(reviewer_dispatch["agent_id"])
            accepted_runs.extend((
                {"process_id": process_id, "role": analyst_role, "request": analyst_request, "response": analyst_response, "dispatch": analyst_dispatch, "response_path": paths["analyst_response"]},
                {"process_id": process_id, "role": "evidence_reviewer", "request": reviewer_request, "response": reviewer_response, "dispatch": reviewer_dispatch, "response_path": paths["reviewer_response"]},
            ))
        if missing:
            blocked = Blocked("native task artifacts are not complete: " + ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else ""))
            self._cache["native_bundle"] = blocked
            raise blocked
        bundle = {
            "processes": processes,
            "models": models,
            "distinct_models": sorted(set(models)),
            "analyst_agent_ids": analyst_ids,
            "reviewer_agent_ids": reviewer_ids,
            "statuses": statuses,
            "accepted_runs": accepted_runs,
        }
        bundle["run_index"] = self._validate_run_index(bundle)
        self._cache["native_bundle"] = bundle
        return bundle

    def _resolve_release_path(self, value: str, label: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(label + " must be a nonempty path")
        candidate = Path(value)
        candidates = [candidate] if candidate.is_absolute() else [ROOT / candidate, self.workspace.parent / candidate, self.workspace / candidate]
        for path in candidates:
            try:
                resolved = path.resolve()
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if resolved.is_file():
                return resolved
        raise ValueError(label + " does not resolve to a public release file: " + value)

    def _validate_run_index(self, bundle: dict[str, Any]) -> dict[str, Any]:
        index_path = self.workspace.parent / "agents" / "task-runs.json"
        index = read_json(index_path)
        required_top = {"version", "runs", "distinct_native_tasks", "models"}
        if not isinstance(index, dict) or set(index) != required_top or index.get("version") != "2.0":
            raise ValueError("native run index fields/version invalid")
        runs = index.get("runs")
        if not isinstance(runs, list) or len(runs) != len(bundle["accepted_runs"]):
            raise ValueError("native run index does not contain every accepted dispatch")
        expected = {(run["process_id"], run["role"]): run for run in bundle["accepted_runs"]}
        observed: dict[tuple[str, str], dict[str, Any]] = {}
        traces: list[str] = []
        receipt_fields = {"request_id", "role", "provider", "model", "agent_id", "response_sha256", "recorded_by", "mode", "effort", "started_at_utc", "completed_at_utc", "retry_history", "parent_review"}
        for run in runs:
            if not isinstance(run, dict) or not ({"process_id", "response_path", "trace_path"} | receipt_fields) <= set(run):
                raise ValueError("native run index entry is incomplete")
            key = (run["process_id"], run["role"])
            if key in observed or key not in expected:
                raise ValueError("native run index has an unknown or duplicate process/role")
            accepted = expected[key]
            if any(run[field] != accepted["dispatch"][field] for field in receipt_fields):
                raise ValueError("native run index differs from accepted dispatch: " + "/".join(key))
            response_path = self._resolve_release_path(run["response_path"], "response_path")
            if response_path.resolve() != accepted["response_path"].resolve() or sha256_file(response_path) != run["response_sha256"]:
                raise ValueError("native run index response binding failed: " + "/".join(key))
            trace_path = self._resolve_release_path(run["trace_path"], "trace_path")
            trace = read_json(trace_path)
            if trace.get("request_id") != run["request_id"] or not isinstance(trace.get("queries"), list) or not trace["queries"]:
                raise ValueError("native trace lacks the indexed request identity or query evidence: " + "/".join(key))
            for field in ("role", "model", "process_id"):
                if trace.get(field) not in (None, run[field]):
                    raise ValueError("native trace " + field + " differs from run index: " + "/".join(key))
            traced_agent = trace.get("native_job") or trace.get("reviewer")
            if traced_agent not in (None, run["agent_id"]):
                raise ValueError("native trace task identity differs from dispatch: " + "/".join(key))
            observed[key] = run
            traces.append(relative(trace_path))
        derived_models = sorted({run["dispatch"]["model"] for run in bundle["accepted_runs"]})
        derived_tasks = len({run["dispatch"]["agent_id"] for run in bundle["accepted_runs"]})
        if index["models"] != derived_models or index["distinct_native_tasks"] != derived_tasks:
            raise ValueError("native run index declared task/model counts do not match accepted dispatches")
        return {"path": relative(index_path), "runs": len(runs), "distinct_native_tasks": derived_tasks, "models": derived_models, "trace_paths": traces}

    def run(self) -> list[dict[str, Any]]:
        workspace_ref = self.ref(self.workspace)
        verification_ref = self.ref(self.verification_path)
        lifecycle_ref = self.ref(self.workspace / "lifecycle" / "summary.json")

        self.evaluate("ACC-PROC-001", "contract", "load processes/*.json and processes/business/*.json", "six exact process slugs with PTS/LTD/RTR/FCL/WGR/MTE contract IDs", ["processes/", "processes/business/"], self._check_proc_001)
        self.evaluate("ACC-PROC-002", "sqlite+artifact", "query lifecycle registry; validate native process journals", "six persisted business lifecycles plus six hashed native task journals", [lifecycle_ref, workspace_ref + "/processes"], self._check_proc_002)
        self.evaluate("ACC-PROC-003", "behavioral", "read lifecycle summary illegal-transition controls", "six illegal first transitions rejected with no instance effect", [lifecycle_ref, "tests/test_lifecycle.py"], self._check_proc_003)
        self.evaluate("ACC-PROC-004", "behavioral", "disposable apply_event replay and changed-key probe", "same event NO_OP; changed payload CONFLICT; one applied business event", ["alma/lifecycle.py", "tests/test_lifecycle.py"], self._check_proc_004)
        self.evaluate("ACC-PROC-005", "behavioral", "disposable missing-approval lifecycle probe", "WAITING/APPROVAL_MISSING while state remains WAITING_APPROVAL", ["alma/lifecycle.py", "specs/PROCESS-CATALOG.md"], self._check_proc_005)
        self.evaluate("ACC-PROC-006", "authority", "inspect packets and reject unsafe lifecycle payload", "synthetic-only evidence and external execution prohibited", ["alma/lifecycle.py", "alma/process_engine.py", workspace_ref + "/processes"], self._check_proc_006)

        self.evaluate("ACC-DATA-001", "sqlite", "PRAGMA table_info/foreign_key_list and broken-batch control", "STRICT typed PK/FK/check relations; invalid batch rejected and prior marts preserved", [workspace_ref + "/warehouse.sqlite3", verification_ref], self._check_data_001)
        self.evaluate("ACC-DATA-002", "catalog", "inspect_schema plus lifecycle sqlite_master", "30 canonical tables, control relations, 11 marts, 4 lifecycle registry tables and declared grains", [workspace_ref + "/lineage.json", workspace_ref + "/lifecycle/lifecycle.sqlite3"], self._check_data_002)
        self.evaluate("ACC-DATA-003", "reconciliation", "compare mart JSON exports to query_mart", "all 11 exported marts equal named SQLite queries", [workspace_ref + "/warehouse.sqlite3", workspace_ref + "/marts"], self._check_data_003)
        self.evaluate("ACC-DATA-004", "lineage", "recompute models/marts SQL hashes and compare lineage.json", "11 named mart SQL files exactly bound by hash and text", [workspace_ref + "/lineage.json", "models/marts/"], self._check_data_004)
        self.evaluate("ACC-DATA-005", "integrity", "recompute workspace.json hashes and inspect metadata", "scenario/seed/as-of/synthetic metadata bound; every manifest hash verifies", [workspace_ref + "/workspace.json", workspace_ref + "/lineage.json"], self._check_data_005)
        self.evaluate("ACC-DATA-006", "behavioral", "read verify_v2 bad-batch preservation control", "changed invalid batch rejected atomically and prior marts preserved", [verification_ref, "scripts/verify_v2.py"], self._check_data_006)
        self.evaluate("ACC-DATA-007", "quality", "read warehouse controls, scenario failures and full tests", "all normal SQL controls and tests pass; controlled failure behavior verified", [verification_ref, workspace_ref + "/warehouse-load.json"], self._check_data_007)

        self.evaluate("ACC-SCEN-001", "source-profile", "inspect normal data.json counts and date window", "365 days, >=36 variants, exactly 1200 orders, multi-item baskets and required domain sources", [workspace_ref + "/data.json", verification_ref], self._check_scen_001)
        self.evaluate("ACC-SCEN-002", "source-profile", "derive normal lifecycle coverage from canonical rows", "multi-item, split settlement/receipt, lifecycle, return, count, cohort and experiment evidence present", [workspace_ref + "/data.json"], self._check_scen_002)
        self.evaluate("ACC-SCEN-003", "scenario+tests", "verify scenario index, six scenario records, mechanisms and lifecycle fault test names", "exact six indexed dataset scenarios plus declared lifecycle/idempotency/agent fault controls pass", [self.ref(self.workspace.parent / "scenarios" / "index.json"), verification_ref, self.ref(self.verification_path.parent / "tests.log"), lifecycle_ref], self._check_scen_003)
        self.evaluate("ACC-SCEN-004", "scenario-manifest", "validate per-scenario verification record fields and interpretation limit", "six source hashes/statuses/issues/counts/mart hashes/summaries plus synthetic limits", [verification_ref], self._check_scen_004)
        self.evaluate("ACC-SCEN-005", "replay", "read same-seed/different-seed/idempotent-load controls", "same seed identical; second seed different and valid; exact batch no-op", [verification_ref], self._check_scen_005)

        self.evaluate("ACC-AGENT-001", "boundary", "inspect deterministic modules and native task requests", "SQL/Python own truth calculations; native tasks consume immutable evidence for analysis", ["alma/warehouse.py", "alma/lifecycle.py", "alma/native_agents.py", workspace_ref + "/processes"], self._check_agent_001)
        self.evaluate("ACC-AGENT-002", "contract", "validate role contracts, requests and response schema", "seven versioned roles with bounded authority/completion/fail-closed rules and hashed requests", ["agents/", "contracts/native-agent-response.schema.json", workspace_ref + "/processes"], self._check_agent_002)
        self.evaluate("ACC-AGENT-003", "native-runtime", "validate six analyst and six reviewer dispatches and release run index", "12 live native dispatches, reviewer differs from analyst per process, >=2 models, Astra reviewer", [workspace_ref + "/processes", self.ref(self.workspace.parent / "agents" / "task-runs.json")], self._check_agent_003)
        self.evaluate("ACC-AGENT-004", "schema+evidence", "validate native responses and terminal packets", "all facts resolve; facts/unknowns/hypotheses/recommendations/review remain separate", [workspace_ref + "/processes", "alma/native_agents.py"], self._check_agent_004)
        self.evaluate("ACC-AGENT-005", "receipt+index", "validate request/response hashes, dispatches, traces and release run index", "12 accepted bundles with matching native receipts and indexed trace paths", [workspace_ref + "/processes", self.ref(self.workspace.parent / "agents" / "task-runs.json")], self._check_agent_005)
        self.evaluate("ACC-AGENT-006", "adversarial", "validate Astra review probes, findings and reviewed file hashes", "all probes pass, all findings independently resolved, no material unresolved finding, reviewed hashes current", ["docs/review-summary-v2.json", "docs/ADVERSARIAL-REVIEW-v2.md", verification_ref], self._check_agent_006)
        self.evaluate("ACC-AGENT-007", "authority+immutability", "hash sources before/after process validation and inspect packets", "native validation leaves source/warehouse/lifecycle unchanged and every action remains prohibited", [workspace_ref + "/processes", workspace_ref + "/workspace.json"], self._check_agent_007)

        self.evaluate("ACC-OUT-001", "export", "compare mart/lifecycle exports with both SQLite databases", "all mart and lifecycle exports reconcile to database rows", [workspace_ref + "/marts", workspace_ref + "/lifecycle/exports"], self._check_out_001)
        self.evaluate("ACC-OUT-002", "decision-packet", "validate weekly-growth-review terminal packet", "<=5 evidence-bound recommendations with metric, guardrail, population, window, closure and blocked execution", [workspace_ref + "/processes/weekly-growth-review/decision-packet.json"], self._check_out_002)
        self.evaluate("ACC-OUT-003", "finance", "query finance_monthly/cash_daily/reconciliation and validate finance packet", "finance components remain distinct and every bridge control passes", [workspace_ref + "/marts/finance_monthly.json", workspace_ref + "/marts/cash_daily.json", workspace_ref + "/marts/reconciliation.json", workspace_ref + "/processes/finance-close/decision-packet.json"], self._check_out_003)
        self.evaluate("ACC-OUT-004", "market-evidence", "validate research register and market-to-experiment packet", "sources retain provenance/limits and native packet preserves unknowns without demand/sales promotion", [workspace_ref + "/research.json", workspace_ref + "/processes/market-to-experiment/decision-packet.json"], self._check_out_004)

        self.evaluate("ACC-REL-002", "end-to-end", "read clean-install receipt, full verification and complete release workspace", "fresh offline build exits zero and all deterministic/native artifacts validate", [self.ref(self.workspace.parent / "clean-install.json"), verification_ref, workspace_ref + "/workspace.json"], self._check_rel_002)
        self.evaluate("ACC-REL-003", "release-audit", f"{sys.executable} scripts/audit_release.py", "fresh and persisted secret/PII-like/license/public-path audit pass", ["scripts/audit_release.py", self.ref(self.workspace.parent / "release-audit.json"), "LICENSE"], self._check_rel_003)

        expected_ids = set(re.findall(r"ACC-[A-Z]+-[0-9]{3}", (ROOT / "specs" / "PRD.md").read_text(encoding="utf-8")))
        result_ids = {row["acceptance_id"] for row in self.results} | {"ACC-REL-001"}
        shape_ok = all(set(row) == {"acceptance_id", "status", "check_type", "command_or_query", "evidence_refs", "observed", "expected", "checked_at_utc"} for row in self.results)
        self.evaluate(
            "ACC-REL-001",
            "acceptance-registry",
            "parse specs/PRD.md and compare generated acceptance IDs/schema",
            "exactly 32 unique PRD IDs, each with required result fields and allowed status",
            ["specs/PRD.md", "specs/SCOPE-MATRIX.md", "scripts/check_scope_v2.py"],
            lambda: (expected_ids == result_ids and len(expected_ids) == 32 and shape_ok, {"prd_ids": len(expected_ids), "result_ids": len(result_ids), "missing": sorted(expected_ids - result_ids), "unexpected": sorted(result_ids - expected_ids), "result_shape_before_self": shape_ok}),
        )
        return self.results

    # Process checks
    def _check_proc_001(self):
        native = process_definitions()
        business = lifecycle_definitions()
        expected = {"procure-to-stock": "PTS-01", "lead-to-delivery": "LTD-01", "return-to-refund": "RTR-01", "finance-close": "FCL-01", "weekly-growth-review": "WGR-01", "market-to-experiment": "MTE-01"}
        mapping = {key: value["contract_id"] for key, value in business.items()}
        valid = set(native) == set(expected) == set(business) and mapping == expected and all(value.get("version") == "2.0" for value in native.values()) and all(value.get("version") == "2.0.0" for value in business.values())
        return valid, {"native_processes": sorted(native), "business_mapping": mapping}

    def _check_proc_002(self):
        database = self.workspace / "lifecycle" / "lifecycle.sqlite3"
        if not database.is_file(): raise Blocked("missing lifecycle database")
        connection = sqlite3.connect(database); connection.row_factory = sqlite3.Row
        try:
            relations = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            instances = [dict(row) for row in connection.execute("SELECT * FROM lifecycle_instances")]
            event_count = connection.execute("SELECT count(*) FROM lifecycle_events").fetchone()[0]
            receipts = [json.loads(row[0]) for row in connection.execute("SELECT receipt_json FROM lifecycle_receipts")]
        finally: connection.close()
        expected_relations = {"lifecycle_instances", "lifecycle_events", "lifecycle_idempotency", "lifecycle_receipts"}
        instance_fields = {"process_id", "process_contract_id", "instance_id", "definition_version", "owner_role", "scenario_id", "run_id", "current_state", "last_event_hash", "updated_at_utc", "synthetic"}
        process_folders = list((self.workspace / "processes").glob("*/state.json"))
        journals_ok = len(process_folders) == 6
        for state_path in process_folders:
            state = read_json(state_path); events = verify_events(state_path.parent)
            journals_ok &= bool(events) and state.get("event_hash") == events[-1]["hash"] and state.get("process_id") == state_path.parent.name
        ok = expected_relations <= relations and len(instances) >= 6 and event_count > 30 and all(instance_fields <= set(row) and row["synthetic"] == 1 for row in instances) and any(receipt.get("details", {}).get("gate") for receipt in receipts) and journals_ok
        return ok, {"relations": sorted(expected_relations & relations), "instances": len(instances), "events": event_count, "receipts": len(receipts), "native_journals": len(process_folders), "hash_chain": verify_hash_chains(database)}

    def _check_proc_003(self):
        summary = self.workspace_json("lifecycle/summary.json")
        checks = summary.get("checks", {})
        ok = summary.get("status") == "PASS" and summary.get("controlled_illegal_transitions") == 6 and checks.get("illegal_transitions_rejected") is True and checks.get("golden_terminal_states") is True
        return ok, {"status": summary.get("status"), "controlled_illegal_transitions": summary.get("controlled_illegal_transitions"), "checks": checks}

    def _check_proc_004(self):
        probe = self.lifecycle_probe()
        ok = probe["first"] == "APPLIED" and probe["replay"] == "NO_OP_REPLAY" and probe["conflict"] == "CONFLICT" and probe["conflict_code"] == "CTR_DUPLICATE_EVENT_CONFLICT" and probe["idempotency_business_events"] == 1
        return ok, probe

    def _check_proc_005(self):
        probe = self.lifecycle_probe()
        ok = probe["approval_attempt"] == "WAITING" and probe["approval_code"] == "APPROVAL_MISSING" and probe["approval_state"] == "WAITING_APPROVAL"
        return ok, {key: probe[key] for key in ("approval_attempt", "approval_code", "approval_state")}

    def _check_proc_006(self):
        probe = self.lifecycle_probe()
        packets = list((self.workspace / "processes").glob("*/decision-packet.json"))
        unsafe = []
        for path in packets:
            packet = read_json(path)
            if packet.get("external_execution") != "PROHIBITED" or packet.get("synthetic") is not True or any(rec.get("execution") != "PROHIBITED" or rec.get("approval_required") is not True for rec in packet.get("recommendations", [])):
                unsafe.append(path.parent.name)
        # Pending live packets are handled by ACC-AGENT-003, not a false failure here.
        return probe["unsafe_payload_rejected"] and not unsafe, {"unsafe_payload_rejected": probe["unsafe_payload_rejected"], "packets_present": len(packets), "unsafe_packets": unsafe}

    # Data checks
    def _check_data_001(self):
        schema = self.schema(); tables = schema["tables"]
        source_ok = True; strict_count = 0; fk_expected = 0; fk_observed = 0
        database = self.workspace / "warehouse.sqlite3"
        connection = sqlite3.connect(database)
        try:
            sql_by_name = {row[0]: row[1] or "" for row in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
        finally: connection.close()
        for name, columns in TABLE_COLUMNS.items():
            meta = tables.get(name, {}); observed_columns = meta.get("columns", [])
            source_ok &= [row["name"] for row in observed_columns] == list(columns)
            source_ok &= bool(observed_columns) and observed_columns[0]["name"] == "id" and observed_columns[0]["pk"] == 1
            source_ok &= all(row["type"] in {"TEXT", "INTEGER"} for row in observed_columns)
            strict_count += "STRICT" in sql_by_name.get(name, "").upper()
            expected_fks = FOREIGN_KEYS.get(name, ())
            fk_expected += len(expected_fks); fk_observed += len(meta.get("foreign_keys", []))
            source_ok &= len(meta.get("foreign_keys", [])) == len(expected_fks)
        verification = self.verification(); replay = verification.get("replay_and_integrity", {})
        ok = source_ok and strict_count == len(TABLE_COLUMNS) and fk_observed == fk_expected and replay.get("bad_batch_rejected_prior_marts_preserved") is True
        return ok, {"source_tables": len(TABLE_COLUMNS), "strict_tables": strict_count, "expected_foreign_keys": fk_expected, "observed_foreign_keys": fk_observed, "bad_batch_preserved": replay.get("bad_batch_rejected_prior_marts_preserved")}

    def _check_data_002(self):
        schema = self.schema(); catalog = schema.get("catalog", {}); names = set(schema["tables"])
        controls = {"coverage", "warehouse_manifest", "ingest_batches", "rejected_batches"}
        lifecycle_db = self.workspace / "lifecycle" / "lifecycle.sqlite3"
        if not lifecycle_db.is_file(): raise Blocked("missing lifecycle database")
        db = sqlite3.connect(lifecycle_db)
        try: lifecycle_names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally: db.close()
        lifecycle_expected = {"lifecycle_instances", "lifecycle_events", "lifecycle_idempotency", "lifecycle_receipts"}
        expected = set(TABLE_COLUMNS) | set(MARTS) | controls
        catalog_ok = all(name in catalog and catalog[name].get("grain") for name in set(TABLE_COLUMNS) | set(MARTS))
        ok = expected <= names and set(schema.get("marts", [])) == set(MARTS) and lifecycle_expected <= lifecycle_names and catalog_ok
        return ok, {"warehouse_relations": len(names), "canonical_tables": len(set(TABLE_COLUMNS) & names), "marts": len(set(MARTS) & names), "controls": sorted(controls & names), "lifecycle_relations": sorted(lifecycle_expected & lifecycle_names), "catalog_grains_complete": catalog_ok}

    def _check_data_003(self):
        database = self.workspace / "warehouse.sqlite3"
        mismatches = []; csv_missing = []
        for name in MARTS:
            exported = read_json(self.workspace / "marts" / f"{name}.json")
            queried = query_mart(database, name)
            if canonical(exported) != canonical(queried): mismatches.append(name)
            csv_path = self.workspace / "marts" / f"{name}.csv"
            if queried and not csv_path.is_file(): csv_missing.append(name)
            if csv_path.is_file():
                with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                    if sum(1 for _ in csv.DictReader(stream)) != len(queried): mismatches.append(name + ":csv-row-count")
        return not mismatches and not csv_missing, {"marts_checked": len(MARTS), "mismatches": mismatches, "missing_csv": csv_missing}

    def _check_data_004(self):
        lineage = self.workspace_json("lineage.json"); sql = lineage.get("sql", {})
        missing = []; mismatches = []
        for name in MARTS:
            path = ROOT / "models" / "marts" / f"{name}.sql"; entry = sql.get(path.name)
            if not entry: missing.append(path.name); continue
            text = path.read_text(encoding="utf-8-sig")
            if entry.get("sha256") != sha256_file(path) or entry.get("text") != text: mismatches.append(path.name)
        return not missing and not mismatches and set(lineage.get("schema", {}).get("marts", [])) == set(MARTS), {"sql_entries": len(sql), "mart_sql_checked": len(MARTS), "missing": missing, "mismatches": mismatches}

    def _check_data_005(self):
        manifest = self.workspace_json("workspace.json"); failed = []
        for name, expected in manifest.get("sha256", {}).items():
            path = self.workspace / name
            if not path.is_file() or sha256_file(path) != expected: failed.append(name)
        for name, expected in manifest.get("binary_sha256", {}).items():
            path = self.workspace / name
            if not path.is_file() or sha256_file(path) != expected: failed.append(name)
        meta = manifest.get("metadata", {})
        ok = not failed and meta.get("synthetic") is True and meta.get("contract_version") == "2.0" and _required_meta(meta)
        return ok, {"text_hashes": len(manifest.get("sha256", {})), "binary_hashes": len(manifest.get("binary_sha256", {})), "failed": failed, "metadata": {key: meta.get(key) for key in ("synthetic", "seed", "scenario", "start_date", "as_of", "contract_version")}}

    def _check_data_006(self):
        replay = self.verification().get("replay_and_integrity", {})
        key = "bad_batch_rejected_prior_marts_preserved"
        return replay.get(key) is True, {key: replay.get(key)}

    def _check_data_007(self):
        verification = self.verification(); load = self.workspace_json("warehouse-load.json")
        controls = load.get("control_results", [])
        scenarios = {row.get("scenario"): row for row in verification.get("scenarios", [])}
        ok = verification.get("tests", {}).get("passed") is True and bool(controls) and all(row.get("passed") == 1 for row in controls) and scenarios.get("missing_cost", {}).get("passed") is True and scenarios.get("broken_link", {}).get("passed") is True
        return ok, {"tests": verification.get("tests"), "warehouse_controls": [{"check_id": row.get("check_id"), "passed": row.get("passed")} for row in controls], "controlled_failures": {name: scenarios.get(name, {}).get("passed") for name in ("missing_cost", "broken_link")}}

    # Scenario checks
    def _check_scen_001(self):
        data = self.workspace_json("data.json"); tables = data["tables"]; meta = data["metadata"]
        days = (date.fromisoformat(meta["as_of"]) - date.fromisoformat(meta["start_date"])).days + 1
        item_counts = Counter(row["order_id"] for row in tables["order_items"])
        checks = {
            "days": days == 365,
            "variants": len(tables["variants"]) >= 36,
            "orders": len(tables["orders"]) == 1200,
            "multi_item_orders": any(value > 1 for value in item_counts.values()),
            "campaigns": bool(tables["campaigns"]), "sessions": bool(tables["sessions"]), "leads": bool(tables["leads"]),
            "experiments": bool(tables["experiments"]), "twelve_expense_months": len({row["date"][:7] for row in tables["expenses"]}) >= 12,
            "synthetic": meta.get("synthetic") is True,
        }
        return all(checks.values()), {"checks": checks, "counts": {name: len(tables[name]) for name in ("variants", "orders", "order_items", "campaigns", "sessions", "leads", "experiments", "expenses")}}

    def _check_scen_002(self):
        data = self.workspace_json("data.json"); tables = data["tables"]; meta = data["metadata"]
        products = {row["id"]: row for row in tables["products"]}; variants = tables["variants"]
        lifecycle_stages = {row["lifecycle"] for row in products.values()}
        lifecycle_stages.update(row["from_stage"] for row in tables["lifecycle_events"])
        lifecycle_stages.update(row["to_stage"] for row in tables["lifecycle_events"])
        payments = Counter(row["order_id"] for row in tables["payments"]); receipts = Counter(row["purchase_order_id"] for row in tables["purchase_receipts"])
        delivered_dates = [date.fromisoformat(row["delivered_date"]) for row in tables["orders"] if row.get("delivered_date")]
        as_of = date.fromisoformat(meta["as_of"])
        checks = {
            "sizes": len({row["size"] for row in variants}) > 1,
            "colors": len({row["color"] for row in variants}) > 3,
            "lifecycles": {"idea", "sample", "launched", "clearance"} <= lifecycle_stages,
            "multi_item_baskets": any(value > 1 for value in Counter(row["order_id"] for row in tables["order_items"]).values()),
            "split_payments": any(value > 1 for value in payments.values()),
            "split_receipts": any(value > 1 for value in receipts.values()),
            "cancellations": any(row["status"] == "cancelled" for row in tables["orders"]),
            "return_dispositions": {0, 1} <= {row["restock"] for row in tables["returns"]},
            "refunds_and_credits": bool(tables["refunds"] and tables["credit_notes"]),
            "inventory_counts": bool(tables["inventory_counts"]),
            "mature_and_immature": any((as_of - value).days >= 30 for value in delivered_dates) and any((as_of - value).days < 30 for value in delivered_dates),
            "experiment_assignment_outcomes": bool(tables["experiment_assignments"] and tables["experiment_outcomes"]),
        }
        return all(checks.values()), {"checks": checks}

    def _check_scen_003(self):
        verification = self.verification(); rows = verification.get("scenarios", [])
        expected = {"normal", "stock_pressure", "promotion_illusion", "cash_squeeze", "missing_cost", "broken_link"}
        index = read_json(self.workspace.parent / "scenarios" / "index.json")
        indexed_rows = index.get("scenarios", []) if isinstance(index, dict) else []
        indexed_names = {row if isinstance(row, str) else row.get("scenario") for row in indexed_rows}
        indexed_details_match = True
        verified_by_name = {row.get("scenario"): row for row in rows}
        for indexed in indexed_rows:
            if not isinstance(indexed, dict):
                continue
            verified = verified_by_name.get(indexed.get("scenario"), {})
            for field in ("status", "passed"):
                if field in indexed and indexed[field] != verified.get(field): indexed_details_match = False
        mechanisms = verification.get("mechanism_checks", {})
        summary = self.workspace_json("lifecycle/summary.json")
        log_path = self.verification_path.parent / "tests.log"
        if not log_path.is_file(): raise Blocked("missing tests.log beside verification")
        log = log_path.read_text(encoding="utf-8-sig")
        required_tests = (
            "test_each_process_rejects_an_illegal_first_transition_without_instance_effect",
            "test_missing_approval_waits_and_overreceipt_rolls_back",
            "test_refund_overflow_and_finance_bridge_mismatch_have_no_transition_effect",
            "test_same_event_is_noop_and_changed_duplicate_blocks_without_duplicate_business_event",
            "test_stale_source_and_late_assignment_are_rejected_by_derived_gates",
            "test_non_synthetic_and_execution_payloads_are_never_accepted",
            "test_exact_values_stale_hash_and_authority",
        )
        missing_tests = [name for name in required_tests if name not in log]
        index_ok = isinstance(index, dict) and index.get("synthetic") is True and indexed_names == expected and indexed_details_match
        ok = index_ok and {row.get("scenario") for row in rows} == expected and all(row.get("passed") for row in rows) and mechanisms and all(mechanisms.values()) and summary.get("checks", {}).get("illegal_transitions_rejected") is True and not missing_tests
        return ok, {"scenarios": sorted(row.get("scenario") for row in rows), "indexed_scenarios": sorted(name for name in indexed_names if name), "scenario_index_valid": index_ok, "scenario_pass": all(row.get("passed") for row in rows), "mechanisms": mechanisms, "illegal_transitions": summary.get("controlled_illegal_transitions"), "missing_fault_tests": missing_tests}

    def _check_scen_004(self):
        verification = self.verification(); rows = verification.get("scenarios", []); hashes = verification.get("source_hashes", {})
        required = {"scenario", "status", "passed", "quality_issues"}
        complete = True; details = {}
        for row in rows:
            name = row.get("scenario")
            built = name != "broken_link"
            complete &= required <= set(row) and bool(re.fullmatch(r"[0-9a-f]{64}", hashes.get(name, "")))
            if built: complete &= {"summary", "counts", "mart_hashes"} <= set(row) and len(row.get("mart_hashes", {})) == len(MARTS)
            else: complete &= row.get("status") == "BLOCKED" and "error" in row
            details[name] = {"status": row.get("status"), "passed": row.get("passed"), "quality_issues": row.get("quality_issues"), "source_hash": hashes.get(name), "mart_hashes": len(row.get("mart_hashes", {}))}
        limit = verification.get("limits", "")
        complete &= "actual native execution" in limit.lower() or "deterministic" in limit.lower()
        return bool(rows) and complete, details

    def _check_scen_005(self):
        replay = self.verification().get("replay_and_integrity", {})
        booleans = {key: value for key, value in replay.items() if isinstance(value, bool)}
        required = {"same_seed_source_replay", "second_seed_valid_and_different", "same_batch_noop", "bad_batch_rejected_prior_marts_preserved"}
        return required <= set(booleans) and all(booleans[key] for key in required), booleans

    # Agent checks
    def _check_agent_001(self):
        requests = list((self.workspace / "processes").glob("*/tasks/*.request.json"))
        modes = []; authority = []
        for path in requests:
            request = read_json(path); modes.append(request.get("execution_mode")); authority.append(request.get("contract", {}).get("authority", {}).get("external_business_actions"))
        source_text = (ROOT / "alma" / "native_agents.py").read_text(encoding="utf-8")
        deterministic_text = (ROOT / "alma" / "lifecycle.py").read_text(encoding="utf-8") + (ROOT / "alma" / "warehouse.py").read_text(encoding="utf-8")
        ok = len(requests) >= 6 and all(mode == "native-codex-task-bridge" for mode in modes) and all(item == "PROHIBITED" for item in authority) and "never pretends a rule template is an LLM call" in source_text and "fail-closed gates" in deterministic_text
        return ok, {"requests": len(requests), "execution_modes": sorted(set(modes)), "authority": sorted(set(authority))}

    def _check_agent_002(self):
        role_paths = sorted((ROOT / "agents").glob("*.json")); invalid = []
        expected_fields = {"id", "version", "name", "objective", "tools", "loop", "output", "runtime", "authority", "completion", "fail_closed"}
        for path in role_paths:
            role = read_json(path)
            if set(role) != expected_fields or role.get("version") != "2.0" or role.get("authority", {}).get("external_business_actions") != "PROHIBITED" or not role.get("completion") or not role.get("fail_closed"):
                invalid.append(path.name)
        schema = read_json(ROOT / "contracts" / "native-agent-response.schema.json")
        requests = list((self.workspace / "processes").glob("*/tasks/*.request.json")); request_failures = []
        for path in requests:
            try: verify_request(read_json(path))
            except ValueError: request_failures.append(relative(path))
        ok = len(role_paths) == 7 and not invalid and schema.get("type") == "object" and bool(schema.get("required")) and len(requests) >= 6 and not request_failures
        return ok, {"roles": len(role_paths), "invalid_roles": invalid, "schema_required_fields": schema.get("required"), "requests_checked": len(requests), "request_failures": request_failures}

    def _check_agent_003(self):
        bundle = self.native_bundle(); processes = bundle["processes"]
        complete_status = all(value["status"] in {"REVIEW", "READY_FOR_OWNER"} for value in processes.values())
        independent = all(value["analyst_agent_id"] != value["reviewer_agent_id"] for value in processes.values())
        astra = any(value["reviewer_model"] == "gpt-6-astra" for value in processes.values())
        ok = len(processes) == 6 and complete_status and independent and len(bundle["distinct_models"]) >= 2 and astra
        return ok, {"processes": processes, "distinct_models": bundle["distinct_models"], "unique_analysts": len(set(bundle["analyst_agent_ids"])), "unique_reviewers": len(set(bundle["reviewer_agent_ids"])), "reviewer_independent_per_process": independent, "astra_reviewer": astra, "run_index": bundle["run_index"]}

    def _check_agent_004(self):
        bundle = self.native_bundle(); processes = bundle["processes"]
        ok = len(processes) == 6 and all(value["facts"] >= 2 and value["status"] in {"REVIEW", "READY_FOR_OWNER"} for value in processes.values())
        return ok, {key: {"status": value["status"], "facts": value["facts"], "recommendations": value["recommendations"], "packet_hash": value["packet_hash"]} for key, value in processes.items()}

    def _check_agent_005(self):
        bundle = self.native_bundle(); receipts = list((self.workspace / "processes").glob("*/tasks/*.dispatch.json"))
        efforts = []; retries = 0
        for path in receipts:
            receipt = read_json(path); efforts.append(receipt["effort"]); retries += len(receipt["retry_history"])
        indexed = bundle["run_index"]
        return len(receipts) == 12 and indexed["runs"] == 12, {"receipts": len(receipts), "models": bundle["distinct_models"], "efforts": sorted(set(efforts)), "retry_entries": retries, "validated_by_native_bundle": True, "run_index": indexed}

    def _check_agent_006(self):
        summary_path = ROOT / "docs" / "review-summary-v2.json"; summary = read_json(summary_path)
        probes = [*summary.get("sql_probes", []), *summary.get("finance_probes", []), *summary.get("bridge_probes", [])]
        unresolved = summary.get("unresolved_material_findings")
        findings = summary.get("findings", [])
        hash_failures = []
        for name, expected in summary.get("reviewed_file_sha256", {}).items():
            path = ROOT / name
            if not path.is_file() or sha256_file(path) != expected: hash_failures.append(name)
        tests_passed = self.verification().get("tests", {}).get("passed") is True
        ok = summary.get("status") == "PASS" and bool(probes) and all(item.get("passed") is True for item in probes) and unresolved == [] and bool(findings) and all(item.get("status") == "RESOLVED_INDEPENDENTLY_RECHECKED" for item in findings) and not hash_failures and tests_passed
        return ok, {"reviewer": summary.get("reviewer"), "probes": len(probes), "probes_passed": sum(item.get("passed") is True for item in probes), "findings": findings, "unresolved": unresolved, "reviewed_hash_failures": hash_failures, "full_tests_passed": tests_passed}

    def _check_agent_007(self):
        targets = [self.workspace / "data.json", self.workspace / "warehouse.sqlite3", self.workspace / "lifecycle" / "lifecycle.sqlite3"]
        if not all(path.is_file() for path in targets): raise Blocked("source/warehouse/lifecycle artifact missing")
        before = {relative(path): sha256_file(path) for path in targets}
        bundle = self.native_bundle()
        after = {relative(path): sha256_file(path) for path in targets}
        unsafe = []
        for process_id in bundle["processes"]:
            packet = read_json(self.workspace / "processes" / process_id / "decision-packet.json")
            if packet.get("external_execution") != "PROHIBITED" or any(rec.get("execution") != "PROHIBITED" or rec.get("approval_required") is not True for rec in packet.get("recommendations", [])):
                unsafe.append(process_id)
        return before == after and not unsafe, {"immutable_hashes_unchanged": before == after, "targets": before, "unsafe_packets": unsafe}

    # Output checks
    def _check_out_001(self):
        mart_ok, mart_observed = self._check_data_003()
        lifecycle_db = self.workspace / "lifecycle" / "lifecycle.sqlite3"
        if not lifecycle_db.is_file(): raise Blocked("missing lifecycle database")
        exports = self.workspace / "lifecycle" / "exports"; mismatches = []
        db = sqlite3.connect(lifecycle_db); db.row_factory = sqlite3.Row
        try:
            for file_name, table in (("instances.json", "lifecycle_instances"), ("events.json", "lifecycle_events"), ("receipts.json", "lifecycle_receipts")):
                exported = read_json(exports / file_name)
                count = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                if len(exported) != count: mismatches.append(file_name)
        finally: db.close()
        return mart_ok and not mismatches, {"mart_exports": mart_observed, "lifecycle_export_mismatches": mismatches}

    def _check_out_002(self):
        self.native_bundle()
        packet = read_json(self.workspace / "processes" / "weekly-growth-review" / "decision-packet.json")
        fields_ok = all(key in packet for key in ("facts", "unknowns", "hypotheses", "recommendations", "review")) and bool(packet["facts"]) and bool(packet["unknowns"])
        rec_fields = {"id", "action", "evidence_refs", "primary_metric", "guardrail", "window", "population", "closure_rule", "approval_required", "execution"}
        rec_ok = len(packet["recommendations"]) <= 5 and all(set(rec) == rec_fields and rec["approval_required"] is True and rec["execution"] == "PROHIBITED" for rec in packet["recommendations"])
        return fields_ok and rec_ok, {"status": packet.get("status"), "facts": len(packet.get("facts", [])), "unknowns": len(packet.get("unknowns", [])), "recommendations": len(packet.get("recommendations", [])), "recommendation_contract": rec_ok}

    def _check_out_003(self):
        self.native_bundle(); database = self.workspace / "warehouse.sqlite3"
        finance = query_mart(database, "finance_monthly"); cash = query_mart(database, "cash_daily"); reconciliation = query_mart(database, "reconciliation")
        required_finance = {"net_revenue_cents", "cogs_cents", "gross_profit_cents", "variable_expense_cents", "expense_accrual_cents", "contribution_after_variable_cents", "operating_after_all_expenses_cents", "net_cash_change_cents"}
        required_cash = {"cash_in_cents", "refund_out_cents", "supplier_out_cents", "expense_out_cents", "net_cash_change_cents", "cumulative_cash_movement_cents"}
        packet = read_json(self.workspace / "processes" / "finance-close" / "decision-packet.json")
        ok = bool(finance and cash and reconciliation) and required_finance <= set(finance[0]) and required_cash <= set(cash[0]) and all(row.get("passed") == 1 for row in reconciliation) and packet.get("external_execution") == "PROHIBITED"
        return ok, {"finance_months": len(finance), "cash_days": len(cash), "finance_fields": sorted(required_finance & set(finance[0] if finance else {})), "cash_fields": sorted(required_cash & set(cash[0] if cash else {})), "reconciliation": [{"check_id": row.get("check_id"), "passed": row.get("passed")} for row in reconciliation], "packet_status": packet.get("status")}

    def _check_out_004(self):
        self.native_bundle(); research = self.workspace_json("research.json")
        sources = research.get("sources", []); source_ok = bool(sources)
        for source in sources:
            source_ok &= all(source.get(key) not in (None, "") for key in ("id", "publisher", "title", "license", "limitations", "status"))
            source_ok &= bool(source.get("published") or source.get("observed_period") or source.get("status") in {"ACCESS_FAILED", "USER_SUPPLIED", "LANDING_ONLY"})
        packet = read_json(self.workspace / "processes" / "market-to-experiment" / "decision-packet.json")
        unknown_text = " ".join(packet.get("unknowns", []) + packet.get("hypotheses", []) + packet.get("review", {}).get("challenges", [])).lower()
        limitation_ok = bool(packet.get("unknowns")) and ("synt" in unknown_text or "demand" in unknown_text or "evidence" in unknown_text)
        return source_ok and limitation_ok and packet.get("external_execution") == "PROHIBITED", {"sources": len(sources), "source_contract": source_ok, "packet_status": packet.get("status"), "unknowns": len(packet.get("unknowns", [])), "limitation_language_present": limitation_ok}

    # Release checks
    def _check_rel_002(self):
        verification = self.verification(); manifest = self.workspace_json("workspace.json")
        native = self.native_bundle()
        clean_path = self.workspace.parent / "clean-install.json"
        clean = read_json(clean_path)
        required = ["warehouse.sqlite3", "lineage.json", "DOSSIER.md", "DOSSIER.html", "lifecycle/summary.json"]
        missing = [name for name in required if not (self.workspace / name).is_file()]
        statuses = native["statuses"]
        fresh = clean.get("fresh_workspace", {})
        comparison = clean.get("comparison_to_v02_workspace", {})
        copied = clean.get("copied_project", {})
        clean_checks = clean.get("checks", {})
        clean_ok = (
            clean.get("version") == "0.2"
            and clean.get("result") == "PASSED"
            and copied.get("network_access") is False
            and copied.get("git_commands") is False
            and fresh.get("workspace_status") == "PASS"
            and fresh.get("source_tables") == 30
            and fresh.get("marts") == 11
            and len(fresh.get("process_status", {})) == 6
            and set(fresh.get("process_status", {}).values()) == {"WAITING_AGENT"}
            and all(value is True for value in clean_checks.values())
            and comparison.get("canonical_data_equal") is True
            and comparison.get("source_table_csv_equal") is True
            and comparison.get("mart_json_equal") is True
            and comparison.get("mart_csv_equal") is True
            and comparison.get("manifest_hash_entries_verified") is True
            and comparison.get("manifest_binary_entries_verified") is True
            and clean.get("portable_snapshot", {}).get("portability_verified") is True
        )
        ok = verification.get("passed") is True and manifest.get("status") in {"PASS", "REVIEW"} and not missing and len(statuses) == 6 and all(value in {"REVIEW", "READY_FOR_OWNER"} for value in statuses.values()) and clean_ok
        return ok, {"verification_passed": verification.get("passed"), "tests": verification.get("tests"), "workspace_status": manifest.get("status"), "missing": missing, "process_statuses": statuses, "clean_install": {"result": clean.get("result"), "network_access": copied.get("network_access"), "fresh_workspace_status": fresh.get("workspace_status"), "source_tables": fresh.get("source_tables"), "marts": fresh.get("marts"), "checks_passed": bool(clean_checks) and all(value is True for value in clean_checks.values()), "portable_snapshot": clean.get("portable_snapshot", {}).get("portability_verified")}}

    def _check_rel_003(self):
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_release.py")], cwd=ROOT, capture_output=True, text=True, timeout=120)
        try: artifact = json.loads(completed.stdout)
        except json.JSONDecodeError as exc: raise ValueError("release audit did not emit JSON: " + completed.stdout[-500:]) from exc
        persisted = read_json(self.workspace.parent / "release-audit.json")
        fields = ("schema_version", "license_present", "findings", "passed", "limits")
        persisted_matches = all(persisted.get(field) == artifact.get(field) for field in fields) and isinstance(persisted.get("text_files_checked"), int) and persisted["text_files_checked"] > 0
        ok = completed.returncode == 0 and artifact.get("passed") is True and artifact.get("license_present") is True and artifact.get("findings") == [] and persisted_matches
        return ok, {"returncode": completed.returncode, "passed": artifact.get("passed"), "license_present": artifact.get("license_present"), "text_files_checked": artifact.get("text_files_checked"), "findings": artifact.get("findings"), "persisted_matches_fresh_audit": persisted_matches}


def _required_meta(meta: dict[str, Any]) -> bool:
    return all(meta.get(key) not in (None, "") for key in ("seed", "scenario", "start_date", "as_of", "currency"))


def write_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value)); temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate all Alma v0.2 PRD acceptance IDs")
    parser.add_argument("--workspace", required=True, help="Completed v0.2 workspace directory")
    parser.add_argument("--verification", required=True, help="verify_v2 verification.json or its directory")
    parser.add_argument("--output", required=True, help="acceptance.json path or output directory")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if output.suffix.lower() != ".json": output = output / "acceptance.json"
    runner = ScopeRunner(Path(args.workspace), Path(args.verification))
    results = runner.run()
    counts = {status: sum(row["status"] == status for row in results) for status in ("PASS", "FAIL", "BLOCKED")}
    overall = "FAIL" if counts["FAIL"] else "BLOCKED" if counts["BLOCKED"] else "PASS"
    artifact = {
        "version": "2.0",
        "status": overall,
        "synthetic": True,
        "workspace": relative(Path(args.workspace)),
        "verification": relative(runner.verification_path),
        "checked_at_utc": runner.checked_at,
        "counts": counts,
        "results": results,
        "limits": "Acceptance of reproducible synthetic analytics and native run evidence; not proof of real Alma performance, adoption, causal impact, or authorization for external business action.",
    }
    write_atomic(output.resolve(), artifact)
    print(json.dumps({"status": overall, "counts": counts, "output": relative(output), "blocked": [row["acceptance_id"] for row in results if row["status"] == "BLOCKED"], "failed": [row["acceptance_id"] for row in results if row["status"] == "FAIL"]}, ensure_ascii=False, indent=2))
    return 0 if overall == "PASS" else 2 if overall == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
