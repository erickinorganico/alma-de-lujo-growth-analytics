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
    sales = _rows(cut,
        "SELECT sales_date, delivered_units, net_revenue_cents, variable_cost_cents, "
        "coverage_status, source_ref FROM sales_aggregates "
        "WHERE sku_id=:sku AND channel_code=:channel AND sales_date>=:start AND sales_date<:end "
        "ORDER BY sales_date, source_ref",
        {"sku": sku_id, "channel": channel_code, "start": start, "end": end})
    revenue = sum(row["net_revenue_cents"] for row in sales)
    delivered = sum(row["delivered_units"] for row in sales)
    variable = sum(row["variable_cost_cents"] for row in sales if row["variable_cost_cents"] is not None)
    cogs = 0
    ordinal_by_version: dict[str, int] = defaultdict(int)
    complete = bool(sales) and all(row["coverage_status"] == "COMPLETE" and row["variable_cost_cents"] is not None for row in sales)
    source_refs = [row["source_ref"] for row in sales]
    version_ids: list[str] = []
    public_prices: dict[str, int] = {}
    for row in sales:
        cost = project_cost(cut, sku_id, row["sales_date"], policy)
        version_id = cost["cost_version_id"]
        if version_id is None or cost["unit_cost_cents"] is None:
            complete = False
            continue
        version_ids.append(version_id)
        public_prices[version_id] = cost["public_price_cents"]
        unit_costs = cost["unit_cost_cents"]
        for ordinal in range(row["delivered_units"]):
            cogs += unit_costs[(ordinal_by_version[version_id] + ordinal) % len(unit_costs)]
        ordinal_by_version[version_id] += row["delivered_units"]
        source_refs.extend(cost["source_refs"])
    last_day = (date.fromisoformat(end) - timedelta(days=1)).isoformat()
    coverage = cut.coverage_status("sales_aggregates", start)
    if coverage not in {"COMPLETE", "ZERO"} or cut.coverage_status("sales_aggregates", last_day) not in {"COMPLETE", "ZERO"}:
        complete = False
    if cut.input_class != "SYNTHETIC_EXAMPLE" and not policy.authorizes_real_cut:
        complete = False
    ratios = economics_ratios(revenue, cogs, variable) if complete else {"markup": None, "gross_margin": None, "contribution_margin": None}
    return {"status": "MEASURED" if complete else ("PARTIAL" if sales else "UNKNOWN"),
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
