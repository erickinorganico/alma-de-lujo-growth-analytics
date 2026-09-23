"""Source-grain, read-only finance projections for verified operating-v1 cuts."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from alma.operating_mart_contracts import BoundCut, MetricDefinition, MetricRow, Policy

SQL_PATH = Path(__file__).resolve().parents[1] / "models" / "operating_finance_marts.sql"

FINANCE_DEFINITIONS = {
    "recorded_unpaid_cents": MetricDefinition(
        "recorded_unpaid_cents", "v1",
        "original_cents - documented_adjustments_cents - distinct_applied_cents",
        "MXN_CENTS", "obligation_id", "as_of", ("obligations", "obligation_payments"),
        "recorded exposure survives partial application coverage", "applied <= adjusted original",
        "finance", "liability_review"),
    "authoritative_outstanding_cents": MetricDefinition(
        "authoritative_outstanding_cents", "v1", "recorded_unpaid_cents if application coverage complete",
        "MXN_CENTS", "obligation_id", "as_of", ("obligations", "obligation_payments"),
        "UNKNOWN when application coverage incomplete", "unique payment and origin IDs",
        "finance", "cash_commitment_review"),
    "reconciled_cash_close_cents": MetricDefinition(
        "reconciled_cash_close_cents", "v1",
        "independently observed opening + distinct settled inflows - outflows = observed closing",
        "MXN_CENTS", "scenario_id", "as_of", ("cash_events", "cash_balance_evidence"),
        "UNKNOWN without observed opening and closing", "opening-plus-flows equals independent close",
        "finance", "cash_floor_review"),
    "cash_layer_cents": MetricDefinition(
        "cash_layer_cents", "v1", "sum(active economic events by separate cash layer)",
        "MXN_CENTS", "scenario_id x horizon x layer", "56/91 day half-open",
        ("cash_events", "cash_balance_evidence"), "UNKNOWN balance without observed close",
        "one active economic identity", "finance", "liquidity_projection_review"),
}


def _query(name: str) -> str:
    for block in SQL_PATH.read_text(encoding="utf-8").split("-- name: ")[1:]:
        label, _, statement = block.partition("\n")
        if label.strip() == name:
            return statement.strip()
    raise ValueError(f"unknown finance query: {name}")


def _rows(cut: BoundCut, statement: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row) for row in cut.connection.execute(statement, parameters or {})]


def reconcile_obligation(
    obligation: dict[str, Any], payments: Iterable[dict[str, Any]], *,
    as_of: str, application_coverage: str,
) -> dict[str, Any]:
    """Calculate recorded exposure; promote it only with complete applications."""
    payments = [payment for payment in payments if payment["paid_date"] <= as_of]
    payment_ids = [payment["payment_id"] for payment in payments]
    if len(payment_ids) != len(set(payment_ids)):
        raise ValueError("duplicate payment application")
    if any(payment["obligation_id"] != obligation["obligation_id"] for payment in payments):
        raise ValueError("payment applies to different obligation")
    original = obligation["original_cents"]
    if not isinstance(original, int) or original < 0:
        raise ValueError("invalid obligation amount")
    if any(not isinstance(payment["amount_cents"], int) or payment["amount_cents"] < 0 for payment in payments):
        raise ValueError("invalid payment cents")
    applied = sum(payment["amount_cents"] for payment in payments)
    if applied > original:
        raise ValueError("payment over-applied")
    if application_coverage not in {"COMPLETE", "PARTIAL", "ZERO", "MISSING", "ERROR", "ESTIMATED", "NOT_APPLICABLE"}:
        raise ValueError("invalid application coverage")
    complete = application_coverage in {"COMPLETE", "ZERO"}
    recorded_unpaid = original - applied
    return {
        "obligation_id": obligation["obligation_id"],
        "origin_type": obligation["origin_type"],
        "origin_id": obligation["origin_id"],
        "due_date": obligation["due_date"],
        "due_bucket": obligation["due_date"] or "UNDATED",
        "original_cents": original,
        "documented_adjustments_cents": 0,
        "recorded_applied_cents": applied,
        "recorded_unpaid_cents": recorded_unpaid,
        "authoritative_outstanding_cents": recorded_unpaid if complete else None,
        "status": "MEASURED" if complete else ("UNKNOWN" if application_coverage in {"MISSING", "ERROR"} else "PARTIAL"),
        "payment_ids": tuple(sorted(payment_ids)),
        "source_refs": tuple(sorted({obligation["source_ref"], *(payment["source_ref"] for payment in payments)})),
        "reconciliation_id": f'obligation:{obligation["obligation_id"]}:{as_of}',
    }


def project_obligations(cut: BoundCut, as_of: str) -> list[dict[str, Any]]:
    """Apply each payment at its canonical ID before origin-state joins."""
    cut.coverage_status("obligations", as_of)
    obligation_rows = _rows(cut, _query("obligations"))
    origins = [(row["origin_type"], row["origin_id"]) for row in obligation_rows]
    if len(origins) != len(set(origins)):
        raise ValueError("duplicate obligation origin")
    payment_rows = _rows(cut, _query("payments_by_id"), {"as_of": as_of})
    raw_count = cut.connection.execute(
        "SELECT COUNT(*) FROM obligation_payments WHERE paid_date <= ?", (as_of,)).fetchone()[0]
    if raw_count != len(payment_rows):
        raise ValueError("payment ID aggregation collision")
    payment_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payment in payment_rows:
        payment_groups[payment["obligation_id"]].append(payment)
    results = []
    coverage = [cut.coverage_status(source, as_of) for source in ("obligations", "obligation_payments")]
    application_coverage = "COMPLETE" if all(value in {"COMPLETE", "ZERO"} for value in coverage) else (
        "MISSING" if any(value in {"MISSING", "ERROR"} for value in coverage) else "PARTIAL")
    for obligation in obligation_rows:
        row = reconcile_obligation(obligation, payment_groups.pop(obligation["obligation_id"], []),
                                   as_of=as_of, application_coverage=application_coverage)
        row.update(cut_id=cut.cut_id, as_of=as_of, timezone=cut.timezone,
                   source_hashes={name: cut.source_hashes[f"{name}.csv"] for name in ("obligations", "obligation_payments")})
        row["metric_row"] = MetricRow(
            "recorded_unpaid_cents", cut.cut_id, as_of,
            {"obligation_id": row["obligation_id"]}, row["original_cents"], 1,
            row["recorded_unpaid_cents"], row["status"],
            ("obligations", "obligation_payments"), row["source_refs"], row["reconciliation_id"])
        results.append(row)
    if payment_groups:
        raise ValueError("orphan payment application")
    return results


def active_cash_events(events: Iterable[dict[str, Any]], as_of: str) -> list[dict[str, Any]]:
    """Select one as-of active leaf per scenario/economic identity."""
    events = list(events)
    by_id = {event["event_id"]: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("duplicate cash event ID")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event["amount_cents"] < 0 or event["direction"] not in {"INFLOW", "OUTFLOW"}:
            raise ValueError("invalid cash event")
        grouped[(event["scenario_id"], event["economic_event_id"])].append(event)
    active = []
    for identity, group in grouped.items():
        descendants: dict[str, dict[str, Any]] = {}
        for event in group:
            predecessor_id = event["supersedes_event_id"]
            if predecessor_id is None:
                continue
            predecessor = by_id.get(predecessor_id)
            if predecessor is None or (predecessor["scenario_id"], predecessor["economic_event_id"]) != identity:
                raise ValueError("cash supersession crosses identity")
            if predecessor_id in descendants:
                raise ValueError("cash supersession fork")
            descendants[predecessor_id] = event
        roots = [event for event in group if event["supersedes_event_id"] is None]
        if len(roots) != 1:
            raise ValueError("ambiguous economic identity")
        ordered = []
        seen: set[str] = set()
        current = roots[0]
        while current is not None:
            if current["event_id"] in seen:
                raise ValueError("cash supersession cycle")
            seen.add(current["event_id"])
            ordered.append(current)
            current = descendants.get(current["event_id"])
        if len(seen) != len(group):
            raise ValueError("disconnected cash identity")
        eligible = [event for event in ordered if event["level"] != "RECONCILED" or
                    (event["event_date"] is not None and event["event_date"] <= as_of)]
        if not eligible:
            continue
        winner = eligible[-1]
        if winner["level"] == "RECONCILED" and not winner.get("payment_id"):
            raise ValueError("settled cash lacks payment evidence")
        active.append(winner)
    return sorted(active, key=lambda event: (event["scenario_id"], event["economic_event_id"]))


def _signed(event: dict[str, Any]) -> int:
    return event["amount_cents"] if event["direction"] == "INFLOW" else -event["amount_cents"]


def reconcile_cash_close(
    events: Iterable[dict[str, Any]], evidence: dict[str, Any] | None, *, coverage: str,
) -> dict[str, Any]:
    """Require both independent observed balances and exact settled-flow bridge."""
    if evidence is None or coverage not in {"COMPLETE", "ZERO"}:
        return {"status": "UNKNOWN", "close_cents": None, "calculated_close_cents": None}
    if (evidence["evidence_status"] != "OBSERVED" or evidence["opening_balance_cents"] is None
            or evidence["closing_balance_cents"] is None or evidence["opening_observed_at"] is None
            or evidence["closing_observed_at"] is None):
        return {"status": "UNKNOWN", "close_cents": None, "calculated_close_cents": None}
    if (evidence["opening_observed_at"][:10] != evidence["period_start"]
            or evidence["closing_observed_at"][:10] != evidence["period_end"]):
        return {"status": "ERROR", "close_cents": None, "calculated_close_cents": None}
    events = [event for event in events if event["level"] == "RECONCILED"
              and event["event_date"] is not None
              and evidence["period_start"] <= event["event_date"] <= evidence["period_end"]]
    ids = [event["event_id"] for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("settled cash event replay")
    calculated = evidence["opening_balance_cents"] + sum(_signed(event) for event in events)
    if calculated != evidence["closing_balance_cents"]:
        return {"status": "ERROR", "close_cents": None, "calculated_close_cents": calculated}
    return {"status": "MEASURED", "close_cents": calculated, "calculated_close_cents": calculated}


def cash_horizons(
    events: Iterable[dict[str, Any]], as_of: str, *, starting_close_cents: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Project 56 and 91 daily dates from the same active event set."""
    events = list(events)
    start = date.fromisoformat(as_of)
    results = {}
    for days in (56, 91):
        end = start + timedelta(days=days)
        layers = {name: 0 for name in ("RECONCILED", "COMMITTED", "EXPECTED")}
        undated = 0
        scenario = 0
        weekly: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        daily_flow: dict[date, int] = defaultdict(int)
        for event in events:
            level = event["level"]
            amount = _signed(event)
            if level == "UNDATED":
                undated += amount
                continue
            if event["event_date"] is None:
                raise ValueError("dated cash layer missing date")
            day = date.fromisoformat(event["event_date"])
            if not start <= day < end:
                continue
            if level == "SCENARIO":
                scenario += amount
                continue
            if level not in layers:
                raise ValueError("unknown cash layer")
            layers[level] += amount
            weekly[(day - start).days // 7][level] += amount
            if level in {"COMMITTED", "EXPECTED"}:
                daily_flow[day] += amount
        daily_closes = None
        daily_minimum = None
        if starting_close_cents is not None:
            balance = starting_close_cents
            daily_closes = {}
            for offset in range(days):
                day = start + timedelta(days=offset)
                balance += daily_flow[day]
                daily_closes[day.isoformat()] = balance
            daily_minimum = min(starting_close_cents, *daily_closes.values())
        results[days] = {"start": as_of, "end": end.isoformat(), "layers_cents": layers,
                         "undated_cents": undated, "scenario_cents": scenario,
                         "weekly_layers_cents": {week: dict(amounts) for week, amounts in weekly.items()},
                         "daily_closes_cents": daily_closes, "daily_minimum_cents": daily_minimum}
    return results


def project_cash(
    cut: BoundCut, as_of: str, policy: Policy, *, scenario_id: str | None = None,
) -> dict[str, Any]:
    """Expose raw layers and only independently reconciled actual/baseline close."""
    if policy.content["bases"].get("cash_projection_selection") != "active_leaf_precedence" or \
            policy.content["bases"].get("cash_floor_basis") != "daily_minimum_cents":
        raise ValueError("unsupported cash projection policy")
    cut.coverage_status("cash_events", as_of)
    events = active_cash_events(_rows(cut, _query("cash_events")), as_of)
    scenarios = {event["scenario_id"] for event in events if event["level"] != "SCENARIO"}
    if scenario_id is None:
        if len(scenarios) != 1:
            raise ValueError("cash scenario must be selected")
        scenario_id = next(iter(scenarios))
    selected = [event for event in events if event["scenario_id"] == scenario_id]
    evidence_rows = _rows(cut, _query("cash_balance_evidence"), {"scenario_id": scenario_id, "as_of": as_of})
    if len(evidence_rows) > 1 and evidence_rows[0]["period_start"] == evidence_rows[1]["period_start"]:
        raise ValueError("ambiguous independent balance evidence")
    evidence = evidence_rows[0] if evidence_rows else None
    coverage_values = [cut.coverage_status(source, as_of) for source in ("cash_events", "cash_balance_evidence")]
    coverage = "COMPLETE" if all(value in {"COMPLETE", "ZERO"} for value in coverage_values) else "PARTIAL"
    close = reconcile_cash_close(selected, evidence, coverage=coverage)
    approved = cut.input_class == "SYNTHETIC_EXAMPLE" or policy.authorizes_real_cut
    horizons = cash_horizons(selected, as_of,
                             starting_close_cents=close["close_cents"] if approved else None)
    actual = sum(_signed(event) for event in selected if event["level"] == "RECONCILED")
    refs = tuple(sorted({event["source_ref"] for event in selected}
                        | ({evidence["source_ref"]} if evidence else set())))
    metric_row = MetricRow(
        "reconciled_cash_close_cents", cut.cut_id, as_of, {"scenario_id": scenario_id},
        evidence["opening_balance_cents"] if evidence else None, 1,
        close["close_cents"], close["status"],
        ("cash_events", "cash_balance_evidence"), refs,
        f"cash:{cut.cut_id}:{scenario_id}:{as_of}", policy.version, policy.sha256, policy.status)
    return {"cut_id": cut.cut_id, "as_of": as_of, "timezone": cut.timezone,
            "scenario_id": scenario_id, "active_event_ids": tuple(event["event_id"] for event in selected),
            "actual_movements_cents": actual, "reconciled_close_cents": close["close_cents"],
            "close_status": close["status"], "horizons": horizons,
            "source_refs": refs,
            "source_hashes": {name: cut.source_hashes[f"{name}.csv"] for name in ("cash_events", "cash_balance_evidence")},
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status, "forecast_status": "REVIEW" if not approved else "MEASURED",
            "metric_row": metric_row, "reconciliation_id": metric_row.reconciliation_id}
