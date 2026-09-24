#!/usr/bin/env python3
"""Initialize deterministic blank or synthetic operating-v1 source packs."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.operating_contracts import (  # noqa: E402
    CONTRACT_VERSION,
    SOURCE_NAMES,
    OperatingContractError,
    canonical_json,
    columns_for,
    validate_metadata,
)


CUTOFF_AT = "2026-09-21T23:59:59-07:00"
TIMEZONE = "America/Tijuana"
WINDOW_START = "2026-09-01"
WINDOW_END = "2026-09-21"


def blank_metadata() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "input_class": "BLANK",
        "cutoff_at": None,
        "timezone": None,
        "currency": "MXN",
        "coverage": {
            name: {"status": "MISSING", "window_start": None, "window_end": None}
            for name in SOURCE_NAMES
        },
    }


def synthetic_metadata() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "input_class": "SYNTHETIC_EXAMPLE",
        "cutoff_at": CUTOFF_AT,
        "timezone": TIMEZONE,
        "currency": "MXN",
        "coverage": {
            name: {"status": "PARTIAL", "window_start": WINDOW_START, "window_end": WINDOW_END}
            for name in SOURCE_NAMES
        },
    }


def synthetic_rows() -> dict[str, list[dict[str, Any]]]:
    """Return a compact, linked example spanning every operating-v1 source."""

    sku = "synthetic:sku-001"
    budget = "synthetic:budget-001"
    purchase_order = "synthetic:po-001"
    receipt = "synthetic:receipt-001"
    obligation = "synthetic:obligation-po-001"
    payment = "synthetic:payment-po-001"
    cohort = "synthetic:cohort-001"
    loan = "synthetic:loan-001"
    quality_return = "synthetic:quality-return-001"
    quality_inspection = "synthetic:quality-inspection-001"
    scenario = "synthetic:scenario-observed"
    economic_event = "synthetic:economic-po-payment-001"
    forecast_event = "synthetic:cash-forecast-001"

    return {
        "sku_catalog": [{
            "sku_id": sku,
            "product_code": "synthetic:product-001",
            "variant_code": "synthetic:variant-001",
            "category_code": "synthetic:socks",
            "color_code": "synthetic:multicolor",
            "size_code": "synthetic:one-size",
            "lifecycle_status": "ACTIVE",
            "effective_date": "2026-09-01",
            "source_ref": "synthetic:source:sku-001",
        }],
        "sales_aggregates": [{
            "sales_date": "2026-09-15",
            "sku_id": sku,
            "channel_code": "synthetic:direct",
            "delivery_cohort_id": cohort,
            "delivered_units": 12,
            "returned_units": 2,
            "restocked_units": 1,
            "net_revenue_cents": 1_200_000,
            "variable_cost_cents": 480_000,
            "coverage_status": "PARTIAL",
            "source_ref": "synthetic:source:sales-001",
        }],
        "availability_daily": [{
            "availability_date": "2026-09-21",
            "sku_id": sku,
            "observed_minutes": 1440,
            "sellable_minutes": 960,
            "stockout_minutes": 480,
            "coverage_status": "PARTIAL",
            "source_ref": "synthetic:source:availability-001",
        }],
        "unmet_demand": [{
            "demand_event_id": "synthetic:demand-001",
            "event_date": "2026-09-21",
            "sku_id": sku,
            "channel_code": "synthetic:direct",
            "requested_units": 3,
            "reason_code": "STOCKOUT",
            "source_ref": "synthetic:source:demand-001",
        }],
        "inventory_counts": [{
            "count_id": "synthetic:count-001",
            "sku_id": sku,
            "cutoff_date": "2026-09-21",
            "on_hand_units": 24,
            "reserved_units": 2,
            "in_transit_units": 2,
            "non_sellable_units": 1,
            "source_ref": "synthetic:source:count-001",
        }],
        "inventory_movements": [
            {
                "movement_id": "synthetic:movement-opening-001",
                "sku_id": sku,
                "event_date": "2026-09-01",
                "movement_type": "OPENING",
                "units": 20,
                "receipt_id": None,
                "quality_event_id": None,
                "loan_id": None,
                "sales_date": None,
                "sales_channel_code": None,
                "source_ref": "synthetic:source:movement-opening-001",
            },
            {
                "movement_id": "synthetic:movement-receipt-001",
                "sku_id": sku,
                "event_date": "2026-09-10",
                "movement_type": "RECEIPT_ACCEPTED",
                "units": 16,
                "receipt_id": receipt,
                "quality_event_id": quality_inspection,
                "loan_id": None,
                "sales_date": None,
                "sales_channel_code": None,
                "source_ref": "synthetic:source:movement-receipt-001",
            },
            {
                "movement_id": "synthetic:movement-sale-001",
                "sku_id": sku,
                "event_date": "2026-09-15",
                "movement_type": "SALE_OUT",
                "units": 12,
                "receipt_id": None,
                "quality_event_id": None,
                "loan_id": None,
                "sales_date": "2026-09-15",
                "sales_channel_code": "synthetic:direct",
                "source_ref": "synthetic:source:movement-sale-001",
            },
            {
                "movement_id": "synthetic:movement-return-001",
                "sku_id": sku,
                "event_date": "2026-09-19",
                "movement_type": "RETURN_RESTOCK",
                "units": 1,
                "receipt_id": None,
                "quality_event_id": quality_return,
                "loan_id": None,
                "sales_date": None,
                "sales_channel_code": None,
                "source_ref": "synthetic:source:movement-return-001",
            },
            {
                "movement_id": "synthetic:movement-loan-001",
                "sku_id": sku,
                "event_date": "2026-09-20",
                "movement_type": "LOAN_OUT",
                "units": 1,
                "receipt_id": None,
                "quality_event_id": None,
                "loan_id": loan,
                "sales_date": None,
                "sales_channel_code": None,
                "source_ref": "synthetic:source:movement-loan-001",
            },
        ],
        "inventory_reservations": [
            {
                "reservation_event_id": "synthetic:reservation-event-001",
                "reservation_id": "synthetic:reservation-001",
                "sku_id": sku,
                "event_date": "2026-09-20",
                "event_type": "PLACE",
                "units": 3,
                "source_ref": "synthetic:source:reservation-place-001",
            },
            {
                "reservation_event_id": "synthetic:reservation-event-002",
                "reservation_id": "synthetic:reservation-001",
                "sku_id": sku,
                "event_date": "2026-09-21",
                "event_type": "RELEASE",
                "units": 1,
                "source_ref": "synthetic:source:reservation-release-001",
            },
        ],
        "cost_versions": [{
            "cost_version_id": "synthetic:cost-version-001",
            "sku_id": sku,
            "effective_date": "2026-09-01",
            "lifecycle_status": "ACTIVE",
            "quantity_basis": 1,
            "public_price_cents": 150_000,
            "selling_fee_bps": 800,
            "currency": "MXN",
            "source_ref": "synthetic:source:cost-version-001",
        }],
        "cost_components": [{
            "component_id": "synthetic:component-001",
            "cost_version_id": "synthetic:cost-version-001",
            "component_code": "synthetic:merchandise",
            "classification": "DIRECT",
            "amount_cents": 40_000,
            "required_flag": 1,
            "quality_status": "KNOWN",
            "included_in_component_id": None,
            "source_ref": "synthetic:source:component-001",
        }],
        "cost_allocations": [{
            "allocation_id": "synthetic:allocation-001",
            "component_id": "synthetic:component-001",
            "sku_id": sku,
            "method_code": "DIRECT",
            "allocated_cents": 40_000,
            "remainder_cents": 0,
            "source_ref": "synthetic:source:allocation-001",
        }],
        "purchase_orders": [{
            "purchase_order_id": purchase_order,
            "sku_id": sku,
            "budget_id": budget,
            "ordered_units": 20,
            "agreed_unit_cents": 45_000,
            "order_date": "2026-09-02",
            "promised_date": "2026-09-10",
            "status_code": "PARTIAL",
            "source_ref": "synthetic:source:po-001",
        }],
        "purchase_receipts": [{
            "receipt_id": receipt,
            "purchase_order_id": purchase_order,
            "received_date": "2026-09-10",
            "received_units": 18,
            "inspection_units": 2,
            "accepted_units": 16,
            "rejected_units": 0,
            "source_ref": "synthetic:source:receipt-001",
        }],
        "obligations": [
            {
                "obligation_id": obligation,
                "origin_type": "PURCHASE_ORDER",
                "origin_id": purchase_order,
                "due_date": "2026-09-18",
                "original_cents": 900_000,
                "currency": "MXN",
                "status_code": "SETTLED",
                "source_ref": "synthetic:source:obligation-po-001",
            },
            {
                "obligation_id": "synthetic:obligation-expense-001",
                "origin_type": "EXPENSE",
                "origin_id": "synthetic:expense-001",
                "due_date": "2026-09-30",
                "original_cents": 100_000,
                "currency": "MXN",
                "status_code": "OPEN",
                "source_ref": "synthetic:source:obligation-expense-001",
            },
        ],
        "obligation_payments": [{
            "payment_id": payment,
            "obligation_id": obligation,
            "paid_date": "2026-09-18",
            "amount_cents": 900_000,
            "source_ref": "synthetic:source:payment-001",
        }],
        "cash_events": [
            {
                "event_id": forecast_event,
                "economic_event_id": economic_event,
                "supersedes_event_id": None,
                "scenario_id": scenario,
                "event_date": "2026-09-18",
                "level": "COMMITTED",
                "direction": "OUTFLOW",
                "amount_cents": 900_000,
                "currency": "MXN",
                "obligation_id": obligation,
                "payment_id": None,
                "source_ref": "synthetic:source:cash-forecast-001",
            },
            {
                "event_id": "synthetic:cash-actual-001",
                "economic_event_id": economic_event,
                "supersedes_event_id": forecast_event,
                "scenario_id": scenario,
                "event_date": "2026-09-18",
                "level": "RECONCILED",
                "direction": "OUTFLOW",
                "amount_cents": 900_000,
                "currency": "MXN",
                "obligation_id": obligation,
                "payment_id": payment,
                "source_ref": "synthetic:source:cash-actual-001",
            },
        ],
        "cash_balance_evidence": [{
            "balance_evidence_id": "synthetic:balance-001",
            "scenario_id": scenario,
            "period_start": "2026-09-01",
            "period_end": "2026-09-21",
            "opening_balance_cents": 2_000_000,
            "closing_balance_cents": 1_100_000,
            "opening_observed_at": "2026-09-01T00:00:00-07:00",
            "closing_observed_at": CUTOFF_AT,
            "evidence_status": "OBSERVED",
            "source_ref": "synthetic:source:balance-001",
        }],
        "budgets": [{
            "budget_id": budget,
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
            "drop_code": "synthetic:drop-001",
            "channel_code": "synthetic:direct",
            "approved_cents": 1_200_000,
            "source_ref": "synthetic:source:budget-001",
        }],
        "budget_allocations": [
            {
                "budget_allocation_id": "synthetic:budget-allocation-po-001",
                "budget_id": budget,
                "origin_type": "PURCHASE_ORDER",
                "origin_id": purchase_order,
                "drop_code": "synthetic:drop-001",
                "channel_code": "synthetic:direct",
                "allocated_cents": 900_000,
                "source_ref": "synthetic:source:budget-allocation-po-001",
            },
            {
                "budget_allocation_id": "synthetic:budget-allocation-expense-001",
                "budget_id": budget,
                "origin_type": "EXPENSE",
                "origin_id": "synthetic:expense-001",
                "drop_code": "synthetic:drop-001",
                "channel_code": "synthetic:direct",
                "allocated_cents": 100_000,
                "source_ref": "synthetic:source:budget-allocation-expense-001",
            },
        ],
        "expenses": [{
            "expense_id": "synthetic:expense-001",
            "budget_id": budget,
            "incurred_date": "2026-09-12",
            "category_code": "synthetic:packaging",
            "amount_cents": 100_000,
            "status_code": "INCURRED",
            "source_ref": "synthetic:source:expense-001",
        }],
        "quality_events": [
            {
                "quality_event_id": quality_return,
                "sku_id": sku,
                "receipt_id": None,
                "delivery_cohort_id": cohort,
                "event_date": "2026-09-19",
                "event_type": "RETURN_REPORTED",
                "units": 2,
                "reason_code": "synthetic:fit",
                "resolution_code": "synthetic:review",
                "source_ref": "synthetic:source:quality-return-001",
            },
            {
                "quality_event_id": quality_inspection,
                "sku_id": sku,
                "receipt_id": receipt,
                "delivery_cohort_id": None,
                "event_date": "2026-09-10",
                "event_type": "INSPECTED",
                "units": 2,
                "reason_code": "synthetic:receipt-check",
                "resolution_code": "synthetic:accepted",
                "source_ref": "synthetic:source:quality-inspection-001",
            },
        ],
        "sales_readiness": [{
            "sku_id": sku,
            "effective_date": "2026-09-21",
            "readiness_status": "READY",
            "missing_info_code": None,
            "source_ref": "synthetic:source:readiness-001",
        }],
        "loans": [{
            "loan_id": loan,
            "sku_id": sku,
            "quantity": 1,
            "recipient_ref": "synthetic:recipient-001",
            "borrowed_date": "2026-09-20",
            "due_date": "2026-09-25",
            "returned_date": None,
            "condition_code": "GOOD",
            "status_code": "OPEN",
            "source_ref": "synthetic:source:loan-001",
        }],
    }


def _write_csv(path: Path, source: str, rows: list[dict[str, Any]]) -> None:
    columns = columns_for(source)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        for row_number, row in enumerate(rows, start=2):
            if tuple(row) != columns:
                raise OperatingContractError("pack.row_columns", f"{source}.csv:{row_number}")
            writer.writerow({column: "" if row[column] is None else row[column] for column in columns})


def initialize_pack(kind: str, output: str | Path) -> Path:
    """Create a new deterministic pack without overwriting existing content."""

    if kind not in {"blank", "synthetic"}:
        raise OperatingContractError("pack.public_kind", "kind")
    destination = Path(output)
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise OperatingContractError("pack.destination_not_empty", "output")
    else:
        destination.mkdir(parents=True)

    if kind == "blank":
        metadata = blank_metadata()
        rows = {name: [] for name in SOURCE_NAMES}
        validate_metadata(metadata, allow_blank=True)
    else:
        metadata = synthetic_metadata()
        rows = synthetic_rows()
        if tuple(rows) != SOURCE_NAMES:
            raise OperatingContractError("pack.sources", "synthetic")
        validate_metadata(metadata)

    (destination / "metadata.json").write_bytes(canonical_json(metadata) + b"\n")
    for source in SOURCE_NAMES:
        _write_csv(destination / f"{source}.csv", source, rows[source])
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="initialize an operating-v1 source pack")
    init.add_argument("--kind", required=True, choices=("blank", "synthetic"))
    init.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        initialize_pack(args.kind, args.output)
    except (OperatingContractError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
