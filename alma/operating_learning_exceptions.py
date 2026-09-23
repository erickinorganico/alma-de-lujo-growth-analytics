"""Coverage-aware product observations and governed operating exceptions."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any, Iterable

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
        "physically received linked returns / eligible delivered units",
        "RATIO", "delivery_cohort_id", "mature as_of",
        ("sales_aggregates", "quality_events"),
        "UNKNOWN if unlinked, immature, or incompletely observed", "never count reported-only return",
        "product", "quality_review"),
    "quality_defect_rate": MetricDefinition("quality_defect_rate", "v1",
        "confirmed rejected linked units / eligible inspected linked units",
        "RATIO", "delivery_cohort_id", "mature as_of",
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
    cohorts = [row for row in sales if row["delivery_cohort_id"] is not None]
    linked_all = len(cohorts) == len(sales) and bool(sales)
    received_return_units = sum(row["units"] for row in quality if row["event_type"] == "RETURN_RECEIVED"
                                and row["delivery_cohort_id"] is not None)
    reported_return_units = sum(row["units"] for row in quality if row["event_type"] == "RETURN_REPORTED"
                                and row["delivery_cohort_id"] is not None)
    maturity_days = policy.content["maturity_windows"]["returns_days"]
    cohort_date = min((row["sales_date"] for row in sales), default=as_of)
    return_coverage = "COMPLETE" if coverage["sales_aggregates"] in {"COMPLETE", "ZERO"} and \
        coverage["quality_events"] in {"COMPLETE", "ZERO"} and all(
        row["coverage_status"] == "COMPLETE" for row in sales) else "PARTIAL"
    if reported_return_units > received_return_units:
        return_coverage = "PARTIAL"
    returns = mature_return_rate(delivered, received_return_units, cohort_date=cohort_date,
        as_of=as_of, maturity_days=maturity_days, linked=linked_all, coverage=return_coverage)
    inspected = sum(row["units"] for row in quality if row["event_type"] == "INSPECTED"
                    and row["delivery_cohort_id"] is not None)
    defects = sum(row["units"] for row in quality if row["event_type"] == "REJECTED"
                  and row["delivery_cohort_id"] is not None)
    defect_rate = mature_return_rate(inspected, defects, cohort_date=cohort_date,
        as_of=as_of, maturity_days=maturity_days, linked=linked_all and inspected > 0,
        coverage=return_coverage)
    mix_by_channel = project_variant_mix(cut, sku_id, start, end, as_of)
    mix = mix_by_channel[0] if len(mix_by_channel) == 1 else {
        "numerator": None, "denominator": None, "value": None, "status": "UNKNOWN"}
    unmet_rows = [{"demand_event_id": row["demand_event_id"], "event_date": row["event_date"],
                   "sku_id": row["sku_id"], "channel_code": row["channel_code"],
                   "reason_code": row["reason_code"], "requested_units_lower_bound": row["requested_units"],
                   "status": "MEASURED" if coverage["unmet_demand"] in {"COMPLETE", "ZERO"} else "PARTIAL",
                   "source_ref": row["source_ref"]} for row in unmet]
    source_refs = tuple(sorted({row["source_ref"] for rows in
        (sales, opening, receipts, restocks, quality, availability, unmet) for row in rows}))
    metrics = {"sell_through": sold, "mature_return_rate": returns,
               "quality_defect_rate": defect_rate, "stockout_exposure": exposure}
    metric_rows = []
    for metric_id, value in metrics.items():
        metric_rows.append(MetricRow(metric_id, cut.cut_id, as_of,
            {"sku_id": sku_id, "window_start": start, "window_end": end},
            value["numerator"], value["denominator"], value["value"], value["status"],
            LEARNING_DEFINITIONS[metric_id].sources, source_refs,
            f"learning:{cut.cut_id}:{metric_id}:{sku_id}:{start}:{end}",
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
            "quality_defects": defect_rate, "exposure": exposure,
            "recorded_unmet": unmet_rows, "preference_status": "UNKNOWN",
            "source_refs": source_refs,
            "source_hashes": {name: cut.source_hashes[f"{name}.csv"] for name in source_names},
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status,
            "decision_status": "REVIEW",
            "metric_rows": metric_rows,
            "reconciliation_id": f"learning:{cut.cut_id}:{sku_id}:{start}:{end}"}
