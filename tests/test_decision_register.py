"""Phase 3 decision register contract and continuity tests."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from alma.decision_register import (
    append_status,
    create_register,
    export_csv,
    import_proposals,
    register_decision,
    verify_register,
)
from alma.native_agents_v1 import digest
from alma.operating_contracts import canonical_json
from alma.weekly_cycle import read_terminal_packet, start_cycle, verify_cycle
from tests.test_native_agents_v1 import receipt_for, response_for, trace_for
from tests.test_weekly_cycle import upstream


MODELS = {
    "merchandiser": "gpt-5.6-terra",
    "finance_analyst": "gpt-5.6-terra",
    "commerce_analyst": "gpt-6-luna",
    "returns_analyst": "gpt-6-luna",
    "growth_analyst": "gpt-6-sol",
    "market_researcher": "gpt-6-sol",
}


def terminal_cycle(home: Path) -> Path:
    from alma.weekly_cycle import record_dispatch, submit_response

    cut, mart = upstream(home)
    cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
    for role in sorted(MODELS):
        request = json.loads((cycle / "tasks" / f"{role}.request.json").read_text("utf-8"))
        response, trace = response_for(request), trace_for(request)
        response_path = cycle / "tasks" / f"{role}.response.json"
        trace_path = cycle / "tasks" / f"{role}.query-trace.json"
        response_path.write_bytes(canonical_json(response))
        trace_path.write_bytes(canonical_json(trace))
        receipt = receipt_for(request, response, trace, MODELS[role])
        receipt["agent_id"] = f"/root/decision_{role}"
        record_dispatch(cycle, role, response_path, trace_path, receipt)
        submit_response(cycle, role, response_path, trace_path,
                        cycle / "tasks" / f"{role}.dispatch.json")
    request = json.loads((cycle / "tasks" / "evidence_reviewer.request.json").read_text("utf-8"))
    response, trace = response_for(request), trace_for(request)
    response["verdict"] = "READY_FOR_OWNER"
    response_path = cycle / "tasks" / "evidence_reviewer.response.json"
    trace_path = cycle / "tasks" / "evidence_reviewer.query-trace.json"
    response_path.write_bytes(canonical_json(response))
    trace_path.write_bytes(canonical_json(trace))
    receipt = receipt_for(request, response, trace, "gpt-6-astra")
    receipt["agent_id"] = "/root/decision_reviewer"
    record_dispatch(cycle, "evidence_reviewer", response_path, trace_path, receipt)
    submit_response(cycle, "evidence_reviewer", response_path, trace_path,
                    cycle / "tasks" / "evidence_reviewer.dispatch.json")
    return cycle


def closure_check() -> dict:
    return {"kind": "machine", "pointer": "/metric_rows/0/value", "operator": "exists",
            "expected": None, "value_type": "existence", "unit": "row",
            "requires_later_cut": True}


class DecisionRegisterContractTests(unittest.TestCase):
    def test_owner_ready_packet_creates_stable_hash_chained_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cycle = terminal_cycle(home)
            packet = read_terminal_packet(cycle)
            recommendation_id = packet["recommendations"][0]["item"]["id"]
            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner", "finance_owner"])
            created = register_decision(register, cycle, recommendation_id, "growth_owner",
                "2026-10-01", "ACCEPT", closure_check())
            verified = verify_register(register, created["anchor"])
            self.assertEqual(created["decision_id"], verified["decisions"][0]["decision_id"])
            self.assertEqual("OPEN", verified["decisions"][0]["status"])
            self.assertEqual("GENESIS", verified["events"][0]["previous_hash"])
            self.assertEqual(verified["events"][0]["hash"], verified["anchor"]["terminal_hash"])
            self.assertEqual(digest(packet["provenance"]["source_sha256"]),
                             verified["decisions"][0]["source_hash"])

    def test_packet_owner_dates_duplicates_and_history_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cycle = terminal_cycle(home)
            packet = read_terminal_packet(cycle)
            recommendation_id = packet["recommendations"][0]["item"]["id"]
            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            for owner, due, choice in (("Erick", "2026-10-01", "ACCEPT"),
                                       ("growth_owner", "01/10/2026", "ACCEPT"),
                                       ("growth_owner", "2026-10-01", "EXECUTE")):
                with self.subTest(owner=owner, due=due, choice=choice), self.assertRaises(ValueError):
                    register_decision(register, cycle, recommendation_id, owner, due, choice,
                                      closure_check())
            created = register_decision(register, cycle, recommendation_id, "growth_owner",
                                        "2026-10-01", "ACCEPT", closure_check())
            with self.assertRaises(ValueError):
                register_decision(register, cycle, recommendation_id, "growth_owner",
                                  "2026-10-01", "ACCEPT", closure_check())
            append_status(register, created["decision_id"], "IN_PROGRESS", "growth_owner")
            with self.assertRaises(ValueError):
                append_status(register, created["decision_id"], "OPEN", "growth_owner")
            events_path = Path(register) / "events.json"
            events = json.loads(events_path.read_text("utf-8"))
            events[0]["due_date"] = "2099-01-01"
            events_path.write_bytes(canonical_json(events))
            with self.assertRaises(ValueError):
                verify_register(register)

    def test_csv_projection_is_deterministic_and_import_is_proposals_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cycle = terminal_cycle(home)
            packet = read_terminal_packet(cycle)
            recommendation_id = packet["recommendations"][0]["item"]["id"]
            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            created = register_decision(register, cycle, recommendation_id, "growth_owner",
                                        "2026-10-01", "ACCEPT", closure_check())
            before = (Path(register) / "events.json").read_bytes()
            destination = home / "projection.csv"
            export_csv(register, destination)
            first = destination.read_bytes()
            export_csv(register, destination)
            self.assertEqual(first, destination.read_bytes())
            proposals = home / "proposals.csv"
            with proposals.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["decision_id", "proposed_status",
                    "owner", "note_code", "new_due_date"])
                writer.writeheader()
                writer.writerow({"decision_id": created["decision_id"],
                    "proposed_status": "IN_PROGRESS", "owner": "growth_owner",
                    "note_code": "OWNER_REVIEWED", "new_due_date": ""})
            parsed = import_proposals(register, proposals)
            self.assertEqual("IN_PROGRESS", parsed[0]["proposed_status"])
            self.assertEqual(before, (Path(register) / "events.json").read_bytes())
            proposals.write_text("decision_id,proposed_status,owner,note_code,new_due_date\n"
                f"{created['decision_id']},IN_PROGRESS,growth_owner,=cmd,\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_proposals(register, proposals)


class DecisionContinuityTests(unittest.TestCase):
    """Task 2 tests are added during its RED phase."""

