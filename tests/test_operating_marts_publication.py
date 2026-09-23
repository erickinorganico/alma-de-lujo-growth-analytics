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
    path.write_text(json.dumps(data), encoding="utf-8")


class PublicationGapTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            demand = pack / "unmet_demand.csv"
            fields, _ = rows(demand)
            write_rows(demand, fields, [])
            coverage(pack, "unmet_demand", "ZERO")
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
            self.assertEqual("ZERO", json.loads((dest / "manifest.json").read_text(encoding="utf-8"))["coverage"]["unmet_demand"]["status"])

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
            def missing_metric(*args):
                families, measures = original(*args)
                return families, [row for row in measures if row.metric_id != "realized_gross_margin"]
            other_private = home / "second" / ".local" / "operating-marts"
            with patch.object(operating_marts, "_collect", side_effect=missing_metric):
                with self.assertRaises(ValueError):
                    operating_marts.build_operating_marts(cut["destination"], other_private,
                        policy_path=POLICY, private_root=other_private)
            self.assertFalse(other_private.exists())


if __name__ == "__main__":
    unittest.main()
