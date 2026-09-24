"""Coverage-aware product observations and governed operating exceptions."""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any, Iterable

from alma.operating_contracts import canonical_json
from alma.operating_cost_inventory import project_cost
from alma.operating_mart_contracts import BoundCut, MetricDefinition, MetricRow, Policy

SQL_PATH = Path(__file__).resolve().parents[1] / "models" / "operating_learning_exceptions.sql"

LEARNING_DEFINITIONS = {
    "sell_through": MetricDefinition("sell_through", "v1",
        "(delivered - physical accepted restocks) / (eligible opening sellable + accepted receipts)",
        "RATIO", "sku x launch window", "[start,end)",
        ("sales_aggregates", "inventory_counts", "purchase_receipts", "inventory_movements"),
        "UNKNOWN without eligible opening sellable or complete source coverage",
        "stockout exposure blocks preference claim", "product", "launch_review"),
    "variant_mix": MetricDefinition("variant_mix", "v1",
        "eligible variant delivered / same-exposure-set eligible delivered",
        "RATIO", "variant x drop x channel", "[start,end)",
        ("sales_aggregates", "availability_daily", "cost_versions"),
        "UNKNOWN without comparable exposure and price", "descriptive only",
        "product", "assortment_review"),
    "mature_return_rate": MetricDefinition("mature_return_rate", "v1",
        "physically received linked returns / mature covered cohort deliveries; aggregate pools eligible cohorts only",
        "RATIO", "delivery_cohort_id or eligible aggregate", "cohort latest delivery + policy returns_days <= as_of",
        ("sales_aggregates", "quality_events"),
        "UNKNOWN if unlinked, immature, or incompletely observed", "never count reported-only return",
        "product", "quality_review"),
    "quality_defect_rate": MetricDefinition("quality_defect_rate", "v1",
        "confirmed rejected units / inspected units in matching mature covered cohorts",
        "RATIO", "delivery_cohort_id or eligible aggregate", "cohort latest delivery + policy returns_days <= as_of",
        ("sales_aggregates", "quality_events"),
        "UNKNOWN without linked inspected denominator", "confirmed events only",
        "quality", "quality_review"),
    "stockout_exposure": MetricDefinition("stockout_exposure", "v1",
        "observed stockout minutes / observed minutes", "RATIO", "sku x observed day/window",
        "[start,end)", ("availability_daily",),
        "UNKNOWN without observed minutes", "incomplete exposure cannot imply weak preference",
        "product", "availability_review"),
    "recorded_unmet_units": MetricDefinition("recorded_unmet_units", "v1",
        "sum recorded requested units by source event", "UNITS", "demand_event_id",
        "[start,end)", ("unmet_demand",),
        "absent channel row is UNKNOWN, never zero", "recorded lower bound only",
        "product", "demand_review"),
}


def _query(name: str) -> str:
    for block in SQL_PATH.read_text(encoding="utf-8").split("-- name: ")[1:]:
        label, _, statement = block.partition("\n")
        if label.strip() == name:
            return statement.strip()
    raise ValueError(f"unknown learning query: {name}")


def _rows(cut: BoundCut, statement: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in cut.connection.execute(statement, parameters)]


def _ratio(numerator: int, denominator: int) -> str:
    with localcontext() as context:
        context.prec = 50
        result = (Decimal(numerator) / Decimal(denominator)).quantize(
            Decimal("0.0000000001"), rounding=ROUND_HALF_EVEN)
    return format(result.normalize(), "f")


def sell_through(
    delivered_units: int, accepted_restocked_units: int,
    opening_sellable_units: int | None, accepted_receipts_units: int,
    *, coverage: str,
) -> dict[str, Any]:
    if any(not isinstance(value, int) or value < 0 for value in
           (delivered_units, accepted_restocked_units, accepted_receipts_units)):
        raise ValueError("invalid sell-through units")
    if accepted_restocked_units > delivered_units:
        raise ValueError("restocks exceed delivered units")
    numerator = delivered_units - accepted_restocked_units
    if opening_sellable_units is None:
        return {"numerator": numerator, "denominator": None, "value": None, "status": "UNKNOWN"}
    if not isinstance(opening_sellable_units, int) or opening_sellable_units < 0:
        raise ValueError("invalid opening sellable units")
    denominator = opening_sellable_units + accepted_receipts_units
    if denominator == 0:
        return {"numerator": numerator, "denominator": 0, "value": None, "status": "NOT_APPLICABLE"}
    if coverage not in {"COMPLETE", "ZERO"}:
        return {"numerator": numerator, "denominator": denominator, "value": None,
                "status": "UNKNOWN" if coverage in {"MISSING", "ERROR"} else "PARTIAL"}
    return {"numerator": numerator, "denominator": denominator,
            "value": _ratio(numerator, denominator), "status": "MEASURED"}


def mature_return_rate(
    delivered_units: int, received_return_units: int, *, cohort_date: str,
    as_of: str, maturity_days: int, linked: bool, coverage: str,
) -> dict[str, Any]:
    if any(not isinstance(value, int) or value < 0 for value in
           (delivered_units, received_return_units, maturity_days)):
        raise ValueError("invalid cohort units or maturity")
    if received_return_units > delivered_units:
        raise ValueError("returns exceed cohort deliveries")
    if not linked or date.fromisoformat(as_of) < date.fromisoformat(cohort_date) + timedelta(days=maturity_days):
        return {"numerator": received_return_units, "denominator": delivered_units,
                "value": None, "status": "UNKNOWN"}
    if delivered_units == 0:
        return {"numerator": received_return_units, "denominator": 0,
                "value": None, "status": "NOT_APPLICABLE"}
    if coverage not in {"COMPLETE", "ZERO"}:
        return {"numerator": received_return_units, "denominator": delivered_units,
                "value": None, "status": "UNKNOWN" if coverage in {"MISSING", "ERROR"} else "PARTIAL"}
    return {"numerator": received_return_units, "denominator": delivered_units,
            "value": _ratio(received_return_units, delivered_units), "status": "MEASURED"}


def variant_mix(
    variant_delivered_units: int, comparable_delivered_units: int, *,
    exposure_comparable: bool, price_comparable: bool, coverage: str,
) -> dict[str, Any]:
    if not exposure_comparable or not price_comparable:
        return {"numerator": variant_delivered_units, "denominator": comparable_delivered_units,
                "value": None, "status": "UNKNOWN"}
    if comparable_delivered_units == 0:
        return {"numerator": variant_delivered_units, "denominator": 0,
                "value": None, "status": "NOT_APPLICABLE"}
    if coverage not in {"COMPLETE", "ZERO"}:
        return {"numerator": variant_delivered_units, "denominator": comparable_delivered_units,
                "value": None, "status": "PARTIAL"}
    return {"numerator": variant_delivered_units, "denominator": comparable_delivered_units,
            "value": _ratio(variant_delivered_units, comparable_delivered_units), "status": "MEASURED"}


def project_variant_mix(
    cut: BoundCut, sku_id: str, start: str, end: str, as_of: str,
) -> list[dict[str, Any]]:
    """Describe one product's variants only across comparable channel exposure."""
    identity_rows = _rows(cut, _query("sku_identity"), {"sku": sku_id})
    if len(identity_rows) != 1:
        raise ValueError("unknown SKU for variant mix")
    product_code = identity_rows[0]["product_code"]
    params = {"product_code": product_code, "start": start, "end": end, "as_of": as_of}
    variants = _rows(cut, _query("product_variants"), params)
    sales = _rows(cut, _query("variant_sales"), params)
    availability = {row["sku_id"]: row for row in _rows(cut, _query("variant_availability"), params)}
    prices = {row["sku_id"]: row["public_price_cents"] for row in
              _rows(cut, _query("variant_prices"), params)}
    variant_ids = {row["sku_id"] for row in variants}
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    exposure_comparable = bool(variant_ids) and all(
        sku in availability and availability[sku]["observed_days"] == days
        and availability[sku]["observed_minutes"] > 0
        and availability[sku]["stockout_minutes"] == 0
        and availability[sku]["coverage_status"] == "COMPLETE"
        for sku in variant_ids)
    price_comparable = len(prices) == len(variant_ids) and bool(prices) and \
        len(set(prices.values())) == 1 and next(iter(prices.values())) > 0
    domain_complete = all(cut.coverage_status(source, as_of) in {"COMPLETE", "ZERO"} for source in
        ("sku_catalog", "sales_aggregates", "availability_daily", "cost_versions"))
    channels = sorted({row["channel_code"] for row in sales})
    results = []
    for channel in channels:
        channel_rows = [row for row in sales if row["channel_code"] == channel]
        numerator = sum(row["delivered_units"] for row in channel_rows if row["sku_id"] == sku_id)
        denominator = sum(row["delivered_units"] for row in channel_rows)
        coverage = "COMPLETE" if domain_complete and all(row["coverage_status"] == "COMPLETE" for row in channel_rows) else "PARTIAL"
        result = variant_mix(numerator, denominator, exposure_comparable=exposure_comparable,
                             price_comparable=price_comparable, coverage=coverage)
        results.append({"product_code": product_code, "drop_code": None,
                        "sku_id": sku_id, "channel_code": channel,
                        "exposure_comparable": exposure_comparable,
                        "public_price_cents": prices.get(sku_id),
                        "price_comparable": price_comparable, **result})
    return results


def project_learning(
    cut: BoundCut, sku_id: str, start: str, end: str, policy: Policy,
) -> dict[str, Any]:
    """Read aggregate observations without manufacturing customer or demand rows."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if not start_date < end_date:
        raise ValueError("empty learning window")
    as_of = (end_date - timedelta(days=1)).isoformat()
    cut.coverage_status("sales_aggregates", as_of)
    params = {"sku": sku_id, "start": start, "end": end, "as_of": as_of}
    sales = _rows(cut, _query("sales_by_cohort"), params)
    opening = _rows(cut, _query("opening_count"), params)
    receipts = _rows(cut, _query("accepted_receipts"), params)
    restocks = _rows(cut, _query("physical_restocks"), params)
    quality = _rows(cut, _query("quality_events"), params)
    quality_outside = _rows(cut, _query("quality_outside"), params)
    availability = _rows(cut, _query("availability"), params)
    unmet = _rows(cut, _query("unmet"), params)
    source_names = ("sales_aggregates", "inventory_counts", "purchase_receipts",
                    "inventory_movements", "quality_events", "availability_daily", "unmet_demand")
    coverage = {name: cut.coverage_status(name, as_of) for name in source_names}
    delivered = sum(row["delivered_units"] for row in sales)
    accepted_restocked = sum(row["units"] for row in restocks)
    if accepted_restocked > delivered:
        raise ValueError("restocks exceed delivered aggregate")
    opening_sellable = (
        opening[0]["on_hand_units"] - opening[0]["non_sellable_units"]
        if opening and opening[0]["cutoff_date"] == start else None
    )
    accepted_receipts = sum(row["accepted_units"] for row in receipts)
    source_coverage = "COMPLETE" if all(coverage[name] in {"COMPLETE", "ZERO"} for name in
        ("sales_aggregates", "inventory_counts", "purchase_receipts", "inventory_movements")) and all(
        row["coverage_status"] == "COMPLETE" for row in sales) else "PARTIAL"
    sold = sell_through(delivered, accepted_restocked, opening_sellable,
                        accepted_receipts, coverage=source_coverage)
    observed_minutes = sum(row["observed_minutes"] for row in availability)
    stockout_minutes = sum(row["stockout_minutes"] for row in availability)
    sellable_minutes = sum(row["sellable_minutes"] for row in availability)
    if any(row["observed_minutes"] < row["sellable_minutes"] + row["stockout_minutes"] for row in availability):
        raise ValueError("availability minutes exceed observation")
    exposure_complete = coverage["availability_daily"] in {"COMPLETE", "ZERO"} and all(
        row["coverage_status"] == "COMPLETE" for row in availability) and len(availability) == (end_date-start_date).days
    exposure_status = ("UNKNOWN" if observed_minutes == 0 else
                       "MEASURED" if exposure_complete else "PARTIAL")
    exposure = {"observed_minutes": observed_minutes, "sellable_minutes": sellable_minutes,
                "stockout_minutes": stockout_minutes, "eligible_days": len(availability) if exposure_complete else None,
                "numerator": stockout_minutes, "denominator": observed_minutes or None,
                "value": _ratio(stockout_minutes, observed_minutes) if exposure_complete and observed_minutes else None,
                "status": exposure_status}
    grouped: dict[str | None, list[dict[str, Any]]] = {}
    for sale in sales:
        grouped.setdefault(sale["delivery_cohort_id"], []).append(sale)
    quality_by_cohort: dict[str, list[dict[str, Any]]] = {}
    for event in quality:
        quality_by_cohort.setdefault(event["delivery_cohort_id"], []).append(event)
    received_return_units = sum(row["units"] for row in quality if row["event_type"] == "RETURN_RECEIVED"
                                and row["delivery_cohort_id"] is not None)
    maturity_days = policy.content["maturity_windows"]["returns_days"]
    cohort_rows = []
    for cohort_id, deliveries in sorted(grouped.items(), key=lambda item: item[0] or ""):
        events = quality_by_cohort.get(cohort_id, []) if cohort_id is not None else []
        units = sum(row["delivered_units"] for row in deliveries)
        received = sum(row["units"] for row in events if row["event_type"] == "RETURN_RECEIVED")
        reported = sum(row["units"] for row in events if row["event_type"] == "RETURN_REPORTED")
        inspected = sum(row["units"] for row in events if row["event_type"] == "INSPECTED")
        defects = sum(row["units"] for row in events if row["event_type"] == "REJECTED")
        latest = max(row["sales_date"] for row in deliveries)
        cohort_coverage = "COMPLETE" if cohort_id is not None and all(
            coverage[name] in {"COMPLETE", "ZERO"} for name in ("sales_aggregates", "quality_events")) and all(
            row["coverage_status"] == "COMPLETE" for row in deliveries) and reported <= received else "PARTIAL"
        mature = date.fromisoformat(as_of) >= date.fromisoformat(latest) + timedelta(days=maturity_days)
        returned = mature_return_rate(units, received, cohort_date=latest, as_of=as_of,
            maturity_days=maturity_days, linked=cohort_id is not None, coverage=cohort_coverage)
        quality_rate = mature_return_rate(inspected, defects, cohort_date=latest, as_of=as_of,
            maturity_days=maturity_days, linked=cohort_id is not None and inspected > 0,
            coverage=cohort_coverage)
        reason = ("UNLINKED" if cohort_id is None else "IMMATURE" if not mature else
                  "INCOMPLETE_COVERAGE" if cohort_coverage != "COMPLETE" else None)
        cohort_rows.append({"delivery_cohort_id": cohort_id, "latest_delivery_date": latest,
            "delivered_units": units, "received_return_units": received,
            "reported_return_units": reported, "inspected_units": inspected,
            "rejected_units": defects, "mature_returns": returned,
            "quality_defects": quality_rate, "exclusion_reason": reason,
            "source_refs": tuple(sorted({row["source_ref"] for row in (*deliveries, *events)}))})
    def pooled(field: str) -> dict[str, Any]:
        eligible = [row[field] for row in cohort_rows if row[field]["status"] == "MEASURED"]
        if not eligible:
            if cohort_rows and all(row[field]["status"] == "NOT_APPLICABLE" for row in cohort_rows):
                return {"numerator": 0, "denominator": 0, "value": None, "status": "NOT_APPLICABLE"}
            return {"numerator": None, "denominator": None, "value": None, "status": "UNKNOWN"}
        numerator = sum(row["numerator"] for row in eligible)
        denominator = sum(row["denominator"] for row in eligible)
        return {"numerator": numerator, "denominator": denominator,
                "value": _ratio(numerator, denominator), "status": "MEASURED"}
    returns = pooled("mature_returns")
    defect_rate = pooled("quality_defects")
    mix_by_channel = project_variant_mix(cut, sku_id, start, end, as_of)
    mix = mix_by_channel[0] if len(mix_by_channel) == 1 else {
        "numerator": None, "denominator": None, "value": None, "status": "UNKNOWN"}
    unmet_rows = [{"demand_event_id": row["demand_event_id"], "event_date": row["event_date"],
                   "sku_id": row["sku_id"], "channel_code": row["channel_code"],
                   "reason_code": row["reason_code"], "requested_units_lower_bound": row["requested_units"],
                   "status": "MEASURED" if coverage["unmet_demand"] in {"COMPLETE", "ZERO"} else "PARTIAL",
                   "source_ref": row["source_ref"]} for row in unmet]
    source_refs = tuple(sorted({row["source_ref"] for rows in
        (sales, opening, receipts, restocks, quality, quality_outside, availability, unmet) for row in rows}))
    metrics = {"sell_through": sold, "mature_return_rate": returns,
               "quality_defect_rate": defect_rate, "stockout_exposure": exposure}
    metric_rows = []
    for metric_id, value in metrics.items():
        metric_rows.append(MetricRow(metric_id, cut.cut_id, as_of,
            {"sku_id": sku_id, "window_start": start, "window_end": end,
             "scope": "eligible_aggregate" if metric_id in {"mature_return_rate", "quality_defect_rate"} else "window"},
            value["numerator"], value["denominator"], value["value"], value["status"],
            LEARNING_DEFINITIONS[metric_id].sources, source_refs,
            f"learning:{cut.cut_id}:{metric_id}:{sku_id}:{start}:{end}",
            policy.version, policy.sha256, policy.status))
    for cohort in cohort_rows:
        for metric_id, key in (("mature_return_rate", "mature_returns"),
                               ("quality_defect_rate", "quality_defects")):
            value = cohort[key]
            metric_rows.append(MetricRow(metric_id, cut.cut_id, as_of,
                {"sku_id": sku_id, "scope": "cohort", "delivery_cohort_id": cohort["delivery_cohort_id"] or "UNLINKED",
                 "window_start": start, "window_end": end},
                value["numerator"], value["denominator"], value["value"], value["status"],
                LEARNING_DEFINITIONS[metric_id].sources, cohort["source_refs"],
                f'learning:{cut.cut_id}:{metric_id}:{sku_id}:{cohort["delivery_cohort_id"] or "UNLINKED"}:{start}:{end}',
                policy.version, policy.sha256, policy.status))
    for row in mix_by_channel:
        metric_rows.append(MetricRow("variant_mix", cut.cut_id, as_of,
            {"sku_id": sku_id, "product_code": row["product_code"],
             "channel_code": row["channel_code"], "window_start": start, "window_end": end},
            row["numerator"], row["denominator"], row["value"], row["status"],
            LEARNING_DEFINITIONS["variant_mix"].sources, source_refs,
            f'learning:{cut.cut_id}:variant_mix:{sku_id}:{row["channel_code"]}:{start}:{end}',
            policy.version, policy.sha256, policy.status))
    for row in unmet_rows:
        metric_rows.append(MetricRow("recorded_unmet_units", cut.cut_id, as_of,
            {"sku_id": sku_id, "channel_code": row["channel_code"], "demand_event_id": row["demand_event_id"]},
            row["requested_units_lower_bound"], None, row["requested_units_lower_bound"], row["status"],
            ("unmet_demand",), (row["source_ref"],),
            f'learning:{cut.cut_id}:unmet:{row["demand_event_id"]}',
            policy.version, policy.sha256, policy.status))
    return {"cut_id": cut.cut_id, "as_of": as_of, "timezone": cut.timezone,
            "sku_id": sku_id, "window_start": start, "window_end": end,
            "gross_delivered_units": delivered, "physical_received_return_units": received_return_units,
            "accepted_restocked_units": accepted_restocked,
            "net_depleted_units": delivered-accepted_restocked,
            "opening_sellable_units": opening_sellable,
            "accepted_receipts_units": accepted_receipts,
            "sell_through": sold, "variant_mix": mix,
            "variant_mix_by_channel": mix_by_channel,
            "mature_returns": returns,
            "quality_defects": defect_rate, "cohort_rows": cohort_rows,
            "excluded_quality_evidence": tuple({"quality_event_id": row["quality_event_id"],
                "delivery_cohort_id": row["delivery_cohort_id"], "event_type": row["event_type"],
                "units": row["units"], "source_ref": row["source_ref"],
                "reason": "UNLINKED" if row["delivery_cohort_id"] is None else "OUTSIDE_SELECTED_COHORT"}
                for row in quality_outside), "exposure": exposure,
            "recorded_unmet": unmet_rows, "preference_status": "UNKNOWN",
            "source_refs": source_refs,
            "source_hashes": {name: cut.source_hashes[f"{name}.csv"] for name in source_names},
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status,
            "decision_status": "REVIEW",
            "metric_rows": metric_rows,
            "reconciliation_id": f"learning:{cut.cut_id}:{sku_id}:{start}:{end}"}


EXCEPTION_CATEGORIES = frozenset({"COST_INCOMPLETE", "RECEIPT_UNINSPECTED", "QUALITY_HOLD",
                                  "SALES_READINESS", "LOAN_RETURN_DUE", "CUSTODY_EVIDENCE_MISSING"})
PUBLIC_CATEGORIES = frozenset({"SALES_READINESS", "QUALITY_HOLD", "LOAN_RETURN_DUE"})
SALES_FIELDS = frozenset({"category", "sku_id", "public_variant", "issue_code", "owner_role",
                          "next_action_code", "due_date", "closure_state"})
PUBLIC_ISSUE_CODES = {"SALES_READINESS": frozenset({"BLOCKED", "REVIEW"}),
                      "QUALITY_HOLD": frozenset({"QUALITY_HOLD"}),
                      "LOAN_RETURN_DUE": frozenset({"OVERDUE"})}
PUBLIC_OWNER_ROLES = {"SALES_READINESS": "COMMERCIAL_OWNER", "QUALITY_HOLD": "QUALITY_OWNER",
                      "LOAN_RETURN_DUE": "CUSTODY_OWNER"}
PUBLIC_NEXT_ACTIONS = {"SALES_READINESS": "RESOLVE_READINESS_BLOCK",
                       "QUALITY_HOLD": "RESOLVE_QUALITY_DISPOSITION",
                       "LOAN_RETURN_DUE": "CONFIRM_LOAN_RETURN"}
_PUBLIC_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9:_-]{0,63}$")
_SENSITIVE = re.compile(r"cost|cents|margin|profit|supplier|bank|recipient|budget|payment|cash|account|@|\d{7,}", re.I)


def _make_exception(
    cut: BoundCut, policy: Policy, category: str, sku_id: str, event_ref: str,
    source: str, source_ref: str, as_of: str, *, issue_code: str,
    due_date: str | None = None, severity: str = "REVIEW",
    closure_evidence_ref: str | None = None,
) -> dict[str, Any]:
    owners = policy.content["bases"].get("exception_owner_roles", {})
    actions = policy.content["bases"].get("exception_next_actions", {})
    if category not in EXCEPTION_CATEGORIES or not owners.get(category) or not actions.get(category):
        raise ValueError("missing exception policy rule")
    if due_date is not None:
        date.fromisoformat(due_date)
    identity = {"cut_id": cut.cut_id, "category": category, "event_ref": event_ref}
    exception_id = hashlib.sha256(canonical_json(identity)).hexdigest()
    return {"exception_id": exception_id, "cut_id": cut.cut_id, "as_of": as_of,
            "category": category, "sku_id": sku_id, "event_ref": event_ref,
            "issue_code": issue_code, "severity": severity,
            "evidence_ref": source_ref, "evidence_sha256": cut.source_hashes[f"{source}.csv"],
            "owner_role": owners[category], "next_action_code": actions[category],
            "due_date": due_date, "closure_status": "CLOSED" if closure_evidence_ref else "UNRESOLVED",
            "closure_evidence_ref": closure_evidence_ref,
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status,
            "reconciliation_id": f"exception:{exception_id}"}


def loan_issue(loan: dict[str, Any], *, has_return_movement: bool,
               as_of: str, grace_days: int) -> str | None:
    if not isinstance(grace_days, int) or grace_days < 0:
        raise ValueError("invalid custody grace period")
    if (loan["returned_date"] is not None or loan["status_code"] == "RETURNED") and not has_return_movement:
        return "CUSTODY_EVIDENCE_MISSING"
    if loan["status_code"] in {"OPEN", "PARTIAL"} and loan["due_date"] is not None and \
            date.fromisoformat(as_of) > date.fromisoformat(loan["due_date"]) + timedelta(days=grace_days):
        return "LOAN_RETURN_DUE"
    return None


def project_exceptions(cut: BoundCut, as_of: str, policy: Policy) -> list[dict[str, Any]]:
    """Derive unresolved actions from canonical evidence, never recipient tokens."""
    cut.coverage_status("sales_readiness", as_of)
    thresholds = policy.content["thresholds"]
    rules = ("receipt_inspection_due_days", "quality_disposition_due_days", "loan_overdue_grace_days")
    if any(name not in thresholds or not isinstance(thresholds[name], int) or thresholds[name] < 0 for name in rules):
        raise ValueError("missing exception timing policy")
    skus = _rows(cut, "SELECT sku_id FROM sku_catalog ORDER BY sku_id", {})
    exceptions = []
    for sku in skus:
        cost = project_cost(cut, sku["sku_id"], as_of, policy)
        if cost["status"] not in {"MEASURED", "ESTIMATED"}:
            source_refs = cost.get("source_refs", ())
            exceptions.append(_make_exception(cut, policy, "COST_INCOMPLETE", sku["sku_id"],
                cost.get("cost_version_id") or sku["sku_id"], "cost_components",
                source_refs[0] if source_refs else sku["sku_id"], as_of,
                issue_code="COST_INCOMPLETE", severity="INTERNAL"))
    for row in _rows(cut, _query("pending_receipts"), {"as_of": as_of}):
        due = (date.fromisoformat(row["received_date"]) +
               timedelta(days=thresholds["receipt_inspection_due_days"])).isoformat()
        exceptions.append(_make_exception(cut, policy, "RECEIPT_UNINSPECTED", row["sku_id"],
            row["receipt_id"], "purchase_receipts", row["source_ref"], as_of,
            issue_code="INSPECTION_PENDING", due_date=due, severity="HOLD"))
    for row in _rows(cut, _query("all_quality"), {"as_of": as_of}):
        if row["event_type"] not in {"RETURN_REPORTED", "REJECTED"}:
            continue
        resolution = (row["resolution_code"] or "").lower()
        if resolution and not any(token in resolution for token in ("review", "pending", "open", "hold")):
            continue
        due = (date.fromisoformat(row["event_date"]) +
               timedelta(days=thresholds["quality_disposition_due_days"])).isoformat()
        exceptions.append(_make_exception(cut, policy, "QUALITY_HOLD", row["sku_id"],
            row["quality_event_id"], "quality_events", row["source_ref"], as_of,
            issue_code="QUALITY_HOLD", due_date=due, severity="HOLD"))
    for row in _rows(cut, _query("readiness_latest"), {"as_of": as_of}):
        if row["readiness_status"] in {"BLOCKED", "REVIEW"}:
            exceptions.append(_make_exception(cut, policy, "SALES_READINESS", row["sku_id"],
                f'{row["sku_id"]}:{row["effective_date"]}', "sales_readiness", row["source_ref"],
                as_of, issue_code=row["readiness_status"], severity="HOLD"))
    returns = {row["loan_id"]: row["returned_units"] for row in
               _rows(cut, _query("loan_return_movements"), {"as_of": as_of})}
    for row in _rows(cut, _query("all_loans"), {"as_of": as_of}):
        issue = loan_issue(row, has_return_movement=returns.get(row["loan_id"], 0) >= row["quantity"],
                           as_of=as_of, grace_days=thresholds["loan_overdue_grace_days"])
        if issue is None:
            continue
        due = row["due_date"]
        exceptions.append(_make_exception(cut, policy, issue, row["sku_id"], row["loan_id"],
            "loans", row["source_ref"], as_of,
            issue_code="OVERDUE" if issue == "LOAN_RETURN_DUE" else "CUSTODY_EVIDENCE_MISSING",
            due_date=due, severity="HOLD"))
    ids = [row["exception_id"] for row in exceptions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate exception identity")
    return sorted(exceptions, key=lambda row: row["exception_id"])


def validate_sales_row(row: dict[str, Any]) -> None:
    """Reject unexpected public shape and sensitive values in allowed fields."""
    if not isinstance(row, dict) or set(row) != SALES_FIELDS:
        raise ValueError("sales projection field mismatch")
    category = row["category"]
    if category not in PUBLIC_CATEGORIES or row["issue_code"] not in PUBLIC_ISSUE_CODES[category]:
        raise ValueError("sales projection category or issue code forbidden")
    if (row["owner_role"] != PUBLIC_OWNER_ROLES[category]
            or row["next_action_code"] != PUBLIC_NEXT_ACTIONS[category]
            or row["closure_state"] not in {"OPEN", "CLOSED"}):
        raise ValueError("sales projection role, action or closure forbidden")
    for key in ("sku_id", "public_variant", "issue_code", "owner_role", "next_action_code"):
        value = row[key]
        if not isinstance(value, str) or not _PUBLIC_TOKEN.fullmatch(value) or _SENSITIVE.search(value):
            raise ValueError("unsafe sales projection value")
    if row["due_date"] is not None:
        date.fromisoformat(row["due_date"])


def sales_readiness_projection(
    cut: BoundCut, exceptions: Iterable[dict[str, Any]], policy: Policy,
) -> list[dict[str, Any]]:
    """Use fixed public fields and issue codes; internal rows never cross."""
    variants = {row["sku_id"]: row["variant_code"] for row in
                _rows(cut, "SELECT sku_id,variant_code FROM sku_catalog", {})}
    public = []
    for issue in exceptions:
        category = issue["category"]
        if category not in EXCEPTION_CATEGORIES:
            raise ValueError("unknown exception category")
        if category not in PUBLIC_CATEGORIES:
            continue
        if issue["owner_role"] != policy.content["bases"]["exception_owner_roles"][category] or \
                issue["next_action_code"] != policy.content["bases"]["exception_next_actions"][category]:
            raise ValueError("exception policy binding mismatch")
        if issue["sku_id"] not in variants:
            raise ValueError("unknown public SKU")
        row = {"category": category, "sku_id": issue["sku_id"],
               "public_variant": variants[issue["sku_id"]],
               "issue_code": issue["issue_code"], "owner_role": issue["owner_role"],
               "next_action_code": issue["next_action_code"], "due_date": issue["due_date"],
               "closure_state": "CLOSED" if issue["closure_status"] == "CLOSED" else "OPEN"}
        validate_sales_row(row)
        public.append(row)
    return public
