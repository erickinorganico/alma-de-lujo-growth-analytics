"""Contract tests for the v1 static offline portal."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from alma.decision_register import close_decision, create_register, register_decision, verify_register
from alma.operating_contracts import canonical_json
from alma.weekly_cycle import read_terminal_packet, start_cycle
from scripts.build_offline_portal_v1 import PortalContractError, collect_portal_model
from tests.test_decision_register import closure_check, later_upstream, terminal_cycle
from tests.test_weekly_cycle import upstream


ROOT = Path(__file__).resolve().parents[1]


class PortalEvidenceTests(unittest.TestCase):
    def test_public_and_unselected_views_do_not_accept_private_evidence(self) -> None:
        public = collect_portal_model(mode="public")
        self.assertEqual("EJEMPLO SINTÉTICO · HISTÓRICO v0.2", public["provenance"]["label"])
        self.assertEqual("historical_synthetic", public["provenance"]["role"])
        self.assertTrue(public["provenance"]["synthetic"])
        self.assertNotIn("private", canonical_json(public).decode("utf-8").lower())

        unselected = collect_portal_model(mode="private")
        self.assertEqual("SIN CORTE PRIVADO SELECCIONADO", unselected["provenance"]["label"])
        self.assertEqual([], unselected["metrics"])
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / ".local" / "weekly-cycles" / "candidate"
            private.mkdir(parents=True)
            with self.assertRaises(PortalContractError):
                collect_portal_model(mode="public", selected_cycle=private)

    def test_verified_synthetic_current_cut_preserves_waiting_state_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
            model = collect_portal_model(mode="private", selected_cycle=cycle)
            current = json.loads((cycle / "current-cut.json").read_text("utf-8"))
            self.assertIn("CORTE PRIVADO ACTUAL", model["provenance"]["label"])
            self.assertIn("SINTÉTICO", model["provenance"]["label"])
            self.assertEqual(current["cut_id"], model["cut"]["cut_id"])
            self.assertEqual(current["manifest_sha256"], model["cut"]["manifest_sha256"])
            self.assertEqual(current["mart_bundle_sha256"], model["cut"]["report_sha256"])
            self.assertEqual("ESPERANDO_RESPUESTA", model["native"]["status"])
            self.assertTrue(all(row["status"] == "ESPERANDO_RESPUESTA"
                                for row in model["native"]["roles"]))
            self.assertIsNone(model["packet"])

    def test_changed_current_report_or_path_escape_blocks_the_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
            original = (cycle / "current-cut.json").read_bytes()
            (cycle / "current-cut.json").write_bytes(original + b"\n")
            with self.assertRaisesRegex(PortalContractError, "blocked|verify|hash"):
                collect_portal_model(mode="private", selected_cycle=cycle)
            with self.assertRaises(PortalContractError):
                collect_portal_model(mode="private", selected_cycle=cycle / ".." / cycle.name)

    def test_two_cut_register_keeps_exact_identity_closure_and_stale_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            first_cycle = terminal_cycle(home / "first")
            packet = read_terminal_packet(first_cycle)
            recommendation_ids = [row["item"]["id"] for row in packet["recommendations"][:2]]
            self.assertEqual(2, len(set(recommendation_ids)))
            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            first = register_decision(register, first_cycle, recommendation_ids[0],
                                      "growth_owner", "2026-10-02", "ACCEPT", closure_check())
            second = register_decision(register, first_cycle, recommendation_ids[1],
                                       "growth_owner", "2026-09-22", "ACCEPT", closure_check())
            cut, marts = later_upstream(home)
            later = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                prior_register=register, prior_anchor=second["anchor"])
            later_cycle = Path(later["destination"])
            current = json.loads((later_cycle / "current-cut.json").read_text("utf-8"))
            evidence = {"cut_id": current["cut_id"],
                        "current_cut_sha256": later["current_cut_sha256"],
                        "pointer": "/metric_rows/0/value",
                        "observed_value": current["metric_rows"][0]["value"]}
            close_decision(register, first["decision_id"], later_cycle, evidence)
            expected = verify_register(register)
            model = collect_portal_model(mode="private", selected_cycle=later_cycle,
                                         decision_register=register)
            self.assertEqual(expected["anchor"], model["decision_register"]["current_anchor"])
            actual = {row["decision_id"]: row for row in model["decisions"]}
            self.assertEqual("CLOSED", actual[first["decision_id"]]["status"])
            self.assertEqual("STALE", actual[second["decision_id"]]["status"])
            for row in expected["decisions"]:
                rendered = actual[row["decision_id"]]
                for key in ("decision_id", "recommendation_id", "status", "source_hash",
                            "packet_hash", "due_date"):
                    self.assertEqual(row[key], rendered[key])
            self.assertTrue(actual[first["decision_id"]]["closure_evidence"])


if __name__ == "__main__":
    unittest.main()
