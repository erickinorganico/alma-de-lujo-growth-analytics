"""Verify and atomically publish one private, read-only Phase 2 mart bundle."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import re
from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from alma.operating_contracts import SOURCE_NAMES, canonical_json
from alma.operating_cost_inventory import (
    project_cost, project_inventory, project_purchases, realized_economics,
)
from alma.operating_finance_marts import (
    FINANCE_DEFINITIONS, project_budgets, project_cash, project_obligations,
)
from alma.operating_learning_exceptions import (
    LEARNING_DEFINITIONS, project_exceptions, project_learning,
    sales_readiness_projection, validate_sales_row,
)
from alma.operating_mart_contracts import (
    MetricDefinition, MetricRow, Policy, bind_cut, load_policy,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / ".local" / "operating-marts"
_MAX = (1 << 63) - 1

COST_DEFINITIONS = {
    "complete_landed_cost_cents": MetricDefinition(
        "complete_landed_cost_cents", "v1", "sum eligible distinct cost components and allocations",
        "MXN_CENTS", "sku_id x cost_version_id", "as_of",
        ("cost_versions", "cost_components", "cost_allocations"),
        "UNKNOWN unless all required components and allocation evidence are complete",
        "component and allocation cents reconcile exactly", "finance", "price_review"),
    "available_units": MetricDefinition(
        "available_units", "v1", "on hand - non-sellable - active reserved",
        "UNITS", "sku_id", "as_of",
        ("inventory_movements", "inventory_counts", "inventory_reservations", "loans", "purchase_receipts"),
        "UNKNOWN on count or custody variance", "physical movements and accepted receipts reconcile",
        "inventory", "replenishment_review"),
    "purchase_remaining_units": MetricDefinition(
        "purchase_remaining_units", "v1", "ordered - received for noncancelled purchase",
        "UNITS", "purchase_order_id", "as_of", ("purchase_orders", "purchase_receipts"),
        "PARTIAL when purchase or receipt coverage incomplete", "distinct receipts <= ordered",
        "purchasing", "delivery_review"),
    "realized_contribution_cents": MetricDefinition(
        "realized_contribution_cents", "v1", "net revenue - unit COGS - variable cost",
        "MXN_CENTS", "sku_id x channel_code", "[start,end)",
        ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"),
        "UNKNOWN without complete dated cost and sales coverage", "same grain and policy basis",
        "finance", "unit_economics_review"),
}

_FAMILY_SOURCES = {
    "cost": ("cost_versions", "cost_components", "cost_allocations"),
    "inventory": ("inventory_movements", "inventory_counts", "inventory_reservations", "loans", "purchase_receipts"),
    "purchases": ("purchase_orders", "purchase_receipts"),
    "economics": ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"),
    "obligations": ("obligations", "obligation_payments"),
    "cash": ("cash_events", "cash_balance_evidence"),
    "budgets": FINANCE_DEFINITIONS["budget_headroom_cents"].sources,
    "learning": tuple(dict.fromkeys(source for definition in LEARNING_DEFINITIONS.values()
                                         for source in definition.sources)),
}


def _semantic_formulas() -> dict[str, str]:
    """The finite family-path contract; new decision fields must be classified here."""
    groups = {
        "cost[]": {
            "known_sum_cents": "sum known eligible component cents",
            "complete_cost_cents": "sum complete eligible landed component cents",
            "unallocated_cents": "eligible component cents not allocated to this SKU",
            "public_price_cents": "effective version public price cents",
            "unit_cost_cents": "complete landed cost divided across quantity basis by stable residual ordinal",
            "unit_cost_cents[]": "complete landed cost cent assigned to this unit ordinal",
        },
        "inventory[]": {
            "owned_units": "on hand plus loaned plus inspection custody units",
            "on_hand_units": "signed distinct physical movements to as-of",
            "sellable_on_hand_units": "on hand minus non-sellable units",
            "inspection_units": "receipt units awaiting inspection",
            "non_sellable_units": "latest observed count non-sellable units",
            "loaned_units": "loan-out minus loan-in custody units",
            "reserved_units": "active reservation events summed once",
            "available_units": "on hand minus non-sellable minus reserved",
            "count_variance_units": "movement-derived on hand minus observed count",
        },
        "purchases[]": {
            "ordered_units": "documented purchase order units",
            "received_units": "sum distinct receipt received units",
            "inspection_units": "sum distinct receipt inspection units",
            "accepted_units": "sum distinct receipt accepted units",
            "rejected_units": "sum distinct receipt rejected units",
            "still_to_receive_units": "ordered minus received for noncancelled order",
            "cancelled_unreceived_units": "ordered minus received for cancelled order",
        },
        "economics[]": {
            "net_revenue_cents": "sum dated same-grain net revenue cents",
            "delivered_units": "sum dated same-grain delivered units",
            "cogs_cents": "canonical pre-filter unit-cost ordinals across SKU and version",
            "variable_cost_cents": "sum dated same-grain variable cost cents",
            "gross_profit_cents": "net revenue minus canonical COGS",
            "contribution_cents": "gross profit minus variable costs",
            "ratios.markup": "gross profit divided by COGS",
            "ratios.gross_margin": "gross profit divided by net revenue",
            "ratios.contribution_margin": "contribution divided by net revenue",
            "public_prices_by_version.{version}": "effective public price cents for selected cost version",
        },
        "obligations[]": {
            "original_cents": "documented original obligation cents",
            "documented_adjustments_cents": "documented VOID cancellation cents only",
            "recorded_applied_cents": "sum distinct payment applications",
            "recorded_unpaid_cents": "original less documented adjustment and applied cents",
            "authoritative_outstanding_cents": "recorded unpaid when application coverage is complete",
        },
        "cash": {
            "actual_movements_cents": "signed active reconciled cash movements",
            "reconciled_close_cents": "observed opening plus settled flows equals independent observed close",
            "horizons.{horizon}.layers_cents.RECONCILED": "signed active reconciled events in half-open horizon",
            "horizons.{horizon}.layers_cents.COMMITTED": "signed active commitments in half-open horizon",
            "horizons.{horizon}.layers_cents.EXPECTED": "signed active expected events in half-open horizon",
            "horizons.{horizon}.undated_cents": "signed active events with no date",
            "horizons.{horizon}.scenario_cents": "signed separate scenario events in half-open horizon",
            "horizons.{horizon}.weekly_layers_cents.{week}.RECONCILED": "signed reconciled events in local seven-day bucket",
            "horizons.{horizon}.weekly_layers_cents.{week}.COMMITTED": "signed commitments in local seven-day bucket",
            "horizons.{horizon}.weekly_layers_cents.{week}.EXPECTED": "signed expected events in local seven-day bucket",
            "horizons.{horizon}.daily_closes_cents": "no daily close without independent opening",
            "horizons.{horizon}.daily_closes_cents.{day}": "independent close plus cumulative daily commitments and expectations",
            "horizons.{horizon}.daily_minimum_cents": "minimum projected daily close including starting close",
        },
        "budgets": {"unallocated_cents": "source cents without an approved target allocation"},
        "budgets.targets[]": {
            "approved_ceiling_cents": "approved budget target ceiling",
            "open_commitment_cents": "allocated purchase amount not yet received",
            "incurred_cents": "allocated received purchases plus incurred expenses",
            "paid_cents": "distinct settlement applications on mapped sources",
            "outstanding_obligation_cents": "mapped obligation original less distinct payments",
            "headroom_cents": "approved ceiling minus open commitment minus incurred",
        },
        "budgets.sources[]": {
            "source_cents": "source purchase or expense amount before target allocation",
            "allocated_cents": "sum exact source shares assigned to targets",
            "unallocated_cents": "source amount less assigned target cents",
            "open_commitment_cents": "source purchase amount not yet received",
            "incurred_cents": "source received purchase or incurred expense amount",
            "paid_cents": "distinct applied payment cents for source obligation",
            "outstanding_obligation_cents": "source obligation less distinct applied payments",
        },
        "learning[]": {
            "gross_delivered_units": "sum selected delivered units",
            "physical_received_return_units": "selected-cohort physically received returns only",
            "accepted_restocked_units": "distinct accepted physical return restocks",
            "net_depleted_units": "delivered minus accepted physical restocks",
            "opening_sellable_units": "eligible opening count on window start less non-sellable",
            "accepted_receipts_units": "accepted receipt units during launch window",
            "sell_through.numerator": "delivered minus accepted physical restocks",
            "sell_through.denominator": "eligible opening sellable plus accepted receipts",
            "sell_through.value": "net depleted divided by eligible sellable supply",
            "mature_returns.numerator": "physically received returns for mature eligible cohorts",
            "mature_returns.denominator": "delivered units for mature eligible cohorts",
            "mature_returns.value": "eligible mature received returns divided by deliveries",
            "quality_defects.numerator": "confirmed rejected units for eligible mature cohorts",
            "quality_defects.denominator": "inspected units for eligible mature cohorts",
            "quality_defects.value": "eligible mature rejects divided by inspected units",
            "variant_mix.numerator": "eligible variant delivered units",
            "variant_mix.denominator": "same-exposure-set delivered units",
            "variant_mix.value": "eligible variant delivered divided by comparable delivered",
            "variant_mix.public_price_cents": "effective public price for exposure comparison",
            "exposure.observed_minutes": "observed availability minutes",
            "exposure.sellable_minutes": "observed sellable minutes",
            "exposure.stockout_minutes": "observed stockout minutes",
            "exposure.eligible_days": "days with complete variant observations",
            "exposure.numerator": "observed stockout minutes",
            "exposure.denominator": "observed availability minutes",
            "exposure.value": "stockout minutes divided by observed minutes",
        },
        "learning[].variant_mix_by_channel[]": {
            "numerator": "eligible variant delivered units in channel",
            "denominator": "same-exposure-set delivered units in channel",
            "value": "channel variant delivered divided by comparable delivered",
            "public_price_cents": "effective public price for channel exposure comparison",
        },
        "learning[].cohort_rows[]": {
            "delivered_units": "selected deliveries in this linked cohort",
            "received_return_units": "physically received returns linked to this cohort",
            "reported_return_units": "reported but not necessarily received returns",
            "inspected_units": "inspected units linked to this cohort",
            "rejected_units": "confirmed rejected units linked to this cohort",
            "mature_returns.numerator": "physical returns in mature covered cohort",
            "mature_returns.denominator": "deliveries in mature covered cohort",
            "mature_returns.value": "physical returns divided by mature cohort deliveries",
            "quality_defects.numerator": "confirmed rejects in mature covered cohort",
            "quality_defects.denominator": "inspected units in mature covered cohort",
            "quality_defects.value": "confirmed rejects divided by mature inspected units",
        },
        "learning[].recorded_unmet[]": {
            "requested_units_lower_bound": "recorded qualified requested units; unrecorded demand unknown",
        },
    }
    return {f"{prefix}.{field}": formula for prefix, fields in groups.items()
            for field, formula in fields.items()}


SEMANTIC_FORMULAS = _semantic_formulas()
_ID_OVERRIDES = {
    "economics[].ratios.gross_margin": "realized_gross_margin",
    "economics[].ratios.markup": "realized_markup",
    "economics[].ratios.contribution_margin": "realized_contribution_margin",
}
_FACT_KEYS = frozenset({
    "as_of", "cut_id", "timezone", "sku_id", "channel_code", "product_code", "drop_code",
    "cost_version_id", "cost_version_ids", "quality", "status", "policy_version", "policy_sha256",
    "policy_status", "reconciliation_id", "source_ref", "source_refs", "source_hashes",
    "purchase_order_id", "receipt_ids", "obligation_id", "origin_id", "origin_type",
    "payment_ids", "due_date", "due_bucket", "scenario_id", "active_event_ids",
    "scenario_event_ids", "event_id", "economic_event_id", "supersedes_event_id",
    "event_date", "level", "direction", "amount_cents", "close_status", "forecast_status",
    "domain_status", "empty_reason", "start", "end", "cash_floor_breached",
    "minimum_cash_floor_cents", "budget_id", "allocation_ids", "window_start", "window_end",
    "delivery_cohort_id", "latest_delivery_date", "exclusion_reason", "reason",
    "quality_event_id", "event_type", "units", "reason_code", "demand_event_id",
    "exposure_comparable", "price_comparable", "preference_status", "decision_status",
    "category", "exception_id", "closure_evidence_ref", "closure_status", "severity",
    "evidence_ref", "evidence_sha256", "event_ref", "issue_code", "next_action_code",
    "owner_role", "public_variant", "closure_state", "metric_row", "metric_rows",
    "active_event_lineage", "scenario_event_lineage", "excluded_quality_evidence",
})
_SKIP_SUBTREES = frozenset({"source_refs", "source_hashes", "receipt_ids", "payment_ids",
                            "allocation_ids", "cost_version_ids", "active_event_ids",
                            "scenario_event_ids", "metric_row", "metric_rows"})


def _semantic_id(path: str) -> str:
    if path in _ID_OVERRIDES:
        return _ID_OVERRIDES[path]
    return "semantic_" + re.sub(r"[^a-z0-9]+", "_", path.lower().replace("[]", "_item")).strip("_")


def _semantic_definitions() -> dict[str, MetricDefinition]:
    result = {}
    for path, formula in SEMANTIC_FORMULAS.items():
        family = path.split(".", 1)[0].replace("[]", "")
        unit = "RATIO" if path.endswith((".value", ".markup", ".gross_margin", ".contribution_margin")) else (
            "UNITS" if path.endswith(("_units", ".eligible_days")) else "MXN_CENTS" if
            "cents" in path or "price" in path else "MINUTES" if "minutes" in path else "UNITS")
        metric_id = _semantic_id(path)
        if metric_id in result:
            raise ValueError("duplicate semantic metric identity")
        result[metric_id] = MetricDefinition(metric_id, "v1", formula, unit,
            path.rsplit(".", 1)[0], "as_of or declared half-open family window",
            _FAMILY_SOURCES[family], "UNKNOWN or PARTIAL when dependent coverage is incomplete",
            "source-grain reconciliation and no inferred zero", "analytics", "decision_review")
    return result


def _private_root(output_root: str | Path, configured: str | Path | None) -> Path:
    """Reject redirection before making any output directory."""
    root = Path(configured) if configured is not None else PRIVATE_ROOT
    target = Path(output_root)
    if root.name != "operating-marts" or root.parent.name != ".local":
        raise ValueError("private root must be .local/operating-marts")
    for path in (root, target):
        if ".." in path.parts:
            raise ValueError("output path traversal")
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
                raise ValueError("symlink or junction output path")
    resolved_root = root.resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    if resolved_target != resolved_root:
        raise ValueError("output outside configured private root")
    return resolved_root


def _definitions() -> dict[str, MetricDefinition]:
    definitions: dict[str, MetricDefinition] = {}
    for family in (COST_DEFINITIONS, FINANCE_DEFINITIONS, LEARNING_DEFINITIONS,
                   _semantic_definitions()):
        for metric_id, definition in family.items():
            if metric_id in definitions or metric_id != definition.id:
                raise ValueError("duplicate or mismatched metric definition")
            definitions[metric_id] = definition
    return definitions


def _metric(
    metric_id: str, cut_id: str, as_of: str, dimensions: dict[str, str], value: int | str | None,
    status: str, sources: tuple[str, ...], source_refs: tuple[str, ...], reconciliation_id: str,
    policy: Policy | None = None,
) -> MetricRow:
    return MetricRow(metric_id, cut_id, as_of, dimensions, value if value is not None else None,
                     1 if value is not None else None, value, status, sources, source_refs,
                     reconciliation_id, policy.version if policy else None,
                     policy.sha256 if policy else None, policy.status if policy else None)


def _pattern_child(parent: str, key: Any) -> str:
    token = str(key)
    if parent == "cash.horizons":
        token = "{horizon}"
    elif parent.endswith(".weekly_layers_cents"):
        token = "{week}"
    elif parent.endswith(".daily_closes_cents"):
        token = "{day}"
    elif parent.endswith(".public_prices_by_version"):
        token = "{version}"
    return f"{parent}.{token}" if parent else token


def _semantic_walk(value: Any, pattern: str = "", actual: str = "",
                   contexts: tuple[dict[str, Any], ...] = ()):
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        if not value:
            yield pattern, actual, value, contexts
        for key, item in value.items():
            child_pattern = _pattern_child(pattern, key)
            child_actual = f"{actual}.{key}" if actual else str(key)
            if key in _SKIP_SUBTREES:
                yield child_pattern, child_actual, item, (*contexts, value)
            else:
                yield from _semantic_walk(item, child_pattern, child_actual, (*contexts, value))
    elif isinstance(value, (tuple, list)):
        if not value:
            yield pattern + "[]", actual + "[]", value, contexts
        for index, item in enumerate(value):
            yield from _semantic_walk(item, pattern + "[]", f"{actual}[{index}]", contexts)
    else:
        yield pattern, actual, value, contexts


def _semantic_status(path: str, value: Any, contexts: tuple[dict[str, Any], ...],
                     cut: Any, existing: list[MetricRow]) -> str:
    if path.startswith("cash.horizons."):
        parts = path.split(".")
        actual_layer = parts[-1] if "layers_cents" in path else (
            "UNDATED" if parts[-1] == "undated_cents" else "SCENARIO" if parts[-1] == "scenario_cents" else None)
        if actual_layer is not None:
            for row in existing:
                if row.metric_id == "cash_layer_cents" and row.dimensions.get("layer") == actual_layer and row.value == value:
                    return row.status
    for context in reversed(contexts):
        status = context.get("status")
        if status in {"MEASURED", "ESTIMATED", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE", "ERROR"}:
            if value is not None and status in {"UNKNOWN", "ERROR"}:
                return "PARTIAL"  # Recorded numerator/fact survives an unknown derived rate.
            if value is None and status in {"MEASURED", "ESTIMATED"}:
                return "NOT_APPLICABLE" if path.endswith((".value", ".markup", ".gross_margin", ".contribution_margin")) else "UNKNOWN"
            return status
    family = path.split(".", 1)[0].replace("[]", "")
    if family == "cash":
        coverage = cut.coverage_status("cash_events", cut.cutoff_at[:10])
        if coverage in {"MISSING", "ERROR"} or value is None:
            return "UNKNOWN"
        return "PARTIAL" if coverage == "PARTIAL" else "MEASURED"
    if family == "learning":
        return "UNKNOWN" if value is None else "PARTIAL"
    return "UNKNOWN" if value is None else "PARTIAL"


def _semantic_publication(families: dict[str, Any], cut: Any, as_of: str,
                          policy: Policy, existing: list[MetricRow]) -> tuple[list[MetricRow], dict[str, Any]]:
    catalog = {path: {"kind": "metric", "metric_id": _semantic_id(path),
                      "formula": formula} for path, formula in SEMANTIC_FORMULAS.items()}
    rows = []
    for pattern, actual, value, contexts in _semantic_walk(families):
        if pattern in SEMANTIC_FORMULAS:
            if isinstance(value, bool) or not isinstance(value, (int, str, type(None))):
                raise ValueError("invalid semantic measure type")
            family = pattern.split(".", 1)[0].replace("[]", "")
            sources = _FAMILY_SOURCES[family]
            status = _semantic_status(pattern, value, contexts, cut, existing)
            dimensions = {"family_path": actual}
            for context in contexts:
                for key in ("sku_id", "channel_code", "cost_version_id", "purchase_order_id",
                            "obligation_id", "budget_id", "drop_code", "delivery_cohort_id",
                            "scenario_id", "window_start", "window_end"):
                    if context.get(key) is not None:
                        dimensions[key] = str(context[key])
            refs = next((tuple(context["source_refs"]) for context in reversed(contexts)
                         if "source_refs" in context), ())
            if pattern.startswith("cash.horizons."):
                horizon = actual.split(".")[2]
                dimensions["horizon"] = horizon
                period = next((context for context in reversed(contexts)
                               if "start" in context and "end" in context), None)
                if period is not None:
                    dimensions["window_start"] = period["start"]
                    dimensions["window_end"] = period["end"]
                layer = (actual.rsplit(".", 1)[-1] if ".layers_cents." in actual else
                         "UNDATED" if actual.endswith(".undated_cents") else
                         "SCENARIO" if actual.endswith(".scenario_cents") else None)
                if layer is not None:
                    published_layer = next((row for row in existing if row.metric_id == "cash_layer_cents"
                        and row.dimensions.get("horizon") == horizon and
                        row.dimensions.get("layer") == layer), None)
                    if published_layer is None or published_layer.value != value:
                        raise ValueError("cash layer and semantic measure mismatch")
                    status, refs = published_layer.status, published_layer.source_refs
            digest = hashlib.sha256(actual.encode("utf-8")).hexdigest()[:20]
            rows.append(_metric(_semantic_id(pattern), cut.cut_id, as_of, dimensions,
                value, status, sources, refs, f"semantic:{cut.cut_id}:{digest}",
                policy if family in {"cost", "economics", "cash", "budgets", "learning"} else None))
        else:
            key = pattern.rsplit(".", 1)[-1].replace("[]", "")
            if pattern.endswith(".source_hashes"):
                if not isinstance(value, dict) or any(
                    name not in SOURCE_NAMES or digest != cut.source_hashes[f"{name}.csv"]
                    for name, digest in value.items()):
                    raise ValueError("family source hash mismatch")
            elif key not in _FACT_KEYS and pattern not in {
                "cash.horizons.{horizon}.weekly_layers_cents",
                "cash.horizons.{horizon}.daily_closes_cents",
                "cash.horizons", "budgets.sources[]", "budgets.targets[]",
                "economics[].public_prices_by_version",
                "learning[].variant_mix_by_channel[]", "learning[].recorded_unmet[]",
                "learning[].cohort_rows[]", "exceptions[]", "sales_readiness[]",
                "cost[]", "inventory[]", "purchases[]", "economics[]", "obligations[]",
                "learning[]"}:
                raise ValueError(f"unclassified family path: {pattern}")
            catalog.setdefault(pattern, {"kind": "fact", "description":
                "verified source, dimension, lineage, status, policy or control evidence"})
    return rows, dict(sorted(catalog.items()))


def _collect(cut: Any, as_of: str, policy: Policy) -> tuple[dict[str, Any], list[MetricRow]]:
    start = cut.coverage["sales_aggregates"]["window_start"] or min(
        (entry["window_start"] for entry in cut.coverage.values()
         if entry["window_start"] is not None), default=as_of)
    end = (date.fromisoformat(as_of) + timedelta(days=1)).isoformat()
    skus = [row[0] for row in cut.connection.execute("SELECT sku_id FROM sku_catalog ORDER BY sku_id")]
    channels = [row[0] for row in cut.connection.execute(
        "SELECT DISTINCT channel_code FROM sales_aggregates ORDER BY channel_code")]
    cost_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    economic_rows: list[dict[str, Any]] = []
    learning_rows: list[dict[str, Any]] = []
    metrics: list[MetricRow] = []
    for sku in skus:
        cost = project_cost(cut, sku, as_of, policy)
        cost_rows.append({"sku_id": sku, **cost})
        metrics.append(_metric("complete_landed_cost_cents", cut.cut_id, as_of,
            {"sku_id": sku, "cost_version_id": cost.get("cost_version_id") or "UNKNOWN"},
            cost.get("complete_cost_cents"), cost["status"],
            COST_DEFINITIONS["complete_landed_cost_cents"].sources,
            tuple(cost.get("source_refs", ())), f"cost:{cut.cut_id}:{sku}:{as_of}", policy))
        inventory = project_inventory(cut, sku, as_of)
        inventory_rows.append(inventory)
        metrics.append(_metric("available_units", cut.cut_id, as_of, {"sku_id": sku},
            inventory["available_units"], inventory["status"],
            COST_DEFINITIONS["available_units"].sources,
            tuple(inventory["source_refs"]), inventory["reconciliation_id"]))
        learning = project_learning(cut, sku, start, end, policy)
        learning_rows.append(learning)
        metrics.extend(learning["metric_rows"])
        for channel in channels:
            economics = realized_economics(cut, sku, channel, start, end, policy)
            economic_rows.append({"sku_id": sku, "channel_code": channel, **economics})
            metrics.append(_metric("realized_contribution_cents", cut.cut_id, as_of,
                {"sku_id": sku, "channel_code": channel, "window_start": start, "window_end": end},
                economics["contribution_cents"], economics["status"],
                COST_DEFINITIONS["realized_contribution_cents"].sources,
                tuple(economics["source_refs"]), economics["reconciliation_id"], policy))
    purchases = project_purchases(cut, as_of)
    for purchase in purchases:
        metrics.append(_metric("purchase_remaining_units", cut.cut_id, as_of,
            {"purchase_order_id": purchase["purchase_order_id"]},
            purchase["still_to_receive_units"], purchase["status"],
            COST_DEFINITIONS["purchase_remaining_units"].sources,
            tuple(purchase["source_refs"]), purchase["reconciliation_id"]))
    obligations = project_obligations(cut, as_of)
    for obligation in obligations:
        metrics.append(obligation["metric_row"])
        value = obligation["authoritative_outstanding_cents"]
        metrics.append(_metric("authoritative_outstanding_cents", cut.cut_id, as_of,
            {"obligation_id": obligation["obligation_id"]}, value,
            "UNKNOWN" if value is None else obligation["status"],
            FINANCE_DEFINITIONS["authoritative_outstanding_cents"].sources,
            tuple(obligation["source_refs"]), obligation["reconciliation_id"] + ":authoritative"))
    cash = project_cash(cut, as_of, policy)
    if cash["metric_row"] is not None:
        metrics.append(cash["metric_row"])
    for horizon, details in cash["horizons"].items():
        layers = {**details["layers_cents"], "UNDATED": details["undated_cents"],
                  "SCENARIO": details["scenario_cents"]}
        lineage = (*cash["active_event_lineage"], *cash["scenario_event_lineage"])
        for layer, value in layers.items():
            matching = [event for event in lineage if event["level"] == layer and
                (layer == "UNDATED" or event["event_date"] is not None and
                 details["start"] <= event["event_date"] < details["end"])]
            source_status = cash["domain_status"]
            if source_status in {"MISSING", "ERROR"}:
                status, published = "UNKNOWN", None
            elif source_status == "PARTIAL":
                status, published = "PARTIAL", value
            elif layer == "RECONCILED":
                status, published = "MEASURED", value
            else:
                status, published = "ESTIMATED", value
            metrics.append(_metric("cash_layer_cents", cut.cut_id, as_of,
                {"scenario_id": cash["scenario_id"], "horizon": str(horizon), "layer": layer,
                 "window_start": details["start"], "window_end": details["end"]},
                published, status,
                FINANCE_DEFINITIONS["cash_layer_cents"].sources,
                tuple(sorted(event["source_ref"] for event in matching)),
                f"cash-layer:{cut.cut_id}:{horizon}:{layer}:{as_of}", policy))
    budgets = project_budgets(cut, as_of, policy)
    metrics.extend(row["metric_row"] for row in budgets["targets"])
    exceptions = project_exceptions(cut, as_of, policy)
    sales = sales_readiness_projection(cut, exceptions, policy)
    for row in sales:
        validate_sales_row(row)
    families = {"cost": cost_rows, "inventory": inventory_rows, "purchases": purchases,
                "economics": economic_rows, "obligations": obligations, "cash": cash,
                "budgets": budgets, "learning": learning_rows, "exceptions": exceptions,
                "sales_readiness": sales}
    semantic_rows, _ = _semantic_publication(families, cut, as_of, policy, metrics)
    metrics.extend(semantic_rows)
    return families, metrics


def _validate(cut: Any, policy: Policy, definitions: dict[str, MetricDefinition],
              metrics: list[MetricRow]) -> None:
    if not metrics or {row.metric_id for row in metrics} - set(definitions):
        raise ValueError("emitted metric lacks definition")
    reconciliations: set[str] = set()
    for row in metrics:
        definition = definitions[row.metric_id]
        if row.cut_id != cut.cut_id or row.reconciliation_id in reconciliations:
            raise ValueError("metric cut or reconciliation identity mismatch")
        reconciliations.add(row.reconciliation_id)
        if not row.coverage_refs or set(row.coverage_refs) - set(definition.sources):
            raise ValueError("metric coverage sources mismatch definition")
        if set(row.coverage_refs) - set(cut.coverage):
            raise ValueError("metric coverage missing from cut")
        if row.policy_sha256 is not None and (row.policy_sha256 != policy.sha256 or
              row.policy_version != policy.version or row.policy_status != policy.status):
            raise ValueError("metric policy binding mismatch")
        for amount in (row.numerator, row.denominator, row.value):
            if isinstance(amount, int) and (amount < -_MAX - 1 or amount > _MAX):
                raise ValueError("metric integer overflow")
        if row.status == "MEASURED" and row.value is None:
            raise ValueError("measured metric without value")


def _controls(metrics: list[MetricRow], exceptions: list[dict[str, Any]]) -> dict[str, Any]:
    families = {"cost_inventory": COST_DEFINITIONS, "finance": FINANCE_DEFINITIONS,
                "learning": LEARNING_DEFINITIONS}
    result: dict[str, Any] = {}
    for family, definitions in families.items():
        semantic_families = {"cost_inventory": ("cost", "inventory", "purchases", "economics"),
                             "finance": ("obligations", "cash", "budgets"),
                             "learning": ("learning",)}[family]
        selected = [row for row in metrics if row.metric_id in definitions or
                    row.dimensions.get("family_path", "").split(".", 1)[0].split("[", 1)[0]
                    in semantic_families]
        counts: dict[str, int] = {}
        for row in selected:
            counts[row.status] = counts.get(row.status, 0) + 1
        result[family] = {"metric_count": len(selected), "status_counts": counts,
                          "reconciliation_ids": sorted(row.reconciliation_id for row in selected)}
    result["exceptions"] = {"exception_count": len(exceptions),
                            "reconciliation_ids": sorted(row["reconciliation_id"] for row in exceptions)}
    return result


def _csv_metric_rows(rows: list[MetricRow]) -> bytes:
    stream = io.StringIO(newline="")
    fields = ("metric_id", "cut_id", "as_of", "dimensions", "numerator", "denominator",
              "value", "status", "reconciliation_id")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        record = asdict(row)
        writer.writerow({field: json.dumps(record[field], sort_keys=True, ensure_ascii=False)
                         if field == "dimensions" else record[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def build_operating_marts(
    cut_path: str | Path, output_root: str | Path, *, policy_path: str | Path,
    private_root: str | Path | None = None,
) -> dict[str, Any]:
    """Verify inputs and all families, then publish a complete immutable private bundle."""
    root = _private_root(output_root, private_root)
    with bind_cut(cut_path) as cut:
        as_of = cut.cutoff_at[:10]
        policy = load_policy(policy_path, as_of=as_of,
                             real_cut=cut.input_class != "SYNTHETIC_EXAMPLE")
        definitions = _definitions()
        families, metrics = _collect(cut, as_of, policy)
        _validate(cut, policy, definitions, metrics)
        expected_semantic, catalog = _semantic_publication(families, cut, as_of, policy, metrics)
        observed_semantic = {row.reconciliation_id: row for row in metrics
                             if row.reconciliation_id.startswith("semantic:")}
        if (len(observed_semantic) != len(expected_semantic) or
            any(expected.metric_id not in definitions or
                observed_semantic.get(expected.reconciliation_id) != expected
                for expected in expected_semantic)):
            raise ValueError("family measure and normalized metric mismatch")
        controls = _controls(metrics, families["exceptions"])
        row_counts = {name: cut.connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                      for name in cut.coverage}
        domain_coverage = {name: {**entry,
            "row_count": row_counts[name],
            "empty_reason": "MISSING_SOURCE" if entry["status"] == "MISSING" else
                "DECLARED_ZERO" if entry["status"] == "ZERO" else
                "NO_ROWS" if row_counts[name] == 0 else None}
            for name, entry in sorted(cut.coverage.items())}
        registry = {name: asdict(definition) for name, definition in sorted(definitions.items())}
        contract_hash = hashlib.sha256(canonical_json({"registry": registry,
            "semantic_formulas": SEMANTIC_FORMULAS, "fact_keys": sorted(_FACT_KEYS)})).hexdigest()
        cut_id = cut.cut_id
        lineage = {"cut_id": cut_id, "cutoff_at": cut.cutoff_at,
                   "input_class": cut.input_class, "source_sha256": cut.source_hashes,
                   "coverage": cut.coverage, "policy_version": policy.version,
                   "policy_sha256": policy.sha256, "policy_status": policy.status,
                   "metric_contract_sha256": contract_hash,
                   "decision_status": "REVIEW" if cut.input_class != "SYNTHETIC_EXAMPLE" and
                      not policy.authorizes_real_cut else "SYNTHETIC_EXAMPLE" if
                      cut.input_class == "SYNTHETIC_EXAMPLE" else "APPROVED"}
        artifacts = {"registry.json": canonical_json(registry),
                     "semantic_catalog.json": canonical_json(catalog),
                     "domain_coverage.json": canonical_json(domain_coverage),
                     "metric_rows.json": canonical_json([asdict(row) for row in metrics]),
                     "metric_rows.csv": _csv_metric_rows(metrics),
                     "controls.json": canonical_json(controls),
                     "families.json": canonical_json(_plain(families)),
                     "exceptions.json": canonical_json(families["exceptions"]),
                     "sales_readiness.json": canonical_json(families["sales_readiness"]),
                     "lineage.json": canonical_json(lineage)}
        destination = root / cut_id / contract_hash
        if destination.exists() or destination.is_symlink():
            raise ValueError("operating mart bundle already exists")
        artifact_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}
        manifest = {"cut_id": cut_id, "policy_version": policy.version,
                    "policy_sha256": policy.sha256, "policy_status": policy.status,
                    "metric_contract_sha256": contract_hash,
                    "source_sha256": cut.source_hashes, "coverage": cut.coverage,
                    "artifacts": sorted(artifacts), "artifact_sha256": artifact_hashes,
                    "decision_status": lineage["decision_status"]}
        # Recheck the path immediately before staging, including newly introduced links.
        if _private_root(output_root, private_root) != root:
            raise ValueError("private output root changed")
        root.mkdir(parents=True, exist_ok=True)
        cut_root = root / cut_id
        if cut_root.exists() and (cut_root.is_symlink() or
                                  (hasattr(cut_root, "is_junction") and cut_root.is_junction())):
            raise ValueError("cut output redirected")
        cut_root.mkdir(exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=cut_root))
        try:
            for name, data in artifacts.items():
                (stage / name).write_bytes(data)
                if hashlib.sha256((stage / name).read_bytes()).hexdigest() != artifact_hashes[name]:
                    raise ValueError("staged artifact hash mismatch")
            (stage / "manifest.json").write_bytes(canonical_json(manifest))
            if destination.exists() or destination.is_symlink():
                raise ValueError("operating mart bundle already exists")
            os.replace(stage, destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    return {"destination": str(destination), "cut_id": cut_id,
            "metric_contract_sha256": contract_hash,
            "policy_sha256": policy.sha256, "metric_count": len(metrics)}
