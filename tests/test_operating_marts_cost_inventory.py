"""Hand oracles for the Phase 2 cost and inventory marts."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alma.operating_contracts import SOURCE_NAMES
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"


class MartContractTests(unittest.TestCase):
    def test_source_registry_and_verified_two_cut_binding(self) -> None:
        from alma.operating_mart_contracts import bind_cut, SOURCE_BINDINGS

        expected = (
            "sku_catalog", "sales_aggregates", "availability_daily", "unmet_demand",
            "inventory_counts", "inventory_movements", "inventory_reservations",
            "cost_versions", "cost_components", "cost_allocations", "purchase_orders",
            "purchase_receipts", "obligations", "obligation_payments", "cash_events",
            "cash_balance_evidence", "budgets", "budget_allocations", "expenses",
            "quality_events", "sales_readiness", "loans",
        )
        self.assertEqual(expected, SOURCE_NAMES)
        self.assertEqual(set(expected), set(SOURCE_BINDINGS))
        with tempfile.TemporaryDirectory() as tmp:
            first = build_operating_workspace(SYNTHETIC_PACK, private_root=Path(tmp) / "one")
            second = build_operating_workspace(SYNTHETIC_PACK, private_root=Path(tmp) / "two")
            for result in (first, second):
                with bind_cut(result["destination"]) as cut:
                    self.assertEqual(result["cut_id"], cut.cut_id)
                    self.assertEqual("America/Tijuana", cut.timezone)
                    self.assertEqual(22, len(cut.source_hashes))
                    self.assertEqual("PARTIAL", cut.coverage["availability_daily"]["status"])
                    self.assertEqual("query_only", cut.connection.execute("PRAGMA query_only").fetchone()[0] and "query_only")
            destination = Path(first["destination"])
            manifest = destination / "workspace.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["sqlite_sha256"] = "0" * 64
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                bind_cut(destination)

    def test_metric_status_and_policy_authority(self) -> None:
        from alma.operating_mart_contracts import MetricDefinition, MetricRow, load_policy

        definition = MetricDefinition("known_cost", "v1", "sum(component_cents)", "MXN_CENTS", "sku", "as_of", ("cost_components",), "UNKNOWN", "cost_complete", "finance", "price_review")
        self.assertEqual("known_cost", definition.id)
        with self.assertRaises(ValueError):
            MetricRow("known_cost", "cut", "2026-09-21", {}, None, None, 0, "BOGUS", (), (), "r1")
        policy_path = ROOT / "policies" / "operating-metrics-synthetic-v1.json"
        policy = load_policy(policy_path, as_of="2026-09-21", real_cut=False)
        self.assertEqual("SYNTHETIC_EXAMPLE", policy.status)
        self.assertFalse(policy.authorizes_real_cut)
        self.assertEqual(64, len(policy.sha256))
        with self.assertRaises(ValueError):
            load_policy(policy_path, as_of="2030-01-01", real_cut=False)
        with self.assertRaises(ValueError):
            load_policy(ROOT / "policies" / "absent.json", as_of="2026-09-21", real_cut=True)


class CostMartTests(unittest.TestCase):
    def test_indivisible_cents_and_missing_component(self) -> None:
        from alma.operating_cost_inventory import allocate_unit_cents, evaluate_cost_version
        from alma.operating_mart_contracts import load_policy

        self.assertEqual((34, 34, 33), allocate_unit_cents(101, 3))
        policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json", as_of="2026-09-21", real_cut=False)
        version = {"cost_version_id": "v1", "sku_id": "s1", "quantity_basis": 3, "public_price_cents": 200}
        component = {"component_id": "c1", "classification": "DIRECT", "amount_cents": 101,
                     "quality_status": "KNOWN", "required_flag": 1, "included_in_component_id": None,
                     "source_ref": "source:c1"}
        allocation = {"allocation_id": "a1", "component_id": "c1", "sku_id": "s1",
                      "allocated_cents": 101, "remainder_cents": 0, "source_ref": "source:a1"}
        result = evaluate_cost_version(version, [component], [allocation], policy)
        self.assertEqual(101, result["known_sum_cents"])
        self.assertEqual((34, 34, 33), result["unit_cost_cents"])
        self.assertEqual(0, result["unallocated_cents"])
        self.assertEqual("COMPLETE_DOCUMENTED", result["quality"])
        missing = dict(component, component_id="c2", amount_cents=None, quality_status="MISSING")
        incomplete = evaluate_cost_version(version, [component, missing], [allocation], policy)
        self.assertEqual(101, incomplete["known_sum_cents"])
        self.assertIsNone(incomplete["complete_cost_cents"])
        self.assertEqual("PARTIAL", incomplete["status"])
        estimated = evaluate_cost_version(version, [dict(component, quality_status="ESTIMATED")], [allocation], policy)
        self.assertEqual("COMPLETE_ESTIMATED", estimated["quality"])

    def test_effective_version_and_ratios(self) -> None:
        from alma.operating_cost_inventory import select_cost_version, economics_ratios

        versions = [
            {"cost_version_id": "old", "effective_date": "2026-09-01", "lifecycle_status": "ACTIVE"},
            {"cost_version_id": "new", "effective_date": "2026-09-20", "lifecycle_status": "ACTIVE"},
        ]
        self.assertEqual("old", select_cost_version(versions, "2026-09-15")["cost_version_id"])
        self.assertEqual("new", select_cost_version(versions, "2026-09-21")["cost_version_id"])
        ratios = economics_ratios(1200, 400, 200)
        self.assertEqual("2", ratios["markup"])
        self.assertEqual("0.6666666667", ratios["gross_margin"])
        self.assertEqual("0.5", ratios["contribution_margin"])
        self.assertIsNone(economics_ratios(0, 0, 0)["gross_margin"])
        self.assertIsNone(economics_ratios(100, 0, 0)["markup"])


if __name__ == "__main__":
    unittest.main()
