"""Versioned, local SQLite warehouse for the synthetic Alma de Lujo v2 contract.

The module deliberately has no dynamic SQL entry point.  Source data is loaded
only through the typed contract below and consumers may query only named marts.
Amounts are MXN integer cents; dates are ISO-8601 calendar dates.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "2.0"

# Insertion order is part of the interchange contract.  Keep the original core
# projection byte-for-byte compatible with alma.validation.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "products": ("id", "name", "category", "collection", "lifecycle"),
    "variants": ("id", "product_id", "size", "color", "price_cents", "cost_cents"),
    "suppliers": ("id", "name"),
    "purchase_orders": ("id", "supplier_id", "variant_id", "ordered_qty", "received_qty", "unit_cost_cents", "status", "date", "paid_cents"),
    "customers": ("id", "acquired_date"),
    "orders": ("id", "customer_id", "channel", "campaign_id", "date", "delivered_date", "status"),
    "order_items": ("id", "order_id", "variant_id", "quantity", "unit_price_cents", "discount_cents", "unit_cost_cents"),
    "payments": ("id", "order_id", "date", "amount_cents", "status"),
    "refunds": ("id", "order_id", "date", "amount_cents", "status"),
    "credit_notes": ("id", "order_item_id", "date", "amount_cents", "reason"),
    "returns": ("id", "order_item_id", "date", "quantity", "restock"),
    "movements": ("id", "variant_id", "date", "kind", "quantity", "reference_id"),
    "reservations": ("id", "order_item_id", "quantity", "status"),
    "expenses": ("id", "date", "category", "amount_cents", "paid_cents", "variable"),
    "funnel": ("id", "date", "channel", "campaign_id", "visits", "leads", "spend_cents"),
    "unmet_demand": ("id", "date", "variant_id", "quantity", "reason"),
    "campaigns": ("id", "name", "channel", "objective", "start_date", "end_date"),
    "content_assets": ("id", "campaign_id", "format", "theme", "published_date", "variant_id"),
    "sessions": ("id", "customer_id", "channel", "campaign_id", "date", "content_asset_id"),
    "leads": ("id", "customer_id", "session_id", "channel", "campaign_id", "date", "intent", "status", "order_id", "variant_id"),
    "purchase_receipts": ("id", "purchase_order_id", "date", "quantity"),
    "supplier_payments": ("id", "purchase_order_id", "date", "amount_cents"),
    "shipments": ("id", "order_id", "date", "status", "delivered_date"),
    "invoices": ("id", "order_id", "date", "amount_cents", "status", "kind"),
    "expense_payments": ("id", "expense_id", "date", "amount_cents"),
    "inventory_counts": ("id", "variant_id", "date", "counted_qty"),
    "experiments": ("id", "name", "hypothesis", "primary_metric", "guardrail", "start_date", "end_date", "status"),
    "experiment_assignments": ("id", "experiment_id", "customer_id", "arm", "assigned_date"),
    "experiment_outcomes": ("id", "assignment_id", "date", "converted", "net_revenue_cents", "contribution_cents", "returned"),
    "lifecycle_events": ("id", "product_id", "date", "from_stage", "to_stage", "reason"),
}
# The legacy validator remains the authority for its own compatible core.  The
# current contract has 16 core relations plus 14 additions = 30 source tables.
from .validation import SCHEMA as _CORE_SCHEMA
CORE_TABLES = tuple(_CORE_SCHEMA)
INSERT_ORDER = (
    "products", "suppliers", "customers", "campaigns", "variants", "purchase_orders", "expenses", "orders",
    "content_assets", "sessions", "order_items", "payments", "refunds", "credit_notes", "returns", "movements",
    "reservations", "funnel", "unmet_demand", "leads", "purchase_receipts", "supplier_payments", "shipments",
    "invoices", "expense_payments", "inventory_counts", "experiments", "experiment_assignments", "experiment_outcomes", "lifecycle_events",
)
MARTS = (
    "sales_daily", "inventory_position", "inventory_aging", "procurement",
    "cash_daily", "finance_monthly", "channel_performance", "customer_cohorts",
    "experiment_results", "funnel_conversion", "reconciliation",
)
RELATION_GRAINS = {
    "sales_daily": "calendar event date", "inventory_position": "variant at snapshot", "inventory_aging": "variant at snapshot",
    "procurement": "purchase order", "cash_daily": "cash event date", "finance_monthly": "calendar month",
    "channel_performance": "channel and campaign", "customer_cohorts": "first-delivery month",
    "experiment_results": "experiment and arm", "funnel_conversion": "channel and campaign", "reconciliation": "named source-to-mart control",
}

NULLABLE = {
    ("variants", "cost_cents"), ("order_items", "unit_cost_cents"),
    ("orders", "delivered_date"), ("funnel", "visits"), ("funnel", "leads"),
    ("content_assets", "variant_id"), ("sessions", "customer_id"),
    ("sessions", "content_asset_id"), ("leads", "session_id"),
    ("leads", "order_id"), ("leads", "variant_id"), ("shipments", "delivered_date"),
}
INTEGER_COLUMNS = {
    "quantity", "ordered_qty", "received_qty", "price_cents", "cost_cents",
    "unit_cost_cents", "unit_price_cents", "discount_cents", "amount_cents",
    "paid_cents", "restock", "variable", "visits", "leads", "spend_cents",
    "counted_qty", "converted", "net_revenue_cents", "contribution_cents", "returned",
}
DATE_COLUMNS = {"date", "acquired_date", "delivered_date", "start_date", "end_date", "published_date", "assigned_date"}
ENUMS = {
    ("orders", "status"): {"delivered", "shipped", "paid", "pending", "cancelled"},
    ("payments", "status"): {"settled", "pending", "failed"},
    ("refunds", "status"): {"settled", "pending"},
    ("reservations", "status"): {"active", "released"},
    ("movements", "kind"): {"opening", "receipt", "sale", "return", "adjustment", "supplier_return"},
    ("leads", "status"): {"open", "converted", "lost"},
    ("shipments", "status"): {"in_transit", "delivered"},
    ("invoices", "status"): {"issued", "void"},
    ("invoices", "kind"): {"management_statement"},
    ("experiments", "status"): {"completed", "running"},
    ("experiment_assignments", "arm"): {"control", "treatment"},
    ("lifecycle_events", "from_stage"): {"idea", "sample", "launched", "clearance", "retired"},
    ("lifecycle_events", "to_stage"): {"idea", "sample", "launched", "clearance", "retired"},
}

FOREIGN_KEYS = {
    "variants": (("product_id", "products", "id"),),
    "purchase_orders": (("supplier_id", "suppliers", "id"), ("variant_id", "variants", "id")),
    "orders": (("customer_id", "customers", "id"), ("campaign_id", "campaigns", "id")),
    "order_items": (("order_id", "orders", "id"), ("variant_id", "variants", "id")),
    "payments": (("order_id", "orders", "id"),), "refunds": (("order_id", "orders", "id"),),
    "credit_notes": (("order_item_id", "order_items", "id"),),
    "returns": (("order_item_id", "order_items", "id"),),
    "movements": (("variant_id", "variants", "id"),),
    "reservations": (("order_item_id", "order_items", "id"),),
    "funnel": (("campaign_id", "campaigns", "id"),),
    "unmet_demand": (("variant_id", "variants", "id"),),
    "content_assets": (("campaign_id", "campaigns", "id"), ("variant_id", "variants", "id")),
    "sessions": (("customer_id", "customers", "id"), ("campaign_id", "campaigns", "id"), ("content_asset_id", "content_assets", "id")),
    "leads": (("customer_id", "customers", "id"), ("session_id", "sessions", "id"), ("campaign_id", "campaigns", "id"), ("order_id", "orders", "id"), ("variant_id", "variants", "id")),
    "purchase_receipts": (("purchase_order_id", "purchase_orders", "id"),),
    "supplier_payments": (("purchase_order_id", "purchase_orders", "id"),),
    "shipments": (("order_id", "orders", "id"),), "invoices": (("order_id", "orders", "id"),),
    "expense_payments": (("expense_id", "expenses", "id"),),
    "inventory_counts": (("variant_id", "variants", "id"),),
    "experiment_assignments": (("experiment_id", "experiments", "id"), ("customer_id", "customers", "id")),
    "experiment_outcomes": (("assignment_id", "experiment_assignments", "id"),),
    "lifecycle_events": (("product_id", "products", "id"),),
}


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _quoted(name: str) -> str:
    # Names are module constants only; the guard makes accidental dynamic SQL fail closed.
    if name not in TABLE_COLUMNS and name not in MARTS and name not in {"coverage", "warehouse_manifest", "ingest_batches", "rejected_batches"}:
        raise ValueError("unrecognized warehouse relation")
    return '"' + name + '"'


def _date_check(column: str) -> str:
    return f"CHECK ({column} LIKE '____-__-__')"


def _column_sql(table: str, column: str) -> str:
    if column == "id":
        return "id TEXT PRIMARY KEY"
    nullable = (table, column) in NULLABLE
    suffix = "" if nullable else " NOT NULL"
    if column in INTEGER_COLUMNS:
        checks: list[str] = []
        if column == "quantity" and table == "movements":
            pass  # ledger sign is constrained by event type in business validation.
        elif column == "contribution_cents":
            pass  # contribution can be negative.
        elif column in {"counted_qty"}:
            checks.append(f"CHECK ({column} >= 0)")
        else:
            checks.append(f"CHECK ({column} >= 0)")
        if column in {"restock", "variable", "converted", "returned"}:
            checks.append(f"CHECK ({column} IN (0,1))")
        return f"{column} INTEGER{suffix}" + (" " + " ".join(checks) if checks else "")
    checks = []
    if column in DATE_COLUMNS:
        checks.append(_date_check(column))
    if (table, column) in ENUMS:
        values = ",".join("'" + x + "'" for x in sorted(ENUMS[table, column]))
        checks.append(f"CHECK ({column} IN ({values}))")
    return f"{column} TEXT{suffix}" + (" " + " ".join(checks) if checks else "")


def _create_schema(db: sqlite3.Connection) -> None:
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = DELETE")
    schema_path = Path(__file__).resolve().parents[1] / "models" / "schema.sql"
    db.executescript(schema_path.read_text(encoding="utf-8"))


def _validate_shape(data: Any) -> None:
    if not isinstance(data, dict) or set(data) != {"metadata", "tables"}:
        raise ValueError("warehouse input must contain metadata and tables only")
    meta, tables = data["metadata"], data["tables"]
    if not isinstance(meta, dict) or meta.get("synthetic") is not True:
        raise ValueError("only explicitly synthetic snapshots are accepted")
    if meta.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("warehouse requires contract_version 2.0")
    if meta.get("currency") != "MXN" or type(meta.get("seed")) is not int:
        raise ValueError("metadata requires MXN currency and integer seed")
    for key in ("start_date", "as_of"):
        try:
            date.fromisoformat(meta[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"metadata.{key} must be an ISO date") from exc
    if meta["start_date"] > meta["as_of"]:
        raise ValueError("start_date is after as_of")
    if not isinstance(tables, dict) or set(tables) != set(TABLE_COLUMNS):
        raise ValueError("tables must exactly match the v2 contract")
    coverage = meta.get("coverage")
    if not isinstance(coverage, dict) or set(coverage) != set(TABLE_COLUMNS) or any(type(v) is not bool for v in coverage.values()):
        raise ValueError("coverage must explicitly contain a boolean for every v2 table")
    for table, columns in TABLE_COLUMNS.items():
        rows = tables[table]
        if not isinstance(rows, list):
            raise ValueError(f"{table}: expected list")
        for row in rows:
            if not isinstance(row, dict) or tuple(row) != columns:
                raise ValueError(f"{table}: columns must exactly match contract order")
            for column, value in row.items():
                if value is None and (table, column) in NULLABLE:
                    continue
                if column in INTEGER_COLUMNS:
                    if type(value) is not int:
                        raise ValueError(f"{table}.{column}: integer required")
                    if column != "contribution_cents" and not (table == "movements" and column == "quantity") and value < 0:
                        raise ValueError(f"{table}.{column}: negative value")
                elif not isinstance(value, str) or not value or len(value) > 500:
                    raise ValueError(f"{table}.{column}: nonempty text <=500 required")
                if column in DATE_COLUMNS:
                    try:
                        date.fromisoformat(value)
                    except ValueError as exc:
                        raise ValueError(f"{table}.{column}: invalid date") from exc
                    if value > meta["as_of"]:
                        raise ValueError(f"{table}.{column}: after snapshot")
                allowed = ENUMS.get((table, column))
                if allowed and value not in allowed:
                    raise ValueError(f"{table}.{column}: invalid enum")


def _core_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Adapt a v2 snapshot to the immutable v1 validator contract."""
    meta = data["metadata"]
    return {"metadata": {key: meta[key] for key in ("synthetic", "seed", "as_of", "scenario", "currency")}
            | {"coverage": {table: meta["coverage"][table] for table in CORE_TABLES}},
            "tables": {table: data["tables"][table] for table in CORE_TABLES}}


def _business_checks(data: dict[str, Any]) -> None:
    """Cross-table v2 checks that cannot be expressed as a SQLite row CHECK."""
    t = data["tables"]
    # Preserve v1 core reconciliation without changing its 17-table API.
    from .validation import validate
    core_failures = [r["id"] for r in validate(_core_projection(data)) if r["status"] == "FAIL"]
    if core_failures:
        raise ValueError("core validation failed: " + ", ".join(core_failures))
    po = {r["id"]: r for r in t["purchase_orders"]}
    expenses = {r["id"]: r for r in t["expenses"]}
    receipts = defaultdict(int)
    for r in t["purchase_receipts"]:
        receipts[r["purchase_order_id"]] += r["quantity"]
        if r["date"] < po[r["purchase_order_id"]]["date"]:
            raise ValueError("purchase receipt precedes purchase order")
    if any(receipts[key] != row["received_qty"] for key, row in po.items()):
        raise ValueError("purchase_receipts must reconcile exactly to received_qty")
    supplier_paid = defaultdict(int)
    for r in t["supplier_payments"]:
        supplier_paid[r["purchase_order_id"]] += r["amount_cents"]
        if r["date"] < po[r["purchase_order_id"]]["date"]:
            raise ValueError("supplier payment precedes purchase order")
    if any(supplier_paid[key] != row["paid_cents"] for key, row in po.items()):
        raise ValueError("supplier_payments must reconcile exactly to paid_cents")
    expense_paid = defaultdict(int)
    for r in t["expense_payments"]:
        expense_paid[r["expense_id"]] += r["amount_cents"]
        if r["date"] < expenses[r["expense_id"]]["date"]:
            raise ValueError("expense payment precedes expense")
    if any(expense_paid[key] != row["paid_cents"] for key, row in expenses.items()):
        raise ValueError("expense_payments must reconcile exactly to paid_cents")
    orders = {r["id"]: r for r in t["orders"]}
    items = {r["id"]: r for r in t["order_items"]}
    returns = {r["id"]: r for r in t["returns"]}
    returned = defaultdict(int)
    for r in returns.values():
        returned[r["order_item_id"]] += r["quantity"]
        order = orders[items[r["order_item_id"]]["order_id"]]
        if order["status"] != "delivered" or r["date"] < order["delivered_date"]:
            raise ValueError("returns require delivered order and event date after delivery")
    if any(returned[key] > row["quantity"] for key, row in items.items()):
        raise ValueError("return quantity exceeds sold line quantity")
    returned_moves = defaultdict(int)
    for r in t["movements"]:
        if r["kind"] == "return":
            if r["reference_id"] not in returns or not returns[r["reference_id"]]["restock"] or r["quantity"] <= 0:
                raise ValueError("only restocked returns may generate positive return movements")
            returned_moves[r["reference_id"]] += r["quantity"]
            if r["date"] != returns[r["reference_id"]]["date"]:
                raise ValueError("return movement must use the return event date")
    if any(returned_moves[key] != (row["quantity"] if row["restock"] else 0) for key, row in returns.items()):
        raise ValueError("return movement must exactly reconcile restocked returns")
    campaigns = {r["id"]: r for r in t["campaigns"]}
    for table, field in (("orders", "date"), ("funnel", "date"), ("sessions", "date"), ("leads", "date")):
        for r in t[table]:
            campaign = campaigns[r["campaign_id"]]
            if not campaign["start_date"] <= r[field] <= campaign["end_date"]:
                raise ValueError(f"{table} event is outside its campaign window")
    customers = {r["id"]: r for r in t["customers"]}
    for table, customer_field, event_field in (("orders", "customer_id", "date"), ("sessions", "customer_id", "date"), ("leads", "customer_id", "date"), ("experiment_assignments", "customer_id", "assigned_date")):
        for r in t[table]:
            customer = r[customer_field]
            if customer is not None and r[event_field] < customers[customer]["acquired_date"]:
                raise ValueError(f"{table} event precedes customer acquisition")
    sessions = {r["id"]: r for r in t["sessions"]}
    for lead in t["leads"]:
        session_id = lead["session_id"]
        if session_id is not None:
            session = sessions[session_id]
            if any(lead[field] != session[field] for field in ("channel", "campaign_id")) or lead["date"] < session["date"]:
                raise ValueError("linked lead must retain session channel, campaign, and chronology")
            if lead["customer_id"] is not None and session["customer_id"] is not None and lead["customer_id"] != session["customer_id"]:
                raise ValueError("linked lead customer conflicts with session")
        if lead["order_id"] is not None:
            order = orders[lead["order_id"]]
            if any(lead[field] != order[field] for field in ("channel", "campaign_id", "customer_id")) or order["date"] < lead["date"]:
                raise ValueError("linked lead order must retain customer/channel/campaign and follow lead")
    shipments_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for shipment in t["shipments"]:
        shipments_by_order[shipment["order_id"]].append(shipment)
        order = orders[shipment["order_id"]]
        if shipment["date"] < order["date"]:
            raise ValueError("shipment precedes order")
        if shipment["status"] == "delivered":
            if shipment["delivered_date"] != order["delivered_date"] or shipment["delivered_date"] < shipment["date"]:
                raise ValueError("delivered shipment must match order delivery date")
        elif shipment["delivered_date"] is not None:
            raise ValueError("in-transit shipment cannot have delivered date")
        settled = sum(p["amount_cents"] for p in t["payments"] if p["order_id"] == order["id"] and p["status"] == "settled" and p["date"] <= shipment["date"])
        expected = sum(i["quantity"] * i["unit_price_cents"] - i["discount_cents"] for i in t["order_items"] if i["order_id"] == order["id"])
        if settled != expected:
            raise ValueError("shipment requires settled full prepayment")
    if data["metadata"]["coverage"]["shipments"]:
        for order in orders.values():
            if order["status"] in {"shipped", "delivered"} and not shipments_by_order[order["id"]]:
                raise ValueError("covered shipped/delivered order is missing shipment event")
    experiments = {r["id"]: r for r in t["experiments"]}
    assignments = {r["id"]: r for r in t["experiment_assignments"]}
    for assignment in assignments.values():
        experiment = experiments[assignment["experiment_id"]]
        if not experiment["start_date"] <= assignment["assigned_date"] <= experiment["end_date"]:
            raise ValueError("experiment assignment is outside experiment window")
    outcomes = Counter(r["assignment_id"] for r in t["experiment_outcomes"])
    if data["metadata"]["coverage"]["experiment_outcomes"] and (any(count != 1 for count in outcomes.values()) or len(outcomes) != len(assignments)):
        raise ValueError("covered experiment outcomes require exactly one outcome per assignment")
    for outcome in t["experiment_outcomes"]:
        assignment = assignments[outcome["assignment_id"]]
        experiment = experiments[assignment["experiment_id"]]
        if outcome["date"] < assignment["assigned_date"] or outcome["date"] > experiment["end_date"]:
            raise ValueError("experiment outcome is outside assignment/experiment window")
    lifecycle_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in t["lifecycle_events"]:
        lifecycle_by_product[event["product_id"]].append(event)
        if event["from_stage"] == event["to_stage"]:
            raise ValueError("lifecycle event must change product stage")
    if data["metadata"]["coverage"]["lifecycle_events"]:
        for product in t["products"]:
            events = lifecycle_by_product[product["id"]]
            if events and sorted(events, key=lambda r: (r["date"], r["id"]))[-1]["to_stage"] != product["lifecycle"]:
                raise ValueError("final lifecycle event must match product lifecycle")


def _insert_snapshot(db: sqlite3.Connection, data: dict[str, Any], digest: str) -> None:
    for table in INSERT_ORDER:
        columns = TABLE_COLUMNS[table]
        marks = ",".join("?" for _ in columns)
        db.executemany(f"INSERT INTO {_quoted(table)} ({','.join(columns)}) VALUES ({marks})",
                       [tuple(row[column] for column in columns) for row in data["tables"][table]])
    db.executemany("INSERT INTO coverage(table_name,covered) VALUES (?,?)",
                   [(name, int(value)) for name, value in data["metadata"]["coverage"].items()])
    model_root = Path(__file__).resolve().parents[1] / "models"
    manifest = {
        "warehouse_contract_version": CONTRACT_VERSION, "source_content_hash": digest,
        "metadata": data["metadata"], "source_tables": list(TABLE_COLUMNS), "marts": list(MARTS),
        "model_hashes": {path.relative_to(model_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [model_root / "schema.sql", *(model_root / "marts" / f"{name}.sql" for name in MARTS)]},
    }
    db.executemany("INSERT INTO warehouse_manifest(key,value) VALUES (?,?)",
                   [(key, json.dumps(value, sort_keys=True, ensure_ascii=False)) for key, value in manifest.items()])
    db.execute("INSERT INTO ingest_batches(content_hash,ingested_at,row_count) VALUES (?,datetime('now'),?)",
               (digest, sum(len(rows) for rows in data["tables"].values())))


def _coverage(table: str) -> str:
    return f"(SELECT covered FROM coverage WHERE table_name='{table}')"


MART_SQL: dict[str, str] = {
    "sales_daily": f"""
      WITH events AS (
       SELECT o.delivered_date AS date, SUM(i.quantity*i.unit_price_cents) gross_revenue_cents,
              SUM(i.discount_cents) discount_cents, 0 credit_note_cents, 0 cogs_cents,
              CASE WHEN {_coverage('order_items')}=1 THEN 1 ELSE 0 END cost_known
       FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.status='delivered' GROUP BY 1
       UNION ALL SELECT cn.date,0,0,SUM(cn.amount_cents),0,1 FROM credit_notes cn GROUP BY 1
       UNION ALL SELECT m.date,0,0,0,
          SUM(CASE WHEN m.kind='sale' THEN i.quantity*i.unit_cost_cents WHEN m.kind='return' THEN -r.quantity*ri.unit_cost_cents END),
          MIN(CASE WHEN COALESCE(i.unit_cost_cents,ri.unit_cost_cents) IS NULL THEN 0 ELSE 1 END)
       FROM movements m LEFT JOIN order_items i ON m.kind='sale' AND m.reference_id=i.id
        LEFT JOIN returns r ON m.kind='return' AND m.reference_id=r.id
        LEFT JOIN order_items ri ON r.order_item_id=ri.id
       WHERE m.kind IN ('sale','return')
       GROUP BY 1
      ) SELECT date, SUM(gross_revenue_cents) gross_revenue_cents, SUM(discount_cents) discount_cents,
       SUM(credit_note_cents) credit_note_cents,
       SUM(gross_revenue_cents)-SUM(discount_cents)-SUM(credit_note_cents) net_revenue_cents,
       CASE WHEN MIN(cost_known)=1 AND {_coverage('order_items')}=1 AND {_coverage('movements')}=1 THEN SUM(cogs_cents) END cogs_cents,
       CASE WHEN MIN(cost_known)=1 AND {_coverage('order_items')}=1 AND {_coverage('movements')}=1 THEN SUM(gross_revenue_cents)-SUM(discount_cents)-SUM(credit_note_cents)-SUM(cogs_cents) END contribution_cents,
       CASE WHEN {_coverage('orders')}=1 AND {_coverage('order_items')}=1 AND {_coverage('credit_notes')}=1 THEN 1 ELSE 0 END revenue_coverage_known
       FROM events GROUP BY date ORDER BY date""",
    "inventory_position": f"""
       WITH ledger AS (SELECT variant_id,SUM(quantity) on_hand_qty FROM movements GROUP BY variant_id),
       reserve AS (SELECT i.variant_id,SUM(r.quantity) reserved_qty FROM reservations r JOIN order_items i ON i.id=r.order_item_id WHERE r.status='active' GROUP BY i.variant_id),
       transit AS (SELECT variant_id,SUM(ordered_qty-received_qty) in_transit_qty FROM purchase_orders WHERE status<>'cancelled' GROUP BY variant_id),
       latest_count AS (SELECT c.variant_id,c.counted_qty,c.date FROM inventory_counts c JOIN (SELECT variant_id,MAX(date) date FROM inventory_counts GROUP BY variant_id) x ON x.variant_id=c.variant_id AND x.date=c.date)
       SELECT v.id variant_id,v.product_id,COALESCE(l.on_hand_qty,0) ledger_on_hand_qty,COALESCE(r.reserved_qty,0) reserved_qty,
       COALESCE(l.on_hand_qty,0)-COALESCE(r.reserved_qty,0) available_qty,COALESCE(t.in_transit_qty,0) in_transit_qty,
       lc.date count_date,lc.counted_qty,CASE WHEN lc.counted_qty IS NULL THEN NULL ELSE lc.counted_qty-COALESCE(l.on_hand_qty,0) END count_discrepancy_qty,
       CASE WHEN {_coverage('movements')}=1 AND {_coverage('reservations')}=1 THEN 1 ELSE 0 END inventory_coverage_known
       FROM variants v LEFT JOIN ledger l ON l.variant_id=v.id LEFT JOIN reserve r ON r.variant_id=v.id LEFT JOIN transit t ON t.variant_id=v.id LEFT JOIN latest_count lc ON lc.variant_id=v.id ORDER BY v.id""",
    "inventory_aging": f"""
       WITH positive_events AS (SELECT variant_id,MAX(date) last_inbound_date FROM movements WHERE quantity>0 GROUP BY variant_id),
       sales AS (SELECT variant_id,SUM(-quantity) shipped_qty FROM movements WHERE kind='sale' GROUP BY variant_id)
       SELECT p.variant_id,p.ledger_on_hand_qty,p.available_qty,e.last_inbound_date,
       CASE WHEN e.last_inbound_date IS NULL THEN NULL ELSE CAST(julianday((SELECT json_extract(value,'$.as_of') FROM warehouse_manifest WHERE key='metadata'))-julianday(e.last_inbound_date) AS INTEGER) END days_since_last_inbound,
       COALESCE(s.shipped_qty,0) shipped_qty,p.inventory_coverage_known FROM inventory_position p LEFT JOIN positive_events e ON e.variant_id=p.variant_id LEFT JOIN sales s ON s.variant_id=p.variant_id ORDER BY p.variant_id""",
    "procurement": f"""
       SELECT po.id purchase_order_id,po.date ordered_date,po.supplier_id,po.variant_id,po.ordered_qty,po.received_qty,po.ordered_qty-po.received_qty open_qty,
       po.unit_cost_cents,po.ordered_qty*po.unit_cost_cents ordered_value_cents,po.paid_cents,COALESCE(r.receipt_qty,0) receipt_event_qty,COALESCE(p.payment_cents,0) supplier_payment_event_cents,
       CASE WHEN po.received_qty=COALESCE(r.receipt_qty,0) AND po.paid_cents=COALESCE(p.payment_cents,0) THEN 1 ELSE 0 END reconciled
       FROM purchase_orders po LEFT JOIN (SELECT purchase_order_id,SUM(quantity) receipt_qty FROM purchase_receipts GROUP BY 1) r ON r.purchase_order_id=po.id LEFT JOIN (SELECT purchase_order_id,SUM(amount_cents) payment_cents FROM supplier_payments GROUP BY 1) p ON p.purchase_order_id=po.id ORDER BY po.date,po.id""",
    "cash_daily": f"""
       WITH events AS (
        SELECT date,amount_cents cash_in_cents,0 refund_out_cents,0 supplier_out_cents,0 expense_out_cents FROM payments WHERE status='settled'
        UNION ALL SELECT date,0,amount_cents,0,0 FROM refunds WHERE status='settled'
        UNION ALL SELECT date,0,0,amount_cents,0 FROM supplier_payments
        UNION ALL SELECT date,0,0,0,amount_cents FROM expense_payments
       ) SELECT date,SUM(cash_in_cents) cash_in_cents,SUM(refund_out_cents) refund_out_cents,SUM(supplier_out_cents) supplier_out_cents,SUM(expense_out_cents) expense_out_cents,
       SUM(cash_in_cents)-SUM(refund_out_cents)-SUM(supplier_out_cents)-SUM(expense_out_cents) net_cash_change_cents,
       SUM(SUM(cash_in_cents)-SUM(refund_out_cents)-SUM(supplier_out_cents)-SUM(expense_out_cents)) OVER (ORDER BY date) cumulative_cash_movement_cents,
       CASE WHEN {_coverage('payments')}=1 AND {_coverage('refunds')}=1 AND {_coverage('supplier_payments')}=1 AND {_coverage('expense_payments')}=1 THEN 1 ELSE 0 END cash_coverage_known
       FROM events GROUP BY date ORDER BY date""",
    "finance_monthly": f"""
       WITH sales AS (SELECT substr(date,1,7) month,SUM(net_revenue_cents) net_revenue_cents,SUM(cogs_cents) cogs_cents,SUM(contribution_cents) contribution_cents,MIN(revenue_coverage_known) revenue_coverage_known FROM sales_daily GROUP BY 1),
       expense_accrual AS (SELECT substr(date,1,7) month,SUM(amount_cents) expense_accrual_cents FROM expenses GROUP BY 1), cash AS (SELECT substr(date,1,7) month,SUM(net_cash_change_cents) net_cash_change_cents FROM cash_daily GROUP BY 1)
       SELECT s.month,s.net_revenue_cents,s.cogs_cents,s.contribution_cents,e.expense_accrual_cents,
       CASE WHEN s.contribution_cents IS NULL THEN NULL ELSE s.contribution_cents-COALESCE(e.expense_accrual_cents,0) END operating_proxy_cents,c.net_cash_change_cents,s.revenue_coverage_known
       FROM sales s LEFT JOIN expense_accrual e ON e.month=s.month LEFT JOIN cash c ON c.month=s.month ORDER BY s.month""",
    "channel_performance": f"""
       SELECT o.channel,COUNT(DISTINCT o.id) delivered_orders,SUM(i.quantity*i.unit_price_cents-i.discount_cents) delivered_line_net_revenue_cents,
       COUNT(DISTINCT o.customer_id) customers,CASE WHEN {_coverage('orders')}=1 AND {_coverage('order_items')}=1 THEN 1 ELSE 0 END coverage_known
       FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.status='delivered' GROUP BY o.channel ORDER BY o.channel""",
    "customer_cohorts": f"""
       SELECT substr(c.acquired_date,1,7) cohort_month,substr(o.delivered_date,1,7) order_month,COUNT(DISTINCT c.id) customers_in_observed_orders,
       COUNT(DISTINCT o.id) delivered_orders,SUM(i.quantity*i.unit_price_cents-i.discount_cents) net_revenue_before_credits_cents,
       CASE WHEN {_coverage('customers')}=1 AND {_coverage('orders')}=1 THEN 1 ELSE 0 END coverage_known
       FROM customers c LEFT JOIN orders o ON o.customer_id=c.id AND o.status='delivered' LEFT JOIN order_items i ON i.order_id=o.id
       GROUP BY 1,2 ORDER BY 1,2""",
    "experiment_results": f"""
       SELECT e.id experiment_id,e.name,e.status,e.primary_metric,e.guardrail,e.start_date,e.end_date,a.arm,COUNT(a.id) assigned_customers,
       SUM(CASE WHEN o.converted=1 THEN 1 ELSE 0 END) converted_customers,AVG(CASE WHEN o.converted=1 THEN 1.0 ELSE 0.0 END) conversion_rate,
       SUM(o.net_revenue_cents) net_revenue_cents,SUM(o.contribution_cents) contribution_cents,SUM(o.returned) returned_customers,
       CASE WHEN e.status='completed' AND COUNT(a.id)>0 THEN 1 ELSE 0 END synthetic_descriptive_only
       FROM experiments e JOIN experiment_assignments a ON a.experiment_id=e.id LEFT JOIN experiment_outcomes o ON o.assignment_id=a.id GROUP BY e.id,a.arm ORDER BY e.id,a.arm""",
    "funnel_conversion": f"""
       WITH aggregate_funnel AS (SELECT channel,campaign_id,SUM(visits) visits,SUM(leads) leads,SUM(spend_cents) spend_cents,MIN(CASE WHEN visits IS NULL OR leads IS NULL THEN 0 ELSE 1 END) measured FROM funnel GROUP BY channel,campaign_id),
       order_counts AS (SELECT channel,campaign_id,COUNT(DISTINCT id) orders FROM orders WHERE status IN ('paid','shipped','delivered') GROUP BY channel,campaign_id)
       SELECT f.channel,f.campaign_id,f.visits,f.leads,COALESCE(o.orders,0) orders,f.spend_cents,
       CASE WHEN f.visits IS NULL OR f.visits=0 THEN NULL ELSE 1.0*f.leads/f.visits END visit_to_lead_rate,
       CASE WHEN f.leads IS NULL OR f.leads=0 THEN NULL ELSE 1.0*COALESCE(o.orders,0)/f.leads END lead_to_order_rate,
       CASE WHEN f.measured=1 AND {_coverage('funnel')}=1 THEN 1 ELSE 0 END funnel_coverage_known
       FROM aggregate_funnel f LEFT JOIN order_counts o ON o.channel=f.channel AND o.campaign_id=f.campaign_id ORDER BY f.channel,f.campaign_id""",
    "reconciliation": """
       SELECT 'sales_net_revenue' check_id,(SELECT COALESCE(SUM(quantity*unit_price_cents-discount_cents),0) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='delivered')-(SELECT COALESCE(SUM(amount_cents),0) FROM credit_notes) source_cents,(SELECT COALESCE(SUM(net_revenue_cents),0) FROM sales_daily) mart_cents
       UNION ALL SELECT 'cash_in',(SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE status='settled'),(SELECT COALESCE(SUM(cash_in_cents),0) FROM cash_daily)
       UNION ALL SELECT 'cash_out',(SELECT COALESCE(SUM(amount_cents),0) FROM refunds WHERE status='settled')+(SELECT COALESCE(SUM(amount_cents),0) FROM supplier_payments)+(SELECT COALESCE(SUM(amount_cents),0) FROM expense_payments),(SELECT COALESCE(SUM(refund_out_cents+supplier_out_cents+expense_out_cents),0) FROM cash_daily)
       UNION ALL SELECT 'purchase_receipts',(SELECT COALESCE(SUM(received_qty),0) FROM purchase_orders),(SELECT COALESCE(SUM(receipt_event_qty),0) FROM procurement)
       UNION ALL SELECT 'supplier_payments',(SELECT COALESCE(SUM(paid_cents),0) FROM purchase_orders),(SELECT COALESCE(SUM(supplier_payment_event_cents),0) FROM procurement)
    """,
}


def _materialize_marts(db: sqlite3.Connection) -> None:
    model_dir = Path(__file__).resolve().parents[1] / "models" / "marts"
    for name in MARTS:
        model_path = model_dir / f"{name}.sql"
        if not model_path.is_file():
            raise ValueError(f"missing authoritative mart SQL: {model_path}")
        query = model_path.read_text(encoding="utf-8")
        for table in TABLE_COLUMNS:
            query = query.replace("{{coverage:" + table + "}}", _coverage(table))
        db.execute(f"CREATE TABLE {_quoted(name)} AS {query}")
    # Keep an explicit boolean evidence field on all reconciliation observations.
    db.execute("ALTER TABLE reconciliation ADD COLUMN passed INTEGER")
    db.execute("UPDATE reconciliation SET passed=CASE WHEN source_cents=mart_cents THEN 1 ELSE 0 END")
    controls = [dict(row) for row in db.execute("SELECT * FROM reconciliation")]
    db.execute("INSERT INTO warehouse_manifest(key,value) VALUES ('control_results',?)", (json.dumps(controls, sort_keys=True),))


def _connect_readonly(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only = ON")
    return db


def _record_rejection(path: Path, data: Any, error: Exception) -> None:
    if not path.exists():
        return
    digest = hashlib.sha256(_canonical(data)).hexdigest()
    try:
        db = sqlite3.connect(path)
        with db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT OR REPLACE INTO rejected_batches(content_hash,rejected_at,error,payload_json) VALUES (?,datetime('now'),?,?)",
                       (digest, str(error)[:2000], _canonical(data).decode("utf-8")))
    except (sqlite3.Error, TypeError, ValueError):
        pass
    finally:
        try: db.close()
        except UnboundLocalError: pass


def build_warehouse(data: dict[str, Any], path: str | Path) -> dict[str, Any]:
    """Create or replace one warehouse atomically after all validations pass."""
    destination = Path(path)
    controls: list[dict[str, Any]] = []
    try:
        _validate_shape(data)
        _business_checks(data)
    except Exception as exc:
        _record_rejection(destination, data, exc)
        raise ValueError(str(exc)) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(_canonical(data)).hexdigest()
    fd, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        db = sqlite3.connect(temporary)
        db.row_factory = sqlite3.Row
        try:
            with db:
                _create_schema(db)
                _insert_snapshot(db, data, digest)
                _materialize_marts(db)
                controls = [dict(row) for row in db.execute("SELECT * FROM reconciliation")]
                violations = list(db.execute("PRAGMA foreign_key_check"))
                if violations:
                    raise ValueError("foreign-key check failed after load")
        finally:
            db.close()
        os.replace(temporary, destination)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        _record_rejection(destination, data, exc)
        raise ValueError(str(exc)) from exc
    return {"path": str(destination), "content_hash": digest, "table_count": len(TABLE_COLUMNS), "marts": list(MARTS), "row_count": sum(len(v) for v in data["tables"].values()), "control_results": controls}


def ingest_batch(path: str | Path, data: dict[str, Any]) -> dict[str, Any]:
    """Idempotently acknowledge an exact snapshot; reject immutable changes.

    Canonical source tables are snapshot-scoped.  A distinct batch may not alter
    an existing primary key; callers build a fresh snapshot for a changed fact.
    """
    target = Path(path)
    if not target.exists():
        return build_warehouse(data, target)
    digest = hashlib.sha256(_canonical(data)).hexdigest()
    try:
        _validate_shape(data)
        _business_checks(data)
        db = sqlite3.connect(target)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if db.execute("SELECT 1 FROM ingest_batches WHERE content_hash=?", (digest,)).fetchone():
                return {"path": str(target), "content_hash": digest, "idempotent": True, "inserted_rows": 0}
            for table, rows in data["tables"].items():
                existing = {r[0] for r in db.execute(f"SELECT id FROM {_quoted(table)}")}
                if existing.intersection(row["id"] for row in rows):
                    raise ValueError("changed snapshot contains immutable existing rows; build a new warehouse")
            raise ValueError("a distinct complete snapshot must be built in a new warehouse")
        finally:
            db.close()
    except Exception as exc:
        _record_rejection(target, data, exc)
        raise ValueError(str(exc)) from exc


def query_mart(path: str | Path, name: str) -> list[dict[str, Any]]:
    """Return a fixed materialized mart.  Arbitrary SQL is intentionally absent."""
    if name not in MARTS:
        raise ValueError("unknown mart")
    db = _connect_readonly(path)
    try:
        return [dict(row) for row in db.execute(f"SELECT * FROM {_quoted(name)}")]
    finally:
        db.close()


def export_marts(path: str | Path, folder: str | Path) -> dict[str, Any]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for name in MARTS:
        target = folder / f"{name}.json"
        target.write_bytes(_canonical(query_mart(path, name)))
        written[name] = str(target)
    return {"folder": str(folder), "marts": written}


def inspect_schema(path: str | Path) -> dict[str, Any]:
    db = _connect_readonly(path)
    try:
        relations = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables: dict[str, Any] = {}
        for name in relations:
            if name.startswith("sqlite_"):
                continue
            tables[name] = {
                "columns": [dict(row) for row in db.execute(f"PRAGMA table_info('{name}')")],
                "foreign_keys": [dict(row) for row in db.execute(f"PRAGMA foreign_key_list('{name}')")],
                "indexes": [dict(row) for row in db.execute(f"PRAGMA index_list('{name}')")],
            }
        manifest = {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key,value FROM warehouse_manifest")}
        catalog = {name: {"relation_type": "source", "grain": "one synthetic contract row", "owner": "synthetic snapshot producer"} for name in TABLE_COLUMNS}
        catalog.update({name: {"relation_type": "materialized mart", "grain": RELATION_GRAINS[name], "owner": "deterministic warehouse"} for name in MARTS})
        return {"contract_version": manifest["warehouse_contract_version"], "manifest": manifest, "tables": tables, "marts": list(MARTS), "catalog": catalog}
    finally:
        db.close()
