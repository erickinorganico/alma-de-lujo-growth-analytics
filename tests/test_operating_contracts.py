"""Executable contract tests for the aggregate operating-v1 source packs."""
from __future__ import annotations

import math
import csv
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from alma.operating_contracts import (
    CONTRACT_VERSION,
    COVERAGE_STATUSES,
    CUT_IDENTITY_FIELDS,
    METADATA_FIELDS,
    SOURCE_NAMES,
    SOURCES,
    OperatingContractError,
    canonical_json,
    columns_for,
    source_contract,
    validate_metadata,
)


EXPECTED_HEADERS = {
    "sku_catalog": ("sku_id", "product_code", "variant_code", "category_code", "color_code", "size_code", "lifecycle_status", "effective_date", "source_ref"),
    "sales_aggregates": ("sales_date", "sku_id", "channel_code", "delivery_cohort_id", "delivered_units", "returned_units", "restocked_units", "net_revenue_cents", "variable_cost_cents", "coverage_status", "source_ref"),
    "availability_daily": ("availability_date", "sku_id", "observed_minutes", "sellable_minutes", "stockout_minutes", "coverage_status", "source_ref"),
    "unmet_demand": ("demand_event_id", "event_date", "sku_id", "channel_code", "requested_units", "reason_code", "source_ref"),
    "inventory_counts": ("count_id", "sku_id", "cutoff_date", "on_hand_units", "reserved_units", "in_transit_units", "non_sellable_units", "source_ref"),
    "inventory_movements": ("movement_id", "sku_id", "event_date", "movement_type", "units", "receipt_id", "quality_event_id", "loan_id", "sales_date", "sales_channel_code", "source_ref"),
    "inventory_reservations": ("reservation_event_id", "reservation_id", "sku_id", "event_date", "event_type", "units", "source_ref"),
    "cost_versions": ("cost_version_id", "sku_id", "effective_date", "lifecycle_status", "quantity_basis", "public_price_cents", "selling_fee_bps", "currency", "source_ref"),
    "cost_components": ("component_id", "cost_version_id", "component_code", "classification", "amount_cents", "required_flag", "quality_status", "included_in_component_id", "source_ref"),
    "cost_allocations": ("allocation_id", "component_id", "sku_id", "method_code", "allocated_cents", "remainder_cents", "source_ref"),
    "purchase_orders": ("purchase_order_id", "sku_id", "budget_id", "ordered_units", "agreed_unit_cents", "order_date", "promised_date", "status_code", "source_ref"),
    "purchase_receipts": ("receipt_id", "purchase_order_id", "received_date", "received_units", "inspection_units", "accepted_units", "rejected_units", "source_ref"),
    "obligations": ("obligation_id", "origin_type", "origin_id", "due_date", "original_cents", "currency", "status_code", "source_ref"),
    "obligation_payments": ("payment_id", "obligation_id", "paid_date", "amount_cents", "source_ref"),
    "cash_events": ("event_id", "economic_event_id", "supersedes_event_id", "scenario_id", "event_date", "level", "direction", "amount_cents", "currency", "obligation_id", "payment_id", "source_ref"),
    "cash_balance_evidence": ("balance_evidence_id", "scenario_id", "period_start", "period_end", "opening_balance_cents", "closing_balance_cents", "opening_observed_at", "closing_observed_at", "evidence_status", "source_ref"),
    "budgets": ("budget_id", "period_start", "period_end", "drop_code", "channel_code", "approved_cents", "source_ref"),
    "budget_allocations": ("budget_allocation_id", "budget_id", "origin_type", "origin_id", "drop_code", "channel_code", "allocated_cents", "source_ref"),
    "expenses": ("expense_id", "budget_id", "incurred_date", "category_code", "amount_cents", "status_code", "source_ref"),
    "quality_events": ("quality_event_id", "sku_id", "receipt_id", "delivery_cohort_id", "event_date", "event_type", "units", "reason_code", "resolution_code", "source_ref"),
    "sales_readiness": ("sku_id", "effective_date", "readiness_status", "missing_info_code", "source_ref"),
    "loans": ("loan_id", "sku_id", "quantity", "recipient_ref", "borrowed_date", "due_date", "returned_date", "condition_code", "status_code", "source_ref"),
}


def metadata(*, input_class: str = "SYNTHETIC_EXAMPLE") -> dict:
    coverage = {
        name: {
            "status": "PARTIAL",
            "window_start": "2026-09-01",
            "window_end": "2026-09-21",
        }
        for name in EXPECTED_HEADERS
    }
    return {
        "contract_version": "operating-v1",
        "input_class": input_class,
        "cutoff_at": "2026-09-21T23:59:59-07:00",
        "timezone": "America/Tijuana",
        "currency": "MXN",
        "coverage": coverage,
    }


class OperatingRegistryTests(unittest.TestCase):
    def test_exact_ordered_headers_for_all_twenty_two_sources(self) -> None:
        self.assertEqual("operating-v1", CONTRACT_VERSION)
        self.assertEqual(tuple(EXPECTED_HEADERS), SOURCE_NAMES)
        self.assertEqual(tuple(EXPECTED_HEADERS), tuple(SOURCES))
        self.assertEqual(22, len(SOURCE_NAMES))
        for name, expected in EXPECTED_HEADERS.items():
            with self.subTest(source=name):
                self.assertEqual(expected, columns_for(name))
                self.assertEqual("source_ref", expected[-1])
                self.assertEqual(1, expected.count("source_ref"))

    def test_contracts_expose_grain_keys_types_units_enums_fks_and_provenance(self) -> None:
        required_sources = {
            "availability_daily",
            "unmet_demand",
            "inventory_movements",
            "inventory_reservations",
            "budget_allocations",
            "cash_balance_evidence",
        }
        self.assertLessEqual(required_sources, set(SOURCE_NAMES))
        for name in SOURCE_NAMES:
            contract = source_contract(name)
            with self.subTest(source=name):
                self.assertTrue(contract["grain"])
                self.assertTrue(contract["primary_key"])
                self.assertIn("unique", contract)
                self.assertIn("foreign_keys", contract)
                self.assertEqual(tuple(EXPECTED_HEADERS[name]), tuple(field["name"] for field in contract["fields"]))
                for field in contract["fields"]:
                    self.assertEqual(
                        {"name", "type", "nullable", "unit", "enum", "provenance", "foreign_key"},
                        set(field),
                    )
                    self.assertIn(field["provenance"], {"source", "derived_identity"})

        cash = {field["name"]: field for field in source_contract("cash_events")["fields"]}
        self.assertFalse(cash["economic_event_id"]["nullable"])
        self.assertTrue(cash["supersedes_event_id"]["nullable"])
        self.assertEqual(("cash_events", ("event_id",)), cash["supersedes_event_id"]["foreign_key"])
        self.assertEqual(("scenario_id", "economic_event_id"), source_contract("cash_events")["economic_identity"])

    def test_registry_owns_metadata_and_cut_identity_field_names(self) -> None:
        self.assertEqual(
            ("contract_version", "input_class", "cutoff_at", "timezone", "currency", "coverage"),
            METADATA_FIELDS,
        )
        self.assertEqual((*METADATA_FIELDS, "source_sha256"), CUT_IDENTITY_FIELDS)
        self.assertEqual(
            {"COMPLETE", "PARTIAL", "ZERO", "MISSING", "NOT_APPLICABLE", "ESTIMATED", "ERROR"},
            set(COVERAGE_STATUSES),
        )

    def test_canonical_json_is_utf8_sorted_compact_and_rejects_nan(self) -> None:
        self.assertEqual(b'{"a":"M\xc3\xa9xico","b":2}', canonical_json({"b": 2, "a": "México"}))
        with self.assertRaises(ValueError):
            canonical_json({"bad": math.nan})


class MetadataContractTests(unittest.TestCase):
    def assert_contract_error(self, expected_code: str, value: dict, **kwargs: object) -> None:
        with self.assertRaises(OperatingContractError) as raised:
            validate_metadata(value, **kwargs)
        self.assertEqual(expected_code, raised.exception.code)
        self.assertIsInstance(raised.exception.location, str)
        self.assertNotIn("2026-09-21T23:59:59-07:00", str(raised.exception))

    def test_valid_synthetic_and_private_metadata(self) -> None:
        self.assertIsNone(validate_metadata(metadata()))
        self.assertIsNone(validate_metadata(metadata(input_class="PRIVATE")))

    def test_blank_requires_explicit_template_allowance(self) -> None:
        value = metadata(input_class="BLANK")
        value["cutoff_at"] = None
        value["timezone"] = None
        for entry in value["coverage"].values():
            entry.update(status="MISSING", window_start=None, window_end=None)
        self.assert_contract_error("metadata.blank_not_buildable", value)
        self.assertIsNone(validate_metadata(value, allow_blank=True))

    def test_rejects_version_currency_coverage_and_window_errors(self) -> None:
        cases: list[tuple[str, callable]] = [
            ("metadata.contract_version", lambda value: value.update(contract_version="2.0")),
            ("metadata.currency", lambda value: value.update(currency="USD")),
            ("metadata.coverage_keys", lambda value: value["coverage"].pop("loans")),
            ("metadata.coverage_status", lambda value: value["coverage"]["loans"].update(status="UNKNOWN")),
            ("metadata.coverage_window", lambda value: value["coverage"]["loans"].update(window_start="2026-09-22", window_end="2026-09-21")),
            ("metadata.coverage_window", lambda value: value["coverage"]["loans"].update(window_end="2026-09-22")),
        ]
        for expected_code, mutate in cases:
            value = metadata()
            mutate(value)
            with self.subTest(code=expected_code):
                self.assert_contract_error(expected_code, value)

    def test_rejects_invalid_cutoff_zone_and_offset_mismatch(self) -> None:
        cases = [
            ("metadata.cutoff_at", {"cutoff_at": "2026-09-21"}),
            ("metadata.timezone", {"timezone": "Mars/Olympus"}),
            ("metadata.timezone_offset", {"cutoff_at": "2026-09-21T23:59:59+00:00"}),
        ]
        for expected_code, update in cases:
            value = metadata()
            value.update(update)
            with self.subTest(code=expected_code):
                self.assert_contract_error(expected_code, value)


class OperatingPackTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    SCRIPT = ROOT / "scripts" / "operating_pack.py"

    def run_init(self, kind: str, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), "init", "--kind", kind, "--output", str(output)],
            cwd=self.ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def read_rows(pack: Path, source: str) -> list[dict[str, str]]:
        with (pack / f"{source}.csv").open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_cli_regenerates_checked_in_packs_byte_for_byte(self) -> None:
        expected_files = {"metadata.json", *(f"{name}.csv" for name in SOURCE_NAMES)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind in ("blank", "synthetic"):
                generated = root / kind
                result = self.run_init(kind, generated)
                self.assertEqual(0, result.returncode, result.stderr)
                checked_in = self.ROOT / "client" / "source-packs" / "v1" / kind
                self.assertEqual(expected_files, {path.name for path in generated.iterdir()})
                self.assertEqual(expected_files, {path.name for path in checked_in.iterdir()})
                for filename in expected_files:
                    with self.subTest(kind=kind, filename=filename):
                        self.assertEqual((checked_in / filename).read_bytes(), (generated / filename).read_bytes())

    def test_blank_pack_has_only_headers_and_nonbuildable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "blank"
            result = self.run_init("blank", output)
            self.assertEqual(0, result.returncode, result.stderr)
            value = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual("BLANK", value["input_class"])
            self.assertIsNone(validate_metadata(value, allow_blank=True))
            with self.assertRaises(OperatingContractError) as raised:
                validate_metadata(value)
            self.assertEqual("metadata.blank_not_buildable", raised.exception.code)
            for name in SOURCE_NAMES:
                with self.subTest(source=name):
                    self.assertEqual([], self.read_rows(output, name))
                    self.assertEqual(",".join(columns_for(name)) + "\n", (output / f"{name}.csv").read_text(encoding="utf-8"))

    def test_synthetic_pack_exercises_linked_operating_facts_and_cash_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic"
            result = self.run_init("synthetic", output)
            self.assertEqual(0, result.returncode, result.stderr)
            value = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual("SYNTHETIC_EXAMPLE", value["input_class"])
            self.assertIsNone(validate_metadata(value))

            rows = {name: self.read_rows(output, name) for name in SOURCE_NAMES}
            self.assertTrue(all(rows.values()))
            self.assertTrue(all(row["source_ref"].startswith("synthetic:") for table in rows.values() for row in table))

            order = rows["purchase_orders"][0]
            receipt = rows["purchase_receipts"][0]
            self.assertEqual("20", order["ordered_units"])
            self.assertEqual(("18", "2", "16", "0"), tuple(receipt[key] for key in ("received_units", "inspection_units", "accepted_units", "rejected_units")))
            self.assertEqual(order["purchase_order_id"], receipt["purchase_order_id"])

            movement_types = {row["movement_type"] for row in rows["inventory_movements"]}
            self.assertLessEqual({"OPENING", "RECEIPT_ACCEPTED"}, movement_types)
            accepted = next(row for row in rows["inventory_movements"] if row["movement_type"] == "RECEIPT_ACCEPTED")
            self.assertEqual(receipt["receipt_id"], accepted["receipt_id"])
            self.assertEqual("16", accepted["units"])
            self.assertLessEqual({"PLACE", "RELEASE"}, {row["event_type"] for row in rows["inventory_reservations"]})
            self.assertTrue(rows["availability_daily"])
            self.assertTrue(rows["unmet_demand"])
            self.assertEqual({"PURCHASE_ORDER", "EXPENSE"}, {row["origin_type"] for row in rows["budget_allocations"]})
            self.assertEqual("OBSERVED", rows["cash_balance_evidence"][0]["evidence_status"])
            self.assertTrue(rows["quality_events"][0]["delivery_cohort_id"])

            cash = rows["cash_events"]
            self.assertEqual(2, len(cash))
            forecast = next(row for row in cash if row["supersedes_event_id"] == "")
            actual = next(row for row in cash if row["supersedes_event_id"])
            self.assertEqual(forecast["economic_event_id"], actual["economic_event_id"])
            self.assertEqual(forecast["event_id"], actual["supersedes_event_id"])
            self.assertEqual("RECONCILED", actual["level"])

    def test_public_rows_use_only_declared_bounded_values(self) -> None:
        forbidden_headers = {"name", "email", "phone", "address", "customer_id", "order_id", "notes", "description"}
        token = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
        integer = re.compile(r"^-?[0-9]+$")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic"
            result = self.run_init("synthetic", output)
            self.assertEqual(0, result.returncode, result.stderr)
            for source in SOURCE_NAMES:
                contract = source_contract(source)
                fields = {field["name"]: field for field in contract["fields"]}
                self.assertFalse(forbidden_headers.intersection(fields))
                for row in self.read_rows(output, source):
                    for name, raw in row.items():
                        if raw == "":
                            self.assertTrue(fields[name]["nullable"])
                        elif fields[name]["type"] in {"integer", "nonnegative_integer", "signed_integer"}:
                            self.assertRegex(raw, integer)
                        elif fields[name]["type"] == "date":
                            self.assertRegex(raw, r"^\d{4}-\d{2}-\d{2}$")
                        elif fields[name]["type"] == "timestamp":
                            self.assertRegex(raw, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
                        else:
                            self.assertRegex(raw, token)

    def test_refuses_nonempty_destination_and_private_public_output_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "existing"
            existing.mkdir()
            marker = existing / "keep.bin"
            marker.write_bytes(b"do-not-change")
            before = {path.relative_to(existing): path.read_bytes() for path in existing.rglob("*") if path.is_file()}
            result = self.run_init("synthetic", existing)
            self.assertNotEqual(0, result.returncode)
            after = {path.relative_to(existing): path.read_bytes() for path in existing.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

            public = root / "client" / "source-packs" / "v1" / "private"
            result = self.run_init("private", public)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(public.exists())

if __name__ == "__main__":
    unittest.main()
