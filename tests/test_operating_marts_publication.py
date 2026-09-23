"""End-to-end gap controls for private Phase 2 publication."""
from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alma.operating_workspace import build_operating_workspace
from alma.operating_mart_contracts import bind_cut
from alma import operating_marts

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


def rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def write_rows(path: Path, fields: list[str], values: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(values)


def coverage(pack: Path, source: str, status: str) -> None:
    path = pack / "metadata.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["coverage"][source]["status"] = status
    if status == "MISSING":
        data["coverage"][source]["window_start"] = None
        data["coverage"][source]["window_end"] = None
    path.write_text(json.dumps(data), encoding="utf-8")


class PublicationGapTests(unittest.TestCase):
    def test_missing_physical_source_and_broken_fk_reject_intake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            missing = home / "missing"
            shutil.copytree(PACK, missing)
            (missing / "cash_events.csv").unlink()
            with self.assertRaises((FileNotFoundError, ValueError)):
                build_operating_workspace(missing, private_root=home / "missing-cuts")
            broken = home / "broken"
            shutil.copytree(PACK, broken)
            path = broken / "obligation_payments.csv"
            fields, values = rows(path)
            values[0]["obligation_id"] = "synthetic:absent-obligation"
            write_rows(path, fields, values)
            with self.assertRaises(ValueError):
                build_operating_workspace(broken, private_root=home / "broken-cuts")

    def test_empty_domain_matrix(self) -> None:
        for domain, status in (("sales_aggregates", "ZERO"), ("sales_aggregates", "MISSING"),
                               ("budgets", "ZERO"), ("budgets", "MISSING"),
                               ("obligation_payments", "MISSING"),
                               ("cash_events", "ZERO"), ("cash_events", "MISSING")):
            with self.subTest(domain=domain, status=status), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                pack = home / "pack"
                shutil.copytree(PACK, pack)
                if domain == "sales_aggregates":
                    path = pack / "sales_aggregates.csv"
                    fields, _ = rows(path); write_rows(path, fields, [])
                    path = pack / "inventory_movements.csv"
                    fields, values = rows(path)
                    write_rows(path, fields, [row for row in values if row["movement_type"] not in
                                              {"SALE_OUT", "RETURN_RESTOCK"}])
                    path = pack / "quality_events.csv"
                    fields, values = rows(path)
                    write_rows(path, fields, [row for row in values if row["delivery_cohort_id"] == ""])
                    counts = pack / "inventory_counts.csv"
                    counts.write_text(counts.read_text(encoding="utf-8").replace(",24,2,", ",35,2,"), encoding="utf-8")
                elif domain == "budgets":
                    for source in ("budgets", "budget_allocations", "expenses", "purchase_orders",
                                   "purchase_receipts", "obligations", "obligation_payments",
                                   "cash_events", "cash_balance_evidence"):
                        path = pack / f"{source}.csv"
                        fields, _ = rows(path); write_rows(path, fields, [])
                        coverage(pack, source, status if source == "budgets" else "ZERO")
                    path = pack / "inventory_movements.csv"
                    fields, values = rows(path)
                    write_rows(path, fields, [row for row in values if row["movement_type"] != "RECEIPT_ACCEPTED"])
                    path = pack / "quality_events.csv"
                    fields, values = rows(path)
                    write_rows(path, fields, [row for row in values if row["receipt_id"] == ""])
                    counts = pack / "inventory_counts.csv"
                    counts.write_text(counts.read_text(encoding="utf-8").replace(",24,2,", ",8,2,"), encoding="utf-8")
                elif domain == "obligation_payments":
                    path = pack / "obligation_payments.csv"
                    fields, _ = rows(path); write_rows(path, fields, [])
                    path = pack / "cash_events.csv"
                    fields, values = rows(path)
                    write_rows(path, fields, [row for row in values if row["level"] != "RECONCILED"])
                    balance = pack / "cash_balance_evidence.csv"
                    balance.write_text(balance.read_text(encoding="utf-8").replace(",1100000,", ",2000000,"), encoding="utf-8")
                elif domain == "cash_events":
                    for source in ("cash_events", "cash_balance_evidence"):
                        path = pack / f"{source}.csv"
                        fields, _ = rows(path); write_rows(path, fields, [])
                        coverage(pack, source, status)
                coverage(pack, domain, status)
                cut = build_operating_workspace(pack, private_root=home / "cuts")
                private = home / ".local" / "operating-marts"
                result = operating_marts.build_operating_marts(cut["destination"], private,
                    policy_path=POLICY, private_root=private)
                dest = Path(result["destination"])
                families = json.loads((dest / "families.json").read_text(encoding="utf-8"))
                metrics = json.loads((dest / "metric_rows.json").read_text(encoding="utf-8"))
                manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(status, manifest["coverage"][domain]["status"])
                domain_coverage = json.loads((dest / "domain_coverage.json").read_text(encoding="utf-8"))
                self.assertEqual(status, domain_coverage[domain]["status"])
                self.assertEqual(0, domain_coverage[domain]["row_count"])
                self.assertEqual("DECLARED_ZERO" if status == "ZERO" else "MISSING_SOURCE",
                                 domain_coverage[domain]["empty_reason"])
                self.assertTrue(families["inventory"])
                if domain == "sales_aggregates":
                    self.assertEqual([], families["economics"])
                    self.assertEqual("UNKNOWN", families["learning"][0]["sell_through"]["status"])
                elif domain == "budgets":
                    self.assertEqual([], families["budgets"]["targets"])
                    self.assertEqual([], families["purchases"])
                elif domain == "obligation_payments":
                    self.assertEqual(900000, next(row for row in families["obligations"]
                        if row["origin_type"] == "PURCHASE_ORDER")["recorded_unpaid_cents"])
                    self.assertTrue(all(row["authoritative_outstanding_cents"] is None
                                        for row in families["obligations"]))
                elif domain == "cash_events":
                    self.assertIsNone(families["cash"]["scenario_id"])
                    self.assertFalse(any(row["metric_id"] == "cash_layer_cents" for row in metrics))

    def test_observed_cash_and_all_layers_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            cash_file = pack / "cash_events.csv"
            fields, cash = rows(cash_file)
            base = cash[-1]
            cash.append(dict(base, event_id="synthetic:cash-in-001", economic_event_id="synthetic:econ-in-001",
                supersedes_event_id="", event_date="2026-09-21", level="RECONCILED",
                direction="INFLOW", amount_cents="100", obligation_id="", payment_id="",
                source_ref="synthetic:source:cash-in-001"))
            for tag, level, amount, day in (("commit", "COMMITTED", "11", "2026-09-21"),
                                            ("expect", "EXPECTED", "13", "2026-09-21"),
                                            ("undated", "UNDATED", "7", ""),
                                            ("scenario", "SCENARIO", "5", "2026-09-21")):
                cash.append(dict(base, event_id=f"synthetic:cash-{tag}",
                    economic_event_id=f"synthetic:econ-{tag}", supersedes_event_id="",
                    event_date=day, level=level, direction="OUTFLOW", amount_cents=amount,
                    obligation_id="synthetic:obligation-po-001" if level == "COMMITTED" else "",
                    payment_id="", source_ref=f"synthetic:source:cash-{tag}"))
            write_rows(cash_file, fields, cash)
            balance = pack / "cash_balance_evidence.csv"
            balance.write_text(balance.read_text(encoding="utf-8").replace(",1100000,", ",1100100,"), encoding="utf-8")
            coverage(pack, "cash_events", "COMPLETE")
            coverage(pack, "cash_balance_evidence", "COMPLETE")
            cut = build_operating_workspace(pack, private_root=home / "cuts")
            private = home / ".local" / "operating-marts"
            result = operating_marts.build_operating_marts(cut["destination"], private,
                policy_path=POLICY, private_root=private)
            dest = Path(result["destination"])
            family = json.loads((dest / "families.json").read_text(encoding="utf-8"))["cash"]
            metrics = json.loads((dest / "metric_rows.json").read_text(encoding="utf-8"))
            self.assertEqual(1100100, family["reconciled_close_cents"])
            for horizon in (56, 91):
                expected = {"RECONCILED": 100, "COMMITTED": -11, "EXPECTED": -13,
                            "UNDATED": -7, "SCENARIO": -5}
                for layer, amount in expected.items():
                    matching = [row for row in metrics if row["metric_id"] == "cash_layer_cents" and
                                row["dimensions"].get("horizon") == str(horizon) and
                                row["dimensions"].get("layer") == layer]
                    self.assertEqual(1, len(matching), (horizon, layer))
                    self.assertEqual(amount, matching[0]["value"])

    def test_zero_unmet_domain_preserves_unrelated_metrics(self) -> None:
        for domain_status in ("ZERO", "MISSING"):
          with self.subTest(status=domain_status), tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            demand = pack / "unmet_demand.csv"
            fields, _ = rows(demand)
            write_rows(demand, fields, [])
            coverage(pack, "unmet_demand", domain_status)
            cut = build_operating_workspace(pack, private_root=home / "cuts")
            private = home / ".local" / "operating-marts"
            result = operating_marts.build_operating_marts(cut["destination"], private,
                policy_path=POLICY, private_root=private)
            dest = Path(result["destination"])
            metrics = json.loads((dest / "metric_rows.json").read_text(encoding="utf-8"))
            registry = json.loads((dest / "registry.json").read_text(encoding="utf-8"))
            self.assertIn("recorded_unmet_units", registry)
            self.assertFalse(any(row["metric_id"] == "recorded_unmet_units" for row in metrics))
            self.assertTrue(any(row["metric_id"] == "available_units" for row in metrics))
            self.assertEqual(domain_status, json.loads((dest / "manifest.json").read_text(encoding="utf-8"))["coverage"]["unmet_demand"]["status"])

    def test_semantic_registry_covers_published_measures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut = build_operating_workspace(PACK, private_root=home / "cuts")
            private = home / ".local" / "operating-marts"
            result = operating_marts.build_operating_marts(cut["destination"], private,
                policy_path=POLICY, private_root=private)
            dest = Path(result["destination"])
            catalog = json.loads((dest / "semantic_catalog.json").read_text(encoding="utf-8"))
            metrics = json.loads((dest / "metric_rows.json").read_text(encoding="utf-8"))
            self.assertIn("economics[].ratios.gross_margin", catalog)
            self.assertTrue(any(row["metric_id"] == "realized_gross_margin" for row in metrics))
            self.assertIn("budgets.targets[].paid_cents", catalog)
            self.assertIn("learning[].mature_returns.value", catalog)
            self.assertEqual("metric", catalog["economics[].ratios.gross_margin"]["kind"])
            original = operating_marts._collect
            original_definitions = operating_marts._definitions
            def missing_metric(*args):
                families, measures = original(*args)
                return families, [row for row in measures if row.metric_id != "realized_gross_margin"]
            other_private = home / "second" / ".local" / "operating-marts"
            with patch.object(operating_marts, "_collect", side_effect=missing_metric), patch.object(
                operating_marts, "_definitions", side_effect=lambda: {key: value for key, value
                    in original_definitions().items() if key != "realized_gross_margin"}):
                with self.assertRaises(ValueError):
                    operating_marts.build_operating_marts(cut["destination"], other_private,
                        policy_path=POLICY, private_root=other_private)
            self.assertFalse(other_private.exists())
            def injected(*args):
                families, measures = original(*args)
                families["economics"][0]["unclassified_profit_cents"] = 7
                return families, measures
            with patch.object(operating_marts, "_collect", side_effect=injected):
                with self.assertRaises(ValueError):
                    operating_marts.build_operating_marts(cut["destination"], other_private,
                        policy_path=POLICY, private_root=other_private)
            self.assertFalse(other_private.exists())

    def test_estimated_economics_serialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            for source in ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"):
                coverage(pack, source, "COMPLETE")
            sales = pack / "sales_aggregates.csv"
            sales.write_text(sales.read_text(encoding="utf-8").replace(",PARTIAL,", ",COMPLETE,"), encoding="utf-8")
            components = pack / "cost_components.csv"
            components.write_text(components.read_text(encoding="utf-8").replace(",KNOWN,", ",ESTIMATED,"), encoding="utf-8")
            cut = build_operating_workspace(pack, private_root=home / "cuts")
            private = home / ".local" / "operating-marts"
            result = operating_marts.build_operating_marts(cut["destination"], private,
                policy_path=POLICY, private_root=private)
            dest = Path(result["destination"])
            family = json.loads((dest / "families.json").read_text(encoding="utf-8"))["economics"][0]
            metrics = json.loads((dest / "metric_rows.json").read_text(encoding="utf-8"))
            self.assertEqual("ESTIMATED", family["status"])
            self.assertEqual(480000, family["cogs_cents"])
            self.assertEqual(240000, family["contribution_cents"])
            for metric_id, expected in (("realized_contribution_cents", 240000),
                (operating_marts._semantic_id("economics[].cogs_cents"), 480000),
                ("realized_gross_margin", "0.6"),
                ("realized_contribution_margin", "0.2"),
                ("realized_markup", "1.5")):
                self.assertTrue(any(row["metric_id"] == metric_id and row["value"] == expected and
                                    row["status"] == "ESTIMATED" for row in metrics), metric_id)


if __name__ == "__main__":
    unittest.main()
