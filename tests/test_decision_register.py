"""Phase 3 decision register contract and continuity tests."""
from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from alma.decision_register import (
    append_status,
    close_decision,
    create_register,
    extend_decision,
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
        response["recommendations"][0]["id"] = f"{role}-inspect-one"
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


def later_upstream(home: Path, cutoff: str = "2026-09-28T23:59:59-07:00") -> tuple[Path, Path]:
    from alma.operating_workspace import build_operating_workspace
    from alma.operating_marts import build_operating_marts

    source = home / "later-source"
    shutil.copytree(Path(__file__).resolve().parents[1] / "client" / "source-packs" / "v1" /
                    "synthetic", source)
    metadata_path = source / "metadata.json"
    metadata = json.loads(metadata_path.read_text("utf-8"))
    metadata["cutoff_at"] = cutoff
    for coverage in metadata["coverage"].values():
        coverage["window_end"] = cutoff[:10]
    metadata_path.write_bytes(canonical_json(metadata))
    cut = build_operating_workspace(source, private_root=home / "later-operating")
    marts = build_operating_marts(cut["destination"], home / ".local" / "later-marts",
        policy_path=Path(__file__).resolve().parents[1] / "policies" /
                    "operating-metrics-synthetic-v1.json",
        private_root=home / ".local" / "later-marts")
    return Path(cut["destination"]), Path(marts["destination"])


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
    def _registered(self, home: Path, due_date: str = "2026-09-25",
                    check: dict | None = None) -> tuple[str, str, dict]:
        cycle = terminal_cycle(home)
        packet = read_terminal_packet(cycle)
        recommendation_id = packet["recommendations"][0]["item"]["id"]
        register = create_register(home / ".local" / "decision-register" / "weekly",
            "weekly", ["growth_owner"])
        created = register_decision(register, cycle, recommendation_id, "growth_owner",
            due_date, "ACCEPT", check or closure_check())
        return register, created["decision_id"], created["anchor"]

    def test_second_cut_carries_stable_identity_and_marks_overdue_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            register, decision_id, anchor = self._registered(home, "2026-09-22")
            cut, marts = later_upstream(home)
            second = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                 prior_register=register, prior_anchor=anchor)
            report = json.loads((Path(second["destination"]) / "current-cut.json").read_text("utf-8"))
            carried = report["carried_decisions"]
            self.assertEqual([decision_id], [row["decision_id"] for row in carried])
            self.assertEqual("STALE", carried[0]["status"])
            self.assertEqual(verify_register(register)["decisions"][0]["source_hash"],
                             carried[0]["source_hash"])
            request = json.loads((Path(second["destination"]) / "tasks" /
                                  "growth_analyst.request.json").read_text("utf-8"))
            self.assertEqual(carried, request["evidence"]["carried_decisions"])
            self.assertEqual("STALE", verify_register(register)["decisions"][0]["status"])
            self.assertEqual("WAITING_ANALYSTS", verify_cycle(second["destination"])["status"])

    def test_extension_before_cutoff_preserves_open_and_records_old_new_due_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            register, decision_id, _ = self._registered(home, "2026-09-25")
            extended = extend_decision(register, decision_id, "2026-10-05", "growth_owner",
                                       "OWNER_EXTENDED")
            cut, marts = later_upstream(home)
            second = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                 prior_register=register, prior_anchor=extended["anchor"])
            state = verify_register(register)
            self.assertEqual("OPEN", state["decisions"][0]["status"])
            self.assertEqual("2026-10-05", state["decisions"][0]["due_date"])
            extension = next(event for event in state["events"] if event["event_type"] == "EXTEND")
            self.assertEqual({"old_due_date": "2026-09-25", "new_due_date": "2026-10-05"},
                             extension["closure_evidence"]["extension"])
            self.assertEqual("OPEN", json.loads((Path(second["destination"]) /
                "current-cut.json").read_text("utf-8"))["carried_decisions"][0]["status"])

    def test_exact_later_cut_pointer_closes_and_forgery_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            register, decision_id, anchor = self._registered(home)
            cut, marts = later_upstream(home)
            second = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                 prior_register=register, prior_anchor=anchor)
            cycle = Path(second["destination"])
            current = json.loads((cycle / "current-cut.json").read_text("utf-8"))
            evidence = {"cut_id": current["cut_id"],
                "current_cut_sha256": second["current_cut_sha256"],
                "pointer": "/metric_rows/0/value",
                "observed_value": current["metric_rows"][0]["value"]}
            forged = dict(evidence, current_cut_sha256="0" * 64)
            with self.assertRaises(ValueError):
                close_decision(register, decision_id, cycle, forged)
            closed = close_decision(register, decision_id, cycle, evidence)
            self.assertEqual("CLOSED", closed["status"])
            self.assertEqual("CLOSED", verify_register(register)["decisions"][0]["status"])

    def test_human_judgment_requires_explicit_local_owner_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            check = {"kind": "human_judgment", "criterion": "Owner accepts the result.",
                     "requires_later_cut": True}
            register, decision_id, anchor = self._registered(home, check=check)
            cut, marts = later_upstream(home)
            second = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                 prior_register=register, prior_anchor=anchor)
            cycle = Path(second["destination"])
            current = json.loads((cycle / "current-cut.json").read_text("utf-8"))
            evidence = {"cut_id": current["cut_id"],
                "current_cut_sha256": second["current_cut_sha256"], "pointer": None,
                "observed_value": None}
            reviewed = close_decision(register, decision_id, cycle, evidence)
            self.assertEqual("REVIEW", reviewed["status"])
            closed = close_decision(register, decision_id, cycle, evidence,
                {"owner_role": "growth_owner", "attested": True,
                 "criterion": "Owner accepts the result.",
                 "scope": "local-owner-attestation"})
            self.assertEqual("CLOSED", closed["status"])
