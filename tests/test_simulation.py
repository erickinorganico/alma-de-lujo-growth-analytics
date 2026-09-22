"""Contract and business-shape tests for the v2 synthetic simulation."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import unittest

from alma.simulation import ADDITIONAL_SCHEMA, ALL_TABLES, TABLE_COLUMNS, core_projection, generate
from alma.validation import validate


class SimulationTests(unittest.TestCase):
    def test_reproducible_complete_shape_and_projection(self) -> None:
        first = generate()
        self.assertEqual(first, generate())
        self.assertEqual(30, len(ALL_TABLES))
        self.assertEqual(set(ALL_TABLES), set(first["tables"]))
        self.assertEqual("2.0", first["metadata"]["contract_version"])
        self.assertEqual(set(ALL_TABLES), set(first["metadata"]["coverage"]))
        for name, rows in first["tables"].items():
            self.assertTrue(rows, name)
            self.assertTrue(all(tuple(row) == TABLE_COLUMNS[name] for row in rows), name)
        projected = core_projection(first)
        self.assertEqual(16, len(projected["tables"]))
        self.assertEqual(set(projected["tables"]), set(core_projection(first)["metadata"]["coverage"]))
        self.assertEqual({row["id"] for row in first["tables"]["products"]}, {row["product_id"] for row in first["tables"]["lifecycle_events"]})

    def test_normal_scale_catalog_and_core_validation(self) -> None:
        data = generate(seed=42, days=365, order_count=1200)
        self.assertEqual(1200, len(data["tables"]["orders"]))
        self.assertGreaterEqual(len(data["tables"]["variants"]), 36)
        categories = {row["category"] for row in data["tables"]["products"]}
        self.assertEqual({"Pilates socks", "Sportswear"}, categories)
        self.assertTrue(all(row["status"] == "PASS" for row in validate(core_projection(data))))
        products = {row["id"]: row for row in data["tables"]["products"]}
        sold_variants = {row["variant_id"] for row in data["tables"]["order_items"]}
        self.assertTrue(all(products[next(v["product_id"] for v in data["tables"]["variants"] if v["id"] == variant)]["lifecycle"] not in {"sample", "idea"} for variant in sold_variants))
        self.assertGreaterEqual(len({row["customer_id"] for row in data["tables"]["orders"]}), 100)
        self.assertGreater(len(data["tables"]["orders"]), len({row["customer_id"] for row in data["tables"]["orders"]}))
        self.assertGreaterEqual(len(data["tables"]["sessions"]), len(data["tables"]["orders"]) * 5)
        self.assertLess(sum(row["status"] == "converted" for row in data["tables"]["leads"]), len(data["tables"]["leads"]) // 2)
        self.assertGreaterEqual(len({row["date"][:7] for row in data["tables"]["expenses"]}), 12)

    def test_event_reconciliations_and_temporal_bounds(self) -> None:
        data = generate()
        tables = data["tables"]
        as_of = date.fromisoformat(data["metadata"]["as_of"])
        po_by_id = {row["id"]: row for row in tables["purchase_orders"]}
        expense_by_id = {row["id"]: row for row in tables["expenses"]}
        paid_by_po = defaultdict(int)
        received_by_po = defaultdict(int)
        paid_by_expense = defaultdict(int)
        for row in tables["supplier_payments"]:
            paid_by_po[row["purchase_order_id"]] += row["amount_cents"]
        for row in tables["purchase_receipts"]:
            received_by_po[row["purchase_order_id"]] += row["quantity"]
            self.assertGreater(row["quantity"], 0)
        for row in tables["expense_payments"]:
            paid_by_expense[row["expense_id"]] += row["amount_cents"]
        self.assertTrue(all(paid_by_po[key] == row["paid_cents"] for key, row in po_by_id.items()))
        self.assertTrue(all(received_by_po[key] == row["received_qty"] for key, row in po_by_id.items()))
        self.assertTrue(all(paid_by_expense[key] == row["paid_cents"] for key, row in expense_by_id.items()))
        self.assertTrue(all(date.fromisoformat(row["date"]) <= as_of for name in ("payments", "refunds", "returns", "movements", "expenses", "funnel") for row in tables[name]))
        self.assertTrue(any(row["restock"] == 1 for row in tables["returns"]))
        self.assertTrue(any(row["restock"] == 0 for row in tables["returns"]))

    def test_valid_scenarios_and_expected_failure_scenarios(self) -> None:
        for scenario in ("normal", "stock_pressure", "promotion_illusion", "cash_squeeze"):
            with self.subTest(scenario=scenario):
                quality = validate(core_projection(generate(scenario=scenario)))
                self.assertTrue(all(row["status"] == "PASS" for row in quality))
        missing = validate(core_projection(generate(scenario="missing_cost")))
        self.assertEqual("UNKNOWN", {row["id"]: row["status"] for row in missing}["cost_coverage"])
        broken = validate(core_projection(generate(scenario="broken_link")))
        self.assertEqual("FAIL", {row["id"]: row["status"] for row in broken}["fk_order_items_variant_id"])

    def test_scenarios_change_their_intended_signals(self) -> None:
        normal = generate()
        promotion = generate(scenario="promotion_illusion")
        pressure = generate(scenario="stock_pressure")
        cash = generate(scenario="cash_squeeze")
        def discount_ratio(data: dict) -> float:
            rows = data["tables"]["order_items"]
            return sum(row["discount_cents"] for row in rows) / sum(row["quantity"] * row["unit_price_cents"] for row in rows)
        self.assertGreater(discount_ratio(promotion), discount_ratio(normal) * 3)
        self.assertGreater(len(pressure["tables"]["unmet_demand"]), len(normal["tables"]["unmet_demand"]))
        self.assertGreater(sum(row["amount_cents"] for row in cash["tables"]["supplier_payments"]), sum(row["amount_cents"] for row in normal["tables"]["supplier_payments"]))
        self.assertGreater(sum(row["counted_qty"] for row in pressure["tables"]["inventory_counts"]), 0)
        self.assertTrue(any(row["counted_qty"] != sum(m["quantity"] for m in pressure["tables"]["movements"] if m["variant_id"] == row["variant_id"]) for row in pressure["tables"]["inventory_counts"]))


if __name__ == "__main__":
    unittest.main()
