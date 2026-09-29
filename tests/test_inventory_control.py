import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"


class InventoryControlTests(unittest.TestCase):
    def test_report_reconciles_canonical_inventory(self) -> None:
        from alma.inventory_control import create_inventory_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".local" / "inventory-runs"
            result = create_inventory_run(PACK, root)
            self.assertEqual("REVIEW", result["status"])
            report = json.loads(Path(result["run"], "inventory-control.json").read_text(encoding="utf-8"))
            row = report["inventory"][0]
            self.assertEqual(24, row["on_hand_units"])
            self.assertEqual(2, row["reserved_units"])
            self.assertEqual(21, row["available_units"])
            self.assertEqual(2, row["recorded_in_transit_units"])
            self.assertEqual(2, row["open_purchase_units"])
            self.assertEqual(0, row["transit_variance_units"])
            self.assertEqual("REVIEW_COVERAGE", row["action"])
            self.assertFalse(report["controls"]["replenishment_proposal"])
            self.assertTrue(Path(result["dashboard"]).is_file())
            receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
            self.assertEqual({"inventory-control.csv", "inventory-control.html", "inventory-control.json"}, set(receipt["files"]))
            with self.assertRaisesRegex(ValueError, "already exists"):
                create_inventory_run(PACK, root)

    def test_count_variance_blocks_inventory_decision(self) -> None:
        from alma.inventory_control import create_inventory_run

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            count_path = pack / "inventory_counts.csv"
            with count_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
                fields = list(rows[0])
            rows[0]["on_hand_units"] = "25"
            with count_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            result = create_inventory_run(pack, home / ".local" / "inventory-runs")
            self.assertEqual("BLOCKED", result["status"])
            report = json.loads(Path(result["run"], "inventory-control.json").read_text(encoding="utf-8"))
            row = report["inventory"][0]
            self.assertEqual(-1, row["count_variance_units"])
            self.assertIsNone(row["available_units"])
            self.assertEqual("RECONCILE_COUNT", row["action"])

    def test_private_output_boundary_is_required(self) -> None:
        from alma.inventory_control import create_inventory_run

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "must end"):
                create_inventory_run(PACK, Path(tmp) / "reports")


if __name__ == "__main__":
    unittest.main()
