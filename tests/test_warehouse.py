"""Warehouse v2 integration tests using the still-compatible v1 fixture core."""
from __future__ import annotations

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from alma.fixtures import generate
from alma.simulation import generate as generate_v2
from alma.warehouse import MARTS, TABLE_COLUMNS, build_warehouse, export_marts, ingest_batch, inspect_schema, query_mart


def v2_fixture() -> dict:
    """Adapt the compact v1 fixture without changing its canonical projection."""
    data = copy.deepcopy(generate(seed=42))
    data["metadata"].update(contract_version="2.0", start_date="2026-06-01")
    campaign_ids = sorted({r["campaign_id"] for r in data["tables"]["orders"] + data["tables"]["funnel"]})
    tables = data["tables"]
    # v2 adds an explicit acquisition-before-event temporal invariant.
    for customer in tables["customers"]:
        customer["acquired_date"] = "2026-06-01"
    tables.update({
        "campaigns": [{"id": cid, "name": f"Synthetic {cid}", "channel": "synthetic", "objective": "test", "start_date": "2026-06-01", "end_date": "2026-09-21"} for cid in campaign_ids],
        "content_assets": [], "sessions": [], "leads": [],
        "purchase_receipts": [{"id": f"receipt-{po['id']}", "purchase_order_id": po["id"], "date": po["date"], "quantity": po["received_qty"]} for po in tables["purchase_orders"] if po["received_qty"]],
        "supplier_payments": [{"id": f"supplier-payment-{po['id']}", "purchase_order_id": po["id"], "date": po["date"], "amount_cents": po["paid_cents"]} for po in tables["purchase_orders"] if po["paid_cents"]],
        "shipments": [], "invoices": [],
        "expense_payments": [{"id": f"expense-payment-{expense['id']}", "expense_id": expense["id"], "date": expense["date"], "amount_cents": expense["paid_cents"]} for expense in tables["expenses"] if expense["paid_cents"]],
        "inventory_counts": [],
        "experiments": [], "experiment_assignments": [], "experiment_outcomes": [], "lifecycle_events": [],
    })
    data["metadata"]["coverage"] = {name: bool(tables[name]) for name in TABLE_COLUMNS}
    return data


class WarehouseTests(unittest.TestCase):
    def test_build_has_strict_relations_marts_and_independent_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alma.sqlite3"
            receipt = build_warehouse(v2_fixture(), path)
            self.assertEqual(30, receipt["table_count"])
            self.assertEqual(set(MARTS), set(receipt["marts"]))
            self.assertTrue(all(row["passed"] == 1 for row in receipt["control_results"]))
            schema = inspect_schema(path)
            self.assertEqual("2.0", schema["contract_version"])
            self.assertTrue(schema["tables"]["order_items"]["foreign_keys"])
            self.assertEqual("variant at snapshot", schema["catalog"]["inventory_position"]["grain"])
            self.assertEqual(set(["schema.sql", *(f"marts/{name}.sql" for name in MARTS)]), set(schema["manifest"]["model_hashes"]))
            self.assertTrue(query_mart(path, "sales_daily"))
            self.assertTrue(all(row["passed"] == 1 for row in query_mart(path, "reconciliation")))
            db = sqlite3.connect(path)
            try:
                strict = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '% STRICT'")}
            finally:
                db.close()
            self.assertTrue(set(TABLE_COLUMNS) <= strict)

    def test_exact_snapshot_is_idempotent_and_invalid_batch_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alma.sqlite3"
            data = v2_fixture()
            build_warehouse(data, path)
            again = ingest_batch(path, data)
            self.assertTrue(again["idempotent"])
            invalid = copy.deepcopy(data)
            invalid["tables"]["orders"][0]["campaign_id"] = "missing-campaign"
            with self.assertRaises(ValueError):
                ingest_batch(path, invalid)
            db = sqlite3.connect(path)
            try:
                self.assertEqual(1, db.execute("SELECT COUNT(*) FROM rejected_batches").fetchone()[0])
                self.assertEqual(len(data["tables"]["orders"]), db.execute("SELECT COUNT(*) FROM orders").fetchone()[0])
            finally:
                db.close()

    def test_fixed_mart_boundary_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "alma.sqlite3"
            build_warehouse(v2_fixture(), db)
            with self.assertRaises(ValueError):
                query_mart(db, "sales_daily; DROP TABLE orders")
            exported = export_marts(db, root / "marts")
            self.assertEqual(set(MARTS), set(exported["marts"]))
            self.assertTrue(all(Path(value).is_file() for value in exported["marts"].values()))

    def test_cogs_recognizes_on_delivery_and_restock_reverses_on_return_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = v2_fixture()
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            rows = {row["date"]: row for row in query_mart(path, "sales_daily")}
            orders = {row["id"]: row for row in data["tables"]["orders"]}
            item = next(row for row in data["tables"]["order_items"] if row["order_id"] == "ord-002")
            delivery = orders[item["order_id"]]["delivered_date"]
            sale_movement = next(row for row in data["tables"]["movements"] if row["kind"] == "sale" and row["reference_id"] == item["id"])
            self.assertNotEqual(delivery, sale_movement["date"])
            self.assertGreaterEqual(rows[delivery]["cogs_cents"], item["quantity"] * item["unit_cost_cents"])
            restock = next(row for row in data["tables"]["returns"] if row["restock"] == 1)
            returned_item = next(row for row in data["tables"]["order_items"] if row["id"] == restock["order_item_id"])
            self.assertLessEqual(rows[restock["date"]]["cogs_cents"], -restock["quantity"] * returned_item["unit_cost_cents"])

    def test_inventory_count_uses_ledger_through_count_date_and_deterministic_tie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = v2_fixture()
            variant = data["tables"]["variants"][0]["id"]
            data["tables"]["inventory_counts"] = [
                {"id": "count-a", "variant_id": variant, "date": "2026-09-10", "counted_qty": 1},
                {"id": "count-z", "variant_id": variant, "date": "2026-09-10", "counted_qty": 99},
            ]
            data["metadata"]["coverage"]["inventory_counts"] = True
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            row = next(value for value in query_mart(path, "inventory_position") if value["variant_id"] == variant)
            expected_ledger = sum(m["quantity"] for m in data["tables"]["movements"] if m["variant_id"] == variant and m["date"] <= "2026-09-10")
            self.assertEqual(99, row["counted_qty"])
            self.assertEqual(99 - expected_ledger, row["count_discrepancy_qty"])

    def test_missing_cost_propagates_to_monthly_profit_instead_of_partial_sum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = v2_fixture()
            data["tables"]["variants"][0]["cost_cents"] = None
            for item in data["tables"]["order_items"]:
                if item["variant_id"] == data["tables"]["variants"][0]["id"]:
                    item["unit_cost_cents"] = None
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            self.assertTrue(any(row["cogs_cents"] is None and row["gross_profit_cents"] is None for row in query_mart(path, "finance_monthly")))

    def test_cohort_and_count_outputs_remain_unknown_when_coverage_is_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = v2_fixture()
            variant = data["tables"]["variants"][0]["id"]
            data["tables"]["inventory_counts"] = [{"id": "uncovered-count", "variant_id": variant, "date": "2026-09-20", "counted_qty": 4}]
            data["metadata"]["coverage"]["inventory_counts"] = False
            data["metadata"]["coverage"]["customers"] = False
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            cohort = query_mart(path, "customer_cohorts")[0]
            self.assertEqual(0, cohort["cohort_coverage_known"])
            self.assertIsNone(cohort["cohort_customers"])
            position = next(row for row in query_mart(path, "inventory_position") if row["variant_id"] == variant)
            self.assertIsNone(position["counted_qty"])
            self.assertIsNone(position["count_discrepancy_qty"])

    def test_funnel_retains_unlinked_leads_and_linked_session_rate_cannot_exceed_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = generate_v2(seed=42, days=365, order_count=80)
            data["tables"]["experiments"][0]["end_date"] = data["metadata"]["as_of"]
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            mart = query_mart(path, "funnel_conversion")
            self.assertEqual(len(data["tables"]["leads"]), sum(row["all_leads"] for row in mart))
            self.assertEqual(sum(1 for row in data["tables"]["leads"] if row["session_id"] is None), sum(row["unlinked_leads"] for row in mart))
            self.assertTrue(all(row["session_to_lead_rate"] is None or row["session_to_lead_rate"] <= 1 for row in mart))

    def test_cohort_repeat_and_partial_experiment_coverage_are_not_misreported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = generate_v2(seed=42, days=365, order_count=1200)
            data["tables"]["experiments"][0]["end_date"] = data["metadata"]["as_of"]
            # Coverage false means no numeric experimental denominator/outcome claim.
            data["metadata"]["coverage"]["experiment_assignments"] = False
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            cohort = query_mart(path, "customer_cohorts")
            self.assertTrue(any(row["repeat_within_30d_customers"] for row in cohort if row["eligible_customers_30d"]))
            self.assertTrue(all(row["assigned_customers"] is None and row["conversion_rate"] is None for row in query_mart(path, "experiment_results")))

    def test_campaign_with_zero_orders_retains_spend_and_reconciles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = generate_v2(seed=11, days=90, order_count=60)
            data["tables"]["campaigns"].append({"id": "camp-no-orders", "name": "Synthetic no-order", "channel": "Instagram", "objective": "test", "start_date": data["metadata"]["start_date"], "end_date": data["metadata"]["as_of"]})
            row = max(data["tables"]["funnel"], key=lambda value: value["spend_cents"])
            row["campaign_id"] = "camp-no-orders"
            path = Path(tmp) / "alma.sqlite3"
            build_warehouse(data, path)
            channel = next(row for row in query_mart(path, "channel_performance") if row["campaign_id"] == "camp-no-orders")
            self.assertEqual(0, channel["delivered_orders"])
            self.assertGreater(channel["marketing_spend_cents"], 0)
            control = {row["check_id"]: row for row in query_mart(path, "reconciliation")}
            self.assertEqual(1, control["marketing_spend"]["passed"])


if __name__ == "__main__":
    unittest.main()
