"""Private operating-cut verification, export, and restore tests."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from alma.operating_archive import export_cut, verify_cut
from alma.operating_contracts import SOURCE_NAMES, OperatingContractError, canonical_json
from alma.operating_workspace import build_operating_workspace, relationship_summary


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
EXPECTED_MEMBERS = {
    "metadata.json",
    "workspace.json",
    "operating.sqlite3",
    *(f"{source}.csv" for source in SOURCE_NAMES),
}


def file_bytes(path: Path) -> dict[str, bytes]:
    return {child.name: child.read_bytes() for child in path.iterdir() if child.is_file()}


class OperatingArchiveFixture(unittest.TestCase):
    SCRIPT = ROOT / "scripts" / "operating_archive.py"

    def build(self, root: Path) -> tuple[dict[str, object], Path]:
        result = build_operating_workspace(SYNTHETIC_PACK, private_root=root)
        return result, Path(str(result["destination"]))

    def assert_error(self, code: str, callback) -> OperatingContractError:
        with self.assertRaises(OperatingContractError) as raised:
            callback()
        self.assertEqual(code, raised.exception.code)
        self.assertTrue(raised.exception.location)
        return raised.exception


class OperatingVerifyExportTests(OperatingArchiveFixture):
    def test_clean_cut_verifies_every_source_database_and_relationship(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            built, cut = self.build(root)
            result = verify_cut(cut, private_root=root)

            self.assertEqual("PASS", result["status"])
            self.assertEqual(built["cut_id"], result["cut_id"])
            self.assertEqual(len(EXPECTED_MEMBERS), result["checked_files"])
            self.assertEqual([], result["issues"])
            self.assertNotIn("source_sha256", result)
            self.assertNotIn("sqlite_sha256", result)

    def test_source_metadata_manifest_and_database_tamper_fail_before_export(self) -> None:
        cases = {
            "source": ("sku_catalog.csv", b"\n", "verify.source_hash"),
            "metadata": ("metadata.json", b" ", "verify.metadata_hash"),
            "manifest": ("workspace.json", b" ", "verify.manifest_canonical"),
            "database": ("operating.sqlite3", b"x", "verify.sqlite_hash"),
        }
        for case, (name, suffix, code) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, cut = self.build(root)
                target = cut / name
                target.write_bytes(target.read_bytes() + suffix)
                self.assert_error(code, lambda: verify_cut(cut, private_root=root))
                output = root / "operating-exports" / f"{case}.zip"
                self.assert_error(code, lambda: export_cut(cut, output, private_root=root))
                self.assertFalse(output.exists())

    def test_relationship_change_fails_even_when_counts_and_manifest_sqlite_hash_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, cut = self.build(root)
            database = cut / "operating.sqlite3"
            connection = sqlite3.connect(database)
            try:
                connection.execute("PRAGMA foreign_keys=OFF")
                connection.execute(
                    "UPDATE cash_events SET supersedes_event_id=NULL "
                    "WHERE supersedes_event_id IS NOT NULL"
                )
                connection.commit()
                changed = relationship_summary(connection)
            finally:
                connection.close()

            manifest_path = cut / "workspace.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["sqlite_sha256"] = hashlib.sha256(database.read_bytes()).hexdigest()
            # Keep counts equal and even record the altered relationship digest. Source rows
            # remain authoritative, so database/source divergence must still fail closed.
            manifest["relationship_check"]["digest"] = changed["digest"]
            manifest_path.write_bytes(canonical_json(manifest) + b"\n")
            self.assert_error("verify.database_rows", lambda: verify_cut(cut, private_root=root))

    def test_export_is_deterministic_exact_private_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            built, cut = self.build(root)
            before = file_bytes(cut)
            first = root / "operating-exports" / "first.zip"
            second = root / "operating-exports" / "second.zip"

            receipt_one = export_cut(cut, first, private_root=root)
            receipt_two = export_cut(cut, second, private_root=root)
            self.assertEqual("PASS", receipt_one["status"])
            self.assertEqual(built["cut_id"], receipt_one["cut_id"])
            self.assertEqual(receipt_one["archive_sha256"], receipt_two["archive_sha256"])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(before, file_bytes(cut))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(sorted(EXPECTED_MEMBERS), archive.namelist())
                self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))

            outside = root.parent / "public-export.zip"
            self.assert_error(
                "path.private_root",
                lambda: export_cut(cut, outside, private_root=root),
            )
            self.assertFalse(outside.exists())
            self.assert_error(
                "archive.exists",
                lambda: export_cut(cut, first, private_root=root),
            )

    def test_verify_and_export_cli_emit_safe_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, cut = self.build(root)
            archive = root / "operating-exports" / "cut.zip"
            verify = subprocess.run(
                [sys.executable, str(self.SCRIPT), "verify", "--cut", str(cut), "--private-root", str(root)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, verify.returncode, verify.stderr)
            self.assertEqual("PASS", json.loads(verify.stdout)["status"])
            export = subprocess.run(
                [
                    sys.executable,
                    str(self.SCRIPT),
                    "export",
                    "--cut",
                    str(cut),
                    "--output",
                    str(archive),
                    "--private-root",
                    str(root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, export.returncode, export.stderr)
            receipt = json.loads(export.stdout)
            self.assertEqual("PASS", receipt["status"])
            self.assertEqual(str(archive.resolve()), receipt["archive"])


if __name__ == "__main__":
    unittest.main()
