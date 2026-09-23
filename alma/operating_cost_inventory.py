"""Exact cost and inventory calculations over a verified operating-v1 cut."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Iterable

from alma.operating_mart_contracts import BoundCut, Policy

SQL_PATH = Path(__file__).resolve().parents[1] / "models" / "operating_cost_inventory.sql"


def _query(name: str) -> str:
    blocks = SQL_PATH.read_text(encoding="utf-8").split("-- name: ")
    for block in blocks[1:]:
        label, _, statement = block.partition("\n")
        if label.strip() == name:
            return statement.strip()
    raise ValueError(f"unknown cost/inventory query: {name}")


def _rows(cut: BoundCut, statement: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in cut.connection.execute(statement, parameters)]


def allocate_unit_cents(amount_cents: int, quantity: int) -> tuple[int, ...]:
    """Residual cents go to the lowest stable ordinal first."""
    if not isinstance(amount_cents, int) or amount_cents < 0 or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("invalid cent allocation basis")
    base, residual = divmod(amount_cents, quantity)
    return tuple(base + (ordinal < residual) for ordinal in range(quantity))


def select_cost_version(versions: Iterable[dict[str, Any]], as_of: str) -> dict[str, Any] | None:
    eligible = [version for version in versions if version["lifecycle_status"] == "ACTIVE" and version["effective_date"] <= as_of]
    dates = [version["effective_date"] for version in eligible]
    if len(dates) != len(set(dates)):
        raise ValueError("overlapping approved cost versions")
    return max(eligible, key=lambda version: version["effective_date"], default=None)


def evaluate_cost_version(
    version: dict[str, Any], components: Iterable[dict[str, Any]],
    allocations: Iterable[dict[str, Any]], policy: Policy,
) -> dict[str, Any]:
    components = list(components)
    allocations = list(allocations)
    by_id = {component["component_id"]: component for component in components}
    if len(by_id) != len(components):
        raise ValueError("duplicate component id")
    included = set(policy.content["bases"]["landed_cost_inclusions"])
    for component in components:
        trail: set[str] = set()
        current = component
        while current["included_in_component_id"] is not None:
            parent = current["included_in_component_id"]
            if parent in trail or parent == component["component_id"]:
                raise ValueError("component inclusion cycle")
            trail.add(parent)
            if parent not in by_id:
                raise ValueError("missing included component")
            current = by_id[parent]
    allocation_by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for allocation in allocations:
        if allocation["component_id"] not in by_id or allocation["sku_id"] != version["sku_id"]:
            raise ValueError("allocation crosses SKU or version")
        allocation_by_component[allocation["component_id"]].append(allocation)
    known_sum = 0
    unallocated = 0
    complete = True
    estimated = False
    source_refs: list[str] = []
    for component in components:
        if component["classification"] not in included or component["included_in_component_id"] is not None:
            continue
        source_refs.append(component["source_ref"])
        amount = component["amount_cents"]
        quality = component["quality_status"]
        if amount is None or quality == "MISSING":
            if component["required_flag"]:
                complete = False
            continue
        if not isinstance(amount, int) or amount < 0:
            raise ValueError("invalid component cents")
        known_sum += amount
        estimated |= quality == "ESTIMATED"
        parts = allocation_by_component[component["component_id"]]
        allocated = sum(part["allocated_cents"] for part in parts)
        remainder = sum(part["remainder_cents"] for part in parts)
        if parts and allocated + remainder != amount:
            raise ValueError("component cents do not reconcile")
        if not parts:
            remainder = amount
        unallocated += remainder
        source_refs.extend(part["source_ref"] for part in parts)
    basis = version["quantity_basis"]
    if not isinstance(basis, int) or basis <= 0 or unallocated:
        complete = False
    quality = None if not complete else ("COMPLETE_ESTIMATED" if estimated else "COMPLETE_DOCUMENTED")
    status = "PARTIAL" if not complete else ("ESTIMATED" if estimated else "MEASURED")
    return {
        "cost_version_id": version["cost_version_id"],
        "known_sum_cents": known_sum,
        "complete_cost_cents": known_sum if complete else None,
        "unallocated_cents": unallocated,
        "unit_cost_cents": allocate_unit_cents(known_sum, basis) if complete else None,
        "public_price_cents": version["public_price_cents"],
        "quality": quality,
        "status": status,
        "source_refs": tuple(sorted(set(source_refs))),
        "reconciliation_id": f'cost:{version["cost_version_id"]}',
    }


def project_cost(cut: BoundCut, sku_id: str, as_of: str, policy: Policy) -> dict[str, Any]:
    versions = _rows(cut, "SELECT * FROM cost_versions WHERE sku_id = :sku_id ORDER BY effective_date", {"sku_id": sku_id})
    version = select_cost_version(versions, as_of)
    if version is None:
        return {"status": "UNKNOWN", "complete_cost_cents": None, "known_sum_cents": 0,
                "cost_version_id": None, "source_refs": ()}
    components = _rows(cut, _query("cost_components"), {"cost_version_id": version["cost_version_id"]})
    allocations = _rows(cut, _query("cost_allocations"), {"cost_version_id": version["cost_version_id"]})
    result = evaluate_cost_version(version, components, allocations, policy)
    coverage = [cut.coverage_status(source, as_of) for source in ("cost_versions", "cost_components", "cost_allocations")]
    if not all(status in {"COMPLETE", "ZERO"} for status in coverage):
        result["status"] = "PARTIAL" if result["known_sum_cents"] else "UNKNOWN"
        result["complete_cost_cents"] = None
        result["unit_cost_cents"] = None
        result["quality"] = None
    if cut.input_class != "SYNTHETIC_EXAMPLE" and not policy.authorizes_real_cut:
        result["status"] = "PARTIAL" if result["known_sum_cents"] else "UNKNOWN"
        result["complete_cost_cents"] = None
        result["unit_cost_cents"] = None
        result["quality"] = None
    result.update(policy_version=policy.version, policy_sha256=policy.sha256, policy_status=policy.status)
    return result


def economics_ratios(net_revenue_cents: int, cogs_cents: int, variable_cost_cents: int) -> dict[str, str | None]:
    if any(not isinstance(value, int) for value in (net_revenue_cents, cogs_cents, variable_cost_cents)):
        raise ValueError("economics requires integer cents")

    def ratio(numerator: int, denominator: int) -> str | None:
        if denominator == 0:
            return None
        result = (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_EVEN)
        return format(result.normalize(), "f")

    gross = net_revenue_cents - cogs_cents
    contribution = gross - variable_cost_cents
    return {"markup": ratio(gross, cogs_cents), "gross_margin": ratio(gross, net_revenue_cents),
            "contribution_margin": ratio(contribution, net_revenue_cents)}


def realized_economics(
    cut: BoundCut, sku_id: str, channel_code: str, start: str, end: str, policy: Policy,
) -> dict[str, Any]:
    """Same-grain realized economics over a half-open local-date window."""
    if start >= end:
        raise ValueError("empty or reversed economics window")
    # Ordinals belong to the canonical SKU/version stream, not to a report slice.
    # Earlier dates and other channels consume residual cents before this slice.
    canonical = _rows(cut,
        "SELECT sales_date, sku_id, channel_code, delivered_units, net_revenue_cents, "
        "variable_cost_cents, coverage_status, source_ref FROM sales_aggregates "
        "WHERE sku_id=:sku AND sales_date<:end "
        "ORDER BY sales_date, sku_id, channel_code",
        {"sku": sku_id, "end": end})
    sales = [row for row in canonical if row["channel_code"] == channel_code and
             start <= row["sales_date"] < end]
    revenue = sum(row["net_revenue_cents"] for row in sales)
    delivered = sum(row["delivered_units"] for row in sales)
    variable = sum(row["variable_cost_cents"] for row in sales if row["variable_cost_cents"] is not None)
    cogs = 0
    ordinal_by_version: dict[str, int] = defaultdict(int)
    complete = bool(sales) and all(row["coverage_status"] == "COMPLETE" and row["variable_cost_cents"] is not None for row in sales)
    estimated = False
    source_refs = [row["source_ref"] for row in sales]
    version_ids: list[str] = []
    public_prices: dict[str, int] = {}
    for row in canonical:
        selected = row["channel_code"] == channel_code and start <= row["sales_date"] < end
        cost = project_cost(cut, sku_id, row["sales_date"], policy)
        version_id = cost["cost_version_id"]
        if version_id is None or cost["unit_cost_cents"] is None:
            if selected:
                complete = False
            continue
        if selected:
            version_ids.append(version_id)
            public_prices[version_id] = cost["public_price_cents"]
            estimated |= cost["status"] == "ESTIMATED"
            source_refs.extend(cost["source_refs"])
        unit_costs = cost["unit_cost_cents"]
        if selected:
            basis = len(unit_costs)
            base, residual = divmod(cost["complete_cost_cents"], basis)
            start_ordinal = ordinal_by_version[version_id]
            count = row["delivered_units"]
            full_cycles, tail = divmod(count, basis)
            offset = start_ordinal % basis
            residual_hits = full_cycles * residual
            residual_hits += min(tail, max(0, residual - offset))
            residual_hits += min(max(0, tail - (basis - offset)), residual)
            cogs += count * base + residual_hits
        ordinal_by_version[version_id] += row["delivered_units"]
    last_day = (date.fromisoformat(end) - timedelta(days=1)).isoformat()
    coverage = cut.coverage_status("sales_aggregates", start)
    if coverage not in {"COMPLETE", "ZERO"} or cut.coverage_status("sales_aggregates", last_day) not in {"COMPLETE", "ZERO"}:
        complete = False
    if cut.input_class != "SYNTHETIC_EXAMPLE" and not policy.authorizes_real_cut:
        complete = False
    ratios = economics_ratios(revenue, cogs, variable) if complete else {"markup": None, "gross_margin": None, "contribution_margin": None}
    return {"status": ("ESTIMATED" if estimated else "MEASURED") if complete else
            ("PARTIAL" if sales else "UNKNOWN"),
            "net_revenue_cents": revenue if sales else None,
            "delivered_units": delivered if sales else None,
            "cogs_cents": cogs if complete else None,
            "variable_cost_cents": variable if complete else None,
            "gross_profit_cents": revenue - cogs if complete else None,
            "contribution_cents": revenue - cogs - variable if complete else None,
            "ratios": ratios, "public_prices_by_version": public_prices,
            "cost_version_ids": tuple(sorted(set(version_ids))),
            "source_refs": tuple(sorted(set(source_refs))),
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status,
            "reconciliation_id": f"economics:{cut.cut_id}:{sku_id}:{channel_code}:{start}:{end}"}


def reconcile_purchase(order: dict[str, Any], receipts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """One order and its distinct physical receipts, without stock side effects."""
    receipts = list(receipts)
    ids = [receipt["receipt_id"] for receipt in receipts]
    if len(ids) != len(set(ids)):
        raise ValueError("receipt replay")
    for receipt in receipts:
        if (any(not isinstance(receipt[field], int) or receipt[field] < 0 for field in
                ("received_units", "inspection_units", "accepted_units", "rejected_units"))
                or receipt["received_units"] != receipt["inspection_units"] + receipt["accepted_units"] + receipt["rejected_units"]):
            raise ValueError("receipt disposition mismatch")
    received = sum(receipt["received_units"] for receipt in receipts)
    ordered = order["ordered_units"]
    if not isinstance(ordered, int) or ordered < 0 or received > ordered:
        raise ValueError("receipt exceeds ordered units")
    cancelled = order["status_code"] == "CANCELLED"
    remaining = ordered - received
    return {
        "purchase_order_id": order["purchase_order_id"],
        "ordered_units": ordered, "received_units": received,
        "inspection_units": sum(receipt["inspection_units"] for receipt in receipts),
        "accepted_units": sum(receipt["accepted_units"] for receipt in receipts),
        "rejected_units": sum(receipt["rejected_units"] for receipt in receipts),
        "still_to_receive_units": 0 if cancelled else remaining,
        "cancelled_unreceived_units": remaining if cancelled else 0,
        "receipt_ids": tuple(sorted(ids)),
        "reconciliation_id": f'purchase:{order["purchase_order_id"]}',
    }


def project_purchases(cut: BoundCut, as_of: str) -> list[dict[str, Any]]:
    """Preaggregate purchase/receipt units before any other dimension joins."""
    aggregates = _rows(cut, _query("purchase_receipts"), {"as_of": as_of})
    results = []
    for aggregate in aggregates:
        receipts = _rows(cut,
            "SELECT * FROM purchase_receipts WHERE purchase_order_id=:po AND received_date<=:as_of "
            "ORDER BY receipt_id", {"po": aggregate["purchase_order_id"], "as_of": as_of})
        result = reconcile_purchase(aggregate, receipts)
        for field in ("received_units", "inspection_units", "accepted_units", "rejected_units"):
            if result[field] != aggregate[field]:
                raise ValueError("purchase preaggregation mismatch")
        coverage = (cut.coverage_status("purchase_orders", as_of),
                    cut.coverage_status("purchase_receipts", as_of))
        result.update(sku_id=aggregate["sku_id"], cut_id=cut.cut_id, as_of=as_of,
                      status="MEASURED" if all(value in {"COMPLETE", "ZERO"} for value in coverage) else "PARTIAL",
                      source_refs=tuple(sorted({row["source_ref"] for row in receipts})))
        results.append(result)
    return results


_MOVEMENT_SIGN = {
    "OPENING": 1, "RECEIPT_ACCEPTED": 1, "SALE_OUT": -1,
    "RETURN_RESTOCK": 1, "LOAN_OUT": -1, "LOAN_IN": 1,
    "ADJUSTMENT_IN": 1, "ADJUSTMENT_OUT": -1,
}


def project_inventory(cut: BoundCut, sku_id: str, as_of: str) -> dict[str, Any]:
    """Reconcile distinct movement identities with count and custody evidence."""
    movements = _rows(cut,
        "SELECT * FROM inventory_movements WHERE sku_id=:sku AND event_date<=:as_of "
        "ORDER BY event_date,movement_id", {"sku": sku_id, "as_of": as_of})
    receipts = _rows(cut,
        "SELECT r.* FROM purchase_receipts r JOIN purchase_orders p ON p.purchase_order_id=r.purchase_order_id "
        "WHERE p.sku_id=:sku AND r.received_date<=:as_of ORDER BY r.received_date,r.receipt_id",
        {"sku": sku_id, "as_of": as_of})
    counts = _rows(cut,
        "SELECT * FROM inventory_counts WHERE sku_id=:sku AND cutoff_date<=:as_of "
        "ORDER BY cutoff_date DESC LIMIT 1", {"sku": sku_id, "as_of": as_of})
    reservation_events = _rows(cut,
        "SELECT * FROM inventory_reservations WHERE sku_id=:sku AND event_date<=:as_of "
        "ORDER BY event_date,reservation_event_id", {"sku": sku_id, "as_of": as_of})
    loans = _rows(cut,
        "SELECT * FROM loans WHERE sku_id=:sku AND borrowed_date<=:as_of",
        {"sku": sku_id, "as_of": as_of})
    ids = [row["movement_id"] for row in movements]
    if len(ids) != len(set(ids)):
        raise ValueError("movement replay")
    accepted = {row["receipt_id"]: row["accepted_units"] for row in receipts}
    by_receipt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    restocked_quality_ids: set[str] = set()
    on_hand = 0
    loaned = 0
    source_refs: list[str] = []
    for movement in movements:
        kind = movement["movement_type"]
        units = movement["units"]
        if kind not in _MOVEMENT_SIGN or not isinstance(units, int) or units < 0:
            raise ValueError("invalid physical movement")
        if kind == "RECEIPT_ACCEPTED":
            receipt_id = movement["receipt_id"]
            if receipt_id not in accepted:
                raise ValueError("orphan accepted receipt movement")
            by_receipt[receipt_id].append(movement)
        if kind == "RETURN_RESTOCK":
            quality_id = movement["quality_event_id"]
            if quality_id is None or quality_id in restocked_quality_ids:
                raise ValueError("return restock replay")
            restocked_quality_ids.add(quality_id)
        on_hand += _MOVEMENT_SIGN[kind] * units
        if on_hand < 0:
            raise ValueError("negative physical stock")
        if kind == "LOAN_OUT":
            loaned += units
        elif kind == "LOAN_IN":
            loaned -= units
        if loaned < 0:
            raise ValueError("negative loan custody")
        source_refs.append(movement["source_ref"])
    for receipt_id, accepted_units in accepted.items():
        matches = by_receipt[receipt_id]
        if len(matches) != (1 if accepted_units else 0) or (matches and matches[0]["units"] != accepted_units):
            raise ValueError("accepted receipt movement mismatch")
    active_reserved: dict[str, int] = defaultdict(int)
    for event in reservation_events:
        sign = 1 if event["event_type"] == "PLACE" else -1
        active_reserved[event["reservation_id"]] += sign * event["units"]
        if active_reserved[event["reservation_id"]] < 0:
            raise ValueError("negative reservation")
        source_refs.append(event["source_ref"])
    reserved = sum(active_reserved.values())
    count = counts[0] if counts else None
    variance = None if count is None else on_hand - count["on_hand_units"]
    non_sellable = count["non_sellable_units"] if count is not None and count["cutoff_date"] == as_of else None
    if count is not None:
        source_refs.append(count["source_ref"])
        if count["cutoff_date"] == as_of and reserved != count["reserved_units"]:
            variance = variance if variance else reserved - count["reserved_units"]
    if loaned != sum(row["quantity"] for row in loans if row["status_code"] in {"OPEN", "PARTIAL"}):
        variance = variance if variance else loaned - sum(row["quantity"] for row in loans if row["status_code"] in {"OPEN", "PARTIAL"})
    inspection = sum(row["inspection_units"] for row in receipts)
    coverage_statuses = [cut.coverage_status(source, as_of) for source in
           ("inventory_movements", "inventory_counts", "inventory_reservations", "loans", "purchase_receipts")]
    blocked_coverage = any(status in {"MISSING", "ERROR"} for status in coverage_statuses)
    complete = count is not None and variance == 0 and non_sellable is not None
    if any(status not in {"COMPLETE", "ZERO"} for status in coverage_statuses):
        complete = False
    available = None if non_sellable is None or variance != 0 or blocked_coverage else on_hand - non_sellable - reserved
    if available is not None and available < 0:
        raise ValueError("negative available stock")
    if variance != 0:
        available = None
    return {
        "sku_id": sku_id, "as_of": as_of,
        "status": "MEASURED" if complete else ("UNKNOWN" if variance != 0 or blocked_coverage or not movements else "PARTIAL"),
        "owned_units": on_hand + loaned + inspection,
        "on_hand_units": on_hand,
        "sellable_on_hand_units": None if non_sellable is None else on_hand - non_sellable,
        "inspection_units": inspection, "non_sellable_units": non_sellable,
        "loaned_units": loaned, "reserved_units": reserved,
        "available_units": available,
        "count_variance_units": variance,
        "source_refs": tuple(sorted(set(source_refs))),
        "reconciliation_id": f"inventory:{cut.cut_id}:{sku_id}:{as_of}",
    }
