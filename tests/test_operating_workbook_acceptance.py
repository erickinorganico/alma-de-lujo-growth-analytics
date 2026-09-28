"""Adversarial acceptance checks for the exact operating-v1 delivery pair."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from alma.operating_contracts import SOURCE_NAMES, SOURCES
from scripts.verify_operating_workbooks import (
    FILES, WorkbookAcceptanceError, check_manifest, inspect_book, normalized,
)

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "client/v1"
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def replace_member(path: Path, member: str, transform) -> None:
    with zipfile.ZipFile(path) as source:
        members = [(item, source.read(item.filename)) for item in source.infolist()]
    with zipfile.ZipFile(path, "w") as target:
        for item, content in members:
            target.writestr(item, transform(content) if item.filename == member else content)


class OperatingWorkbookAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        for filename in [*FILES.values(), "workbook-manifest.json"]:
            shutil.copyfile(DELIVERY / filename, self.root / filename)

    def test_delivery_inventory_roundtrips_22_sources_and_no_business_formulas(self) -> None:
        manifest = check_manifest(self.root / "workbook-manifest.json")
        self.assertEqual(list(SOURCE_NAMES), manifest["relations"])
        for kind, entry in manifest["workbooks"].items():
            self.assertEqual(0, entry["formula_count"])
            self.assertEqual(0, entry["cached_result_count"])
            self.assertEqual(0, entry["business_total_count"])
            self.assertEqual(set(SOURCE_NAMES), set(entry["source_pack_sha256"]))
            self.assertEqual(25, len(entry["sheets"]))
            self.assertTrue(all(not formulas for formulas in entry["formula_cells"].values()))
            self.assertTrue(all(entry["sheets"][name]["validations"] for name in SOURCE_NAMES))
            if kind == "blank":
                self.assertTrue(all(count == 0 for count in entry["row_counts"].values()))
            else:
                self.assertTrue(all(count > 0 for count in entry["row_counts"].values()))

    def test_decimal_cents_preserve_null_and_zero_and_reject_fraction(self) -> None:
        field = next(field for field in SOURCES["sales_aggregates"]["fields"]
                     if field["name"] == "net_revenue_cents")
        self.assertEqual("", normalized(None, field, "test"))
        self.assertEqual("0", normalized(0, field, "test"))
        self.assertEqual("1200000", normalized(1200000.0, field, "test"))
        with self.assertRaisesRegex(WorkbookAcceptanceError, "fractional"):
            normalized("1.5", field, "test")

    def test_modified_workbook_or_member_hash_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        replace_member(book, "docProps/app.xml", lambda data: data.replace(b"Microsoft Excel", b"Other Program"))
        with self.assertRaisesRegex(WorkbookAcceptanceError, "manifest/hash/surface mismatch"):
            check_manifest(self.root / "workbook-manifest.json")
        manifest_path = self.root / "workbook-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["workbooks"]["synthetic"]["members"]["docProps/app.xml"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(WorkbookAcceptanceError, "manifest/hash/surface mismatch"):
            check_manifest(manifest_path)

    def test_formula_and_changed_cached_value_fail(self) -> None:
        book = self.root / FILES["synthetic"]
        def mutation(data: bytes) -> bytes:
            root = ET.fromstring(data)
            cell = root.find(f".//{MAIN}c[@r='A7']")
            assert cell is not None
            cell.attrib.pop("t", None)
            for child in list(cell):
                cell.remove(child)
            ET.SubElement(cell, f"{MAIN}f").text = "1+1"
            ET.SubElement(cell, f"{MAIN}v").text = "999"
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        replace_member(book, "xl/worksheets/sheet4.xml", mutation)
        with self.assertRaisesRegex(Exception, "formula"):
            inspect_book(book, "synthetic")

    def test_hidden_content_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        def mutation(data: bytes) -> bytes:
            root = ET.fromstring(data)
            rows = root.findall(f".//{MAIN}sheetData/{MAIN}row")
            self.assertTrue(rows)
            rows[-1].set("hidden", "1")
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        replace_member(book, "xl/worksheets/sheet4.xml", mutation)
        with self.assertRaisesRegex(WorkbookAcceptanceError, "hidden row"):
            inspect_book(book, "synthetic")

    def test_external_relationship_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        def mutation(data: bytes) -> bytes:
            root = ET.fromstring(data)
            ET.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                          {"Id": "rIdOutside", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                           "Target": "https://example.invalid", "TargetMode": "External"})
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        replace_member(book, "xl/_rels/workbook.xml.rels", mutation)
        with self.assertRaisesRegex(WorkbookAcceptanceError, "external relationship"):
            inspect_book(book, "synthetic")

    def test_metadata_leak_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        replace_member(book, "docProps/core.xml", lambda data: data.replace(b"Alma de Lujo", b"private@example.com"))
        with self.assertRaisesRegex(WorkbookAcceptanceError, "metadata leak"):
            inspect_book(book, "synthetic")

    def test_formula_injection_in_source_cell_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        def mutation(data: bytes) -> bytes:
            root = ET.fromstring(data)
            cell = root.find(f".//{MAIN}c[@r='A7']")
            assert cell is not None
            cell.set("t", "inlineStr")
            for child in list(cell):
                cell.remove(child)
            ET.SubElement(ET.SubElement(cell, f"{MAIN}is"), f"{MAIN}t").text = "=HYPERLINK(\"https://example.invalid\")"
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        replace_member(book, "xl/worksheets/sheet4.xml", mutation)
        with self.assertRaisesRegex(Exception, "formula injection|workbook.value"):
            inspect_book(book, "synthetic")

    def test_unexpected_active_part_fails(self) -> None:
        book = self.root / FILES["synthetic"]
        with zipfile.ZipFile(book, "a") as archive:
            archive.writestr("xl/vbaProject.bin", b"not a macro")
        with self.assertRaisesRegex(WorkbookAcceptanceError, "active XLSX part"):
            inspect_book(book, "synthetic")


if __name__ == "__main__":
    unittest.main()
