"""Adversarial acceptance checks for the exact operating-v1 delivery pair."""
from __future__ import annotations

import json
import hashlib
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from alma.operating_contracts import SOURCE_NAMES, SOURCES
from alma.operating_workbook import WorkbookContractError, _inspect_archive
from scripts.build_operating_workbooks import sanitize_excel_saved_workbook
from scripts.verify_operating_workbooks import (
    FILES, WorkbookAcceptanceError, check_manifest, check_receipts, inspect_book, normalized,
)

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "client/v1"
EXCEL_EVIDENCE = ROOT / "evidence/v1.0/excel"
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

    def test_final_excel_and_page_receipts_are_complete(self) -> None:
        manifest = check_manifest(DELIVERY / "workbook-manifest.json")
        self.assertEqual("FINAL_EXCEL", manifest["stage"])
        self.assertEqual({"workbooks": 2, "pdfs": 50, "pages": 62}, check_receipts(
            manifest, EXCEL_EVIDENCE / "excel-recalculation.json",
            EXCEL_EVIDENCE / "visual-inspection.json"))

    def test_final_receipt_negative_controls(self) -> None:
        manifest = check_manifest(DELIVERY / "workbook-manifest.json")
        root = self.root / "excel"
        shutil.copytree(EXCEL_EVIDENCE, root)
        excel = root / "excel-recalculation.json"
        visual = root / "visual-inspection.json"
        self.assertEqual(62, check_receipts(manifest, excel, visual)["pages"])
        with self.assertRaisesRegex(WorkbookAcceptanceError, "required"):
            check_receipts(manifest, None, visual)
        original = json.loads(visual.read_text(encoding="utf-8"))
        cases = (
            (lambda data: data["pages"].pop(), "visual page count"),
            (lambda data: data["pages"].__setitem__(1, data["pages"][0]), "missing/duplicate"),
            (lambda data: data.__setitem__("excel_receipt_sha256", "0" * 64), "stale visual/Excel receipt"),
            (lambda data: data["pages"][0].__setitem__("png_sha256", "0" * 64), "PNG missing/hash"),
            (lambda data: data["pages"][0].__setitem__("inspected", False), "uninspected"),
        )
        for mutate, error in cases:
            altered = json.loads(json.dumps(original))
            mutate(altered)
            visual.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(WorkbookAcceptanceError, error):
                check_receipts(manifest, excel, visual)
        visual.write_text(json.dumps(original), encoding="utf-8")
        missing_png = root / original["pages"][0]["png"]
        missing_png.unlink()
        with self.assertRaisesRegex(WorkbookAcceptanceError, "PNG missing/hash"):
            check_receipts(manifest, excel, visual)
        shutil.copyfile(EXCEL_EVIDENCE / original["pages"][0]["png"], missing_png)
        (root / "unlisted.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(WorkbookAcceptanceError, "unexpected/missing Excel evidence"):
            check_receipts(manifest, excel, visual)

    def test_post_excel_sanitization_delta_proof_is_fail_closed(self) -> None:
        manifest = check_manifest(DELIVERY / "workbook-manifest.json")
        root = self.root / "sanitization"
        shutil.copytree(EXCEL_EVIDENCE, root)
        excel = root / "excel-recalculation.json"
        visual = root / "visual-inspection.json"
        receipt = json.loads(excel.read_text(encoding="utf-8"))
        receipt["workbooks"][0]["post_excel_sanitization"]["members_sha256_before"]["docProps/core.xml"] = "0" * 64
        excel.write_text(json.dumps(receipt), encoding="utf-8")
        visual_receipt = json.loads(visual.read_text(encoding="utf-8"))
        visual_receipt["excel_receipt_sha256"] = hashlib.sha256(excel.read_bytes()).hexdigest()
        visual.write_text(json.dumps(visual_receipt), encoding="utf-8")
        with self.assertRaisesRegex(WorkbookAcceptanceError, "unexpected post-Excel member changed"):
            check_receipts(manifest, excel, visual)

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

    def test_absolute_path_metadata_fails_closed(self) -> None:
        book = self.root / FILES["synthetic"]
        private_path = b'C:\\Users\\erick\\OneDrive\\private.xlsx'
        replace_member(book, "xl/workbook.xml", lambda data: data.replace(
            b"</workbook>", b'<x15ac:absPath url="' + private_path + b'"/></workbook>'))
        with self.assertRaisesRegex(WorkbookAcceptanceError, "absolute path privacy leak"):
            inspect_book(book, "synthetic")
        with self.assertRaisesRegex(WorkbookContractError, "workbook.absolute_path"):
            _inspect_archive(book)

    def test_excel_sanitizer_returns_receipt_proof_for_next_recalculation(self) -> None:
        book = self.root / FILES["synthetic"]
        replace_member(book, "xl/workbook.xml", lambda data: data.replace(
            b"</workbook>",
            b'<x15ac:absPath xmlns:x15ac="http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac" '
            b'url="C:\\\\Users\\\\erick\\\\private\\\\client\\\\v1\\\\"/></workbook>'))
        replace_member(book, "docProps/core.xml", lambda data: data.replace(
            b"<cp:lastModifiedBy>Alma de Lujo</cp:lastModifiedBy>",
            b"<cp:lastModifiedBy>Local User</cp:lastModifiedBy>"))

        proof = sanitize_excel_saved_workbook(book)

        self.assertEqual("remove-x15ac-absPath-only-v1", proof["contract"])
        self.assertEqual(["xl/workbook.xml"], proof["changed_members"])
        self.assertEqual(1, proof["removed_abs_path_elements"])
        self.assertNotEqual(proof["pre_sanitization_sha256"], proof["final_sha256"])
        self.assertEqual(proof["final_sha256"], __import__("hashlib").sha256(book.read_bytes()).hexdigest())
        self.assertEqual(proof["members_sha256_before"]["docProps/core.xml"],
                         proof["members_sha256_after"]["docProps/core.xml"])
        self.assertEqual(proof["members_sha256_after"]["xl/workbook.xml"],
                         proof["normalized_workbook_xml_sha256"])
        self.assertEqual("Alma de Lujo", __import__("openpyxl").load_workbook(book).properties.lastModifiedBy)
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
