"""Strict operating-v1 intake and immutable workspace tests."""
from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from alma.operating_contracts import SOURCE_NAMES, OperatingContractError, columns_for
from alma.operating_interchange import MAX_CSV_BYTES, parse_pack


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

        controls: list[tuple[str, Callable[[PackFixture], None], str]] = [
            ("relation.sku", set_value("availability_daily", "sku_id", "synthetic:missing-sku"), "synthetic:missing-sku"),
            ("relation.receipt", set_value("inventory_movements", "receipt_id", "synthetic:missing-receipt"), "synthetic:missing-receipt"),
            ("relation.obligation", set_value("cash_events", "obligation_id", "synthetic:missing-obligation"), "synthetic:missing-obligation"),
            ("relation.payment", set_value("cash_events", "payment_id", "synthetic:missing-payment"), "synthetic:missing-payment"),
            ("relation.origin", set_value("budget_allocations", "origin_id", "synthetic:missing-origin"), "synthetic:missing-origin"),
            ("stock.duplicate_post", duplicate_receipt_movement, "synthetic:movement-receipt-duplicate"),
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


if __name__ == "__main__":
    unittest.main()
