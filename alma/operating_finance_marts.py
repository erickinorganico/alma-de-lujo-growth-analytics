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
    "budget_headroom_cents": MetricDefinition(
        "budget_headroom_cents", "v1",
        "approved ceiling - open commitment - incurred, after source-to-target cent bridge",
        "MXN_CENTS", "budget_id x drop_code x channel_code", "budget period [start,end)",
        ("budgets", "budget_allocations", "purchase_orders", "purchase_receipts", "expenses", "obligations", "obligation_payments"),
        "UNKNOWN without approved policy, complete coverage and mapped sources",
        "paid settlement never added to exposure", "finance", "budget_reallocation_review"),
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
    documented_adjustments = original if obligation.get("status_code") == "VOID" else 0
    adjusted_original = original - documented_adjustments
    if applied > adjusted_original:
        raise ValueError("payment over-applied")
    if application_coverage not in {"COMPLETE", "PARTIAL", "ZERO", "MISSING", "ERROR", "ESTIMATED", "NOT_APPLICABLE"}:
        raise ValueError("invalid application coverage")
    complete = application_coverage in {"COMPLETE", "ZERO"}
    recorded_unpaid = adjusted_original - applied
    if complete and obligation.get("status_code") == "SETTLED" and recorded_unpaid:
        raise ValueError("settled obligation retains balance")
    return {
        "obligation_id": obligation["obligation_id"],
        "origin_type": obligation["origin_type"],
        "origin_id": obligation["origin_id"],
        "due_date": obligation["due_date"],
        "due_bucket": obligation["due_date"] or "UNDATED",
        "original_cents": original,
        "documented_adjustments_cents": documented_adjustments,
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
    scenario_events = [event for event in events if event["level"] == "SCENARIO"]
    evidence_rows = _rows(cut, _query("cash_balance_evidence"), {"scenario_id": scenario_id, "as_of": as_of})
    if len(evidence_rows) > 1 and evidence_rows[0]["period_start"] == evidence_rows[1]["period_start"]:
        raise ValueError("ambiguous independent balance evidence")
    evidence = evidence_rows[0] if evidence_rows else None
    coverage_values = [cut.coverage_status(source, as_of) for source in ("cash_events", "cash_balance_evidence")]
    coverage = "COMPLETE" if all(value in {"COMPLETE", "ZERO"} for value in coverage_values) else "PARTIAL"
    close = reconcile_cash_close(selected, evidence, coverage=coverage)
    approved = cut.input_class == "SYNTHETIC_EXAMPLE" or policy.authorizes_real_cut
    horizons = cash_horizons([*selected, *(event for event in scenario_events if event not in selected)], as_of,
                             starting_close_cents=close["close_cents"] if approved else None)
    cash_floor_cents = policy.content["thresholds"].get("minimum_cash_floor_cents")
    if not isinstance(cash_floor_cents, int) or cash_floor_cents < 0:
        raise ValueError("invalid cash floor policy")
    for horizon in horizons.values():
        horizon["minimum_cash_floor_cents"] = cash_floor_cents
        horizon["cash_floor_breached"] = (None if horizon["daily_minimum_cents"] is None
                                         else horizon["daily_minimum_cents"] < cash_floor_cents)
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
            "scenario_event_ids": tuple(event["event_id"] for event in scenario_events),
            "actual_movements_cents": actual, "reconciled_close_cents": close["close_cents"],
            "close_status": close["status"], "horizons": horizons,
            "source_refs": refs,
            "source_hashes": {name: cut.source_hashes[f"{name}.csv"] for name in ("cash_events", "cash_balance_evidence")},
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status,
            "forecast_status": "REVIEW" if not approved else ("UNKNOWN" if close["close_cents"] is None else "ESTIMATED"),
            "active_event_lineage": tuple({"event_id": event["event_id"],
                "economic_event_id": event["economic_event_id"],
                "supersedes_event_id": event["supersedes_event_id"],
                "level": event["level"], "source_ref": event["source_ref"]} for event in selected),
            "metric_row": metric_row, "reconciliation_id": metric_row.reconciliation_id}


def allocate_source_cents(
    origin: tuple[str, str], source_cents: int, allocations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Retain the exact unmapped source residual after explicit target shares."""
    if not isinstance(source_cents, int) or source_cents < 0:
        raise ValueError("invalid source cents")
    allocations = list(allocations)
    ids = [row["budget_allocation_id"] for row in allocations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate budget allocation ID")
    target_cents: dict[tuple[str, str, str], int] = {}
    for row in allocations:
        if (row["origin_type"], row["origin_id"]) != origin:
            raise ValueError("budget allocation crosses economic origin")
        target = (row["budget_id"], row["drop_code"], row["channel_code"])
        if target in target_cents:
            raise ValueError("duplicate allocation target")
        amount = row["allocated_cents"]
        if not isinstance(amount, int) or amount < 0:
            raise ValueError("invalid allocation cents")
        target_cents[target] = amount
    assigned = sum(target_cents.values())
    if assigned > source_cents:
        raise ValueError("budget allocations exceed source")
    return {"origin": origin, "source_cents": source_cents,
            "target_cents": target_cents, "unallocated_cents": source_cents - assigned,
            "allocation_ids": tuple(sorted(ids)),
            "reconciliation_id": f"allocation:{origin[0]}:{origin[1]}"}


def distribute_state_cents(state_cents: int, source_cents: int, shares: dict[str, Any]) -> dict[str, Any]:
    """Largest-remainder split with stable target keys; all state cents survive."""
    if not isinstance(state_cents, int) or state_cents < 0 or source_cents < 0:
        raise ValueError("invalid state cents")
    if source_cents == 0:
        if state_cents:
            raise ValueError("nonzero state on zero source")
        return {"target_cents": {key: 0 for key in shares["target_cents"]}, "unallocated_cents": 0}
    weights: list[tuple[tuple[str, str, str] | None, int]] = [
        *sorted(shares["target_cents"].items()), (None, shares["unallocated_cents"])]
    if sum(weight for _, weight in weights) != source_cents:
        raise ValueError("source shares do not reconcile")
    values = {key: (state_cents * weight) // source_cents for key, weight in weights}
    remainders = [(state_cents * weight) % source_cents for _, weight in weights]
    residual = state_cents - sum(values.values())
    # A real target precedes the unmapped bucket on ties.
    order = sorted(range(len(weights)), key=lambda index: (-remainders[index],
                   weights[index][0] is None, weights[index][0] or ("", "", "")))
    for index in order[:residual]:
        values[weights[index][0]] += 1
    return {"target_cents": {key: values[key] for key in shares["target_cents"]},
            "unallocated_cents": values[None]}


def project_budgets(cut: BoundCut, as_of: str, policy: Policy) -> dict[str, Any]:
    """Map one economic source into mutually exclusive budget states."""
    if policy.content["bases"].get("budget_headroom_basis") != \
            "approved_minus_open_commitment_minus_allocated_incurred":
        raise ValueError("unsupported budget headroom policy")
    budgets = _rows(cut, _query("budgets"), {"as_of": as_of})
    budget_by_id = {row["budget_id"]: row for row in _rows(cut, _query("budgets_all"))}
    active_budget_ids = {row["budget_id"] for row in budgets}
    allocations = _rows(cut, _query("budget_allocations"))
    allocations_by_origin: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in allocations:
        allocations_by_origin[(row["origin_type"], row["origin_id"])].append(row)
    scoped_origins = {(row["origin_type"], row["origin_id"]) for row in allocations
                      if row["budget_id"] in active_budget_ids}
    purchase_rows = _rows(cut, _query("purchase_sources"), {"as_of": as_of})
    receipt_totals = {row["purchase_order_id"]: row["received_units"] for row in
                      _rows(cut, _query("purchase_receipt_totals"), {"as_of": as_of})}
    expense_rows = _rows(cut, _query("expense_sources"), {"as_of": as_of})
    obligations = _rows(cut, _query("obligations"))
    obligation_by_origin: dict[tuple[str, str], dict[str, Any]] = {}
    for obligation in obligations:
        origin = (obligation["origin_type"], obligation["origin_id"])
        if origin in obligation_by_origin:
            raise ValueError("ambiguous obligation origin")
        obligation_by_origin[origin] = obligation
    payments = _rows(cut, _query("payments_by_id"), {"as_of": as_of})
    payment_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payment in payments:
        payment_groups[payment["obligation_id"]].append(payment)
    sources: dict[tuple[str, str], dict[str, Any]] = {}
    for po in purchase_rows:
        origin = ("PURCHASE_ORDER", po["purchase_order_id"])
        if po["budget_id"] not in active_budget_ids and origin not in scoped_origins:
            continue
        ordered = po["ordered_units"]
        received = receipt_totals.get(po["purchase_order_id"], 0)
        if received > ordered:
            raise ValueError("purchase receipt exceeds ordered units")
        total = ordered * po["agreed_unit_cents"]
        incurred = received * po["agreed_unit_cents"]
        open_commitment = total - incurred if po["status_code"] in {"OPEN", "PARTIAL"} else 0
        sources[origin] = {"source_cents": total, "open_commitment_cents": open_commitment,
                           "incurred_cents": incurred, "source_ref": po["source_ref"]}
    for expense in expense_rows:
        origin = ("EXPENSE", expense["expense_id"])
        if expense["budget_id"] not in active_budget_ids and origin not in scoped_origins:
            continue
        amount = expense["amount_cents"]
        sources[origin] = {"source_cents": amount, "open_commitment_cents": 0,
                           "incurred_cents": amount if expense["status_code"] == "INCURRED" else 0,
                           "source_ref": expense["source_ref"]}
    target_states: dict[tuple[str, str, str], dict[str, int]] = {}
    target_refs: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for budget in budgets:
        key = (budget["budget_id"], budget["drop_code"], budget["channel_code"])
        target_states[key] = {"approved_ceiling_cents": budget["approved_cents"],
                              "open_commitment_cents": 0, "incurred_cents": 0,
                              "paid_cents": 0, "outstanding_obligation_cents": 0}
        target_refs[key].add(budget["source_ref"])
    source_results = []
    unallocated_total = 0
    for origin, source in sorted(sources.items()):
        obligation = obligation_by_origin.get(origin)
        applied = 0
        outstanding = 0
        if obligation is not None:
            if obligation["original_cents"] != source["source_cents"]:
                raise ValueError("obligation amount differs from economic source")
            balance = reconcile_obligation(obligation, payment_groups.pop(obligation["obligation_id"], []),
                                           as_of=as_of, application_coverage="COMPLETE")
            applied = balance["recorded_applied_cents"]
            outstanding = balance["recorded_unpaid_cents"]
        origin_allocations = allocations_by_origin.pop(origin, [])
        shares = allocate_source_cents(origin, source["source_cents"], origin_allocations)
        for target in shares["target_cents"]:
            if target[0] not in budget_by_id:
                raise ValueError("allocation targets missing budget")
            target_states.setdefault(target, {"approved_ceiling_cents": 0,
                "open_commitment_cents": 0, "incurred_cents": 0, "paid_cents": 0,
                "outstanding_obligation_cents": 0})
            target_refs[target].add(source["source_ref"])
        for allocation in origin_allocations:
            target_refs[(allocation["budget_id"], allocation["drop_code"], allocation["channel_code"])].add(allocation["source_ref"])
        unallocated_total += shares["unallocated_cents"]
        for field, amount in (("open_commitment_cents", source["open_commitment_cents"]),
                              ("incurred_cents", source["incurred_cents"]),
                              ("paid_cents", applied),
                              ("outstanding_obligation_cents", outstanding)):
            distributed = distribute_state_cents(amount, source["source_cents"], shares)
            for target, cents in distributed["target_cents"].items():
                target_states[target][field] += cents
        source_results.append({"origin_type": origin[0], "origin_id": origin[1],
                               **source, "paid_cents": applied,
                               "outstanding_obligation_cents": outstanding,
                               "allocated_cents": sum(shares["target_cents"].values()),
                               "unallocated_cents": shares["unallocated_cents"],
                               "allocation_ids": shares["allocation_ids"],
                               "reconciliation_id": shares["reconciliation_id"]})
    all_origins = ({("PURCHASE_ORDER", row["purchase_order_id"]) for row in
                    _rows(cut, "SELECT purchase_order_id FROM purchase_orders")}
                   | {("EXPENSE", row["expense_id"]) for row in
                      _rows(cut, "SELECT expense_id FROM expenses")})
    if any(origin not in all_origins for origin in allocations_by_origin):
        raise ValueError("allocation references absent economic source")
    required = ("budgets", "budget_allocations", "purchase_orders", "purchase_receipts",
                "expenses", "obligations", "obligation_payments")
    coverage = [cut.coverage_status(name, as_of) for name in required]
    approved = cut.input_class == "SYNTHETIC_EXAMPLE" or policy.authorizes_real_cut
    headroom_eligible = approved and not unallocated_total and all(
        status in {"COMPLETE", "ZERO"} for status in coverage)
    targets = []
    for target, state in sorted(target_states.items()):
        budget_id, drop_code, channel_code = target
        if budget_id not in active_budget_ids:
            continue
        headroom = (state["approved_ceiling_cents"] - state["open_commitment_cents"] - state["incurred_cents"])
        status = "MEASURED" if headroom_eligible else "PARTIAL"
        reconciliation_id = f"budget:{cut.cut_id}:{budget_id}:{drop_code}:{channel_code}:{as_of}"
        metric_row = MetricRow("budget_headroom_cents", cut.cut_id, as_of,
            {"budget_id": budget_id, "drop_code": drop_code, "channel_code": channel_code},
            state["approved_ceiling_cents"], 1, headroom if headroom_eligible else None,
            status, required, tuple(sorted(target_refs[target])), reconciliation_id,
            policy.version, policy.sha256, policy.status)
        targets.append({"budget_id": budget_id, "drop_code": drop_code,
                        "channel_code": channel_code, **state,
                        "headroom_cents": headroom if headroom_eligible else None,
                        "status": status, "cut_id": cut.cut_id, "as_of": as_of,
                        "policy_version": policy.version, "policy_sha256": policy.sha256,
                        "policy_status": policy.status,
                        "source_refs": tuple(sorted(target_refs[target])),
                        "reconciliation_id": reconciliation_id, "metric_row": metric_row})
    return {"cut_id": cut.cut_id, "as_of": as_of, "timezone": cut.timezone,
            "targets": targets, "sources": source_results,
            "unallocated_cents": unallocated_total,
            "source_hashes": {name: cut.source_hashes[f"{name}.csv"] for name in required},
            "policy_version": policy.version, "policy_sha256": policy.sha256,
            "policy_status": policy.status}
