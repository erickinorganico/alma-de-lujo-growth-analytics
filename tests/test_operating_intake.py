"""Strict operating-v1 intake and immutable workspace tests."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from alma.operating_contracts import SOURCE_NAMES, OperatingContractError, columns_for
from alma.operating_interchange import MAX_CSV_BYTES, parse_pack
from alma.operating_workspace import build_operating_workspace, relationship_summary


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"


class PackFixture:
    def __init__(self, root: Path) -> None:
        self.path = root / "pack"
        shutil.copytree(SYNTHETIC_PACK, self.path)

    def metadata(self) -> dict[str, Any]:
        return json.loads((self.path / "metadata.json").read_text(encoding="utf-8"))

    def write_metadata(self, value: dict[str, Any]) -> None:
        (self.path / "metadata.json").write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="",
        )

    def rows(self, source: str) -> list[dict[str, str]]:
        with (self.path / f"{source}.csv").open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def write_rows(
        self,
        source: str,
        rows: list[dict[str, Any]],
        *,
        header: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        fields = list(header or columns_for(source))
        with (self.path / f"{source}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


class OperatingParserTests(unittest.TestCase):
    def test_future_cash_projection_dates_preserve_cutoff(self) -> None:
        for level in ("EXPECTED", "COMMITTED", "SCENARIO"):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                events = fixture.rows("cash_events")
                projection = dict(events[0], event_id=f"synthetic:future-{level.lower()}",
                    economic_event_id=f"synthetic:economic-future-{level.lower()}",
                    supersedes_event_id="", event_date="2026-09-22", level=level,
                    amount_cents="13", payment_id="", source_ref=f"synthetic:future-source-{level.lower()}",
                    obligation_id="synthetic:obligation-expense-001" if level == "COMMITTED" else "")
                fixture.write_rows("cash_events", [*events, projection])
                parsed = parse_pack(fixture.path)
                future = parsed["tables"]["cash_events"][-1]
                self.assertEqual(date(2026, 9, 22), future["event_date"])
                self.assertEqual((level, projection["economic_event_id"], projection["source_ref"]),
                    (future["level"], future["economic_event_id"], future["source_ref"]))
                raw_hash = hashlib.sha256((fixture.path / "cash_events.csv").read_bytes()).hexdigest()
                self.assertEqual(raw_hash, parsed["source_sha256"]["cash_events.csv"])
                built = build_operating_workspace(fixture.path, private_root=Path(tmp) / "cuts")
                self.assertEqual(raw_hash, built["manifest"]["source_sha256"]["cash_events.csv"])
                self.assertEqual("2026-09-21T23:59:59-07:00", built["manifest"]["cutoff_at"])
                connection = sqlite3.connect(Path(built["destination"]) / "operating.sqlite3")
                try:
                    stored = connection.execute("SELECT event_date,level,economic_event_id,source_ref FROM cash_events WHERE event_id=?",
                                                (projection["event_id"],)).fetchone()
                    self.assertEqual(("2026-09-22", level, projection["economic_event_id"], projection["source_ref"]), stored)
                finally:
                    connection.close()
                projection["amount_cents"] = "14"
                fixture.write_rows("cash_events", [*events, projection])
                changed = build_operating_workspace(fixture.path, private_root=Path(tmp) / "changed-cuts")
                self.assertNotEqual(built["cut_id"], changed["cut_id"])
                self.assertNotEqual(raw_hash, changed["manifest"]["source_sha256"]["cash_events.csv"])
                self.assertEqual(built["manifest"]["cutoff_at"], changed["manifest"]["cutoff_at"])
                self.assertEqual(built["manifest"]["coverage"], changed["manifest"]["coverage"])

    def test_future_observations_still_rejected(self) -> None:
        for source, field in (("cash_events", "event_date"), ("sales_aggregates", "sales_date"),
                              ("inventory_movements", "event_date"), ("quality_events", "event_date")):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                values = fixture.rows(source)
                values[-1][field] = "2026-09-22"
                fixture.write_rows(source, values)
                error = self.assert_parse_error(fixture, "value.after_cutoff")
                self.assertIn(f"{source}.csv", error.location)
        for invalid_level in ("INVALID", ""):
            with self.subTest(level=invalid_level), tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                values = fixture.rows("cash_events")
                values[-1]["event_date"] = "2026-09-22"
                values[-1]["level"] = invalid_level
                fixture.write_rows("cash_events", values)
                self.assert_parse_error(fixture, "value.enum" if invalid_level else "value.required")
        for name, changes, code in (
            ("malformed_date", {"event_date": "2026-13-22"}, "value.date"),
            ("missing_committed_origin", {"level": "COMMITTED", "obligation_id": ""}, "cash.committed_origin"),
            ("invalid_supersession", {"supersedes_event_id": "synthetic:absent-event"}, "cash.supersedes_orphan"),
            ("duplicate_identity", {"economic_event_id": "synthetic:economic-po-payment-001"}, "cash.supersedes_chain"),
            ("future_observed", {"level": "RECONCILED"}, "value.after_cutoff"),
        ):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                values = fixture.rows("cash_events")
                candidate = dict(values[0], event_id=f"synthetic:cash-future-{name}",
                    economic_event_id=f"synthetic:economic-future-{name}",
                    supersedes_event_id="", event_date="2026-09-22", level="EXPECTED",
                    amount_cents="13", obligation_id="", payment_id="",
                    source_ref=f"synthetic:source:future-{name}")
                candidate.update(changes)
                fixture.write_rows("cash_events", [*values, candidate])
                self.assert_parse_error(fixture, code)

    def fixture(self, tmp: str) -> PackFixture:
        return PackFixture(Path(tmp))

    def assert_parse_error(
        self,
        fixture: PackFixture,
        expected_code: str,
        *,
        private_root: Path | None = None,
        private_value: str | None = None,
    ) -> OperatingContractError:
        with self.assertRaises(OperatingContractError) as raised:
            parse_pack(fixture.path, private_root=private_root)
        self.assertEqual(expected_code, raised.exception.code)
        self.assertTrue(raised.exception.location)
        if private_value is not None:
            self.assertNotIn(private_value, str(raised.exception))
        return raised.exception

    def test_exact_synthetic_pack_parses_typed_rows_and_raw_hashes(self) -> None:
        parsed = parse_pack(SYNTHETIC_PACK)
        self.assertEqual(tuple(SOURCE_NAMES), tuple(parsed["tables"]))
        self.assertEqual({f"{name}.csv" for name in SOURCE_NAMES}, set(parsed["source_sha256"]))
        self.assertEqual([], parsed["diagnostics"])
        self.assertEqual("PARTIAL", parsed["metadata"]["coverage"]["availability_daily"]["status"])
        self.assertEqual(0, parsed["tables"]["purchase_receipts"][0]["rejected_units"])
        self.assertIsNone(parsed["tables"]["loans"][0]["returned_date"])
        self.assertIsInstance(parsed["tables"]["purchase_orders"][0]["ordered_units"], int)
        self.assertIsInstance(parsed["tables"]["purchase_orders"][0]["order_date"], date)
        self.assertIsInstance(parsed["tables"]["cash_balance_evidence"][0]["opening_observed_at"], datetime)
        receipt = parsed["tables"]["purchase_receipts"][0]
        self.assertEqual((18, 2, 16, 0), tuple(receipt[key] for key in ("received_units", "inspection_units", "accepted_units", "rejected_units")))

    def test_zero_missing_partial_and_null_remain_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            metadata = fixture.metadata()
            metadata["coverage"]["sales_readiness"] = {
                "status": "ZERO",
                "window_start": "2026-09-01",
                "window_end": "2026-09-21",
            }
            metadata["coverage"]["unmet_demand"] = {
                "status": "MISSING",
                "window_start": None,
                "window_end": None,
            }
            fixture.write_metadata(metadata)
            fixture.write_rows("sales_readiness", [])
            fixture.write_rows("unmet_demand", [])
            parsed = parse_pack(fixture.path)
            self.assertEqual("ZERO", parsed["metadata"]["coverage"]["sales_readiness"]["status"])
            self.assertEqual("MISSING", parsed["metadata"]["coverage"]["unmet_demand"]["status"])
            self.assertEqual([], parsed["tables"]["sales_readiness"])
            self.assertEqual([], parsed["tables"]["unmet_demand"])
            self.assertIsNone(parsed["tables"]["loans"][0]["returned_date"])
            self.assertEqual(0, parsed["tables"]["purchase_receipts"][0]["rejected_units"])

    def test_private_pack_must_resolve_inside_authorized_private_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = self.fixture(tmp)
            metadata = fixture.metadata()
            metadata["input_class"] = "PRIVATE"
            fixture.write_metadata(metadata)
            self.assert_parse_error(fixture, "path.private_root", private_root=root / "private")
            private_root = root / "private"
            private_root.mkdir()
            private_pack = private_root / "pack"
            shutil.move(str(fixture.path), private_pack)
            parsed = parse_pack(private_pack, private_root=private_root)
            self.assertEqual("PRIVATE", parsed["metadata"]["input_class"])

    def test_metadata_file_set_and_size_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            metadata = fixture.metadata()
            metadata["contract_version"] = "wrong"
            fixture.write_metadata(metadata)
            self.assert_parse_error(fixture, "metadata.contract_version")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            (fixture.path / "unexpected.txt").write_text("hidden", encoding="utf-8")
            self.assert_parse_error(fixture, "pack.files")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            with (fixture.path / "unmet_demand.csv").open("wb") as stream:
                stream.truncate(MAX_CSV_BYTES + 1)
            self.assert_parse_error(fixture, "csv.size")

    def test_header_shape_ragged_and_required_blank_fail_safely(self) -> None:
        header_mutations: list[tuple[str, Callable[[list[str]], list[str]]]] = [
            ("csv.header_order", lambda header: [header[1], header[0], *header[2:]]),
            ("csv.header_duplicate", lambda header: [header[0], header[0], *header[2:]]),
            ("csv.header", lambda header: [*header, "extra_code"]),
            ("csv.header", lambda header: [*header, "customer_name"]),
        ]
        for expected_code, mutate in header_mutations:
            with tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                rows = fixture.rows("sku_catalog")
                fixture.write_rows("sku_catalog", rows, header=mutate(list(columns_for("sku_catalog"))))
                with self.subTest(code=expected_code):
                    self.assert_parse_error(fixture, expected_code)

        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            path = fixture.path / "sku_catalog.csv"
            with path.open("a", encoding="utf-8", newline="") as stream:
                stream.write("too,few,columns\n")
            self.assert_parse_error(fixture, "csv.ragged")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            rows = fixture.rows("sku_catalog")
            rows[0]["sku_id"] = ""
            fixture.write_rows("sku_catalog", rows)
            self.assert_parse_error(fixture, "value.required")

    def test_invalid_date_integer_enum_and_pii_like_value_fail_safely(self) -> None:
        cases: list[tuple[str, str, str, str, str]] = [
            ("sku_catalog", "effective_date", "2026-02-30", "value.date", "2026-02-30"),
            ("purchase_orders", "ordered_units", "2.5", "value.integer", "2.5"),
            ("purchase_orders", "status_code", "UNKNOWN", "value.enum", "UNKNOWN"),
            ("sku_catalog", "product_code", "Alice Smith", "value.token", "Alice Smith"),
            ("loans", "recipient_ref", "5551234567", "value.pii", "5551234567"),
        ]
        for source, column, value, code, secret in cases:
            with tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                rows = fixture.rows(source)
                rows[0][column] = value
                fixture.write_rows(source, rows)
                with self.subTest(source=source, column=column):
                    self.assert_parse_error(fixture, code, private_value=secret)

    def test_duplicate_primary_composite_and_nullable_unique_keys_fail(self) -> None:
        cases = ["sku_catalog", "sales_aggregates"]
        for source in cases:
            with tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                rows = fixture.rows(source)
                rows.append(dict(rows[0]))
                fixture.write_rows(source, rows)
                with self.subTest(source=source):
                    self.assert_parse_error(fixture, "key.duplicate")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(tmp)
            rows = fixture.rows("cash_events")
            fork = dict(rows[1])
            fork["event_id"] = "synthetic:cash-fork-001"
            fixture.write_rows("cash_events", [*rows, fork])
            self.assert_parse_error(fixture, "key.duplicate")

    def test_broken_source_relationships_and_business_controls_fail(self) -> None:
        def set_value(source: str, column: str, value: str) -> Callable[[PackFixture], None]:
            def mutate(fixture: PackFixture) -> None:
                rows = fixture.rows(source)
                rows[0][column] = value
                fixture.write_rows(source, rows)
            return mutate

        def duplicate_receipt_movement(fixture: PackFixture) -> None:
            rows = fixture.rows("inventory_movements")
            receipt = next(row for row in rows if row["movement_type"] == "RECEIPT_ACCEPTED")
            duplicate = dict(receipt)
            duplicate["movement_id"] = "synthetic:movement-receipt-duplicate"
            rows.append(duplicate)
            fixture.write_rows("inventory_movements", rows)

        def negative_reservation(fixture: PackFixture) -> None:
            rows = fixture.rows("inventory_reservations")
            rows[0]["event_type"] = "RELEASE"
            fixture.write_rows("inventory_reservations", rows)

        def remove_receipt_movement(fixture: PackFixture) -> None:
            rows = [
                row for row in fixture.rows("inventory_movements")
                if row["movement_type"] != "RECEIPT_ACCEPTED"
            ]
            fixture.write_rows("inventory_movements", rows)

        controls: list[tuple[str, Callable[[PackFixture], None], str]] = [
            ("relation.sku", set_value("availability_daily", "sku_id", "synthetic:missing-sku"), "synthetic:missing-sku"),
            ("relation.receipt", set_value("inventory_movements", "receipt_id", "synthetic:missing-receipt"), "synthetic:missing-receipt"),
            ("relation.obligation", set_value("cash_events", "obligation_id", "synthetic:missing-obligation"), "synthetic:missing-obligation"),
            ("relation.payment", set_value("cash_events", "payment_id", "synthetic:missing-payment"), "synthetic:missing-payment"),
            ("relation.origin", set_value("budget_allocations", "origin_id", "synthetic:missing-origin"), "synthetic:missing-origin"),
            ("stock.duplicate_post", duplicate_receipt_movement, "synthetic:movement-receipt-duplicate"),
            ("stock.missing_post", remove_receipt_movement, "synthetic:receipt-001"),
            ("reservation.negative", negative_reservation, "RELEASE"),
            ("availability.minutes", set_value("availability_daily", "observed_minutes", "1441"), "1441"),
            ("relation.demand_sku", set_value("unmet_demand", "sku_id", "synthetic:missing-demand-sku"), "synthetic:missing-demand-sku"),
            ("cash.balance", set_value("cash_balance_evidence", "closing_balance_cents", "1100001"), "1100001"),
            ("relation.cohort", set_value("quality_events", "delivery_cohort_id", "synthetic:missing-cohort"), "synthetic:missing-cohort"),
        ]
        for expected_code, mutate, secret in controls:
            with tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                mutate(fixture)
                with self.subTest(code=expected_code):
                    self.assert_parse_error(fixture, expected_code, private_value=secret)

    def test_cash_supersession_orphan_self_cycle_fork_and_cross_identity_fail(self) -> None:
        def mutate_cash(fixture: PackFixture, case: str) -> None:
            rows = fixture.rows("cash_events")
            forecast, actual = rows
            if case == "orphan":
                actual["supersedes_event_id"] = "synthetic:missing-event"
            elif case == "self":
                actual["supersedes_event_id"] = actual["event_id"]
            elif case == "cycle":
                forecast["supersedes_event_id"] = actual["event_id"]
            elif case == "fork":
                fork = dict(actual)
                fork["event_id"] = "synthetic:cash-fork-001"
                rows.append(fork)
            elif case == "cross_identity":
                actual["economic_event_id"] = "synthetic:other-economic-event"
            elif case == "origin_change":
                actual["obligation_id"] = "synthetic:obligation-expense-001"
                actual["payment_id"] = ""
            fixture.write_rows("cash_events", rows)

        expected = {
            "orphan": "cash.supersedes_orphan",
            "self": "cash.supersedes_self",
            "cycle": "cash.supersedes_cycle",
            "fork": "key.duplicate",
            "cross_identity": "cash.supersedes_identity",
            "origin_change": "cash.supersedes_origin",
        }
        for case, code in expected.items():
            with tempfile.TemporaryDirectory() as tmp:
                fixture = self.fixture(tmp)
                mutate_cash(fixture, case)
                with self.subTest(case=case):
                    self.assert_parse_error(fixture, code)


class OperatingWorkspaceTests(unittest.TestCase):
    SCRIPT = ROOT / "scripts" / "operating_build.py"

    def test_build_publishes_exact_strict_source_workspace_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_operating_workspace(SYNTHETIC_PACK, private_root=root)
            destination = Path(result["destination"])
            self.assertEqual(root / "operating-cuts" / result["cut_id"], destination)
            self.assertTrue((destination / "operating.sqlite3").is_file())
            self.assertTrue((destination / "workspace.json").is_file())
            self.assertEqual(
                {"workspace.json", "operating.sqlite3", "metadata.json", *(f"{name}.csv" for name in SOURCE_NAMES)},
                {path.name for path in destination.iterdir()},
            )
            manifest = json.loads((destination / "workspace.json").read_text(encoding="utf-8"))
            self.assertEqual(result["cut_id"], manifest["cut_id"])
            self.assertEqual("operating-v1", manifest["contract_version"])
            self.assertEqual("PASS", manifest["quality_status"])
            self.assertEqual(22, len(manifest["row_counts"]))
            self.assertEqual(22, len(manifest["key_counts"]))
            self.assertEqual(
                hashlib.sha256((destination / "operating.sqlite3").read_bytes()).hexdigest(),
                manifest["sqlite_sha256"],
            )
            self.assertEqual(
                hashlib.sha256((destination / "metadata.json").read_bytes()).hexdigest(),
                manifest["metadata_sha256"],
            )
            self.assertEqual("OBSERVED", manifest["cash_evidence_status"])
            self.assertEqual("PASS", manifest["cohort_link_status"])
            self.assertEqual("PASS", manifest["relationship_check"]["status"])

            connection = sqlite3.connect(destination / "operating.sqlite3")
            connection.row_factory = sqlite3.Row
            try:
                tables = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_list")
                    if row["type"] == "table" and not row["name"].startswith("sqlite_")
                }
                self.assertEqual(set(SOURCE_NAMES), tables)
                strict = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_list")
                    if row["type"] == "table" and row["strict"] == 1
                }
                self.assertEqual(set(SOURCE_NAMES), strict)
                self.assertEqual([], list(connection.execute("PRAGMA foreign_key_check")))
                self.assertNotIn("orders", tables)
                self.assertNotIn("customers", tables)
                self.assertNotIn("sales_daily", tables)
                chain = list(connection.execute(
                    "SELECT event_id,economic_event_id,supersedes_event_id FROM cash_events ORDER BY event_id"
                ))
                self.assertEqual(2, len(chain))
                self.assertEqual(1, sum(row["supersedes_event_id"] is not None for row in chain))
                summary = relationship_summary(connection)
                self.assertEqual(manifest["relationship_check"]["digest"], summary["digest"])
                self.assertEqual(1, len(summary["cash"]["active_leaf_ids"]))
                self.assertEqual(1, len(summary["cash"]["supersession_edges"]))
            finally:
                connection.close()

    def test_cut_identity_is_stable_and_binds_raw_bytes_cutoff_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_operating_workspace(SYNTHETIC_PACK, private_root=root / "first")
            second = build_operating_workspace(SYNTHETIC_PACK, private_root=root / "second")
            self.assertEqual(first["cut_id"], second["cut_id"])
            self.assertEqual(first["manifest"]["normalized_rows_digest"], second["manifest"]["normalized_rows_digest"])
            self.assertEqual(first["manifest"]["sqlite_sha256"], second["manifest"]["sqlite_sha256"])

            raw_fixture = PackFixture(root / "raw")
            csv_path = raw_fixture.path / "availability_daily.csv"
            csv_path.write_bytes(csv_path.read_bytes().replace(b"\n", b"\r\n"))
            raw = build_operating_workspace(raw_fixture.path, private_root=root / "raw-root")
            self.assertNotEqual(first["cut_id"], raw["cut_id"])
            self.assertEqual(first["manifest"]["normalized_rows_digest"], raw["manifest"]["normalized_rows_digest"])

            cutoff_fixture = PackFixture(root / "cutoff")
            cutoff_meta = cutoff_fixture.metadata()
            cutoff_meta["cutoff_at"] = "2026-09-21T23:59:58-07:00"
            cutoff_fixture.write_metadata(cutoff_meta)
            cutoff = build_operating_workspace(cutoff_fixture.path, private_root=root / "cutoff-root")
            self.assertNotEqual(first["cut_id"], cutoff["cut_id"])

            coverage_fixture = PackFixture(root / "coverage")
            coverage_meta = coverage_fixture.metadata()
            coverage_meta["coverage"]["availability_daily"]["status"] = "ESTIMATED"
            coverage_fixture.write_metadata(coverage_meta)
            coverage = build_operating_workspace(coverage_fixture.path, private_root=root / "coverage-root")
            self.assertNotEqual(first["cut_id"], coverage["cut_id"])

    def test_existing_cut_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_operating_workspace(SYNTHETIC_PACK, private_root=root)
            destination = Path(first["destination"])
            before = {path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()}
            with self.assertRaises(OperatingContractError) as raised:
                build_operating_workspace(SYNTHETIC_PACK, private_root=root)
            self.assertEqual("workspace.exists", raised.exception.code)
            after = {path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()}
            self.assertEqual(before, after)

    def test_distinct_cuts_coexist_under_one_private_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_operating_workspace(SYNTHETIC_PACK, private_root=root)
            fixture = PackFixture(root / "changed")
            metadata = fixture.metadata()
            metadata["coverage"]["availability_daily"]["status"] = "ESTIMATED"
            fixture.write_metadata(metadata)
            second = build_operating_workspace(fixture.path, private_root=root)
            self.assertNotEqual(first["cut_id"], second["cut_id"])
            self.assertTrue(Path(first["destination"]).is_dir())
            self.assertTrue(Path(second["destination"]).is_dir())

    def test_invalid_pack_and_publish_failure_leave_no_cut_or_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = PackFixture(root / "invalid")
            rows = fixture.rows("availability_daily")
            rows[0]["sku_id"] = "synthetic:missing"
            fixture.write_rows("availability_daily", rows)
            with self.assertRaises(OperatingContractError):
                build_operating_workspace(fixture.path, private_root=root / "private-invalid")
            invalid_private = root / "private-invalid"
            self.assertFalse((invalid_private / "operating-cuts").exists())
            self.assertFalse(any(invalid_private.glob(".staging-*")) if invalid_private.exists() else False)

            publish_root = root / "private-publish"
            with mock.patch("alma.operating_workspace.os.replace", side_effect=OSError("synthetic publish failure")):
                with self.assertRaises(OperatingContractError) as raised:
                    build_operating_workspace(SYNTHETIC_PACK, private_root=publish_root)
            self.assertEqual("workspace.publish", raised.exception.code)
            self.assertFalse((publish_root / "operating-cuts").exists())
            self.assertEqual([], list(publish_root.glob(".staging-*")))

    def test_cli_validate_and_build_emit_safe_json_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validate = subprocess.run(
                [sys.executable, str(self.SCRIPT), "validate", "--input", str(SYNTHETIC_PACK)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, validate.returncode, validate.stderr)
            validate_receipt = json.loads(validate.stdout)
            self.assertEqual("PASS", validate_receipt["status"])
            self.assertEqual(22, validate_receipt["sources"])

            build = subprocess.run(
                [
                    sys.executable,
                    str(self.SCRIPT),
                    "build",
                    "--input",
                    str(SYNTHETIC_PACK),
                    "--private-root",
                    str(root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, build.returncode, build.stderr)
            build_receipt = json.loads(build.stdout)
            self.assertEqual("PASS", build_receipt["status"])
            self.assertTrue((Path(build_receipt["destination"]) / "workspace.json").is_file())


if __name__ == "__main__":
    unittest.main()
