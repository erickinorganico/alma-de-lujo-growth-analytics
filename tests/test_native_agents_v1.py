"""Disposable synthetic validator fixtures; no fixture is evidence of live inference."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from alma.operating_contracts import canonical_json
from alma.weekly_cycle import start_cycle
from tests.test_weekly_cycle import ROOT, upstream
from alma.native_agents_v1 import (
    validate_request, validate_response, validate_query_trace, validate_dispatch,
)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def response_for(request: dict) -> dict:
    return {"version": "operating-cycle-v1", "request_id": request["request_id"],
        "role": request["role"], "cut_id": request["cut_id"], "run_id": request["run_id"],
        "evidence_hash": request["evidence_hash"],
        "current_cut_sha256": request["current_cut_sha256"],
        "manifest_sha256": request["manifest_sha256"],
        "mart_bundle_sha256": request["mart_bundle_sha256"],
        "metric_contract_sha256": request["metric_contract_sha256"],
        "summary": "Synthetic cut has limited coverage; compare denominator and timing.",
        "facts": [
            {"id": "cut", "statement": "The verified cut ID is fixed.",
             "kind": "observation", "evidence_refs": ["/cut/cut_id"],
             "value": request["evidence"]["cut"]["cut_id"]},
            {"id": "metric", "statement": "A cited metric row retains its typed value.",
             "kind": "observation", "evidence_refs": ["/metric_rows/0/value"],
             "value": request["evidence"]["metric_rows"][0]["value"]}],
        "unknowns": ["Synthetic observations do not prove private-client demand."],
        "hypotheses": ["Measured mix may differ in a later observed window."],
        "recommendations": [{"id": "inspect-one", "action": "Review this metric with the owner.",
            "evidence_refs": ["/metric_rows/0/value"], "primary_metric": "cited metric row",
            "guardrail": "no spend without owner approval", "population": "synthetic sample",
            "window": "current cut", "closure_rule": "owner verifies next eligible cut",
            "approval_required": True, "execution": "PROHIBITED"}],
        "challenges": ["Check whether missing coverage changes the denominator."],
        "verdict": "REVIEW"}


def trace_for(request: dict) -> dict:
    row = request["evidence"]["metric_rows"][0]
    return {"version": "operating-cycle-v1", "request_id": request["request_id"],
        "role": request["role"], "queries": [{
            "query_id": "metric_rows.by_reconciliation_id",
            "question": "Which frozen row has this reconciliation ID?",
            "parameters": {"reconciliation_id": row["reconciliation_id"]},
            "result_refs": ["/metric_rows/0"], "row_count": 1}],
        "unavailable_reason": None}


def receipt_for(request: dict, response: dict, trace: dict,
                model: str = "gpt-5.6-terra") -> dict:
    return {"version": "operating-cycle-v1", "request_id": request["request_id"],
        "role": request["role"], "provider": "native-codex", "model": model,
        "agent_id": "/root/fixture_merchandiser", "effort": "medium",
        "started_at_utc": "2026-09-23T16:00:00Z", "completed_at_utc": "2026-09-23T16:02:00Z",
        "response_sha256": digest(response), "query_trace_sha256": digest(trace),
        "recorded_by": "parent-runtime", "mode": "live",
        "parent_validation_scope": "schema,evidence,typed-values,registered-query,hashes,authority"}


class NativeV1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        home = Path(cls.temporary.name)
        cut, mart = upstream(home)
        cycle = start_cycle(cut, mart, home / ".local" / "weekly-cycles")
        cls.requests = {role: json.loads(path.read_text(encoding="utf-8"))
            for role, path in ((role, Path(cycle["destination"]) / "tasks" /
                               f"{role}.request.json") for role in cycle["expected_roles"])}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_response_registered_query_and_parent_receipt(self) -> None:
        request = self.requests["merchandiser"]
        response, trace = response_for(request), trace_for(request)
        receipt = receipt_for(request, response, trace)
        self.assertTrue(validate_request(request))
        self.assertTrue(validate_response(request, response))
        self.assertTrue(validate_query_trace(request, trace))
        self.assertTrue(validate_dispatch(request, response, trace, receipt))

    def test_stale_typed_pointer_authority_and_bounds_fail(self) -> None:
        request = self.requests["merchandiser"]
        baseline = response_for(request)
        changes = (
            ("stale request", lambda row: row.update(request_id="0" * 64)),
            ("stale report", lambda row: row.update(current_cut_sha256="0" * 64)),
            ("bad pointer", lambda row: row["facts"][0].update(evidence_refs=["/cut/~2"])),
            ("missing pointer", lambda row: row["facts"][0].update(evidence_refs=["/cut/missing"])),
            ("typed null", lambda row: row["facts"][1].update(value=0)),
            ("extra mutation", lambda row: row.update(workspace_mutation=True)),
            ("business action", lambda row: row["recommendations"][0].update(execution="EXECUTE")),
            ("oversize", lambda row: row.update(summary="x" * 12001)),
            ("no unknown", lambda row: row.update(unknowns=[])),
        )
        for label, change in changes:
            with self.subTest(label=label):
                row = copy.deepcopy(baseline)
                change(row)
                with self.assertRaises(ValueError):
                    validate_response(request, row)
        changed_request = copy.deepcopy(request)
        changed_request["evidence"]["cut"]["cut_id"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_request(changed_request)

    def test_registered_query_and_receipt_tamper_fail(self) -> None:
        request = self.requests["merchandiser"]
        response, trace = response_for(request), trace_for(request)
        for label, change in (
            ("unregistered", lambda row: row["queries"][0].update(query_id="sql.execute")),
            ("wrong row", lambda row: row["queries"][0].update(result_refs=["/metric_rows/1"])),
            ("mutation", lambda row: row["queries"][0].update(sql="DELETE FROM metrics")),
            ("absent", lambda row: row.update(queries=[])),
        ):
            with self.subTest(label=label):
                row = copy.deepcopy(trace)
                change(row)
                with self.assertRaises(ValueError):
                    validate_query_trace(request, row)
        baseline = receipt_for(request, response, trace)
        for label, change in (
            ("wrong trace", lambda row: row.update(query_trace_sha256="0" * 64)),
            ("wrong model", lambda row: row.update(model="gpt-6-luna")),
            ("wrong provider", lambda row: row.update(provider="openai-api")),
            ("wrong mode", lambda row: row.update(mode="simulated")),
            ("no identity", lambda row: row.update(agent_id="fixture")),
            ("reverse time", lambda row: row.update(completed_at_utc="2026-09-23T15:00:00Z")),
            ("no parent scope", lambda row: row.update(parent_validation_scope="schema-only")),
        ):
            with self.subTest(label=label):
                row = copy.deepcopy(baseline)
                change(row)
                with self.assertRaises(ValueError):
                    validate_dispatch(request, response, trace, row)

    def test_role_contract_matches_every_request(self) -> None:
        contract = json.loads((ROOT / "agents" / "native-cycle-v1.roles.json").read_text(encoding="utf-8"))
        self.assertEqual("operating-cycle-v1", contract["version"])
        self.assertEqual(7, len(contract["roles"]))
        for role, request in self.requests.items():
            with self.subTest(role=role):
                self.assertEqual(request["expected_model_family"], contract["roles"][role]["model_family"])
                self.assertEqual(request["write_scope"], contract["roles"][role]["write_scope"])
                self.assertEqual(set(request["evidence"]["families"]),
                                 set(contract["roles"][role]["families"]))
                self.assertTrue(contract["roles"][role]["registered_query_required"])
                self.assertNotIn("row-level order", json.dumps(contract["roles"][role]).lower())
                self.assertNotIn("synthetic only", json.dumps(contract["roles"][role]).lower())
