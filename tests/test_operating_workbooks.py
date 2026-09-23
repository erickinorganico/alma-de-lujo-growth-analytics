"""Contract tests for the operating-v1 workbook editing boundary."""
from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from alma.operating_contracts import CONTRACT_VERSION, SOURCE_NAMES, columns_for
from alma.operating_interchange import parse_pack
from alma.operating_mart_contracts import load_policy
from scripts.operating_pack import synthetic_rows


ROOT = Path(__file__).resolve().parents[1]


class OperatingWorkbookGenerationTests(unittest.TestCase):
    def _build(self, root: Path) -> dict:
        from scripts.build_operating_workbooks import build_operating_workbooks

        return build_operating_workbooks(root)

    def test_blank_and_synthetic_books_follow_the_final_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._build(root)
            self.assertEqual(CONTRACT_VERSION, manifest["contract_version"])
            self.assertEqual(22, manifest["relation_count"])
            self.assertEqual(list(SOURCE_NAMES), manifest["relations"])
            self.assertEqual(2, len(manifest["policies"]))
            for kind in ("blank", "synthetic"):
                book_path = root / manifest["workbooks"][kind]["path"]
                pack_path = root / manifest["source_packs"][kind]["path"]
                self.assertEqual(
                    manifest["workbooks"][kind]["sha256"],
                    hashlib.sha256(book_path.read_bytes()).hexdigest(),
                )
                workbook = load_workbook(book_path, data_only=False, keep_links=False)
                self.assertEqual(
                    ["INICIO", "DICCIONARIO", "COMPLETITUD", *SOURCE_NAMES],
                    workbook.sheetnames,
                )
                for relation in SOURCE_NAMES:
                    with self.subTest(kind=kind, relation=relation):
                        sheet = workbook[relation]
                        self.assertEqual(
                            list(columns_for(relation)),
                            [sheet.cell(6, column).value for column in range(1, len(columns_for(relation)) + 1)],
                        )
                        self.assertEqual("A7", sheet.freeze_panes)
                        self.assertEqual("landscape", sheet.page_setup.orientation)
                        self.assertEqual("1:6", sheet.print_title_rows)
                        self.assertEqual("1", str(sheet.page_setup.fitToWidth))
                        self.assertTrue(sheet.auto_filter.ref.startswith("A6:"))
                        self.assertTrue(sheet.data_validations.count >= 1)
                        rows = [
                            [sheet.cell(row, column).value for column in range(1, len(columns_for(relation)) + 1)]
                            for row in range(7, sheet.max_row + 1)
                        ]
                        rows = [row for row in rows if any(value is not None for value in row)]
                        if kind == "blank":
                            self.assertEqual([], rows)
                        else:
                            self.assertEqual(len(synthetic_rows()[relation]), len(rows))
                            self.assertIn("SYNTHETIC", str(sheet["A2"].value).upper())
                workbook.close()
                if kind == "synthetic":
                    parsed = parse_pack(pack_path)
                    self.assertEqual(list(SOURCE_NAMES), list(parsed["tables"]))
                else:
                    metadata = json.loads((pack_path / "metadata.json").read_text(encoding="utf-8"))
                    self.assertEqual("BLANK", metadata["input_class"])

    def test_completeness_matrix_covers_each_relation_and_interactions(self) -> None:
        from scripts.build_operating_workbooks import COMPLETENESS_MATRIX, omission_impact

        self.assertEqual(set(SOURCE_NAMES), set(COMPLETENESS_MATRIX))
        for relation in SOURCE_NAMES:
            with self.subTest(relation=relation):
                row = COMPLETENESS_MATRIX[relation]
                self.assertIn(row["classification"], {"REQUIRED", "OPTIONAL"})
                self.assertIn(row["omission_state"], {"UNKNOWN", "PARTIAL", "REVIEW", "BLOCKED"})
                self.assertTrue(row["metric_families"])
                self.assertEqual(row["omission_state"], omission_impact((relation,))["state"])
        self.assertEqual("BLOCKED", omission_impact(("sku_catalog", "sales_aggregates"))["state"])
        self.assertEqual("UNKNOWN", omission_impact(("sales_aggregates", "quality_events"))["state"])
        self.assertEqual(
            sorted(set(COMPLETENESS_MATRIX["sales_aggregates"]["metric_families"])
                       | set(COMPLETENESS_MATRIX["quality_events"]["metric_families"])),
            omission_impact(("sales_aggregates", "quality_events"))["metric_families"],
        )

    def test_policy_materials_are_separate_hash_bound_and_unapproved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._build(root)
            self.assertNotIn("policies", manifest["relations"])
            for policy in manifest["policies"]:
                path = root / policy["path"]
                content = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(policy["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                loaded = load_policy(path, as_of="2026-09-21", real_cut=False)
                self.assertEqual(content["status"], loaded.status)
                self.assertIsNone(content["owner_approval_ref"])
            self.assertEqual(
                {"REVIEW", "SYNTHETIC_EXAMPLE"},
                {json.loads((root / policy["path"]).read_text(encoding="utf-8"))["status"]
                 for policy in manifest["policies"]},
            )

    def test_generated_manifest_rehashes_every_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._build(root)
            persisted = json.loads((root / "workbook-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest, persisted)
            for relative, digest in manifest["files"].items():
                self.assertEqual(digest, hashlib.sha256((root / relative).read_bytes()).hexdigest())


class WorkbookImportTests(unittest.TestCase):
    """Task 2 tests are completed after the generator contract is green."""

    pass


if __name__ == "__main__":
    unittest.main()
