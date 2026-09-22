"""CLI artifact, output-ownership, receipt, and roundtrip integration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from alma.__main__ import build
from alma.fixtures import generate
from alma.storage import import_csv, load_sqlite


EXPECTED_REPORTS = {
    "report.md",
    "report.html",
    "charts/monthly_finance.svg",
    "charts/color_stock.svg",
    "charts/cash_bridge.svg",
}


class CliArtifactIntegrationTests(unittest.TestCase):
    def test_build_rejects_unowned_existing_directory_and_preserves_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "user-files"
            target.mkdir()
            protected = target / "keep.txt"
            protected.write_text("user content", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not an Alma generated folder"):
                build(target)
            self.assertEqual("user content", protected.read_text(encoding="utf-8"))
            self.assertEqual({"keep.txt"}, {path.name for path in target.iterdir()})

    def test_build_writes_reports_roundtrips_and_receipt_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo"
            report = build(output)
            self.assertEqual("PASS", report["meta"]["status"])
            self.assertEqual("alma-generated-v1", (output / ".alma-generated").read_text(encoding="utf-8"))

            base = {"data.json", "report.json", "decisions.json", "quality.json", "receipt.json", "alma.sqlite3"}
            self.assertTrue(all((output / name).is_file() for name in base | EXPECTED_REPORTS))
            self.assertEqual(generate(), import_csv(output / "csv"))
            self.assertEqual(generate(), load_sqlite(output / "alma.sqlite3"))

            receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
            self.assertTrue(receipt["synthetic"])
            self.assertEqual("PASS", receipt["status"])
            self.assertTrue(EXPECTED_REPORTS <= set(receipt["sha256"]))
            for relative, expected_hash in receipt["sha256"].items():
                with self.subTest(relative=relative):
                    artifact = output / relative
                    self.assertTrue(artifact.is_file())
                    self.assertEqual(expected_hash, hashlib.sha256(artifact.read_bytes()).hexdigest())

            markdown = (output / "report.md").read_text(encoding="utf-8")
            html = (output / "report.html").read_text(encoding="utf-8")
            self.assertIn("DATOS SINTÉTICOS", markdown)
            self.assertIn("DATOS SINTÉTICOS", html)
            self.assertNotIn("<script", html.lower())
            self.assertIsNone(re.search(r'''<(?:img|script|link|iframe|object|embed|source)\b[^>]*\b(?:src|href|data)\s*=\s*["']https?://''', html, re.IGNORECASE))
            self.assertIsNone(re.search(r"<link\b[^>]*\brel\s*=\s*['\"]?stylesheet", html, re.IGNORECASE))

    def test_normal_and_red_scenarios_use_separate_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            normal = root / "normal"
            red = root / "missing-cost"
            normal_report = build(normal)
            normal_hash = hashlib.sha256((normal / "report.json").read_bytes()).hexdigest()
            red_report = build(red, scenario="missing_cost")
            self.assertEqual("PASS", normal_report["meta"]["status"])
            self.assertEqual("BLOCKED", red_report["meta"]["status"])
            self.assertEqual(normal_hash, hashlib.sha256((normal / "report.json").read_bytes()).hexdigest())
            self.assertEqual("normal", json.loads((normal / "receipt.json").read_text(encoding="utf-8"))["scenario"])
            self.assertEqual("missing_cost", json.loads((red / "receipt.json").read_text(encoding="utf-8"))["scenario"])


if __name__ == "__main__":
    unittest.main()
