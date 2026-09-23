"""Hand oracles for the Phase 2 cost and inventory marts."""
from __future__ import annotations

import json
import hashlib
import shutil
import csv
import tempfile
import unittest
from pathlib import Path

from alma.operating_contracts import SOURCE_NAMES
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"


class MartContractTests(unittest.TestCase):
    def test_source_registry_and_verified_two_cut_binding(self) -> None:
        from alma.operating_mart_contracts import bind_cut, SOURCE_BINDINGS, REQUIRED_SEMANTIC_FIELDS

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
        self.assertEqual(set(expected), set(REQUIRED_SEMANTIC_FIELDS))
        for source, fields in REQUIRED_SEMANTIC_FIELDS.items():
            self.assertTrue(set(fields) <= set(SOURCE_BINDINGS[source]["fields"]))
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
                    with self.assertRaises(ValueError):
                        cut.coverage_status("sales_aggregates", "2026-09-22")
            destination = Path(first["destination"])
            manifest = destination / "workspace.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["sqlite_sha256"] = "0" * 64
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                bind_cut(destination)
            source = Path(second["destination"]) / "cost_components.csv"
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                bind_cut(second["destination"])

    def test_metric_status_and_policy_authority(self) -> None:
        from alma.operating_mart_contracts import MetricDefinition, MetricRow, load_policy

        definition = MetricDefinition("known_cost", "v1", "sum(component_cents)", "MXN_CENTS", "sku", "as_of", ("cost_components",), "UNKNOWN", "cost_complete", "finance", "price_review")
        self.assertEqual("known_cost", definition.id)
        with self.assertRaises(ValueError):
            MetricRow("known_cost", "cut", "2026-09-21", {}, None, None, 0, "BOGUS", (), (), "r1")
        with self.assertRaises(ValueError):
            MetricRow("known_cost", "cut", "2026-09-21", {}, None, None, 0, "UNKNOWN", (), (), "r1")
        self.assertEqual(0, MetricRow("known_cost", "cut", "2026-09-21", {}, 0, 1, 0, "MEASURED", (), (), "r1").value)
        policy_path = ROOT / "policies" / "operating-metrics-synthetic-v1.json"
        policy = load_policy(policy_path, as_of="2026-09-21", real_cut=False)
        self.assertEqual("SYNTHETIC_EXAMPLE", policy.status)
        self.assertFalse(policy.authorizes_real_cut)
        self.assertEqual(64, len(policy.sha256))
        self.assertEqual("active_leaf_precedence", policy.content["bases"]["cash_projection_selection"])
        self.assertEqual("daily_minimum_cents", policy.content["bases"]["cash_floor_basis"])
        self.assertEqual(
            "approved_minus_open_commitment_minus_allocated_incurred",
            policy.content["bases"]["budget_headroom_basis"],
        )
        self.assertEqual(0, policy.content["thresholds"]["minimum_cash_floor_cents"])
        self.assertEqual("FINANCE_OWNER", policy.content["bases"]["exception_owner_roles"]["COST_INCOMPLETE"])
        self.assertEqual("INSPECT_RECEIPT", policy.content["bases"]["exception_next_actions"]["RECEIPT_UNINSPECTED"])
        self.assertEqual(2, policy.content["thresholds"]["receipt_inspection_due_days"])
        with self.assertRaises(ValueError):
            load_policy(policy_path, as_of="2030-01-01", real_cut=False)
        with self.assertRaises(ValueError):
            load_policy(ROOT / "policies" / "absent.json", as_of="2026-09-21", real_cut=True)
        with tempfile.TemporaryDirectory() as tmp:
            policy_copy = Path(tmp) / "policy.json"
            content = json.loads(policy_path.read_text(encoding="utf-8"))
            for status in ("REVIEW", "APPROVED"):
                content["status"] = status
                content["owner_approval_ref"] = "synthetic:approval-001" if status == "APPROVED" else None
                content["sha256"] = hashlib.sha256(json.dumps(
                    {key: value for key, value in content.items() if key != "sha256"},
                    sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")).hexdigest()
                policy_copy.write_text(json.dumps(content), encoding="utf-8")
                loaded = load_policy(policy_copy, as_of="2026-09-21", real_cut=True)
                self.assertEqual(status == "APPROVED", loaded.authorizes_real_cut)


class CostMartTests(unittest.TestCase):
    def test_cogs_partition_invariance(self) -> None:
        from alma.operating_cost_inventory import realized_economics
        from alma.operating_mart_contracts import bind_cut, load_policy

        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            shutil.copytree(SYNTHETIC_PACK, pack)
            metadata_file = pack / "metadata.json"
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            for source in ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            sales_file = pack / "sales_aggregates.csv"
            with sales_file.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                template = next(reader)
            rows = []
            for day, channel, ref, cohort in (("2026-09-15", "synthetic:direct", "a", "001"),
                                              ("2026-09-16", "synthetic:direct", "b", "002"),
                                              ("2026-09-17", "synthetic:wholesale", "c", "003")):
                rows.append(dict(template, sales_date=day, channel_code=channel,
                                 delivery_cohort_id=f"synthetic:cohort-{cohort}",
                                 delivered_units="1", returned_units="1" if ref == "a" else "0",
                                 restocked_units="1" if ref == "a" else "0",
                                 net_revenue_cents="100", variable_cost_cents="0",
                                 coverage_status="COMPLETE", source_ref=f"synthetic:source:sales-{ref}"))
            with sales_file.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
                writer.writeheader(); writer.writerows(rows)
            movements_file = pack / "inventory_movements.csv"
            with movements_file.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                move_fields = reader.fieldnames
                movements = list(reader)
            sale_movement = next(row for row in movements if row["movement_type"] == "SALE_OUT")
            sale_movement["units"] = "1"
            for day, channel, ref in (("2026-09-16", "synthetic:direct", "b"),
                                      ("2026-09-17", "synthetic:wholesale", "c")):
                movements.append(dict(sale_movement, movement_id=f"synthetic:movement-sale-{ref}",
                    event_date=day, sales_date=day, sales_channel_code=channel,
                    source_ref=f"synthetic:source:movement-sale-{ref}"))
            with movements_file.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=move_fields, lineterminator="\n")
                writer.writeheader(); writer.writerows(movements)
            counts = pack / "inventory_counts.csv"
            counts.write_text(counts.read_text(encoding="utf-8").replace(",24,2,", ",33,2,"), encoding="utf-8")
            version = pack / "cost_versions.csv"
            version.write_text(version.read_text(encoding="utf-8").replace(",ACTIVE,1,", ",ACTIVE,3,"), encoding="utf-8")
            component = pack / "cost_components.csv"
            component.write_text(component.read_text(encoding="utf-8").replace(",40000,", ",101,"), encoding="utf-8")
            allocation = pack / "cost_allocations.csv"
            allocation.write_text(allocation.read_text(encoding="utf-8").replace(",40000,", ",101,"), encoding="utf-8")
            result = build_operating_workspace(pack, private_root=Path(tmp) / "cuts")
            policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json",
                                 as_of="2026-09-21", real_cut=False)
            with bind_cut(result["destination"]) as cut:
                sku = "synthetic:sku-001"
                combined = realized_economics(cut, sku, "synthetic:direct", "2026-09-15", "2026-09-17", policy)
                first = realized_economics(cut, sku, "synthetic:direct", "2026-09-15", "2026-09-16", policy)
                second = realized_economics(cut, sku, "synthetic:direct", "2026-09-16", "2026-09-17", policy)
                third = realized_economics(cut, sku, "synthetic:wholesale", "2026-09-17", "2026-09-18", policy)
                self.assertEqual(68, combined["cogs_cents"])
                self.assertEqual([34, 34, 33], [first["cogs_cents"], second["cogs_cents"], third["cogs_cents"]])
                self.assertEqual(101, combined["cogs_cents"] + third["cogs_cents"])

    def test_estimated_cost_propagates_to_economics(self) -> None:
        from alma.operating_cost_inventory import project_cost, realized_economics
        from alma.operating_mart_contracts import bind_cut, load_policy

        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            shutil.copytree(SYNTHETIC_PACK, pack)
            metadata_file = pack / "metadata.json"
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            for source in ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            sales_file = pack / "sales_aggregates.csv"
            sales_file.write_text(sales_file.read_text(encoding="utf-8").replace(",PARTIAL,", ",COMPLETE,"), encoding="utf-8")
            component = pack / "cost_components.csv"
            component.write_text(component.read_text(encoding="utf-8").replace(",KNOWN,", ",ESTIMATED,"), encoding="utf-8")
            result = build_operating_workspace(pack, private_root=Path(tmp) / "cuts")
            policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json",
                                 as_of="2026-09-21", real_cut=False)
            with bind_cut(result["destination"]) as cut:
                cost = project_cost(cut, "synthetic:sku-001", "2026-09-15", policy)
                economics = realized_economics(cut, "synthetic:sku-001", "synthetic:direct",
                                               "2026-09-15", "2026-09-16", policy)
                self.assertEqual("ESTIMATED", cost["status"])
                self.assertEqual("ESTIMATED", economics["status"])
                self.assertEqual(480000, economics["cogs_cents"])
                self.assertEqual(240000, economics["contribution_cents"])
                self.assertEqual("0.2", economics["ratios"]["contribution_margin"])

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
        from alma.operating_cost_inventory import project_inventory, project_purchases
        from alma.operating_mart_contracts import bind_cut

        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(SYNTHETIC_PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                purchase = project_purchases(cut, "2026-09-21")[0]
                self.assertEqual(20, purchase["ordered_units"])
                self.assertEqual(18, purchase["received_units"])
                self.assertEqual(2, purchase["still_to_receive_units"])
                stock = project_inventory(cut, "synthetic:sku-001", "2026-09-21")
                self.assertEqual(24, stock["on_hand_units"])
                self.assertEqual(2, stock["inspection_units"])
                self.assertEqual(1, stock["loaned_units"])
                self.assertEqual(2, stock["reserved_units"])
                self.assertEqual(1, stock["non_sellable_units"])
                self.assertEqual(21, stock["available_units"])
                self.assertEqual("PARTIAL", stock["status"])
                cut.coverage["inventory_movements"]["status"] = "MISSING"
                blocked = project_inventory(cut, "synthetic:sku-001", "2026-09-21")
                self.assertEqual("UNKNOWN", blocked["status"])
                self.assertIsNone(blocked["available_units"])

    def test_count_variance_blocks_available_units(self) -> None:
        from unittest import mock
        from alma import operating_cost_inventory as mart
        from alma.operating_mart_contracts import bind_cut

        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(SYNTHETIC_PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                original_rows = mart._rows

                def changed_count(bound, statement, parameters):
                    rows = original_rows(bound, statement, parameters)
                    if "FROM inventory_counts" in statement and rows:
                        rows[0]["on_hand_units"] += 1
                    return rows

                with mock.patch.object(mart, "_rows", side_effect=changed_count):
                    stock = mart.project_inventory(cut, "synthetic:sku-001", "2026-09-21")
                self.assertEqual(-1, stock["count_variance_units"])
                self.assertEqual("UNKNOWN", stock["status"])
                self.assertIsNone(stock["available_units"])


if __name__ == "__main__":
    unittest.main()
