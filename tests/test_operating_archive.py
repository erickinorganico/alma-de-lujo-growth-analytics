"""Private operating-cut verification, export, and restore tests."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from alma.operating_archive import (
    MAX_COMPRESSION_RATIO,
    MAX_MANIFEST_BYTES,
    export_cut,
    restore_cut,
    verify_cut,
)
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

    def exported(self, root: Path) -> tuple[Path, Path]:
        _, cut = self.build(root)
        archive = root / "operating-exports" / "cut.zip"
        export_cut(cut, archive, private_root=root)
        return cut, archive

    def archive_members(self, archive: Path) -> dict[str, bytes]:
        with zipfile.ZipFile(archive) as source:
            return {info.filename: source.read(info) for info in source.infolist()}

    def write_archive(self, path: Path, members: list[tuple[str | zipfile.ZipInfo, bytes]]) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in members:
                archive.writestr(name, data)


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


class OperatingRestoreTests(OperatingArchiveFixture):
    def test_round_trip_preserves_every_byte_and_identity_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cut, archive = self.exported(root)
            destination = root / "restored-cut"
            receipt = restore_cut(archive, destination, private_root=root)

            self.assertEqual("PASS", receipt["status"])
            self.assertEqual(destination.resolve(), Path(receipt["destination"]))
            self.assertEqual(file_bytes(cut), file_bytes(destination))
            original_manifest = json.loads((cut / "workspace.json").read_text(encoding="utf-8"))
            restored_manifest = json.loads((destination / "workspace.json").read_text(encoding="utf-8"))
            for key in (
                "cut_id",
                "source_sha256",
                "normalized_rows_digest",
                "sqlite_sha256",
                "row_counts",
                "key_counts",
                "relationship_check",
            ):
                self.assertEqual(original_manifest[key], restored_manifest[key])
            self.assertEqual("PASS", verify_cut(destination, private_root=root)["status"])

    def test_restore_rejects_duplicate_unexpected_missing_and_unsafe_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, original = self.exported(root)
            members = self.archive_members(original)
            cases: dict[str, tuple[str, list[tuple[str | zipfile.ZipInfo, bytes]]]] = {
                "duplicate": (
                    "archive.duplicate",
                    [(name, data) for name, data in members.items()] + [("metadata.json", members["metadata.json"])],
                ),
                "unexpected": (
                    "archive.member",
                    [(name, data) for name, data in members.items()] + [("extra.txt", b"x")],
                ),
                "missing": (
                    "archive.members",
                    [(name, data) for name, data in members.items() if name != "metadata.json"],
                ),
                "traversal": (
                    "archive.path",
                    [(name, data) for name, data in members.items()] + [("../escape.txt", b"x")],
                ),
                "absolute": (
                    "archive.path",
                    [(name, data) for name, data in members.items()] + [("/absolute.txt", b"x")],
                ),
            }
            symlink = zipfile.ZipInfo("unsafe-link")
            symlink.create_system = 3
            symlink.external_attr = (0o120777 << 16)
            cases["symlink"] = (
                "archive.symlink",
                [(name, data) for name, data in members.items()] + [(symlink, b"metadata.json")],
            )
            for case, (code, contents) in cases.items():
                with self.subTest(case=case):
                    candidate = root / "operating-exports" / f"{case}.zip"
                    self.write_archive(candidate, contents)
                    destination = root / f"restored-{case}"
                    self.assert_error(code, lambda: restore_cut(candidate, destination, private_root=root))
                    self.assertFalse(destination.exists())

    def test_restore_rejects_oversized_and_high_ratio_members_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, original = self.exported(root)
            members = self.archive_members(original)

            oversized = root / "operating-exports" / "oversized.zip"
            oversized_members = dict(members)
            oversized_members["workspace.json"] = b"x" * (MAX_MANIFEST_BYTES + 1)
            self.write_archive(oversized, list(oversized_members.items()))
            self.assert_error(
                "archive.member_size",
                lambda: restore_cut(oversized, root / "restored-oversized", private_root=root),
            )

            bomb = root / "operating-exports" / "bomb.zip"
            bomb_members = dict(members)
            bomb_members["sku_catalog.csv"] = b"0" * (MAX_COMPRESSION_RATIO * 1000)
            self.write_archive(bomb, list(bomb_members.items()))
            self.assert_error(
                "archive.compression_ratio",
                lambda: restore_cut(bomb, root / "restored-bomb", private_root=root),
            )
            self.assertEqual([], list(root.glob(".restore-*")))

    def test_restore_revalidates_cash_supersession_balance_and_cohort_gates(self) -> None:
        def cash_bytes(raw: bytes, mutation: str) -> bytes:
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
            if mutation == "self":
                rows[1]["supersedes_event_id"] = rows[1]["event_id"]
            elif mutation == "cycle":
                rows[0]["supersedes_event_id"] = rows[1]["event_id"]
            elif mutation == "double_count":
                rows[1]["supersedes_event_id"] = ""
            elif mutation == "fork":
                fork = dict(rows[1])
                fork["event_id"] = "synthetic:cash-actual-fork"
                fork["payment_id"] = ""
                rows.append(fork)
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=rows[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue().encode("utf-8")

        cases = {
            "self": ("cash_events.csv", "cash.supersedes_self"),
            "cycle": ("cash_events.csv", "cash.supersedes_cycle"),
            "fork": ("cash_events.csv", "key.duplicate"),
            "double_count": ("cash_events.csv", "cash.supersedes_chain"),
            "balance": ("cash_balance_evidence.csv", "cash.balance"),
        }
        for case, (filename, code) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, original = self.exported(root)
                members = self.archive_members(original)
                if filename == "cash_events.csv":
                    members[filename] = cash_bytes(members[filename], case)
                else:
                    members[filename] = members[filename].replace(b",1100000,", b",1100001,")
                manifest = json.loads(members["workspace.json"].decode("utf-8"))
                manifest["source_sha256"][filename] = hashlib.sha256(members[filename]).hexdigest()
                members["workspace.json"] = canonical_json(manifest) + b"\n"
                candidate = root / "operating-exports" / f"{case}.zip"
                self.write_archive(candidate, list(members.items()))
                destination = root / f"restored-{case}"
                self.assert_error(code, lambda: restore_cut(candidate, destination, private_root=root))
                self.assertFalse(destination.exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, original = self.exported(root)
            members = self.archive_members(original)
            metadata = json.loads(members["metadata.json"].decode("utf-8"))
            metadata["coverage"]["quality_events"]["status"] = "COMPLETE"
            members["metadata.json"] = canonical_json(metadata) + b"\n"
            quality = members["quality_events.csv"].decode("utf-8").replace(
                "synthetic:cohort-001,2026-09-19,RETURN_REPORTED",
                ",2026-09-19,RETURN_REPORTED",
            ).encode("utf-8")
            members["quality_events.csv"] = quality
            manifest = json.loads(members["workspace.json"].decode("utf-8"))
            manifest["metadata_sha256"] = hashlib.sha256(members["metadata.json"]).hexdigest()
            manifest["source_sha256"]["quality_events.csv"] = hashlib.sha256(quality).hexdigest()
            members["workspace.json"] = canonical_json(manifest) + b"\n"
            candidate = root / "operating-exports" / "cohort.zip"
            self.write_archive(candidate, list(members.items()))
            self.assert_error(
                "quality.cohort_required",
                lambda: restore_cut(candidate, root / "restored-cohort", private_root=root),
            )

    def test_existing_or_outside_destination_fails_without_changing_prior_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, archive = self.exported(root)
            destination = root / "existing"
            destination.mkdir()
            marker = destination / "marker.txt"
            marker.write_bytes(b"prior")
            self.assert_error(
                "archive.destination_exists",
                lambda: restore_cut(archive, destination, private_root=root),
            )
            self.assertEqual(b"prior", marker.read_bytes())
            outside = root.parent / "outside-restored-cut"
            self.assert_error(
                "path.private_root",
                lambda: restore_cut(archive, outside, private_root=root),
            )
            self.assertFalse(outside.exists())
            self.assertEqual([], list(root.glob(".restore-*")))

    def test_restore_cli_documents_and_runs_all_three_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, archive = self.exported(root)
            destination = root / "cli-restored"
            help_result = subprocess.run(
                [sys.executable, str(self.SCRIPT), "--help"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, help_result.returncode)
            for command in ("verify", "export", "restore"):
                self.assertIn(command, help_result.stdout)
            restored = subprocess.run(
                [
                    sys.executable,
                    str(self.SCRIPT),
                    "restore",
                    "--archive",
                    str(archive),
                    "--destination",
                    str(destination),
                    "--private-root",
                    str(root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, restored.returncode, restored.stderr)
            self.assertEqual("PASS", json.loads(restored.stdout)["status"])
            self.assertTrue(destination.is_dir())


if __name__ == "__main__":
    unittest.main()
