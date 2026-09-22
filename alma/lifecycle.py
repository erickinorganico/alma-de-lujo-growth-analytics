"""Synthetic business lifecycle replay with immutable events and fail-closed gates.

This module is an analytical demonstration.  It validates explicitly supplied
synthetic events; it does not reconstruct unobserved real operations and has no
connector or business-action execution path.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFINITION_DIR = ROOT / "processes" / "business"


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def definitions() -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(DEFINITION_DIR.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8-sig"))
        if path.stem != item.get("id") or item["id"] in found:
            raise ValueError("Business process definition identity mismatch")
        required = {"contract_id", "id", "version", "owner", "initial_state", "terminal_states", "transitions"}
        if set(item) != required or not item["transitions"]:
            raise ValueError("Business process definition fields invalid: " + path.name)
        found[item["id"]] = item
    expected = {
        "procure-to-stock", "lead-to-delivery", "return-to-refund",
        "finance-close", "weekly-growth-review", "market-to-experiment",
    }
    if set(found) != expected:
        raise ValueError("Exactly six business process definitions are required")
    return found


def _connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = _connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_instances (
              process_id TEXT NOT NULL,
              process_contract_id TEXT NOT NULL,
              instance_id TEXT NOT NULL,
              definition_version TEXT NOT NULL,
              owner_role TEXT NOT NULL,
              scenario_id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              current_state TEXT NOT NULL,
              blocked_reason TEXT,
              last_event_hash TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              synthetic INTEGER NOT NULL CHECK (synthetic = 1),
              PRIMARY KEY (process_id, instance_id)
            ) STRICT;

            CREATE TABLE IF NOT EXISTS lifecycle_events (
              process_id TEXT NOT NULL,
              instance_id TEXT NOT NULL,
              sequence INTEGER NOT NULL CHECK (sequence > 0),
              event_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              from_state TEXT NOT NULL,
              to_state TEXT NOT NULL,
              occurred_at_utc TEXT NOT NULL,
              recorded_at_utc TEXT NOT NULL,
              payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
              payload_hash TEXT NOT NULL,
              source_refs_json TEXT NOT NULL CHECK (json_valid(source_refs_json)),
              idempotency_key TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL,
              synthetic INTEGER NOT NULL CHECK (synthetic = 1),
              PRIMARY KEY (process_id, instance_id, sequence),
              UNIQUE (event_id),
              UNIQUE (event_hash),
              FOREIGN KEY (process_id, instance_id)
                REFERENCES lifecycle_instances(process_id, instance_id)
            ) STRICT;

            CREATE TABLE IF NOT EXISTS lifecycle_idempotency (
              process_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              instance_id TEXT NOT NULL,
              event_id TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              result_status TEXT NOT NULL,
              receipt_json TEXT NOT NULL CHECK (json_valid(receipt_json)),
              PRIMARY KEY (process_id, idempotency_key)
            ) STRICT;

            CREATE TABLE IF NOT EXISTS lifecycle_receipts (
              receipt_id TEXT PRIMARY KEY,
              process_id TEXT NOT NULL,
              instance_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              status TEXT NOT NULL,
              exception_code TEXT,
              state_before TEXT NOT NULL,
              state_after TEXT NOT NULL,
              event_hash TEXT,
              recorded_at_utc TEXT NOT NULL,
              receipt_json TEXT NOT NULL CHECK (json_valid(receipt_json))
            ) STRICT;

            CREATE TRIGGER IF NOT EXISTS lifecycle_events_no_update
              BEFORE UPDATE ON lifecycle_events BEGIN SELECT RAISE(ABORT, 'lifecycle events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS lifecycle_events_no_delete
              BEFORE DELETE ON lifecycle_events BEGIN SELECT RAISE(ABORT, 'lifecycle events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS lifecycle_idempotency_no_update
              BEFORE UPDATE ON lifecycle_idempotency BEGIN SELECT RAISE(ABORT, 'idempotency records are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS lifecycle_idempotency_no_delete
              BEFORE DELETE ON lifecycle_idempotency BEGIN SELECT RAISE(ABORT, 'idempotency records are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS lifecycle_receipts_no_update
              BEFORE UPDATE ON lifecycle_receipts BEGIN SELECT RAISE(ABORT, 'lifecycle receipts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS lifecycle_receipts_no_delete
              BEFORE DELETE ON lifecycle_receipts BEGIN SELECT RAISE(ABORT, 'lifecycle receipts are immutable'); END;
            """
        )
        db.commit()
    finally:
        db.close()
    return path


def _utc(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("Timestamp must use UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _required(payload: dict[str, Any], *keys: str) -> bool:
    return all(key in payload and payload[key] is not None and payload[key] != "" for key in keys)


def _positive_int(value: Any, allow_zero: bool = False) -> bool:
    return type(value) is int and (value >= 0 if allow_zero else value > 0)


def _approval(payload: dict[str, Any], instance_id: str) -> bool:
    approval = payload.get("approval")
    return (
        isinstance(approval, dict)
        and approval.get("synthetic") is True
        and approval.get("decision") == "APPROVE"
        and approval.get("scope") == instance_id
        and isinstance(approval.get("approval_id"), str)
        and bool(approval["approval_id"])
        and isinstance(approval.get("approver_role"), str)
        and approval["approver_role"].startswith("synthetic_")
    )


def _forbid_execution(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in {"execute", "executed", "external_action"} and child not in (False, None, "PROHIBITED"):
                raise ValueError("External business execution is prohibited")
            if lowered == "execution" and child != "PROHIBITED":
                raise ValueError("Execution field must be PROHIBITED")
            _forbid_execution(child)
    elif isinstance(value, list):
        for child in value:
            _forbid_execution(child)


def _payloads(db: sqlite3.Connection, process_id: str, instance_id: str, event_type: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT event_type,payload_json,occurred_at_utc FROM lifecycle_events WHERE process_id=? AND instance_id=?"
    args: list[Any] = [process_id, instance_id]
    if event_type is not None:
        sql += " AND event_type=?"
        args.append(event_type)
    sql += " ORDER BY sequence"
    return [{"event_type": row["event_type"], "payload": json.loads(row["payload_json"]), "occurred_at_utc": row["occurred_at_utc"]} for row in db.execute(sql, args)]


def _first_payload(history: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    return next((row["payload"] for row in history if row["event_type"] == event_type), None)


def _gate(
    gate: str,
    process_id: str,
    instance_id: str,
    payload: dict[str, Any],
    history: list[dict[str, Any]],
) -> tuple[str, str | None, dict[str, Any]]:
    """Return PASS/WAITING/FAIL, exception code, and observed gate evidence."""
    if gate == "reason":
        ok = isinstance(payload.get("reason"), str) and bool(payload["reason"].strip())
        return ("PASS", None, {}) if ok else ("FAIL", "REASON_REQUIRED", {})
    if gate == "synthetic_approval":
        if _approval(payload, instance_id):
            return "PASS", None, {"approval_id": payload["approval"]["approval_id"], "synthetic": True}
        return "WAITING", "APPROVAL_MISSING", {"required_scope": instance_id}

    if process_id == "procure-to-stock":
        drafted = _first_payload(history, "po_drafted") or {}
        ordered = drafted.get("quantity", 0)
        receipts = [row["payload"] for row in history if row["event_type"] in {"goods_partially_received", "goods_fully_received"}]
        accepted = sum(row.get("accepted_qty", 0) for row in receipts)
        rejected = sum(row.get("rejected_qty", 0) for row in receipts)
        if gate == "valid_po":
            ok = _positive_int(payload.get("quantity")) and _positive_int(payload.get("unit_cost_cents"), True) and payload.get("currency") == "MXN"
            return ("PASS", None, {"ordered": payload.get("quantity")}) if ok else ("FAIL", "PROC_INVALID_PO", {})
        if gate == "po_totals":
            expected = drafted.get("quantity", -1) * drafted.get("unit_cost_cents", -1)
            ok = payload.get("total_cents") == expected and expected >= 0
            return ("PASS", None, {"expected_total_cents": expected}) if ok else ("FAIL", "PROC_TOTAL_MISMATCH", {"expected_total_cents": expected})
        if gate == "dispatch_quantity":
            qty = payload.get("quantity")
            ok = _positive_int(qty) and qty <= ordered
            return ("PASS", None, {"ordered": ordered}) if ok else ("FAIL", "PROC_OVER_DISPATCH", {"ordered": ordered})
        if gate in {"receipt_quantity", "full_receipt"}:
            add_accepted, add_rejected = payload.get("accepted_qty"), payload.get("rejected_qty", 0)
            numeric = _positive_int(add_accepted, True) and _positive_int(add_rejected, True) and add_accepted + add_rejected > 0
            cumulative = accepted + rejected + (add_accepted or 0) + (add_rejected or 0)
            if not numeric or cumulative > ordered:
                return "FAIL", "PROC_OVER_RECEIPT", {"ordered": ordered, "attempted_cumulative": cumulative}
            if gate == "full_receipt" and cumulative != ordered:
                return "FAIL", "PROC_RECEIPT_INCOMPLETE", {"ordered": ordered, "attempted_cumulative": cumulative}
            return "PASS", None, {"ordered": ordered, "cumulative": cumulative}
        if gate == "receipt_inventory_bridge":
            ok = payload.get("accepted_units") == accepted and payload.get("inventory_units") == accepted
            return ("PASS", None, {"accepted": accepted}) if ok else ("FAIL", "INV_LEDGER_RECEIPT_MISMATCH", {"accepted": accepted})

    if process_id == "lead-to-delivery":
        order = _first_payload(history, "order_placed") or {}
        reserved = (_first_payload(history, "inventory_reserved") or {}).get("quantity", 0)
        shipped = sum(row["payload"].get("quantity", 0) for row in history if row["event_type"] == "shipment_posted")
        if gate == "lead_source":
            ok = _required(payload, "channel", "source_kind") and payload["source_kind"] in {"session", "offline_declared"}
            return ("PASS", None, {}) if ok else ("FAIL", "SOURCE_NOT_OBSERVED", {})
        if gate == "valid_order":
            lines = payload.get("lines")
            ok = isinstance(lines, list) and bool(lines)
            total = 0
            if ok:
                for line in lines:
                    if not isinstance(line, dict) or not _positive_int(line.get("quantity")) or not _positive_int(line.get("unit_price_cents"), True) or line.get("lifecycle") in {"idea", "sample"}:
                        ok = False
                        break
                    total += line["quantity"] * line["unit_price_cents"] - line.get("discount_cents", 0)
            ok = ok and payload.get("ordered_cents") == total and total >= 0
            return ("PASS", None, {"calculated_ordered_cents": total}) if ok else ("FAIL", "ORDER_INVALID_LINE", {"calculated_ordered_cents": total})
        if gate == "order_policy":
            ok = isinstance(payload.get("policy_version"), str) and bool(payload["policy_version"])
            return ("PASS", None, {}) if ok else ("FAIL", "ORDER_POLICY_REVIEW", {})
        if gate == "settlement":
            ok = _positive_int(payload.get("amount_cents"), True) and payload.get("amount_cents") == order.get("ordered_cents")
            return ("PASS", None, {}) if ok else ("FAIL", "PAYMENT_RECONCILIATION", {"ordered_cents": order.get("ordered_cents")})
        if gate == "payment_attempt":
            ok = _required(payload, "attempt_id", "failure_code")
            return ("PASS", None, {}) if ok else ("FAIL", "PAYMENT_ATTEMPT_INVALID", {})
        if gate == "available_stock":
            ok = _positive_int(payload.get("quantity")) and _positive_int(payload.get("available_units"), True) and payload["quantity"] <= payload["available_units"]
            return ("PASS", None, {}) if ok else ("FAIL", "INV_NEGATIVE_AVAILABLE", {})
        if gate == "reserved_quantity":
            ok = _positive_int(payload.get("quantity")) and payload["quantity"] <= reserved
            return ("PASS", None, {}) if ok else ("FAIL", "SHIPMENT_RESERVATION_MISMATCH", {"reserved": reserved})
        if gate == "shipment_quantity":
            qty = payload.get("quantity")
            ok = _positive_int(qty) and shipped + qty <= reserved
            return ("PASS", None, {"reserved": reserved}) if ok else ("FAIL", "SHIPMENT_RESERVATION_MISMATCH", {"reserved": reserved})
        if gate == "delivery_quantity":
            qty = payload.get("quantity")
            ok = _positive_int(qty) and qty <= shipped
            return ("PASS", None, {"shipped": shipped}) if ok else ("FAIL", "STATE_INVALID_TRANSITION", {"shipped": shipped})

    if process_id == "return-to-refund":
        requested = _first_payload(history, "return_requested") or {}
        authorized = _first_payload(history, "return_authorized") or {}
        received = _first_payload(history, "return_received") or {}
        inspected = _first_payload(history, "return_inspected") or {}
        refund_request = _first_payload(history, "refund_requested") or {}
        if gate == "return_eligibility":
            ok = _positive_int(payload.get("requested_qty")) and _positive_int(payload.get("delivered_qty")) and payload["requested_qty"] <= payload["delivered_qty"]
            return ("PASS", None, {}) if ok else ("FAIL", "RETURN_EXCEEDS_DELIVERED", {})
        if gate == "return_approval":
            ok = _approval(payload, instance_id) and payload.get("authorized_qty") == requested.get("requested_qty") and _positive_int(payload.get("authorized_amount_cents"), True)
            return ("PASS", None, {}) if ok else ("WAITING", "APPROVAL_MISSING", {})
        if gate == "tracking_status":
            ok = _required(payload, "tracking_status")
            return ("PASS", None, {}) if ok else ("FAIL", "RETURN_TRACKING_UNKNOWN", {})
        if gate == "return_receipt":
            ok = _positive_int(payload.get("received_qty")) and payload["received_qty"] <= authorized.get("authorized_qty", 0)
            return ("PASS", None, {}) if ok else ("FAIL", "RETURN_OVER_RECEIPT", {})
        if gate == "disposition":
            ok = payload.get("disposition") in {"RESTOCK", "DAMAGED", "REPAIR", "DISCARD"} and payload.get("quantity") == received.get("received_qty")
            return ("PASS", None, {}) if ok else ("FAIL", "RETURN_DISPOSITION_UNKNOWN", {})
        if gate == "refund_approval":
            amount = payload.get("amount_cents")
            ok = _approval(payload, instance_id) and _positive_int(amount, True) and amount <= authorized.get("authorized_amount_cents", -1) and amount <= payload.get("eligible_settled_cents", -1)
            return ("PASS", None, {}) if ok else ("WAITING", "APPROVAL_MISSING", {})
        if gate == "refund_limit":
            amount = payload.get("amount_cents")
            limit = min(payload.get("eligible_settled_cents", -1), refund_request.get("amount_cents", -1))
            ok = _positive_int(amount, True) and amount <= limit
            return ("PASS", None, {"limit": limit}) if ok else ("FAIL", "FIN_REFUND_EXCEEDS_SETTLED", {"limit": limit})
        if gate == "return_bridge":
            expected_restock = received.get("received_qty", 0) if inspected.get("disposition") == "RESTOCK" else 0
            ok = payload.get("restock_units") == expected_restock and payload.get("refund_cents", 0) <= authorized.get("authorized_amount_cents", 0)
            return ("PASS", None, {"expected_restock": expected_restock}) if ok else ("FAIL", "RETURN_CREDIT_MISMATCH", {})

    if process_id == "finance-close":
        if gate == "period_contract":
            ok = _required(payload, "period_start", "period_end", "currency", "policy_version") and payload["currency"] == "MXN" and payload["period_start"] <= payload["period_end"]
            return ("PASS", None, {}) if ok else ("FAIL", "FIN_PERIOD_INVALID", {})
        if gate == "cutoff":
            ok = _required(payload, "as_of_date", "coverage_status") and payload["coverage_status"] in {"COMPLETE", "PARTIAL"}
            return ("PASS", None, {}) if ok else ("FAIL", "SOURCE_NOT_OBSERVED", {})
        if gate == "control_totals":
            ok = isinstance(payload.get("source_totals"), dict) and bool(payload["source_totals"])
            return ("PASS", None, {}) if ok else ("FAIL", "FIN_CONTROL_TOTALS_MISSING", {})
        if gate == "controls_pass":
            results = payload.get("check_results")
            required = {"keys", "lifecycle", "coverage"}
            ok = isinstance(results, dict) and required <= set(results) and all(results[key] == "PASS" for key in required)
            return ("PASS", None, {"checks": sorted(results) if isinstance(results, dict) else []}) if ok else ("FAIL", "FIN_CONTROLS_FAILED", {})
        if gate == "finance_bridge":
            source = payload.get("source_components")
            mart = payload.get("mart_components")
            ok = isinstance(source, dict) and source == mart and bool(source)
            return ("PASS", None, {"components": sorted(source) if isinstance(source, dict) else []}) if ok else ("FAIL", "FIN_BRIDGE_MISMATCH", {})
        if gate == "reopen_approval":
            ok = _approval(payload, instance_id) and _required(payload, "reason")
            return ("PASS", None, {}) if ok else ("WAITING", "APPROVAL_MISSING", {})

    if process_id == "weekly-growth-review":
        bound = _first_payload(history, "data_bound") or {}
        if gate == "review_period":
            ok = _required(payload, "week_start", "week_end", "owner_role") and payload["week_start"] <= payload["week_end"]
            return ("PASS", None, {}) if ok else ("FAIL", "REVIEW_PERIOD_INVALID", {})
        if gate == "evidence_binding":
            hashes = payload.get("artifact_hashes")
            refs = payload.get("available_evidence_refs")
            ok = isinstance(hashes, dict) and bool(hashes) and all(re.fullmatch(r"[0-9a-f]{64}", value or "") for value in hashes.values()) and isinstance(refs, list) and bool(refs)
            return ("PASS", None, {}) if ok else ("FAIL", "DATA_QUALITY_BLOCK", {})
        if gate == "agent_request":
            ok = _required(payload, "request_id", "role") and payload.get("execution_mode") == "native-codex-task-bridge" and payload.get("external_execution") == "PROHIBITED"
            return ("PASS", None, {}) if ok else ("FAIL", "AGENT_REQUEST_INVALID", {})
        if gate == "evidence_response":
            available = set(bound.get("available_evidence_refs", []))
            facts = payload.get("facts")
            recs = payload.get("recommendations")
            ok = isinstance(facts, list) and len(facts) >= 2 and isinstance(recs, list) and len(recs) <= 5
            if ok:
                for item in facts + recs:
                    refs = item.get("evidence_refs") if isinstance(item, dict) else None
                    if not isinstance(refs, list) or not refs or not set(refs) <= available:
                        ok = False
                        break
                for rec in recs:
                    if rec.get("approval_required") is not True or rec.get("execution") != "PROHIBITED":
                        ok = False
                        break
            return ("PASS", None, {}) if ok else ("FAIL", "AGENT_EVIDENCE_UNRESOLVED", {})
        if gate == "proposal_limit":
            proposals = payload.get("proposals")
            ok = isinstance(proposals, list) and len(proposals) <= 5 and all(isinstance(p, dict) and p.get("approval_required") is True and p.get("execution") == "PROHIBITED" for p in proposals)
            return ("PASS", None, {"proposal_count": len(proposals) if isinstance(proposals, list) else None}) if ok else ("FAIL", "WGR_TOO_MANY_ACTIONS", {})
        if gate == "next_review":
            ok = _required(payload, "next_review_date", "packet_hash") and bool(re.fullmatch(r"[0-9a-f]{64}", payload["packet_hash"]))
            return ("PASS", None, {}) if ok else ("FAIL", "NEXT_REVIEW_MISSING", {})

    if process_id == "market-to-experiment":
        submitted = _first_payload(history, "evidence_submitted") or {}
        if gate == "research_question":
            ok = _required(payload, "question", "decision_owner")
            return ("PASS", None, {}) if ok else ("FAIL", "RESEARCH_QUESTION_INVALID", {})
        if gate == "source_plan":
            ok = isinstance(payload.get("candidate_sources"), list) and bool(payload["candidate_sources"]) and payload.get("external_execution") == "PROHIBITED"
            return ("PASS", None, {}) if ok else ("FAIL", "MARKET_SOURCE_PLAN_INVALID", {})
        if gate == "market_provenance":
            sources = payload.get("sources")
            keys = {"id", "authority", "observed_date", "scope", "license", "method", "limitation"}
            ok = isinstance(sources, list) and bool(sources) and all(isinstance(s, dict) and keys <= set(s) and all(s[k] not in (None, "") for k in keys) for s in sources)
            return ("PASS", None, {"source_count": len(sources) if isinstance(sources, list) else 0}) if ok else ("FAIL", "MARKET_PROVENANCE_MISSING", {})
        if gate == "market_freshness":
            as_of = payload.get("as_of_date")
            days = payload.get("max_age_days")
            try:
                stale = not _positive_int(days) or any((date.fromisoformat(as_of) - date.fromisoformat(s["observed_date"])).days > days for s in submitted.get("sources", []))
            except (TypeError, ValueError, KeyError):
                stale = True
            return ("FAIL", "SOURCE_STALE", {}) if stale else ("PASS", None, {})
        if gate == "experiment_contract":
            fields = ("hypothesis", "primary_metric", "guardrail", "population", "assignment", "window", "sample_criterion", "estimator", "close_rule")
            ok = _required(payload, *fields)
            return ("PASS", None, {}) if ok else ("FAIL", "EXPERIMENT_CONTRACT_INCOMPLETE", {})
        if gate == "prospective_assignment":
            try:
                assigned = datetime.fromisoformat(payload["assigned_at_utc"].replace("Z", "+00:00"))
                outcome = datetime.fromisoformat(payload["first_outcome_at_utc"].replace("Z", "+00:00")) if payload.get("first_outcome_at_utc") else None
                ok = outcome is None or assigned <= outcome
            except (KeyError, TypeError, ValueError):
                ok = False
            return ("PASS", None, {}) if ok else ("FAIL", "EXP_ASSIGNMENT_INVALID", {})
        if gate == "experiment_window":
            ok = _required(payload, "window_start", "window_end") and payload["window_start"] <= payload["window_end"] and payload.get("early_stop") is False
            return ("PASS", None, {}) if ok else ("FAIL", "EXP_WINDOW_INVALID", {})
        if gate == "experiment_evidence":
            assignment = _first_payload(history, "assignment_started")
            window = _first_payload(history, "window_ended")
            try:
                assignment_is_prospective = bool(assignment) and (
                    not assignment.get("first_outcome_at_utc")
                    or datetime.fromisoformat(assignment["assigned_at_utc"].replace("Z", "+00:00"))
                    <= datetime.fromisoformat(assignment["first_outcome_at_utc"].replace("Z", "+00:00"))
                )
            except (KeyError, TypeError, ValueError):
                assignment_is_prospective = False
            valid_window = bool(window) and window.get("early_stop") is False and window.get("window_start", "") <= window.get("window_end", "")
            ok = assignment_is_prospective and valid_window and _positive_int(payload.get("eligible_units")) and payload.get("guardrail_status") in {"PASS", "FAIL"} and payload.get("conclusion") in {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE"}
            return ("PASS", None, {"assignment_is_prospective": assignment_is_prospective, "valid_window": valid_window}) if ok else ("FAIL", "EXP_EVIDENCE_INSUFFICIENT", {})

    return "FAIL", "GATE_NOT_IMPLEMENTED", {"gate": gate}


def _receipt(
    process_id: str,
    instance_id: str,
    idempotency_key: str,
    status: str,
    state_before: str,
    state_after: str,
    recorded_at_utc: str,
    exception_code: str | None = None,
    event_hash: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = {
        "version": "2.0",
        "process_id": process_id,
        "instance_id": instance_id,
        "idempotency_key": idempotency_key,
        "status": status,
        "state_before": state_before,
        "state_after": state_after,
        "exception_code": exception_code,
        "event_hash": event_hash,
        "recorded_at_utc": recorded_at_utc,
        "synthetic": True,
        "external_execution": "PROHIBITED",
        "details": details or {},
    }
    value["receipt_id"] = _digest(value)
    return value


def _store_receipt(db: sqlite3.Connection, value: dict[str, Any]) -> None:
    db.execute(
        "INSERT OR IGNORE INTO lifecycle_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            value["receipt_id"], value["process_id"], value["instance_id"], value["idempotency_key"],
            value["status"], value["exception_code"], value["state_before"], value["state_after"],
            value["event_hash"], value["recorded_at_utc"], _canonical(value).decode().strip(),
        ),
    )


def apply_event(
    database: str | Path,
    *,
    process_id: str,
    instance_id: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
    idempotency_key: str,
    occurred_at_utc: str,
    source_refs: list[str],
    scenario_id: str = "synthetic-demo",
    run_id: str = "lifecycle-v2",
    synthetic: bool = True,
    recorded_at_utc: str | None = None,
) -> dict[str, Any]:
    """Validate and append one synthetic event, returning an immutable receipt."""
    all_definitions = definitions()
    if process_id not in all_definitions:
        raise ValueError("Unknown business process")
    if synthetic is not True:
        raise ValueError("Only explicitly synthetic lifecycle events are authorized")
    for label, value in (("instance_id", instance_id), ("event_id", event_id), ("event_type", event_type), ("idempotency_key", idempotency_key), ("scenario_id", scenario_id), ("run_id", run_id)):
        if not isinstance(value, str) or not value or len(value) > 300:
            raise ValueError(label + " must be a bounded nonempty string")
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")
    _forbid_execution(payload)
    if not isinstance(source_refs, list) or not source_refs or not all(isinstance(ref, str) and ref.startswith("synthetic://") and len(ref) <= 500 for ref in source_refs):
        raise ValueError("Synthetic source references are required")
    occurred = _utc(occurred_at_utc)
    recorded = _utc(recorded_at_utc or occurred)
    definition = all_definitions[process_id]
    request = {
        "process_id": process_id, "instance_id": instance_id, "event_id": event_id,
        "event_type": event_type, "payload": payload, "idempotency_key": idempotency_key,
        "occurred_at_utc": occurred, "source_refs": source_refs, "scenario_id": scenario_id,
        "run_id": run_id, "synthetic": True,
    }
    request_hash = _digest(request)
    initialize(database)
    db = _connect(database)
    try:
        db.execute("BEGIN IMMEDIATE")
        prior_key = db.execute(
            "SELECT * FROM lifecycle_idempotency WHERE process_id=? AND idempotency_key=?",
            (process_id, idempotency_key),
        ).fetchone()
        instance = db.execute(
            "SELECT * FROM lifecycle_instances WHERE process_id=? AND instance_id=?",
            (process_id, instance_id),
        ).fetchone()
        state = instance["current_state"] if instance else definition["initial_state"]
        if prior_key:
            if prior_key["request_hash"] == request_hash:
                value = _receipt(process_id, instance_id, idempotency_key, "NO_OP_REPLAY", state, state, recorded, details={"original_status": prior_key["result_status"]})
                _store_receipt(db, value)
                db.commit()
                return value
            after = "BLOCKED" if instance else state
            if instance:
                db.execute(
                    "UPDATE lifecycle_instances SET current_state='BLOCKED',blocked_reason='CTR_DUPLICATE_EVENT_CONFLICT',updated_at_utc=? WHERE process_id=? AND instance_id=?",
                    (recorded, process_id, instance_id),
                )
            value = _receipt(process_id, instance_id, idempotency_key, "CONFLICT", state, after, recorded, "CTR_DUPLICATE_EVENT_CONFLICT", details={"prior_request_hash": prior_key["request_hash"], "changed_request_hash": request_hash})
            _store_receipt(db, value)
            db.commit()
            return value

        last = db.execute(
            "SELECT occurred_at_utc FROM lifecycle_events WHERE process_id=? AND instance_id=? ORDER BY sequence DESC LIMIT 1",
            (process_id, instance_id),
        ).fetchone()
        if last and occurred < last["occurred_at_utc"]:
            value = _receipt(process_id, instance_id, idempotency_key, "REJECTED", state, state, recorded, "EVENT_TIME_REVERSED")
            db.execute("INSERT INTO lifecycle_idempotency VALUES (?,?,?,?,?,?,?)", (process_id, idempotency_key, instance_id, event_id, request_hash, value["status"], _canonical(value).decode().strip()))
            _store_receipt(db, value); db.commit(); return value

        transition = next((item for item in definition["transitions"] if item["event"] == event_type and state in item["from"]), None)
        if transition is None:
            value = _receipt(process_id, instance_id, idempotency_key, "REJECTED", state, state, recorded, "STATE_INVALID_TRANSITION", details={"event_type": event_type})
            db.execute("INSERT INTO lifecycle_idempotency VALUES (?,?,?,?,?,?,?)", (process_id, idempotency_key, instance_id, event_id, request_hash, value["status"], _canonical(value).decode().strip()))
            _store_receipt(db, value); db.commit(); return value

        history = _payloads(db, process_id, instance_id)
        gate_status, exception, gate_details = _gate(transition["gate"], process_id, instance_id, payload, history)
        if gate_status != "PASS":
            status = "WAITING" if gate_status == "WAITING" else "REJECTED"
            value = _receipt(process_id, instance_id, idempotency_key, status, state, state, recorded, exception, details={"gate": transition["gate"], **gate_details})
            db.execute("INSERT INTO lifecycle_idempotency VALUES (?,?,?,?,?,?,?)", (process_id, idempotency_key, instance_id, event_id, request_hash, value["status"], _canonical(value).decode().strip()))
            _store_receipt(db, value); db.commit(); return value

        if not instance:
            db.execute(
                "INSERT INTO lifecycle_instances VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (process_id, definition["contract_id"], instance_id, definition["version"], definition["owner"], scenario_id, run_id, state, None, "GENESIS", recorded, 1),
            )
        previous_row = db.execute(
            "SELECT sequence,event_hash FROM lifecycle_events WHERE process_id=? AND instance_id=? ORDER BY sequence DESC LIMIT 1",
            (process_id, instance_id),
        ).fetchone()
        sequence = (previous_row["sequence"] if previous_row else 0) + 1
        previous_hash = previous_row["event_hash"] if previous_row else "GENESIS"
        payload_hash = _digest(payload)
        event = {
            "process_id": process_id, "instance_id": instance_id, "sequence": sequence,
            "event_id": event_id, "event_type": event_type, "from_state": state,
            "to_state": transition["to"], "occurred_at_utc": occurred, "recorded_at_utc": recorded,
            "payload": payload, "payload_hash": payload_hash, "source_refs": source_refs,
            "idempotency_key": idempotency_key, "previous_hash": previous_hash, "synthetic": True,
        }
        event_hash = _digest(event)
        db.execute(
            "INSERT INTO lifecycle_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (process_id, instance_id, sequence, event_id, event_type, state, transition["to"], occurred, recorded,
             _canonical(payload).decode().strip(), payload_hash, _canonical(source_refs).decode().strip(), idempotency_key, previous_hash, event_hash, 1),
        )
        db.execute(
            "UPDATE lifecycle_instances SET current_state=?,blocked_reason=NULL,last_event_hash=?,updated_at_utc=? WHERE process_id=? AND instance_id=?",
            (transition["to"], event_hash, recorded, process_id, instance_id),
        )
        value = _receipt(process_id, instance_id, idempotency_key, "APPLIED", state, transition["to"], recorded, event_hash=event_hash, details={"gate": transition["gate"], **gate_details})
        db.execute("INSERT INTO lifecycle_idempotency VALUES (?,?,?,?,?,?,?)", (process_id, idempotency_key, instance_id, event_id, request_hash, value["status"], _canonical(value).decode().strip()))
        _store_receipt(db, value)
        db.commit()
        return value
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_hash_chains(database: str | Path) -> dict[str, Any]:
    initialize(database)
    checked = 0
    db = _connect(database)
    try:
        for instance in db.execute("SELECT process_id,instance_id,last_event_hash FROM lifecycle_instances ORDER BY process_id,instance_id"):
            previous = "GENESIS"
            rows = db.execute("SELECT * FROM lifecycle_events WHERE process_id=? AND instance_id=? ORDER BY sequence", (instance["process_id"], instance["instance_id"])).fetchall()
            for expected_sequence, row in enumerate(rows, 1):
                event = {
                    "process_id": row["process_id"], "instance_id": row["instance_id"], "sequence": row["sequence"],
                    "event_id": row["event_id"], "event_type": row["event_type"], "from_state": row["from_state"],
                    "to_state": row["to_state"], "occurred_at_utc": row["occurred_at_utc"], "recorded_at_utc": row["recorded_at_utc"],
                    "payload": json.loads(row["payload_json"]), "payload_hash": row["payload_hash"],
                    "source_refs": json.loads(row["source_refs_json"]), "idempotency_key": row["idempotency_key"],
                    "previous_hash": row["previous_hash"], "synthetic": True,
                }
                if row["sequence"] != expected_sequence or row["previous_hash"] != previous or _digest(event) != row["event_hash"] or _digest(event["payload"]) != row["payload_hash"]:
                    raise ValueError("Lifecycle event hash chain mismatch")
                previous = row["event_hash"]
                checked += 1
            if rows and instance["last_event_hash"] != previous:
                raise ValueError("Lifecycle instance checkpoint mismatch")
    finally:
        db.close()
    return {"status": "PASS", "events_checked": checked, "synthetic": True}


def export_lifecycle(database: str | Path, folder: str | Path) -> dict[str, Any]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Any] = {"definitions": list(definitions().values())}
    db = _connect(database)
    try:
        for name, table in (("instances", "lifecycle_instances"), ("events", "lifecycle_events"), ("receipts", "lifecycle_receipts")):
            rows = [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY process_id,instance_id,rowid")]
            for row in rows:
                for key in ("payload_json", "source_refs_json", "receipt_json"):
                    if key in row:
                        row[key[:-5]] = json.loads(row.pop(key))
            outputs[name] = rows
    finally:
        db.close()
    for name, value in outputs.items():
        path = folder / (name + ".json")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(_canonical(value)); temporary.replace(path)
    return {"status": "PASS", "counts": {key: len(value) for key, value in outputs.items()}, "hash_chain": verify_hash_chains(database), "synthetic": True}


def _demo_approval(instance_id: str, sequence: str) -> dict[str, Any]:
    return {"approval_id": "synthetic-approval-" + sequence, "approver_role": "synthetic_founder_fixture", "scope": instance_id, "decision": "APPROVE", "synthetic": True}


def run_lifecycle_demo(output_folder: str | Path) -> dict[str, Any]:
    """Build deterministic golden and controlled-failure lifecycle evidence."""
    output = Path(output_folder).resolve()
    output.mkdir(parents=True, exist_ok=True)
    database = output / "lifecycle.sqlite3"
    if database.exists():
        raise FileExistsError("Lifecycle demo database exists; choose a fresh output folder")
    initialize(database)
    receipts: list[dict[str, Any]] = []
    golden_receipts: list[dict[str, Any]] = []
    illegal_receipts: list[dict[str, Any]] = []
    counter = 0

    def emit(process: str, instance: str, event: str, payload: dict[str, Any], *, key: str | None = None, day: int | None = None, event_id: str | None = None) -> dict[str, Any]:
        nonlocal counter
        counter += 1
        stamp_day = day if day is not None else counter
        stamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=stamp_day - 1)
        stamp_text = stamp.isoformat().replace("+00:00", "Z")
        logical_key = key or f"{process}:{instance}:synthetic:{event}:{counter}:2.0.0"
        result = apply_event(
            database, process_id=process, instance_id=instance, event_id=event_id or f"evt-{counter:04d}",
            event_type=event, payload=payload, idempotency_key=logical_key,
            occurred_at_utc=stamp_text,
            recorded_at_utc=stamp_text,
            source_refs=[f"synthetic://lifecycle-demo/{process}/{instance}/{event}/{counter}"],
        )
        receipts.append(result)
        return result

    # Six golden analytical replays. Approvals are explicit synthetic fixtures,
    # never evidence of user authorization for a real business action.
    instance = "po-golden"
    emit("procure-to-stock", instance, "po_drafted", {"quantity": 20, "unit_cost_cents": 9000, "currency": "MXN"})
    emit("procure-to-stock", instance, "po_submitted", {"total_cents": 180000})
    emit("procure-to-stock", instance, "po_approved", {"approval": _demo_approval(instance, "po")})
    emit("procure-to-stock", instance, "goods_partially_received", {"accepted_qty": 8, "rejected_qty": 0})
    emit("procure-to-stock", instance, "goods_fully_received", {"accepted_qty": 12, "rejected_qty": 0})
    emit("procure-to-stock", instance, "po_reconciled", {"accepted_units": 20, "inventory_units": 20})

    instance = "order-golden"
    emit("lead-to-delivery", instance, "lead_captured", {"channel": "synthetic-social", "source_kind": "session"})
    emit("lead-to-delivery", instance, "lead_qualified", {"reason": "synthetic purchase intent"})
    emit("lead-to-delivery", instance, "order_placed", {"lines": [{"quantity": 2, "unit_price_cents": 25000, "discount_cents": 0, "lifecycle": "launched"}], "ordered_cents": 50000})
    emit("lead-to-delivery", instance, "order_accepted", {"policy_version": "synthetic-v2"})
    emit("lead-to-delivery", instance, "payment_settled", {"amount_cents": 50000})
    emit("lead-to-delivery", instance, "inventory_reserved", {"quantity": 2, "available_units": 10})
    emit("lead-to-delivery", instance, "fulfilment_started", {"quantity": 2})
    emit("lead-to-delivery", instance, "shipment_posted", {"quantity": 2})
    emit("lead-to-delivery", instance, "delivery_confirmed", {"quantity": 2})

    instance = "return-golden"
    emit("return-to-refund", instance, "return_requested", {"requested_qty": 1, "delivered_qty": 2})
    emit("return-to-refund", instance, "return_authorized", {"authorized_qty": 1, "authorized_amount_cents": 25000, "approval": _demo_approval(instance, "return")})
    emit("return-to-refund", instance, "return_received", {"received_qty": 1})
    emit("return-to-refund", instance, "return_inspected", {"quantity": 1, "disposition": "RESTOCK"})
    emit("return-to-refund", instance, "refund_requested", {"amount_cents": 25000, "eligible_settled_cents": 50000, "approval": _demo_approval(instance, "refund")})
    emit("return-to-refund", instance, "refund_settled", {"amount_cents": 25000, "eligible_settled_cents": 50000})
    emit("return-to-refund", instance, "case_closed", {"restock_units": 1, "refund_cents": 25000})

    instance = "close-golden"
    emit("finance-close", instance, "period_opened", {"period_start": "2025-12-01", "period_end": "2025-12-31", "currency": "MXN", "policy_version": "synthetic-v2"})
    emit("finance-close", instance, "cutoff_applied", {"as_of_date": "2025-12-31", "coverage_status": "COMPLETE"})
    emit("finance-close", instance, "controls_started", {"source_totals": {"net_revenue_cents": 50000}})
    emit("finance-close", instance, "controls_passed", {"check_results": {"keys": "PASS", "lifecycle": "PASS", "coverage": "PASS"}})
    bridge = {"net_revenue_cents": 50000, "cogs_cents": 18000, "cash_cents": 42000}
    emit("finance-close", instance, "bridges_reconciled", {"source_components": bridge, "mart_components": bridge})
    emit("finance-close", instance, "close_approved", {"approval": _demo_approval(instance, "close")})

    instance = "growth-golden"
    evidence_hash = "a" * 64
    available_refs = ["/marts/channel/0", "/marts/experiment/0"]
    emit("weekly-growth-review", instance, "review_opened", {"week_start": "2025-12-22", "week_end": "2025-12-28", "owner_role": "synthetic_growth_owner"})
    emit("weekly-growth-review", instance, "data_bound", {"artifact_hashes": {"workspace": evidence_hash}, "available_evidence_refs": available_refs})
    emit("weekly-growth-review", instance, "agent_task_emitted", {"request_id": "synthetic-request", "role": "growth_analyst", "execution_mode": "native-codex-task-bridge", "external_execution": "PROHIBITED"})
    emit("weekly-growth-review", instance, "agent_response_submitted", {"facts": [{"evidence_refs": [available_refs[0]]}, {"evidence_refs": [available_refs[1]]}], "recommendations": [{"evidence_refs": [available_refs[0]], "approval_required": True, "execution": "PROHIBITED"}]})
    proposals = [{"id": "proposal-1", "approval_required": True, "execution": "PROHIBITED"}]
    emit("weekly-growth-review", instance, "review_packet_built", {"proposals": proposals})

    instance = "experiment-golden"
    sources = [{"id": "source-1", "authority": "Synthetic public-source fixture", "observed_date": "2026-01-01", "scope": "Mexico context", "license": "link only", "method": "synthetic observation", "limitation": "does not measure Alma demand"}]
    emit("market-to-experiment", instance, "question_opened", {"question": "Which product hypothesis merits a synthetic test?", "decision_owner": "synthetic_growth_owner"})
    emit("market-to-experiment", instance, "research_started", {"candidate_sources": ["source-1"], "external_execution": "PROHIBITED"})
    emit("market-to-experiment", instance, "evidence_submitted", {"sources": sources})
    emit("market-to-experiment", instance, "evidence_accepted", {"as_of_date": "2026-01-20", "max_age_days": 60})
    design = {"hypothesis": "Synthetic treatment changes contribution per eligible visit", "primary_metric": "contribution per eligible visit", "guardrail": "return rate", "population": "synthetic eligible visits", "assignment": "random 1:1", "window": "28 days", "sample_criterion": "predeclared synthetic threshold", "estimator": "difference in means", "close_rule": "close at window; insufficient sample is inconclusive"}
    emit("market-to-experiment", instance, "experiment_designed", design)
    emit("market-to-experiment", instance, "experiment_approved", {"approval": _demo_approval(instance, "experiment")})
    emit("market-to-experiment", instance, "assignment_started", {"assigned_at_utc": "2026-01-21T00:00:00Z", "first_outcome_at_utc": "2026-01-22T00:00:00Z"})
    emit("market-to-experiment", instance, "window_ended", {"window_start": "2026-01-21", "window_end": "2026-02-18", "early_stop": False}, day=60)
    emit("market-to-experiment", instance, "analysis_completed", {"eligible_units": 100, "guardrail_status": "PASS", "conclusion": "INCONCLUSIVE"}, day=61)

    golden_receipts.extend(receipts)

    # One illegal transition for each definition.
    illegal_event = {
        "procure-to-stock": "goods_fully_received", "lead-to-delivery": "delivery_confirmed",
        "return-to-refund": "refund_settled", "finance-close": "close_approved",
        "weekly-growth-review": "review_packet_built", "market-to-experiment": "analysis_completed",
    }
    for process, event in illegal_event.items():
        illegal_receipts.append(emit(process, "illegal-" + process, event, {"quantity": 1}))

    exported = export_lifecycle(database, output / "exports")
    db = _connect(database)
    try:
        actual_states = {(row["process_id"], row["instance_id"]): row["current_state"] for row in db.execute("SELECT process_id,instance_id,current_state FROM lifecycle_instances")}
    finally:
        db.close()
    expected_states = {
        ("procure-to-stock", "po-golden"): "CLOSED",
        ("lead-to-delivery", "order-golden"): "DELIVERED",
        ("return-to-refund", "return-golden"): "CLOSED",
        ("finance-close", "close-golden"): "CLOSED",
        ("weekly-growth-review", "growth-golden"): "REVIEW_READY",
        ("market-to-experiment", "experiment-golden"): "CLOSED",
    }
    checks = {
        "golden_events_applied": all(item["status"] == "APPLIED" for item in golden_receipts),
        "golden_terminal_states": all(actual_states.get(key) == value for key, value in expected_states.items()),
        "illegal_transitions_rejected": len(illegal_receipts) == 6 and all(item["status"] == "REJECTED" and item["exception_code"] == "STATE_INVALID_TRANSITION" for item in illegal_receipts),
        "hash_chain": exported["hash_chain"]["status"] == "PASS",
    }
    summary = {
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "database": "lifecycle.sqlite3",
        "golden_instances": 6,
        "controlled_illegal_transitions": 6,
        "receipt_status_counts": {status: sum(r["status"] == status for r in receipts) for status in sorted({r["status"] for r in receipts})},
        "checks": checks,
        "golden_terminal_states": {process + "/" + instance: actual_states.get((process, instance)) for process, instance in expected_states},
        "exports": exported,
        "synthetic": True,
        "external_execution": "PROHIBITED",
        "limitation": "Analytical replay of explicit synthetic events; it does not reconstruct unobserved real business events.",
    }
    path = output / "summary.json"
    path.write_bytes(_canonical(summary))
    return summary
