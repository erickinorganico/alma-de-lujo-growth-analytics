"""Single source of truth for the aggregate ``operating-v1`` input contract.

This module defines source shape and metadata only.  It deliberately remains
separate from the released row-level v0.2 warehouse and interchange contract.
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CONTRACT_VERSION = "operating-v1"
METADATA_FIELDS = (
    "contract_version",
    "input_class",
    "cutoff_at",
    "timezone",
    "currency",
    "coverage",
)
CUT_IDENTITY_FIELDS = (*METADATA_FIELDS, "source_sha256")
INPUT_CLASSES = ("BLANK", "SYNTHETIC_EXAMPLE", "PRIVATE")
COVERAGE_STATUSES = (
    "COMPLETE",
    "PARTIAL",
    "ZERO",
    "MISSING",
    "NOT_APPLICABLE",
    "ESTIMATED",
    "ERROR",
)
TOKEN_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"


class OperatingContractError(ValueError):
    """A safe, machine-readable operating-contract validation error."""

    def __init__(self, code: str, location: str) -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def canonical_json(value: Any) -> bytes:
    """Serialize a value to the canonical bytes used by later identity hashes."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


_SOURCE_DEFINITIONS: tuple[
    tuple[str, str, tuple[str, ...], tuple[tuple[str, ...], ...], tuple[str, ...]], ...
] = (
    ("sku_catalog", "one sellable variant", ("sku_id",), (), ("sku_id", "product_code", "variant_code", "category_code", "color_code", "size_code", "lifecycle_status", "effective_date")),
    ("sales_aggregates", "date x SKU x channel", ("sales_date", "sku_id", "channel_code"), (), ("sales_date", "sku_id", "channel_code", "delivery_cohort_id", "delivered_units", "returned_units", "restocked_units", "net_revenue_cents", "variable_cost_cents", "coverage_status")),
    ("availability_daily", "SKU x date", ("availability_date", "sku_id"), (), ("availability_date", "sku_id", "observed_minutes", "sellable_minutes", "stockout_minutes", "coverage_status")),
    ("unmet_demand", "one recorded demand observation", ("demand_event_id",), (), ("demand_event_id", "event_date", "sku_id", "channel_code", "requested_units", "reason_code")),
    ("inventory_counts", "one inventory count event", ("count_id",), (("sku_id", "cutoff_date"),), ("count_id", "sku_id", "cutoff_date", "on_hand_units", "reserved_units", "in_transit_units", "non_sellable_units")),
    ("inventory_movements", "one stock movement event", ("movement_id",), (), ("movement_id", "sku_id", "event_date", "movement_type", "units", "receipt_id", "quality_event_id", "loan_id", "sales_date", "sales_channel_code")),
    ("inventory_reservations", "one reservation delta event", ("reservation_event_id",), (), ("reservation_event_id", "reservation_id", "sku_id", "event_date", "event_type", "units")),
    ("cost_versions", "one SKU cost version", ("cost_version_id",), (("sku_id", "effective_date"),), ("cost_version_id", "sku_id", "effective_date", "lifecycle_status", "quantity_basis", "public_price_cents", "selling_fee_bps", "currency")),
    ("cost_components", "one component in a cost version", ("component_id",), (("cost_version_id", "component_code"),), ("component_id", "cost_version_id", "component_code", "classification", "amount_cents", "required_flag", "quality_status", "included_in_component_id")),
    ("cost_allocations", "one component allocation to a SKU", ("allocation_id",), (("component_id", "sku_id"),), ("allocation_id", "component_id", "sku_id", "method_code", "allocated_cents", "remainder_cents")),
    ("purchase_orders", "one SKU purchase order", ("purchase_order_id",), (), ("purchase_order_id", "sku_id", "budget_id", "ordered_units", "agreed_unit_cents", "order_date", "promised_date", "status_code")),
    ("purchase_receipts", "one physical receipt event", ("receipt_id",), (), ("receipt_id", "purchase_order_id", "received_date", "received_units", "inspection_units", "accepted_units", "rejected_units")),
    ("obligations", "one payable economic origin", ("obligation_id",), (("origin_type", "origin_id"),), ("obligation_id", "origin_type", "origin_id", "due_date", "original_cents", "currency", "status_code")),
    ("obligation_payments", "one applied observed payment", ("payment_id",), (), ("payment_id", "obligation_id", "paid_date", "amount_cents")),
    ("cash_events", "one immutable cash evidence row", ("event_id",), (), ("event_id", "economic_event_id", "supersedes_event_id", "scenario_id", "event_date", "level", "direction", "amount_cents", "currency", "obligation_id", "payment_id")),
    ("cash_balance_evidence", "one scenario opening/closing evidence window", ("balance_evidence_id",), (("scenario_id", "period_start", "period_end"),), ("balance_evidence_id", "scenario_id", "period_start", "period_end", "opening_balance_cents", "closing_balance_cents", "opening_observed_at", "closing_observed_at", "evidence_status")),
    ("budgets", "one approved drop/channel/window budget", ("budget_id",), (("period_start", "period_end", "drop_code", "channel_code"),), ("budget_id", "period_start", "period_end", "drop_code", "channel_code", "approved_cents")),
    ("budget_allocations", "one explicit origin allocation into a budget", ("budget_allocation_id",), (("budget_id", "origin_type", "origin_id", "drop_code", "channel_code"),), ("budget_allocation_id", "budget_id", "origin_type", "origin_id", "drop_code", "channel_code", "allocated_cents")),
    ("expenses", "one incurred economic expense", ("expense_id",), (), ("expense_id", "budget_id", "incurred_date", "category_code", "amount_cents", "status_code")),
    ("quality_events", "one quality, return, or inspection event", ("quality_event_id",), (), ("quality_event_id", "sku_id", "receipt_id", "delivery_cohort_id", "event_date", "event_type", "units", "reason_code", "resolution_code")),
    ("sales_readiness", "one SKU assessment per effective date", ("sku_id", "effective_date"), (), ("sku_id", "effective_date", "readiness_status", "missing_info_code")),
    ("loans", "one loan or custody event", ("loan_id",), (), ("loan_id", "sku_id", "quantity", "recipient_ref", "borrowed_date", "due_date", "returned_date", "condition_code", "status_code")),
)

SOURCE_NAMES = tuple(definition[0] for definition in _SOURCE_DEFINITIONS)

_NULLABLE = {
    ("sales_aggregates", "delivery_cohort_id"),
    ("sales_aggregates", "variable_cost_cents"),
    ("inventory_movements", "receipt_id"),
    ("inventory_movements", "quality_event_id"),
    ("inventory_movements", "loan_id"),
    ("inventory_movements", "sales_date"),
    ("inventory_movements", "sales_channel_code"),
    ("cost_components", "amount_cents"),
    ("cost_components", "included_in_component_id"),
    ("purchase_orders", "budget_id"),
    ("purchase_orders", "promised_date"),
    ("obligations", "due_date"),
    ("cash_events", "supersedes_event_id"),
    ("cash_events", "event_date"),
    ("cash_events", "obligation_id"),
    ("cash_events", "payment_id"),
    ("cash_balance_evidence", "opening_balance_cents"),
    ("cash_balance_evidence", "closing_balance_cents"),
    ("cash_balance_evidence", "opening_observed_at"),
    ("cash_balance_evidence", "closing_observed_at"),
    ("expenses", "budget_id"),
    ("quality_events", "receipt_id"),
    ("quality_events", "delivery_cohort_id"),
    ("quality_events", "resolution_code"),
    ("sales_readiness", "missing_info_code"),
    ("loans", "due_date"),
    ("loans", "returned_date"),
}

_ENUMS: dict[tuple[str, str], tuple[Any, ...]] = {
    ("sku_catalog", "lifecycle_status"): ("DRAFT", "ACTIVE", "RETIRED"),
    ("sales_aggregates", "coverage_status"): ("COMPLETE", "PARTIAL", "ESTIMATED"),
    ("availability_daily", "coverage_status"): ("COMPLETE", "PARTIAL", "ESTIMATED"),
    ("unmet_demand", "reason_code"): ("STOCKOUT", "SIZE_UNAVAILABLE", "OTHER_RECORDED"),
    ("inventory_movements", "movement_type"): ("OPENING", "RECEIPT_ACCEPTED", "SALE_OUT", "RETURN_RESTOCK", "LOAN_OUT", "LOAN_IN", "ADJUSTMENT_IN", "ADJUSTMENT_OUT"),
    ("inventory_reservations", "event_type"): ("PLACE", "RELEASE", "CONSUME"),
    ("cost_versions", "lifecycle_status"): ("DRAFT", "ACTIVE", "RETIRED"),
    ("cost_versions", "currency"): ("MXN",),
    ("cost_components", "classification"): ("DIRECT", "ALLOCATED", "EXCLUDED"),
    ("cost_components", "required_flag"): (0, 1),
    ("cost_components", "quality_status"): ("KNOWN", "MISSING", "ESTIMATED", "NOT_APPLICABLE"),
    ("cost_allocations", "method_code"): ("UNITS", "WEIGHT", "DIRECT"),
    ("purchase_orders", "status_code"): ("OPEN", "PARTIAL", "CLOSED", "CANCELLED"),
    ("obligations", "origin_type"): ("PURCHASE_ORDER", "EXPENSE"),
    ("obligations", "currency"): ("MXN",),
    ("obligations", "status_code"): ("OPEN", "PARTIAL", "SETTLED", "VOID"),
    ("cash_events", "level"): ("RECONCILED", "COMMITTED", "EXPECTED", "UNDATED", "SCENARIO"),
    ("cash_events", "direction"): ("INFLOW", "OUTFLOW"),
    ("cash_events", "currency"): ("MXN",),
    ("cash_balance_evidence", "evidence_status"): ("OBSERVED", "PARTIAL", "MISSING", "ESTIMATED", "ERROR"),
    ("budget_allocations", "origin_type"): ("PURCHASE_ORDER", "EXPENSE"),
    ("expenses", "status_code"): ("INCURRED", "VOID"),
    ("quality_events", "event_type"): ("RETURN_REPORTED", "RETURN_RECEIVED", "INSPECTED", "RESTOCKED", "REJECTED", "REFUNDED"),
    ("sales_readiness", "readiness_status"): ("READY", "BLOCKED", "REVIEW"),
    ("loans", "condition_code"): ("GOOD", "DAMAGED", "UNKNOWN"),
    ("loans", "status_code"): ("OPEN", "PARTIAL", "RETURNED", "LOST"),
}

_DATE_FIELDS = {
    "sales_date", "availability_date", "event_date", "cutoff_date", "effective_date",
    "order_date", "promised_date", "received_date", "due_date", "paid_date",
    "period_start", "period_end", "incurred_date", "borrowed_date", "returned_date",
}
_TIMESTAMP_FIELDS = {"opening_observed_at", "closing_observed_at"}
_INTEGER_FIELDS = {
    "delivered_units", "returned_units", "restocked_units", "observed_minutes", "sellable_minutes",
    "stockout_minutes", "requested_units", "on_hand_units", "reserved_units", "in_transit_units",
    "non_sellable_units", "units", "quantity_basis", "selling_fee_bps", "required_flag",
    "ordered_units", "received_units", "inspection_units", "accepted_units", "rejected_units", "quantity",
}
_SIGNED_MONEY_FIELDS = {"net_revenue_cents", "variable_cost_cents", "opening_balance_cents", "closing_balance_cents"}

_FIELD_FOREIGN_KEYS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    (source, "sku_id"): ("sku_catalog", ("sku_id",))
    for source in SOURCE_NAMES
    if source not in {"sku_catalog", "cash_events", "cash_balance_evidence", "budgets", "budget_allocations", "expenses", "obligations", "obligation_payments", "purchase_receipts"}
}
_FIELD_FOREIGN_KEYS.update({
    ("cost_components", "cost_version_id"): ("cost_versions", ("cost_version_id",)),
    ("cost_components", "included_in_component_id"): ("cost_components", ("component_id",)),
    ("cost_allocations", "component_id"): ("cost_components", ("component_id",)),
    ("purchase_orders", "budget_id"): ("budgets", ("budget_id",)),
    ("purchase_receipts", "purchase_order_id"): ("purchase_orders", ("purchase_order_id",)),
    ("obligation_payments", "obligation_id"): ("obligations", ("obligation_id",)),
    ("cash_events", "supersedes_event_id"): ("cash_events", ("event_id",)),
    ("cash_events", "obligation_id"): ("obligations", ("obligation_id",)),
    ("cash_events", "payment_id"): ("obligation_payments", ("payment_id",)),
    ("budget_allocations", "budget_id"): ("budgets", ("budget_id",)),
    ("expenses", "budget_id"): ("budgets", ("budget_id",)),
    ("quality_events", "receipt_id"): ("purchase_receipts", ("receipt_id",)),
    ("quality_events", "delivery_cohort_id"): ("sales_aggregates", ("delivery_cohort_id",)),
    ("inventory_movements", "receipt_id"): ("purchase_receipts", ("receipt_id",)),
    ("inventory_movements", "quality_event_id"): ("quality_events", ("quality_event_id",)),
    ("inventory_movements", "loan_id"): ("loans", ("loan_id",)),
})

_SOURCE_FOREIGN_KEYS: dict[str, tuple[dict[str, Any], ...]] = {
    "inventory_movements": (
        {"fields": ("sales_date", "sku_id", "sales_channel_code"), "target": "sales_aggregates", "target_fields": ("sales_date", "sku_id", "channel_code")},
    ),
    "obligations": (
        {"fields": ("origin_type", "origin_id"), "target": ("purchase_orders", "expenses"), "target_fields": ("purchase_order_id", "expense_id"), "polymorphic": True},
    ),
    "budget_allocations": (
        {"fields": ("origin_type", "origin_id"), "target": ("purchase_orders", "expenses"), "target_fields": ("purchase_order_id", "expense_id"), "polymorphic": True},
    ),
}


def _field_type(name: str) -> tuple[str, str]:
    if name in _DATE_FIELDS:
        return "date", "ISO-8601 date"
    if name in _TIMESTAMP_FIELDS:
        return "timestamp", "ISO-8601 timestamp with offset"
    if name in _SIGNED_MONEY_FIELDS:
        return "signed_integer", "MXN cents"
    if name.endswith("_cents"):
        return "nonnegative_integer", "MXN cents"
    if name in _INTEGER_FIELDS:
        if name.endswith("_minutes"):
            return "nonnegative_integer", "minutes"
        if name == "selling_fee_bps":
            return "nonnegative_integer", "basis points"
        if name == "required_flag":
            return "integer", "boolean 0 or 1"
        return "nonnegative_integer", "count"
    if name == "source_ref":
        return "bounded_token", "source record token"
    if name.endswith("_id") or name.endswith("_code") or name in {"currency", "level", "direction", "classification", "coverage_status", "evidence_status", "method_code", "recipient_ref"}:
        return "bounded_token", "identifier or code"
    return "bounded_token", "code"


def _make_field(source: str, name: str) -> dict[str, Any]:
    field_type, unit = _field_type(name)
    return {
        "name": name,
        "type": field_type,
        "nullable": (source, name) in _NULLABLE,
        "unit": unit,
        "enum": _ENUMS.get((source, name)),
        "provenance": "source",
        "foreign_key": _FIELD_FOREIGN_KEYS.get((source, name)),
    }


SOURCES: dict[str, dict[str, Any]] = {}
for _name, _grain, _primary_key, _unique, _columns in _SOURCE_DEFINITIONS:
    _all_columns = (*_columns, "source_ref")
    SOURCES[_name] = {
        "name": _name,
        "filename": f"{_name}.csv",
        "grain": _grain,
        "primary_key": _primary_key,
        "unique": _unique,
        "foreign_keys": _SOURCE_FOREIGN_KEYS.get(_name, ()),
        "fields": tuple(_make_field(_name, column) for column in _all_columns),
        "provenance_field": "source_ref",
    }
SOURCES["cash_events"]["economic_identity"] = ("scenario_id", "economic_event_id")
SOURCES["cash_events"]["unique_non_null"] = (("supersedes_event_id",),)
SOURCES["sales_aggregates"]["unique_non_null"] = (("delivery_cohort_id",),)


def columns_for(name: str) -> tuple[str, ...]:
    """Return the exact ordered CSV header for a registered source."""

    try:
        return tuple(field["name"] for field in SOURCES[name]["fields"])
    except KeyError as exc:
        raise OperatingContractError("source.unknown", "source") from exc


def source_contract(name: str) -> dict[str, Any]:
    """Return an isolated copy of a complete source contract."""

    try:
        return copy.deepcopy(SOURCES[name])
    except KeyError as exc:
        raise OperatingContractError("source.unknown", "source") from exc


def _parse_date(value: Any, location: str) -> date:
    if not isinstance(value, str):
        raise OperatingContractError("metadata.coverage_window", location)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OperatingContractError("metadata.coverage_window", location) from exc


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    day = 1 + (weekday - first.weekday()) % 7 + (occurrence - 1) * 7
    return date(year, month, day)


def _fallback_iana_offset(timezone_name: str, cutoff: datetime) -> timedelta | None:
    """Return the business-zone offset when Windows has no IANA database.

    The supported operating zone follows the US border DST schedule: the
    second Sunday in March through the first Sunday in November.  Keeping this
    narrow avoids pretending that an unknown IANA zone was validated.
    """

    if timezone_name != "America/Tijuana":
        return None
    local_wall_time = cutoff.replace(tzinfo=None)
    dst_start = datetime.combine(
        _nth_weekday(local_wall_time.year, 3, weekday=6, occurrence=2),
        datetime.min.time(),
    ).replace(hour=2)
    dst_end = datetime.combine(
        _nth_weekday(local_wall_time.year, 11, weekday=6, occurrence=1),
        datetime.min.time(),
    ).replace(hour=2)
    return timedelta(hours=-7 if dst_start <= local_wall_time < dst_end else -8)


def validate_metadata(metadata: Any, *, allow_blank: bool = False) -> None:
    """Validate exact operating-v1 metadata without exposing supplied values."""

    if not isinstance(metadata, dict) or set(metadata) != set(METADATA_FIELDS):
        raise OperatingContractError("metadata.shape", "metadata")
    if metadata["contract_version"] != CONTRACT_VERSION:
        raise OperatingContractError("metadata.contract_version", "contract_version")
    input_class = metadata["input_class"]
    if input_class not in INPUT_CLASSES:
        raise OperatingContractError("metadata.input_class", "input_class")
    if metadata["currency"] != "MXN":
        raise OperatingContractError("metadata.currency", "currency")

    if input_class == "BLANK":
        if not allow_blank:
            raise OperatingContractError("metadata.blank_not_buildable", "input_class")
        if metadata["cutoff_at"] is not None or metadata["timezone"] is not None:
            raise OperatingContractError("metadata.blank_template", "cutoff_at")
        cutoff_local_date = None
    else:
        cutoff_value = metadata["cutoff_at"]
        if not isinstance(cutoff_value, str):
            raise OperatingContractError("metadata.cutoff_at", "cutoff_at")
        try:
            cutoff = datetime.fromisoformat(cutoff_value)
        except ValueError as exc:
            raise OperatingContractError("metadata.cutoff_at", "cutoff_at") from exc
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise OperatingContractError("metadata.cutoff_at", "cutoff_at")
        timezone_name = metadata["timezone"]
        if not isinstance(timezone_name, str):
            raise OperatingContractError("metadata.timezone", "timezone")
        try:
            zone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            expected_offset = _fallback_iana_offset(timezone_name, cutoff)
            if expected_offset is None:
                raise OperatingContractError("metadata.timezone", "timezone") from exc
            cutoff_local_date = cutoff.date()
        else:
            local_cutoff = cutoff.astimezone(zone)
            expected_offset = local_cutoff.utcoffset()
            cutoff_local_date = local_cutoff.date()
        if expected_offset != cutoff.utcoffset():
            raise OperatingContractError("metadata.timezone_offset", "timezone")

    coverage = metadata["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != set(SOURCE_NAMES):
        raise OperatingContractError("metadata.coverage_keys", "coverage")
    for source in SOURCE_NAMES:
        location = f"coverage.{source}"
        entry = coverage[source]
        if not isinstance(entry, dict) or set(entry) != {"status", "window_start", "window_end"}:
            raise OperatingContractError("metadata.coverage_shape", location)
        status = entry["status"]
        if status not in COVERAGE_STATUSES:
            raise OperatingContractError("metadata.coverage_status", f"{location}.status")
        start_value, end_value = entry["window_start"], entry["window_end"]
        if (start_value is None) != (end_value is None):
            raise OperatingContractError("metadata.coverage_window", location)
        if start_value is not None:
            start = _parse_date(start_value, f"{location}.window_start")
            end = _parse_date(end_value, f"{location}.window_end")
            if start > end or (cutoff_local_date is not None and end > cutoff_local_date):
                raise OperatingContractError("metadata.coverage_window", location)
        if input_class == "BLANK" and (status != "MISSING" or start_value is not None):
            raise OperatingContractError("metadata.blank_template", location)
        if status in {"MISSING", "NOT_APPLICABLE"} and start_value is not None:
            raise OperatingContractError("metadata.coverage_window", location)
        if status == "ERROR" and not allow_blank:
            raise OperatingContractError("metadata.coverage_error", location)


__all__ = [
    "CONTRACT_VERSION",
    "COVERAGE_STATUSES",
    "CUT_IDENTITY_FIELDS",
    "INPUT_CLASSES",
    "METADATA_FIELDS",
    "SOURCE_NAMES",
    "SOURCES",
    "TOKEN_PATTERN",
    "OperatingContractError",
    "canonical_json",
    "columns_for",
    "source_contract",
    "validate_metadata",
]
