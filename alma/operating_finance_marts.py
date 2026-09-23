"""Source-grain, read-only finance projections for verified operating-v1 cuts."""
from __future__ import annotations

from collections import defaultdict
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
