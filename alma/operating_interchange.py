"""Strict parser and whole-pack validator for ``operating-v1`` sources."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .operating_contracts import (
    SOURCE_NAMES,
    TOKEN_PATTERN,
    OperatingContractError,
    canonical_json,
    columns_for,
    source_contract,
    validate_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
MAX_METADATA_BYTES = 1_000_000
MAX_CSV_BYTES = 20_000_000
MAX_ROWS_PER_SOURCE = 250_000
_TOKEN = re.compile(TOKEN_PATTERN)
_INTEGER = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_PHONE_LIKE = re.compile(r"^[0-9]{7,15}$")


def _fail(code: str, location: str) -> None:
    raise OperatingContractError(code, location)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _read_metadata(pack: Path) -> tuple[dict[str, Any], str]:
    path = pack / "metadata.json"
    if path.is_symlink():
        _fail("path.symlink", "metadata.json")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise OperatingContractError("metadata.missing", "metadata.json") from exc
    if size > MAX_METADATA_BYTES:
        _fail("metadata.size", "metadata.json")
    raw = path.read_bytes()
    try:
        metadata = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatingContractError("metadata.json", "metadata.json") from exc
    validate_metadata(metadata)
    return metadata, hashlib.sha256(raw).hexdigest()


def _coerce_value(
    source: str,
    field: dict[str, Any],
    raw: str,
    row_number: int,
    cutoff_date: date,
) -> Any:
    name = field["name"]
    location = f"{source}.csv:{row_number}:{name}"
    if raw == "":
        if field["nullable"]:
            return None
        _fail("value.required", location)

    field_type = field["type"]
    if field_type in {"integer", "nonnegative_integer", "signed_integer"}:
        if not _INTEGER.fullmatch(raw):
            _fail("value.integer", location)
        value = int(raw)
        if field_type == "nonnegative_integer" and value < 0:
            _fail("value.range", location)
        if name == "selling_fee_bps" and value > 10_000:
            _fail("value.range", location)
    elif field_type == "date":
        try:
            value = date.fromisoformat(raw)
        except ValueError as exc:
            raise OperatingContractError("value.date", location) from exc
        if value.isoformat() != raw:
            _fail("value.date", location)
        if name not in {"promised_date", "due_date", "period_end"} and value > cutoff_date:
            _fail("value.after_cutoff", location)
    elif field_type == "timestamp":
        try:
            value = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise OperatingContractError("value.timestamp", location) from exc
        if value.tzinfo is None or value.utcoffset() is None:
            _fail("value.timestamp", location)
    else:
        if not _TOKEN.fullmatch(raw):
            _fail("value.token", location)
        if _PHONE_LIKE.fullmatch(raw):
            _fail("value.pii", location)
        value = raw

    allowed = field["enum"]
    if allowed is not None and value not in allowed:
        _fail("value.enum", location)
    return value


def _read_source(pack: Path, source: str, cutoff_date: date) -> tuple[list[dict[str, Any]], str]:
    filename = f"{source}.csv"
    path = pack / filename
    if path.is_symlink():
        _fail("path.symlink", filename)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise OperatingContractError("csv.missing", filename) from exc
    if size > MAX_CSV_BYTES:
        _fail("csv.size", filename)
    raw_bytes = path.read_bytes()
    fields = source_contract(source)["fields"]
    expected = list(columns_for(source))
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            try:
                header = next(reader)
            except StopIteration:
                _fail("csv.header", filename)
            if len(set(header)) != len(header):
                _fail("csv.header_duplicate", f"{filename}:1")
            if header != expected:
                if len(header) == len(expected) and set(header) == set(expected):
                    _fail("csv.header_order", f"{filename}:1")
                _fail("csv.header", f"{filename}:1")
            for row_number, values in enumerate(reader, start=2):
                if row_number > MAX_ROWS_PER_SOURCE + 1:
                    _fail("csv.rows", filename)
                if len(values) != len(expected):
                    _fail("csv.ragged", f"{filename}:{row_number}")
                rows.append({
                    field["name"]: _coerce_value(source, field, raw, row_number, cutoff_date)
                    for field, raw in zip(fields, values, strict=True)
                })
    except UnicodeDecodeError as exc:
        raise OperatingContractError("csv.encoding", filename) from exc
    return rows, hashlib.sha256(raw_bytes).hexdigest()


def _row_location(source: str, index: int, column: str | None = None) -> str:
    base = f"{source}.csv:{index + 2}"
    return f"{base}:{column}" if column else base


def _validate_keys(tables: dict[str, list[dict[str, Any]]]) -> None:
    for source in SOURCE_NAMES:
        contract = source_contract(source)
        constraints = [contract["primary_key"], *contract["unique"]]
        for columns in constraints:
            seen: set[tuple[Any, ...]] = set()
            for index, row in enumerate(tables[source]):
                key = tuple(row[column] for column in columns)
                if key in seen:
                    _fail("key.duplicate", _row_location(source, index))
                seen.add(key)
        for columns in contract.get("unique_non_null", ()):
            seen_non_null: set[tuple[Any, ...]] = set()
            for index, row in enumerate(tables[source]):
                key = tuple(row[column] for column in columns)
                if any(value is None for value in key):
                    continue
                if key in seen_non_null:
                    _fail("key.duplicate", _row_location(source, index))
                seen_non_null.add(key)


def _index(tables: dict[str, list[dict[str, Any]]], source: str, columns: tuple[str, ...]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {tuple(row[column] for column in columns): row for row in tables[source]}


def _validate_declared_foreign_keys(tables: dict[str, list[dict[str, Any]]]) -> None:
    cache: dict[tuple[str, tuple[str, ...]], set[tuple[Any, ...]]] = {}
    for source in SOURCE_NAMES:
        contract = source_contract(source)
        for index, row in enumerate(tables[source]):
            for field in contract["fields"]:
                foreign = field["foreign_key"]
                value = row[field["name"]]
                if foreign is None or value is None:
                    continue
                if source == "cash_events" and field["name"] == "supersedes_event_id":
                    continue  # D-11 emits more precise orphan/self/cycle diagnostics below.
                target, target_fields = foreign
                cache_key = (target, tuple(target_fields))
                if cache_key not in cache:
                    cache[cache_key] = {
                        tuple(target_row[column] for column in target_fields)
                        for target_row in tables[target]
                        if all(target_row[column] is not None for column in target_fields)
                    }
                if (value,) not in cache[cache_key]:
                    if field["name"] == "sku_id":
                        code = "relation.demand_sku" if source == "unmet_demand" else "relation.sku"
                    elif field["name"] == "receipt_id":
                        code = "relation.receipt"
                    elif field["name"] == "obligation_id":
                        code = "relation.obligation"
                    elif field["name"] == "payment_id":
                        code = "relation.payment"
                    elif field["name"] == "delivery_cohort_id":
                        code = "relation.cohort"
                    else:
                        code = "relation.foreign_key"
                    _fail(code, _row_location(source, index, field["name"]))


def _validate_rows(tables: dict[str, list[dict[str, Any]]], metadata: dict[str, Any]) -> None:
    cutoff = datetime.fromisoformat(metadata["cutoff_at"]).date()
    sales = _index(tables, "sales_aggregates", ("sales_date", "sku_id", "channel_code"))
    cohorts = {row["delivery_cohort_id"]: row for row in tables["sales_aggregates"] if row["delivery_cohort_id"] is not None}
    receipts = _index(tables, "purchase_receipts", ("receipt_id",))
    purchase_orders = _index(tables, "purchase_orders", ("purchase_order_id",))
    obligations = _index(tables, "obligations", ("obligation_id",))
    payments = _index(tables, "obligation_payments", ("payment_id",))
    budgets = _index(tables, "budgets", ("budget_id",))
    expenses = _index(tables, "expenses", ("expense_id",))
    quality = _index(tables, "quality_events", ("quality_event_id",))
    loans = _index(tables, "loans", ("loan_id",))

    for index, row in enumerate(tables["sales_aggregates"]):
        if row["restocked_units"] > row["returned_units"]:
            _fail("sales.restock", _row_location("sales_aggregates", index))
    for index, row in enumerate(tables["inventory_counts"]):
        if row["reserved_units"] + row["non_sellable_units"] > row["on_hand_units"]:
            _fail("inventory.count", _row_location("inventory_counts", index))
    for index, row in enumerate(tables["availability_daily"]):
        if row["sellable_minutes"] + row["stockout_minutes"] > row["observed_minutes"] or row["observed_minutes"] > 1440:
            _fail("availability.minutes", _row_location("availability_daily", index))

    received_by_order: dict[str, int] = defaultdict(int)
    for index, row in enumerate(tables["purchase_receipts"]):
        purchase_order = purchase_orders[(row["purchase_order_id"],)]
        if row["received_date"] < purchase_order["order_date"]:
            _fail("receipt.date", _row_location("purchase_receipts", index))
        if row["received_units"] != row["inspection_units"] + row["accepted_units"] + row["rejected_units"]:
            _fail("receipt.disposition", _row_location("purchase_receipts", index))
        received_by_order[row["purchase_order_id"]] += row["received_units"]
    for purchase_order_id, received in received_by_order.items():
        if received > purchase_orders[(purchase_order_id,)]["ordered_units"]:
            _fail("receipt.ordered_limit", "purchase_receipts.csv")

    for index, row in enumerate(tables["obligations"]):
        target = purchase_orders if row["origin_type"] == "PURCHASE_ORDER" else expenses
        if (row["origin_id"],) not in target:
            _fail("relation.origin", _row_location("obligations", index, "origin_id"))
    paid_by_obligation: dict[str, int] = defaultdict(int)
    for row in tables["obligation_payments"]:
        paid_by_obligation[row["obligation_id"]] += row["amount_cents"]
    for obligation_id, paid in paid_by_obligation.items():
        if paid > obligations[(obligation_id,)]["original_cents"]:
            _fail("payment.amount", "obligation_payments.csv")

    components = _index(tables, "cost_components", ("component_id",))
    versions = _index(tables, "cost_versions", ("cost_version_id",))
    allocated: dict[str, int] = defaultdict(int)
    residual: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(tables["cost_allocations"]):
        component = components[(row["component_id"],)]
        version = versions[(component["cost_version_id"],)]
        if row["sku_id"] != version["sku_id"]:
            _fail("cost.allocation_sku", _row_location("cost_allocations", index))
        allocated[row["component_id"]] += row["allocated_cents"]
        residual[row["component_id"]].add(row["remainder_cents"])
    for component_id, total in allocated.items():
        component = components[(component_id,)]
        if component["amount_cents"] is None or len(residual[component_id]) != 1 or total + next(iter(residual[component_id])) != component["amount_cents"]:
            _fail("cost.reconciliation", "cost_allocations.csv")
    for index, row in enumerate(tables["cost_components"]):
        included = row["included_in_component_id"]
        if included is not None:
            if included == row["component_id"]:
                _fail("cost.inclusion_self", _row_location("cost_components", index))
            if components[(included,)]["cost_version_id"] != row["cost_version_id"]:
                _fail("cost.inclusion_version", _row_location("cost_components", index))
    for component in tables["cost_components"]:
        seen: set[str] = set()
        current = component
        while current["included_in_component_id"] is not None:
            if current["component_id"] in seen:
                _fail("cost.inclusion_cycle", "cost_components.csv")
            seen.add(current["component_id"])
            current = components[(current["included_in_component_id"],)]

    allocations_by_origin: dict[tuple[str, str], int] = defaultdict(int)
    for index, row in enumerate(tables["budget_allocations"]):
        budget = budgets[(row["budget_id"],)]
        if (row["drop_code"], row["channel_code"]) != (budget["drop_code"], budget["channel_code"]):
            _fail("budget.dimension", _row_location("budget_allocations", index))
        target = purchase_orders if row["origin_type"] == "PURCHASE_ORDER" else expenses
        if (row["origin_id"],) not in target:
            _fail("relation.origin", _row_location("budget_allocations", index, "origin_id"))
        allocations_by_origin[(row["origin_type"], row["origin_id"])] += row["allocated_cents"]
    for (origin_type, origin_id), total in allocations_by_origin.items():
        target = purchase_orders if origin_type == "PURCHASE_ORDER" else expenses
        origin = target[(origin_id,)]
        limit = origin["ordered_units"] * origin["agreed_unit_cents"] if origin_type == "PURCHASE_ORDER" else origin["amount_cents"]
        if total > limit:
            _fail("budget.origin_limit", "budget_allocations.csv")

    reservation_balances: dict[str, int] = defaultdict(int)
    reservation_skus: dict[str, str] = {}
    for index, row in sorted(enumerate(tables["inventory_reservations"]), key=lambda item: (item[1]["event_date"], item[0])):
        reservation = row["reservation_id"]
        previous_sku = reservation_skus.setdefault(reservation, row["sku_id"])
        if previous_sku != row["sku_id"]:
            _fail("reservation.sku", _row_location("inventory_reservations", index))
        delta = row["units"] if row["event_type"] == "PLACE" else -row["units"]
        reservation_balances[reservation] += delta
        if reservation_balances[reservation] < 0:
            _fail("reservation.negative", _row_location("inventory_reservations", index))
    if (
        metadata["coverage"]["inventory_reservations"]["status"] == "COMPLETE"
        and metadata["coverage"]["inventory_counts"]["status"] == "COMPLETE"
    ):
        reservation_end = date.fromisoformat(metadata["coverage"]["inventory_reservations"]["window_end"])
        active_by_sku: dict[str, int] = defaultdict(int)
        for reservation, balance in reservation_balances.items():
            active_by_sku[reservation_skus[reservation]] += balance
        count_by_sku = {
            row["sku_id"]: row
            for row in tables["inventory_counts"]
            if row["cutoff_date"] == reservation_end
        }
        for sku_id in {row["sku_id"] for row in tables["sku_catalog"]}:
            if sku_id not in count_by_sku or count_by_sku[sku_id]["reserved_units"] != active_by_sku[sku_id]:
                _fail("reservation.count_reconciliation", "inventory_counts.csv")

    movement_links: dict[tuple[str, str], int] = defaultdict(int)
    opening_by_sku: dict[str, int] = defaultdict(int)
    for index, row in enumerate(tables["inventory_movements"]):
        movement_type = row["movement_type"]
        if movement_type == "OPENING":
            opening_by_sku[row["sku_id"]] += 1
        elif movement_type == "RECEIPT_ACCEPTED":
            receipt_id = row["receipt_id"]
            if receipt_id is None or (receipt_id,) not in receipts:
                _fail("relation.receipt", _row_location("inventory_movements", index, "receipt_id"))
            movement_links[(movement_type, receipt_id)] += 1
            if row["units"] != receipts[(receipt_id,)]["accepted_units"]:
                _fail("stock.units", _row_location("inventory_movements", index))
        elif movement_type == "SALE_OUT":
            key = (row["sales_date"], row["sku_id"], row["sales_channel_code"])
            if None in key or key not in sales:
                _fail("relation.sales", _row_location("inventory_movements", index))
            movement_links[(movement_type, repr(key))] += 1
            if row["units"] != sales[key]["delivered_units"]:
                _fail("stock.units", _row_location("inventory_movements", index))
        elif movement_type == "RETURN_RESTOCK":
            quality_id = row["quality_event_id"]
            if quality_id is None or (quality_id,) not in quality:
                _fail("relation.quality", _row_location("inventory_movements", index))
            movement_links[(movement_type, quality_id)] += 1
            if row["units"] > quality[(quality_id,)]["units"]:
                _fail("stock.units", _row_location("inventory_movements", index))
        elif movement_type in {"LOAN_OUT", "LOAN_IN"}:
            loan_id = row["loan_id"]
            if loan_id is None or (loan_id,) not in loans:
                _fail("relation.loan", _row_location("inventory_movements", index))
            movement_links[(movement_type, loan_id)] += 1
            if row["units"] != loans[(loan_id,)]["quantity"]:
                _fail("stock.units", _row_location("inventory_movements", index))
        if any(count > 1 for count in movement_links.values()):
            _fail("stock.duplicate_post", _row_location("inventory_movements", index))
    for (receipt_id,), receipt in receipts.items():
        if receipt["accepted_units"] > 0 and movement_links[("RECEIPT_ACCEPTED", receipt_id)] != 1:
            _fail("stock.missing_post", "inventory_movements.csv")
    for sales_key, sales_row in sales.items():
        if sales_row["delivered_units"] > 0 and movement_links[("SALE_OUT", repr(sales_key))] != 1:
            _fail("stock.missing_post", "inventory_movements.csv")
    movement_coverage = metadata["coverage"]["inventory_movements"]
    if movement_coverage["status"] == "COMPLETE":
        expected_start = date.fromisoformat(movement_coverage["window_start"])
        sku_ids = {row["sku_id"] for row in tables["sku_catalog"]}
        if any(opening_by_sku[sku] != 1 for sku in sku_ids):
            _fail("stock.opening", "inventory_movements.csv")
        if any(row["event_date"] != expected_start for row in tables["inventory_movements"] if row["movement_type"] == "OPENING"):
            _fail("stock.opening_date", "inventory_movements.csv")

    for index, row in enumerate(tables["quality_events"]):
        cohort_id = row["delivery_cohort_id"]
        if cohort_id is not None:
            cohort = cohorts.get(cohort_id)
            if cohort is None or cohort["sku_id"] != row["sku_id"]:
                _fail("relation.cohort", _row_location("quality_events", index, "delivery_cohort_id"))
        if metadata["coverage"]["quality_events"]["status"] == "COMPLETE" and row["event_type"].startswith("RETURN_") and cohort_id is None:
            _fail("quality.cohort_required", _row_location("quality_events", index))

    for index, row in enumerate(tables["loans"]):
        if row["due_date"] is not None and row["due_date"] < row["borrowed_date"]:
            _fail("loan.due_date", _row_location("loans", index))
        if row["returned_date"] is not None and row["returned_date"] < row["borrowed_date"]:
            _fail("loan.returned_date", _row_location("loans", index))

    _validate_cash(tables, obligations, payments, cutoff)


def _validate_cash(
    tables: dict[str, list[dict[str, Any]]],
    obligations: dict[tuple[Any, ...], dict[str, Any]],
    payments: dict[tuple[Any, ...], dict[str, Any]],
    cutoff: date,
) -> None:
    events = tables["cash_events"]
    by_id = {row["event_id"]: row for row in events}
    successors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    level_rank = {"UNDATED": 0, "EXPECTED": 1, "COMMITTED": 2, "RECONCILED": 3}
    for index, row in enumerate(events):
        group = (row["scenario_id"], row["economic_event_id"])
        groups[group].append(row)
        predecessor_id = row["supersedes_event_id"]
        if predecessor_id is not None:
            if predecessor_id == row["event_id"]:
                _fail("cash.supersedes_self", _row_location("cash_events", index))
            predecessor = by_id.get(predecessor_id)
            if predecessor is None:
                _fail("cash.supersedes_orphan", _row_location("cash_events", index))
            if (predecessor["scenario_id"], predecessor["economic_event_id"]) != group:
                _fail("cash.supersedes_identity", _row_location("cash_events", index))
            if predecessor["direction"] != row["direction"] or predecessor["currency"] != row["currency"] or predecessor["obligation_id"] != row["obligation_id"]:
                _fail("cash.supersedes_origin", _row_location("cash_events", index))
            visited = {row["event_id"]}
            cursor = predecessor
            while True:
                if cursor["event_id"] in visited:
                    _fail("cash.supersedes_cycle", _row_location("cash_events", index))
                visited.add(cursor["event_id"])
                cursor_predecessor = cursor["supersedes_event_id"]
                if cursor_predecessor is None:
                    break
                if cursor_predecessor not in by_id:
                    _fail("cash.supersedes_orphan", _row_location("cash_events", index))
                cursor = by_id[cursor_predecessor]
            if predecessor["level"] == "RECONCILED" or predecessor["level"] == "SCENARIO" or row["level"] == "SCENARIO":
                _fail("cash.supersedes_level", _row_location("cash_events", index))
            if level_rank[row["level"]] < level_rank[predecessor["level"]]:
                _fail("cash.supersedes_level", _row_location("cash_events", index))
            successors[predecessor_id].append(row)
        if row["level"] == "COMMITTED" and row["obligation_id"] is None:
            _fail("cash.committed_origin", _row_location("cash_events", index))
        if row["level"] in {"EXPECTED", "UNDATED", "SCENARIO"} and (row["obligation_id"] is not None or row["payment_id"] is not None):
            _fail("cash.layer_origin", _row_location("cash_events", index))
        if row["level"] == "SCENARIO" and predecessor_id is not None:
            _fail("cash.scenario_chain", _row_location("cash_events", index))
    if any(len(values) > 1 for values in successors.values()):
        _fail("cash.supersedes_fork", "cash_events.csv")

    active: list[dict[str, Any]] = []
    for group, rows in groups.items():
        roots = [row for row in rows if row["supersedes_event_id"] is None]
        leaves = [row for row in rows if row["event_id"] not in successors]
        edges = sum(1 for row in rows if row["supersedes_event_id"] is not None)
        if len(rows) > 1 and (len(roots) != 1 or len(leaves) != 1 or edges != len(rows) - 1):
            visited: set[str] = set()
            current = rows[0]
            while current["supersedes_event_id"] is not None:
                if current["event_id"] in visited:
                    _fail("cash.supersedes_cycle", "cash_events.csv")
                visited.add(current["event_id"])
                current = by_id[current["supersedes_event_id"]]
            _fail("cash.supersedes_chain", "cash_events.csv")
        active.extend(leaves)

    active_payment_ids: set[str] = set()
    active_observed_refs: set[tuple[str, str]] = set()
    for row in active:
        if row["level"] != "RECONCILED":
            continue
        if row["event_date"] is None:
            _fail("cash.reconciled_date", "cash_events.csv")
        payment_id = row["payment_id"]
        if payment_id is not None:
            if payment_id in active_payment_ids:
                _fail("cash.payment_duplicate", "cash_events.csv")
            active_payment_ids.add(payment_id)
            payment = payments.get((payment_id,))
            if payment is None:
                _fail("relation.payment", "cash_events.csv")
            if row["obligation_id"] != payment["obligation_id"] or row["amount_cents"] != payment["amount_cents"] or row["event_date"] != payment["paid_date"] or row["direction"] != "OUTFLOW":
                _fail("cash.payment_match", "cash_events.csv")
        elif row["obligation_id"] is not None:
            _fail("cash.reconciled_origin", "cash_events.csv")
        else:
            observed_ref = (row["scenario_id"], row["source_ref"])
            if observed_ref in active_observed_refs:
                _fail("cash.source_ref", "cash_events.csv")
            active_observed_refs.add(observed_ref)

    observed_windows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(tables["cash_balance_evidence"]):
        if row["period_start"] > row["period_end"]:
            _fail("cash.balance_window", _row_location("cash_balance_evidence", index))
        if row["evidence_status"] == "OBSERVED":
            required = ("opening_balance_cents", "closing_balance_cents", "opening_observed_at", "closing_observed_at")
            if any(row[field] is None for field in required):
                _fail("cash.balance_observed", _row_location("cash_balance_evidence", index))
            if row["opening_observed_at"] > row["closing_observed_at"]:
                _fail("cash.balance_observed", _row_location("cash_balance_evidence", index))
            if (
                row["opening_observed_at"].date() != row["period_start"]
                or row["closing_observed_at"].date() != row["period_end"]
            ):
                _fail("cash.balance_observed", _row_location("cash_balance_evidence", index))
            observed_windows[row["scenario_id"]].append(row)
    for scenario, windows in observed_windows.items():
        ordered = sorted(windows, key=lambda row: row["period_start"])
        for previous, current in zip(ordered, ordered[1:]):
            if current["period_start"] <= previous["period_end"]:
                _fail("cash.balance_overlap", "cash_balance_evidence.csv")
        for window in ordered:
            signed = sum(
                row["amount_cents"] * (1 if row["direction"] == "INFLOW" else -1)
                for row in active
                if row["level"] == "RECONCILED"
                and row["scenario_id"] == scenario
                and window["period_start"] <= row["event_date"] <= window["period_end"]
            )
            if window["closing_balance_cents"] - window["opening_balance_cents"] != signed:
                _fail("cash.balance", "cash_balance_evidence.csv")
    for row in active:
        if row["level"] == "RECONCILED" and not any(
            window["period_start"] <= row["event_date"] <= window["period_end"]
            for window in observed_windows.get(row["scenario_id"], [])
        ):
            _fail("cash.balance_missing", "cash_events.csv")


def parse_pack(path: str | Path, *, private_root: str | Path | None = None) -> dict[str, Any]:
    """Parse and validate a complete pack without creating persistent output."""

    pack = Path(path)
    if pack.is_symlink():
        _fail("path.symlink", "pack")
    try:
        resolved = pack.resolve(strict=True)
    except OSError as exc:
        raise OperatingContractError("path.missing", "pack") from exc
    if not resolved.is_dir():
        _fail("path.directory", "pack")
    expected_files = {"metadata.json", *(f"{name}.csv" for name in SOURCE_NAMES)}
    actual_files = {child.name for child in resolved.iterdir()}
    if actual_files != expected_files or any(not child.is_file() for child in resolved.iterdir()):
        _fail("pack.files", "pack")
    if any(child.is_symlink() for child in resolved.iterdir()):
        _fail("path.symlink", "pack")

    metadata, metadata_sha256 = _read_metadata(resolved)
    if metadata["input_class"] == "PRIVATE":
        authorized_root = Path(private_root) if private_root is not None else ROOT / ".local"
        try:
            authorized_root = authorized_root.resolve(strict=True)
        except OSError as exc:
            raise OperatingContractError("path.private_root", "pack") from exc
        if not _inside(resolved, authorized_root):
            _fail("path.private_root", "pack")

    cutoff_date = datetime.fromisoformat(metadata["cutoff_at"]).date()
    tables: dict[str, list[dict[str, Any]]] = {}
    source_sha256: dict[str, str] = {}
    for source in SOURCE_NAMES:
        rows, digest = _read_source(resolved, source, cutoff_date)
        coverage = metadata["coverage"][source]
        if coverage["status"] in {"MISSING", "NOT_APPLICABLE", "ZERO"} and rows:
            _fail("coverage.rows", f"coverage.{source}")
        if coverage["status"] == "ZERO" and coverage["window_start"] is None:
            _fail("coverage.zero_window", f"coverage.{source}")
        tables[source] = rows
        source_sha256[f"{source}.csv"] = digest

    _validate_keys(tables)
    _validate_declared_foreign_keys(tables)
    _validate_rows(tables, metadata)
    normalized_rows_digest = hashlib.sha256(canonical_json(_jsonable(tables))).hexdigest()
    return {
        "metadata": metadata,
        "tables": tables,
        "source_sha256": source_sha256,
        "metadata_sha256": metadata_sha256,
        "normalized_rows_digest": normalized_rows_digest,
        "diagnostics": [],
    }


__all__ = [
    "MAX_CSV_BYTES",
    "MAX_METADATA_BYTES",
    "MAX_ROWS_PER_SOURCE",
    "parse_pack",
]
