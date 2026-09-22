from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))

from alma.fixtures import TABLE_COLUMNS, generate


class FixtureTests(unittest.TestCase):
    def test_normal_fixture_is_deterministic_and_has_exact_columns(self):
        first = generate()
        second = generate()
        self.assertEqual(first, second)
        self.assertEqual(first["metadata"], {**first["metadata"], "seed": 42, "scenario": "normal"})
        self.assertIs(first["metadata"]["synthetic"], True)
        self.assertEqual(first["metadata"]["as_of"], "2026-09-21")
        for name, rows in first["tables"].items():
            self.assertTrue(rows)
            self.assertTrue(all(tuple(row) == TABLE_COLUMNS[name] for row in rows))


    def test_catalog_and_dates_cover_the_declared_business_shape(self):
        data = generate()
        products = data["tables"]["products"]
        self.assertEqual({row["category"] for row in products}, {"Pilates socks", "Sportswear"})
        self.assertEqual({row["lifecycle"] for row in products}, {"idea", "launched", "sample", "clearance"})
        socks = [row for row in data["tables"]["variants"] if row["product_id"] == "prod-socks"]
        self.assertEqual(len(socks), 5)
        self.assertEqual({row["color"] for row in socks}, {"Black", "Ivory", "Rose", "Sage", "Lilac"})
        dates = [date.fromisoformat(row["date"]) for row in data["tables"]["orders"]]
        self.assertGreaterEqual(min(dates), date(2026, 6, 24))
        self.assertLessEqual(max(dates), date(2026, 9, 21))
        statuses = {row["status"] for row in data["tables"]["orders"]}
        self.assertTrue({"delivered", "shipped", "paid", "pending", "cancelled"} <= statuses)


    def test_normal_reconciles_items_payments_stock_and_commercial_limits(self):
        data = generate()
        tables = data["tables"]
        orders = {row["id"]: row for row in tables["orders"]}
        items = {row["id"]: row for row in tables["order_items"]}
        sold = {item_id for item_id, item in items.items() if orders[item["order_id"]]["status"] in ("shipped", "delivered")}
        sales = [row for row in tables["movements"] if row["kind"] == "sale"]
        self.assertEqual({row["reference_id"] for row in sales}, sold)
        self.assertTrue(all(row["quantity"] < 0 for row in sales))
        returns = tables["returns"]
        self.assertTrue(all(row["quantity"] <= items[row["order_item_id"]]["quantity"] for row in returns))
        delivered = {row["id"] for row in tables["orders"] if row["status"] == "delivered"}
        for credit in tables["credit_notes"]:
            item = items[credit["order_item_id"]]
            self.assertIn(orders[item["order_id"]]["id"], delivered)
            self.assertLessEqual(credit["amount_cents"], item["quantity"] * item["unit_price_cents"] - item["discount_cents"])
        settled = {row["order_id"]: row["amount_cents"] for row in tables["payments"] if row["status"] == "settled"}
        self.assertTrue(all(refund["amount_cents"] <= settled[refund["order_id"]] for refund in tables["refunds"]))
        self.assertTrue(all(po["paid_cents"] <= po["ordered_qty"] * po["unit_cost_cents"] for po in tables["purchase_orders"]))
        balance = {}
        for movement in tables["movements"]:
            balance[movement["variant_id"]] = balance.get(movement["variant_id"], 0) + movement["quantity"]
        self.assertTrue(all(quantity >= 0 for quantity in balance.values()))
        self.assertTrue(any(row["visits"] is None for row in tables["funnel"] if row["channel"] == "DM"))
        active = {row["order_item_id"]: row["quantity"] for row in tables["reservations"] if row["status"] == "active"}
        self.assertEqual(active, {"item-009": 2, "item-010": 1})
        wrap_balance = sum(row["quantity"] for row in tables["movements"] if row["variant_id"] == "var-wrap-sand")
        self.assertEqual(wrap_balance, 0)
        marketing = {row["date"]: row["amount_cents"] for row in tables["expenses"] if row["category"] == "marketing"}
        funnel_spend = {row["date"]: row["spend_cents"] for row in tables["funnel"] if row["spend_cents"]}
        self.assertEqual(marketing, funnel_spend)
        sale_dates = {row["reference_id"]: row["date"] for row in tables["movements"] if row["kind"] == "sale"}
        payments_by_order = {}
        for payment in tables["payments"]:
            if payment["status"] == "settled":
                payments_by_order.setdefault(payment["order_id"], []).append(payment["date"])
        for item in items.values():
            order = orders[item["order_id"]]
            if item["id"] not in sale_dates:
                continue
            self.assertGreaterEqual(sale_dates[item["id"]], max([order["date"], *payments_by_order.get(order["id"], [])]))
            if order["status"] == "delivered":
                self.assertLessEqual(sale_dates[item["id"]], order["delivered_date"])


    def test_failure_scenarios_are_reproducible_and_targeted(self):
        missing_cost = generate(scenario="missing_cost")
        self.assertTrue(any(row["cost_cents"] is None for row in missing_cost["tables"]["variants"]))
        self.assertTrue(any(row["unit_cost_cents"] is None for row in missing_cost["tables"]["order_items"]))

        negative_stock = generate(scenario="negative_stock")
        self.assertTrue(any(row["kind"] == "adjustment" and row["quantity"] < 0 for row in negative_stock["tables"]["movements"]))

        missing_payment = generate(scenario="missing_payment")
        self.assertFalse(any(row["id"] == "pay-003" for row in missing_payment["tables"]["payments"]))
        self.assertTrue(any(row["id"] == "ord-003" and row["status"] == "delivered" for row in missing_payment["tables"]["orders"]))

        duplicate = generate(scenario="duplicate_event")
        ids = [row["id"] for row in duplicate["tables"]["movements"]]
        self.assertNotEqual(len(ids), len(set(ids)))
        self.assertEqual(generate(scenario="duplicate_event"), duplicate)
