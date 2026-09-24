"""Release invariants over two different synthetic operating cuts.

Native responses constructed here are TEST_FIXTURE validator probes, never live work.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from alma.operating_archive import export_cut, restore_cut, verify_cut
from alma.operating_contracts import canonical_json
from alma.operating_workspace import build_operating_workspace
from alma.operating_marts import build_operating_marts
from alma.weekly_cycle import start_cycle, verify_cycle
from alma.decision_register import create_register, register_decision, verify_register, close_decision
from tests.test_decision_register import closure_check, terminal_cycle
from scripts import verify_v1


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "tests/fixtures/release_v1/two_week_scenario.json"
SOURCE = ROOT / "client/source-packs/v1/synthetic"
POLICY = ROOT / "policies/operating-metrics-synthetic-v1.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _pack(home: Path, week: dict) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    pack = home / week["id"]
    shutil.copytree(SOURCE, pack)
    metadata = _json(pack / "metadata.json")
    metadata["cutoff_at"] = week["cutoff_at"]
    for coverage in metadata["coverage"].values():
        coverage["window_end"] = week["cutoff_at"][:10]
    (pack / "metadata.json").write_bytes(canonical_json(metadata))
    sales = pack / "sales_aggregates.csv"
    with sales.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update({key: str(value) for key, value in week["sales"].items()})
    with sales.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    movements = pack / "inventory_movements.csv"
    with movements.open(newline="", encoding="utf-8") as stream:
        movement_rows = list(csv.DictReader(stream))
    for row in movement_rows:
        if row["movement_type"] == "SALE_OUT":
            row["units"] = str(week["sales"]["delivered_units"])
    with movements.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(movement_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(movement_rows)
    return pack


def _upstream(home: Path, pack: Path) -> tuple[Path, Path]:
    cut = build_operating_workspace(pack, private_root=home / "operating")
    mart_root = home / ".local/operating-marts"
    mart = build_operating_marts(cut["destination"], mart_root,
                                 policy_path=POLICY, private_root=mart_root)
    return Path(cut["destination"]), Path(mart["destination"])


class TwoWeekReleaseAcceptance(unittest.TestCase):
    def test_two_materially_different_weeks_replay_and_restore(self) -> None:
        scenario = _json(SCENARIO)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            identities = []
            for week in scenario["weeks"]:
                pack = _pack(home / "inputs", week)
                cut, mart = _upstream(home / week["id"], pack)
                state = start_cycle(cut, mart, home / week["id"] / ".local/weekly-cycles")
                manifest = _json(cut / "workspace.json")
                report = _json(Path(state["destination"]) / "current-cut.json")
                self.assertEqual("WAITING_ANALYSTS", verify_cycle(state["destination"])["status"])
                self.assertEqual(week["cutoff_at"], manifest["cutoff_at"])
                self.assertEqual(week["cutoff_at"], report["cutoff_at"])
                self.assertEqual(hashlib.sha256((pack / "sales_aggregates.csv").read_bytes()).hexdigest(),
                                 manifest["source_sha256"]["sales_aggregates.csv"])
                with (pack / "sales_aggregates.csv").open(newline="", encoding="utf-8") as stream:
                    source_rows = list(csv.DictReader(stream))
                # Independent Decimal/integer oracle; no float arithmetic.
                self.assertEqual(int(Decimal(source_rows[0]["delivered_units"])),
                                 week["expected"]["delivered_units"])
                self.assertEqual(int(Decimal(source_rows[0]["net_revenue_cents"])),
                                 week["expected"]["net_revenue_cents"])
                self.assertEqual(int(Decimal(source_rows[0]["net_revenue_cents"]) -
                                     Decimal(source_rows[0]["variable_cost_cents"])),
                                 week["expected"]["revenue_after_variable_cents"])
                self.assertTrue(report["metric_rows"])
                self.assertTrue(_json(mart / "manifest.json"))
                receipt = export_cut(cut, home / week["id"] / "operating" /
                                     "operating-exports" / "cut.zip", private_root=home / week["id"] / "operating")
                restored = restore_cut(home / week["id"] / "operating" /
                                       "operating-exports" / "cut.zip",
                                       home / week["id"] / "operating" / "operating-cuts" /
                                       (manifest["cut_id"] + "-restored"),
                                       private_root=home / week["id"] / "operating")
                self.assertEqual("PASS", verify_cut(restored["destination"],
                                 private_root=home / week["id"] / "operating")["status"])
                self.assertEqual(manifest["relationship_check"],
                                 _json(Path(restored["destination"]) / "workspace.json")["relationship_check"])
                replay_cut = build_operating_workspace(pack, private_root=home / "replay" /
                                                       week["id"] / "operating")
                self.assertEqual(manifest["cut_id"], replay_cut["manifest"]["cut_id"])
                self.assertEqual(manifest["relationship_check"],
                                 replay_cut["manifest"]["relationship_check"])
                self.assertEqual("PASS", receipt["status"])
                identities.append((manifest["cut_id"], manifest["source_sha256"],
                                   state["current_cut_sha256"], state["task_bundle_sha256"]))
            self.assertNotEqual(identities[0], identities[1])
            self.assertNotEqual(identities[0][0], identities[1][0])
            self.assertNotEqual(identities[0][1], identities[1][1])

    def test_tamper_duplicate_and_partial_coverage_fail_closed(self) -> None:
        scenario = _json(SCENARIO)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = _pack(home / "inputs", scenario["weeks"][0])
            cut, mart = _upstream(home / "valid", pack)
            state = start_cycle(cut, mart, home / "valid/.local/weekly-cycles")
            source = cut / "sales_aggregates.csv"
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                verify_cycle(state["destination"])
            duplicate = _pack(home / "inputs", scenario["weeks"][0] | {"id": "duplicate"})
            sales = duplicate / "sales_aggregates.csv"
            with sales.open("rb") as stream:
                lines = stream.readlines()
            sales.write_bytes(b"".join(lines + lines[1:]))
            with self.assertRaises(ValueError):
                build_operating_workspace(duplicate, private_root=home / "duplicate-operating")
            missing = _pack(home / "inputs", scenario["weeks"][0] | {"id": "missing"})
            metadata = _json(missing / "metadata.json")
            metadata["coverage"]["availability_daily"] = {"status": "MISSING",
                "window_start": None, "window_end": None}
            (missing / "metadata.json").write_bytes(canonical_json(metadata))
            (missing / "availability_daily.csv").write_bytes(
                (missing / "availability_daily.csv").read_bytes().split(b"\n", 1)[0] + b"\n")
            partial_cut, partial_mart = _upstream(home / "missing", missing)
            partial = start_cycle(partial_cut, partial_mart, home / "missing/.local/weekly-cycles")
            report = _json(Path(partial["destination"]) / "current-cut.json")
            self.assertEqual("MISSING", report["coverage"]["availability_daily"]["status"])
            self.assertNotEqual("READY_FOR_OWNER", partial["status"])

    def test_reviewed_fixture_decision_carries_original_anchor_and_closes(self) -> None:
        scenario = _json(SCENARIO)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            fixture_cycle = terminal_cycle(home / "fixture")  # TEST_FIXTURE, not live proof.
            packet = _json(fixture_cycle / "decision-packet.json")
            register = create_register(home / ".local/decision-register/closure", "closure", ["growth_owner"])
            recommendation = packet["recommendations"][0]["item"]["id"]
            created = register_decision(register, fixture_cycle, recommendation, "growth_owner",
                                        scenario["closure_due_date"], "ACCEPT", closure_check())
            original = verify_register(register)["decisions"][0]
            week_two = _pack(home / "inputs", scenario["weeks"][1])
            cut, mart = _upstream(home / "week_two", week_two)
            later = start_cycle(cut, mart, home / "week_two/.local/weekly-cycles",
                                prior_register=register, prior_anchor=created["anchor"])
            report = _json(Path(later["destination"]) / "current-cut.json")
            self.assertEqual(created["decision_id"], report["carried_decisions"][0]["decision_id"])
            self.assertEqual(original["source_hash"], report["carried_decisions"][0]["source_hash"])
            self.assertEqual("STALE", report["carried_decisions"][0]["status"])
            evidence = {"cut_id": later["cut_id"], "current_cut_sha256": later["current_cut_sha256"],
                        "pointer": "/metric_rows/0/value",
                        "observed_value": report["metric_rows"][0]["value"]}
            with self.assertRaises(ValueError):
                close_decision(register, created["decision_id"], later["destination"],
                               evidence | {"current_cut_sha256": "0" * 64})
            closed = close_decision(register, created["decision_id"], later["destination"], evidence)
            self.assertEqual("CLOSED", closed["status"])
            self.assertEqual(original["source_hash"], verify_register(register)["decisions"][0]["source_hash"])


class ReleaseRunnerContractTests(unittest.TestCase):
    def test_aggregate_v1_route_has_fourteen_distinct_native_tasks(self) -> None:
        contract = verify_v1._routing()
        self.assertEqual(6, contract["analysts_per_cut"])
        self.assertEqual(1, contract["independent_reviews_per_cut"])
        self.assertEqual(14, contract["required_native_tasks"])

    def test_preparation_never_claims_native_execution(self) -> None:
        (ROOT / ".local").mkdir(exist_ok=True)
        tmp = Path(tempfile.mkdtemp(dir=ROOT / ".local", prefix="r-"))
        try:
            output = tmp / "v1-acceptance"
            result = verify_v1.prepare_live(output)
            index = _json(output / "run-index.json")
            self.assertEqual("WAITING_NATIVE_TASKS", result["status"])
            self.assertEqual("NOT_YET_RUN", index["native_execution"])
            self.assertEqual(14, index["required_native_tasks"])
            self.assertEqual(2, len(index["weeks"]))
            for week in index["weeks"]:
                state = verify_cycle(verify_v1._extended(output / week["cycle"]))
                self.assertEqual("WAITING_ANALYSTS", state["status"])
                self.assertEqual(6, len(state["expected_roles"]))
            with self.assertRaises(ValueError):
                verify_v1.finalize_live(output, ROOT / ".local/v1-acceptance/no-summary.json")
        finally:
            shutil.rmtree(verify_v1._extended(tmp), ignore_errors=True)

    def test_schema_valid_fixture_is_rejected_as_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cycle = terminal_cycle(Path(tmp))
            state = verify_cycle(cycle)
            with self.assertRaises(ValueError):
                verify_v1._native_entry(cycle, "merchandiser", state)

    def test_failed_deterministic_gate_blocks_overall_receipt(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            output = ROOT / ".local/v1-acceptance/test-failed-gate.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(canonical_json({"status": "PASS", "stale": True}))
            with mock.patch.object(verify_v1, "_gate", return_value={"status": "FAIL", "gate": "probe"}):
                result = verify_v1.deterministic(output)
            self.assertEqual("FAIL", result["status"])
            self.assertRegex(result["candidate_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual("NOT_RUN_BY_DETERMINISTIC_VERIFIER", result["native_execution"])
            self.assertEqual("UNKNOWN", result["external_gates"]["EXT-01"])
            self.assertEqual("REVIEW", result["external_gates"]["EXT-03"])
            self.assertEqual("FAIL", _json(output)["status"])
            self.assertNotIn("stale", _json(output))
            output.unlink()

    def test_gate_receipt_preserves_the_actual_argument_vector(self) -> None:
        import sys

        command = [sys.executable, "-c", "print('ok')"]
        gate = verify_v1._gate("argv-probe", command, timeout=10)
        self.assertEqual("PASS", gate["status"])
        self.assertEqual([".venv/Scripts/python.exe", "-c", "print('ok')"], gate["command"])
