"""Cross-module integration tests with independently hand-computed expectations."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))

from alma.analytics import analyze
from alma.fixtures import generate


def hand_computed_fixture() -> dict:
    """One auditable scenario; expected figures below are calculated by hand."""
    tables = {
        "products": [
            {"id": "p1", "name": "Synthetic Grip Socks", "category": "Pilates socks", "collection": "Synthetic", "lifecycle": "launched"}
        ],
        "variants": [
            {"id": "v1", "product_id": "p1", "size": "M", "color": "Rose", "price_cents": 10000, "cost_cents": 4000}
        ],
        "suppliers": [{"id": "s1", "name": "Synthetic Supplier"}],
        "purchase_orders": [
            {"id": "po1", "supplier_id": "s1", "variant_id": "v1", "ordered_qty": 10, "received_qty": 5, "unit_cost_cents": 4000, "status": "partial", "date": "2026-07-05", "paid_cents": 20000}
        ],
        "customers": [{"id": "c1", "acquired_date": "2026-07-10"}],
        "orders": [
            {"id": "o1", "customer_id": "c1", "channel": "Instagram", "campaign_id": "synthetic-campaign", "date": "2026-08-01", "delivered_date": "2026-08-03", "status": "delivered"}
        ],
        "order_items": [
            {"id": "i1", "order_id": "o1", "variant_id": "v1", "quantity": 2, "unit_price_cents": 10000, "discount_cents": 1000, "unit_cost_cents": 4000}
        ],
        "payments": [
            {"id": "pay1", "order_id": "o1", "date": "2026-08-01", "amount_cents": 19000, "status": "settled"}
        ],
        "refunds": [
            {"id": "refund1", "order_id": "o1", "date": "2026-08-06", "amount_cents": 2000, "status": "settled"}
        ],
        "credit_notes": [
            {"id": "credit1", "order_item_id": "i1", "date": "2026-08-06", "amount_cents": 3000, "reason": "synthetic adjustment"}
        ],
        "returns": [
            {"id": "return1", "order_item_id": "i1", "date": "2026-08-06", "quantity": 1, "restock": 1}
        ],
        "movements": [
            {"id": "m-open", "variant_id": "v1", "date": "2026-06-25", "kind": "opening", "quantity": 10, "reference_id": "opening-v1"},
            {"id": "m-receipt", "variant_id": "v1", "date": "2026-07-05", "kind": "receipt", "quantity": 5, "reference_id": "po1"},
            {"id": "m-sale", "variant_id": "v1", "date": "2026-08-01", "kind": "sale", "quantity": -2, "reference_id": "i1"},
            {"id": "m-return", "variant_id": "v1", "date": "2026-08-06", "kind": "return", "quantity": 1, "reference_id": "return1"},
        ],
        "reservations": [
            {"id": "reserve1", "order_item_id": "i1", "quantity": 2, "status": "released"}
        ],
        "expenses": [
            {"id": "expense1", "date": "2026-08-10", "category": "synthetic packaging", "amount_cents": 5000, "paid_cents": 3000, "variable": 1}
        ],
        "funnel": [
            {"id": "f1", "date": "2026-08-01", "channel": "Instagram", "campaign_id": "synthetic-campaign", "visits": 100, "leads": 10, "spend_cents": 0}
        ],
        "unmet_demand": [
            {"id": "u1", "date": "2026-08-11", "variant_id": "v1", "quantity": 1, "reason": "synthetic requested color unavailable"}
        ],
    }
    return {
        "metadata": {
            "synthetic": True,
            "seed": 7,
            "as_of": "2026-09-21",
            "scenario": "hand-computed",
            "currency": "MXN",
            "coverage": {name: True for name in tables},
        },
        "tables": tables,
    }


class AnalyticsIntegrationTests(unittest.TestCase):
    def test_hand_computed_finance_stock_and_commerce(self) -> None:
        report = analyze(hand_computed_fixture())

        self.assertEqual("PASS", report["meta"]["status"])
        self.assertEqual(
            {
                "gross_revenue_cents": 20000,
                "discounts_cents": 1000,
                "credits_cents": 3000,
                "net_revenue_cents": 16000,
                "cogs_cents": 4000,
                "gross_profit_cents": 12000,
                "gross_margin_pct": 75.0,
                "opex_cents": 5000,
                "variable_expenses_cents": 5000,
                "contribution_cents": 7000,
                "operating_proxy_cents": 7000,
                "cash_in_cents": 19000,
                "cash_out_cents": 25000,
                "net_cash_cents": -6000,
                "orders": 1,
                "delivered_orders": 1,
                "repeat_rate_pct": 0.0,
                "inventory_value_cents": 56000,
            },
            report["kpis"],
        )

        self.assertEqual(1, len(report["inventory"]))
        stock = report["inventory"][0]
        self.assertEqual(
            {"on_hand": 14, "reserved": 0, "available": 14, "in_transit": 5, "sold_units": 2, "value_cents": 56000, "sell_through_pct": 6.67},
            {key: stock[key] for key in ("on_hand", "reserved", "available", "in_transit", "sold_units", "value_cents", "sell_through_pct")},
        )
        self.assertEqual(16000, report["orders"][0]["recognized_cents"])
        self.assertEqual(19000, report["orders"][0]["settled_cents"])
        self.assertEqual(2000, report["orders"][0]["refunded_cents"])
        self.assertEqual(5, report["purchases"][0]["in_transit"])

    def test_normal_generated_report_is_deterministic_and_json_serializable(self) -> None:
        first = analyze(generate(seed=42))
        second = analyze(generate(seed=42))
        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(second, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        self.assertTrue(first["meta"]["synthetic"])
        self.assertEqual("PASS", first["meta"]["status"])
        self.assertEqual(first["meta"]["coverage"], generate(seed=42)["metadata"]["coverage"])

    def test_red_scenarios_block_or_preserve_unknowns(self) -> None:
        expectations = {
            "missing_cost": ("UNKNOWN", "cost_coverage"),
            "negative_stock": ("FAIL", "stock_nonnegative"),
            "missing_payment": ("FAIL", "payment_reconciliation"),
            "duplicate_event": ("FAIL", "unique_movements"),
        }
        for scenario, (quality_status, quality_id) in expectations.items():
            with self.subTest(scenario=scenario):
                report = analyze(generate(seed=42, scenario=scenario))
                self.assertEqual("BLOCKED", report["meta"]["status"])
                quality = {row["id"]: row for row in report["quality"]}
                self.assertEqual(quality_status, quality[quality_id]["status"])
                if scenario == "missing_cost":
                    self.assertIsNone(report["kpis"]["cogs_cents"])
                    self.assertIsNone(report["kpis"]["gross_profit_cents"])
                    self.assertIsNone(report["kpis"]["gross_margin_pct"])
                    self.assertIsNone(report["kpis"]["inventory_value_cents"])

    def test_missing_coverage_is_unknown_not_zero(self) -> None:
        data = copy.deepcopy(hand_computed_fixture())
        data["metadata"]["coverage"]["funnel"] = False
        report = analyze(data)
        channel = report["channels"][0]
        self.assertEqual("BLOCKED", report["meta"]["status"])
        self.assertIsNone(channel["visits"])
        self.assertIsNone(channel["leads"])
        self.assertIsNone(channel["spend_cents"])
        self.assertIsNone(channel["conversion_pct"])
        quality = {row["id"]: row for row in report["quality"]}
        self.assertEqual("UNKNOWN", quality["coverage_funnel"]["status"])

    def test_coverage_matrix_propagates_unknown_to_dependent_outputs(self) -> None:
        cases = {
            "variants": (
                ("kpis", "inventory_value_cents"),
                ("inventory", 0, "on_hand"),
                ("inventory", 0, "available"),
                ("inventory", 0, "cost_cents"),
                ("inventory", 0, "value_cents"),
                ("inventory", 0, "sold_units"),
                ("inventory", 0, "sell_through_pct"),
                ("inventory", 0, "days_since_sale"),
            ),
            "orders": (
                ("kpis", "gross_revenue_cents"),
                ("kpis", "net_revenue_cents"),
                ("kpis", "orders"),
                ("kpis", "delivered_orders"),
                ("kpis", "repeat_rate_pct"),
                ("orders", 0, "recognized_cents"),
                ("channels", 0, "orders"),
                ("channels", 0, "conversion_pct"),
            ),
            "payments": (
                ("kpis", "cash_in_cents"),
                ("kpis", "net_cash_cents"),
                ("orders", 0, "settled_cents"),
            ),
            "expenses": (
                ("kpis", "opex_cents"),
                ("kpis", "variable_expenses_cents"),
                ("kpis", "operating_proxy_cents"),
                ("kpis", "cash_out_cents"),
                ("kpis", "net_cash_cents"),
            ),
        }

        def resolve(value, path):
            for part in path:
                value = value[part]
            return value

        for table, paths in cases.items():
            with self.subTest(table=table):
                data = copy.deepcopy(hand_computed_fixture())
                data["metadata"]["coverage"][table] = False
                report = analyze(data)
                self.assertEqual("BLOCKED", report["meta"]["status"])
                self.assertEqual("UNKNOWN", {q["id"]: q for q in report["quality"]}[f"coverage_{table}"]["status"])
                for path in paths:
                    self.assertIsNone(resolve(report, path), f"{table} coverage should null {path}")
                if table == "variants":
                    self.assertEqual("UNKNOWN", report["inventory"][0]["status"])

    def test_inventory_lifecycle_separates_stockout_from_prelaunch(self) -> None:
        data = hand_computed_fixture()
        data["tables"]["purchase_orders"][0]["received_qty"] = 0
        data["tables"]["movements"] = [
            {"id": "m-open", "variant_id": "v1", "date": "2026-06-25", "kind": "opening", "quantity": 2, "reference_id": "opening-v1"},
            {"id": "m-sale", "variant_id": "v1", "date": "2026-08-01", "kind": "sale", "quantity": -2, "reference_id": "i1"},
        ]
        data["tables"]["returns"][0]["restock"] = 0
        launched = analyze(data)
        self.assertEqual("STOCKOUT", launched["inventory"][0]["status"])

        prelaunch_data = copy.deepcopy(data)
        prelaunch_data["tables"]["products"][0]["lifecycle"] = "sample"
        prelaunch = analyze(prelaunch_data)
        self.assertEqual("PRELAUNCH", prelaunch["inventory"][0]["status"])
        self.assertNotIn("v1", " ".join(fact["text"] for packet in prelaunch["decisions"] for fact in packet["facts"] if "umbral" in fact["text"]))

    def test_cli_demo_publishes_valid_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo"
            demo = subprocess.run(
                [sys.executable, "-m", "alma", "demo", "--output", str(output)],
                cwd=Path(__file__).parents[1],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(0, demo.returncode, demo.stdout + demo.stderr)
            report_path = output / "report.json"
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["meta"]["synthetic"])
            self.assertEqual("PASS", report["meta"]["status"])

if __name__ == "__main__":
    unittest.main()
