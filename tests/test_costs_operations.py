import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_costs_operations.py"
SPEC = importlib.util.spec_from_file_location("build_costs_operations", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


class CostOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
        cls.manifest_path = ROOT / "client" / "costs-operations-manifest.json"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.metrics = module.calculate()

    def test_every_public_source_is_synthetic_unique_and_hashed(self):
        for source in self.manifest["sources"]:
            path = ROOT / "client" / source["source_path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), source["row_count"])
            self.assertTrue(rows)
            self.assertTrue(all(row["synthetic"] == "1" for row in rows))
            key_fields = [part.strip() for part in source["primary_key"].split("+")]
            keys = [tuple(row[field] for field in key_fields) for row in rows]
            self.assertEqual(len(keys), len(set(keys)))

    def test_cost_coverage_keeps_unknowns_unknown(self):
        rows = {row["sku"]: row for row in self.metrics["cost_metrics"]}
        self.assertEqual(rows["PIL-NEGRO"]["known_total_cents"], 1_040_000)
        self.assertEqual(rows["PIL-NEGRO"]["unit_management_cost_cents"], 10_400)
        self.assertEqual(str(rows["PIL-NEGRO"]["contribution_margin"]), "0.5722")
        self.assertEqual(str(rows["PIL-NEGRO"]["markup_on_cost"]), "1.6450")
        self.assertEqual(rows["PIL-LILA"]["known_total_cents"], 220_000)
        self.assertIsNone(rows["PIL-LILA"]["unit_management_cost_cents"])
        self.assertIsNone(rows["PIL-LILA"]["contribution_margin"])
        self.assertIn("COMPRA_PROVEEDOR", rows["PIL-LILA"]["missing_components"])

    def test_allocations_reconcile_without_duplication(self):
        self.assertTrue(all(row["reconciles"] for row in self.metrics["allocation_controls"]))
        for row in self.metrics["allocation_controls"]:
            self.assertEqual(row["allocated_cents"] + row["remainder_cents"], row["source_cents"])

    def test_receipt_bridge_and_available_quantity(self):
        row = next(row for row in self.metrics["purchase_metrics"] if row["purchase_order_id"] == "PO-OPS-001")
        self.assertEqual((row["ordered_qty"], row["received_qty"], row["accepted_qty"], row["inspection_qty"], row["still_to_receive_qty"]), (20, 18, 16, 2, 2))
        self.assertEqual(row["available_from_receipt_qty"], 16)
        self.assertEqual(row["received_qty"], row["accepted_qty"] + row["inspection_qty"] + row["rejected_qty"])

    def test_obligation_balance_does_not_double_count_origin(self):
        row = next(row for row in self.metrics["obligation_metrics"] if row["obligation_id"] == "OBL-001")
        self.assertEqual((row["original_cents"], row["paid_cents"], row["outstanding_cents"]), (180_000, 100_000, 80_000))

    def test_cash_scenario_is_separate_and_non_executing(self):
        scenarios = {row["scenario_id"]: row for row in self.metrics["cash_scenarios"]}
        self.assertEqual(scenarios["BASE"]["closing_cents"] - scenarios["REINVESTIR_TOP"]["closing_cents"], 420_000)
        self.assertEqual(scenarios["BASE"]["level"], "ASSUMED_OPENING_PLUS_EXPECTED_AND_COMMITTED")
        self.assertEqual(scenarios["BASE"]["opening_level"], "ASSUMPTION_UNRECONCILED")
        self.assertEqual(scenarios["BASE"]["opening_source_ref"], "SYN-OPENING-01")
        self.assertEqual(scenarios["REINVESTIR_TOP"]["decision"], "COMPARE_ONLY_NO_EXECUTION")
        self.assertEqual(self.manifest["external_execution"], "PROHIBITED")

    def test_skus_bridge_to_the_client_catalog(self):
        bridge = self.manifest["catalog_bridge"]
        self.assertEqual(bridge["status"], "EXPLICIT_SYNTHETIC_SKU_CONTRACT")
        self.assertEqual(bridge["unresolved_skus"], [])

    def test_metric_contract_is_decision_ready(self):
        required = {"id", "formula", "unit", "grain", "window", "sources", "unknown", "guardrail", "decision"}
        for metric in self.manifest["metric_definitions"]:
            self.assertTrue(required.issubset(metric))
            self.assertTrue(metric["sources"])

    def test_output_contains_no_customer_pii_or_external_actions(self):
        public = [ROOT / "client" / "COSTOS_Y_OPERACION.html", self.manifest_path]
        public.extend(ROOT / "client" / source["source_path"] for source in self.manifest["sources"])
        text = "\n".join(path.read_text(encoding="utf-8-sig", errors="replace") for path in public).lower()
        for forbidden in ("@gmail.com", "@hotmail.com", "telefono", "whatsapp", "access_token", "secret_key"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
