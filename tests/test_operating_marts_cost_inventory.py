"""Hand oracles for the Phase 2 cost and inventory marts."""
from __future__ import annotations

import json
import shutil
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

    def test_realized_economics_needs_complete_coverage(self) -> None:
        from alma.operating_cost_inventory import realized_economics
        from alma.operating_mart_contracts import bind_cut, load_policy

        policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json", as_of="2026-09-15", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            partial = build_operating_workspace(SYNTHETIC_PACK, private_root=Path(tmp) / "partial")
            with bind_cut(partial["destination"]) as cut:
                row = realized_economics(cut, "synthetic:sku-001", "synthetic:direct", "2026-09-15", "2026-09-16", policy)
                self.assertEqual("PARTIAL", row["status"])
                self.assertEqual(1200000, row["net_revenue_cents"])
                self.assertIsNone(row["cogs_cents"])
            pack = Path(tmp) / "pack"
            shutil.copytree(SYNTHETIC_PACK, pack)
            metadata_path = pack / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for source in ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            sales_path = pack / "sales_aggregates.csv"
            sales_path.write_text(sales_path.read_text(encoding="utf-8").replace(",PARTIAL,", ",COMPLETE,"), encoding="utf-8")
            complete = build_operating_workspace(pack, private_root=Path(tmp) / "complete")
            with bind_cut(complete["destination"]) as cut:
                row = realized_economics(cut, "synthetic:sku-001", "synthetic:direct", "2026-09-15", "2026-09-16", policy)
                self.assertEqual("MEASURED", row["status"])
                self.assertEqual(480000, row["cogs_cents"])
                self.assertEqual(240000, row["contribution_cents"])
                self.assertEqual("0.2", row["ratios"]["contribution_margin"])


class InventoryMartTests(unittest.TestCase):
    def test_purchase_receipt_conservation_and_replay(self) -> None:
        from alma.operating_cost_inventory import reconcile_purchase

        order = {"purchase_order_id": "po", "ordered_units": 20, "status_code": "PARTIAL"}
        receipt = {"receipt_id": "r1", "received_units": 18, "inspection_units": 2,
                   "accepted_units": 16, "rejected_units": 0}
        result = reconcile_purchase(order, [receipt])
        self.assertEqual(2, result["still_to_receive_units"])
        self.assertEqual(16, result["accepted_units"])
        with self.assertRaises(ValueError):
            reconcile_purchase(order, [receipt, receipt])
        with self.assertRaises(ValueError):
            reconcile_purchase(order, [dict(receipt, accepted_units=17)])

    def test_synthetic_custody_uses_one_receipt_and_only_physical_restock(self) -> None:
        from alma.operating_cost_inventory import project_inventory
        from alma.operating_mart_contracts import bind_cut

        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(SYNTHETIC_PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                stock = project_inventory(cut, "synthetic:sku-001", "2026-09-21")
                self.assertEqual(24, stock["on_hand_units"])
                self.assertEqual(2, stock["inspection_units"])
                self.assertEqual(1, stock["loaned_units"])
                self.assertEqual(2, stock["reserved_units"])
                self.assertEqual(1, stock["non_sellable_units"])
                self.assertEqual(21, stock["available_units"])
                self.assertEqual("PARTIAL", stock["status"])


if __name__ == "__main__":
    unittest.main()
