"""Deterministic synthetic business simulation for the v2 Alma contract.

The module creates a complete, synthetic source snapshot.  It is deliberately
stdlib-only: the rows are useful as a reproducible fixture and are not claims
about Alma de Lujo's real customers, products, or performance.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import random
from typing import Any

from .validation import SCHEMA


AS_OF = date(2026, 9, 21)
CORE_TABLES = tuple(SCHEMA)
ADDITIONAL_SCHEMA = {
    "campaigns": "id name channel objective start_date end_date",
    "content_assets": "id campaign_id format theme published_date variant_id",
    "sessions": "id customer_id channel campaign_id date content_asset_id",
    "leads": "id customer_id session_id channel campaign_id date intent status order_id variant_id",
    "purchase_receipts": "id purchase_order_id date quantity",
    "supplier_payments": "id purchase_order_id date amount_cents",
    "shipments": "id order_id date status delivered_date",
    "invoices": "id order_id date amount_cents status kind",
    "expense_payments": "id expense_id date amount_cents",
    "inventory_counts": "id variant_id date counted_qty",
    "experiments": "id name hypothesis primary_metric guardrail start_date end_date status",
    "experiment_assignments": "id experiment_id customer_id arm assigned_date",
    "experiment_outcomes": "id assignment_id date converted net_revenue_cents contribution_cents returned",
    "lifecycle_events": "id product_id date from_stage to_stage reason",
}
ALL_TABLES = CORE_TABLES + tuple(ADDITIONAL_SCHEMA)

SCENARIO_MECHANISMS = {
    "normal": "Balanced synthetic baseline with seasonal demand and repeat customers.",
    "stock_pressure": "Lower safety stock, more unmet demand, and physical-count discrepancies create a low-cover stress case.",
    "promotion_illusion": "Synthetic discounts increase order volume while reducing contribution per order.",
    "cash_squeeze": "Suppliers are paid before receipt and for open quantities, creating a cash timing stress case.",
    "missing_cost": "A subset of standard costs is intentionally unavailable; margin and inventory value remain unknown.",
    "broken_link": "One synthetic foreign-key reference is intentionally broken so ingestion must reject the snapshot.",
}
VALID_SCENARIOS = frozenset(SCENARIO_MECHANISMS)


def _columns(schema: dict[str, str]) -> dict[str, tuple[str, ...]]:
    return {name: tuple(value.split()) for name, value in schema.items()}


TABLE_COLUMNS = {**_columns(SCHEMA), **_columns(ADDITIONAL_SCHEMA)}


def _row(table: str, **values: Any) -> dict[str, Any]:
    """Create a row in normative insertion order."""
    return {column: values[column] for column in TABLE_COLUMNS[table]}


def _iso(day: date) -> str:
    return day.isoformat()


def _month_starts(first: date, last: date) -> list[date]:
    result: list[date] = []
    cursor = first.replace(day=1)
    while cursor <= last:
        result.append(max(first, cursor))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return result


def _bounded(day: date, first: date, last: date) -> date:
    return max(first, min(last, day))


def _weighted_variant(rng: random.Random, variants: list[dict[str, Any]], sock_bias: float) -> dict[str, Any]:
    socks = [v for v in variants if v["product_id"] == "prod-socks"]
    apparel = [v for v in variants if v["product_id"] != "prod-socks" and v["product_id"] != "prod-wrap"]
    pool = socks if rng.random() < sock_bias else apparel
    return rng.choice(pool)


def _make_catalog(scenario: str, rng: random.Random) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    products = [
        _row("products", id="prod-socks", name="Grip Pilates Socks", category="Pilates socks", collection="Studio Essentials", lifecycle="launched"),
        _row("products", id="prod-leggings", name="Flow Leggings", category="Sportswear", collection="Flow", lifecycle="launched"),
        _row("products", id="prod-tops", name="Sculpt Studio Top", category="Sportswear", collection="Studio Essentials", lifecycle="launched"),
        _row("products", id="prod-shorts", name="Move Biker Shorts", category="Sportswear", collection="Move", lifecycle="clearance"),
        _row("products", id="prod-wrap", name="Recovery Wrap Concept", category="Sportswear", collection="Future Concepts", lifecycle="sample"),
    ]
    specs = [
        ("prod-socks", "sock", ["Black", "Ivory", "Rose", "Sage", "Lilac", "Coral"], ["S", "M", "L"], 11900, 4200),
        ("prod-leggings", "legging", ["Black", "Navy", "Olive"], ["S", "M", "L"], 29900, 11200),
        ("prod-tops", "top", ["Black", "Sand", "Rose"], ["S", "M", "L"], 21900, 8200),
        ("prod-shorts", "short", ["Black", "Coral", "Navy"], ["S", "M", "L"], 18900, 7100),
        ("prod-wrap", "wrap", ["Sand"], ["O/S"], 25900, 9800),
    ]
    variants: list[dict[str, Any]] = []
    for product_id, prefix, colors, sizes, price, cost in specs:
        for color in colors:
            for size in sizes:
                variants.append(_row("variants", id=f"var-{prefix}-{color.lower()}-{size.lower().replace('/', '-')}", product_id=product_id, size=size, color=color, price_cents=price, cost_cents=cost))
    if scenario == "missing_cost":
        # Include both a sock and an apparel cost gap, and make sure sold lines
        # use the gap below rather than silently replacing it with zero.
        chosen = {v["id"] for v in variants if v["product_id"] in {"prod-socks", "prod-leggings", "prod-tops"} and int(v["id"].split("-")[-1] in {"s", "m"})}
        # The deterministic slice keeps the gap stable while covering enough
        # rows to make unknown margin visible in downstream calculations.
        chosen.update(v["id"] for i, v in enumerate(variants) if i % 11 == 0)
        for variant in variants:
            if variant["id"] in chosen:
                variant["cost_cents"] = None
    return products, variants


def generate(seed: int = 42, scenario: str = "normal", days: int = 365, order_count: int = 1200) -> dict[str, Any]:
    """Return a deterministic 30-table synthetic snapshot.

    ``days`` counts the inclusive snapshot window ending at the fixed
    ``as_of`` date.  ``order_count`` controls order rows exactly; all other
    event tables derive from those rows.
    """
    if type(seed) is not int:
        raise TypeError("seed must be an integer")
    if scenario not in VALID_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    if type(days) is not int or days < 1:
        raise ValueError("days must be a positive integer")
    if type(order_count) is not int or order_count < 1:
        raise ValueError("order_count must be a positive integer")

    rng = random.Random(seed)
    first = AS_OF - timedelta(days=days - 1)
    products, variants = _make_catalog(scenario, rng)
    variant_by_id = {v["id"]: v for v in variants}
    sellable = [v for v in variants if v["product_id"] != "prod-wrap"]

    tables: dict[str, list[dict[str, Any]]] = {name: [] for name in ALL_TABLES}
    tables["products"] = products
    tables["variants"] = variants
    lifecycle_paths = {
        "prod-socks": [("idea", "sample"), ("sample", "launched")],
        "prod-leggings": [("idea", "sample"), ("sample", "launched")],
        "prod-tops": [("idea", "sample"), ("sample", "launched")],
        "prod-shorts": [("idea", "sample"), ("sample", "clearance")],
        "prod-wrap": [("idea", "sample")],
    }
    for product_index, product in enumerate(products):
        for event_index, (from_stage, to_stage) in enumerate(lifecycle_paths[product["id"]]):
            event_day = _bounded(first + timedelta(days=min(days - 1, 4 + product_index * 3 + event_index * 24)), first, AS_OF)
            tables["lifecycle_events"].append(_row("lifecycle_events", id=f"lifecycle-{product_index+1:02d}-{event_index+1:02d}", product_id=product["id"], date=_iso(event_day), from_stage=from_stage, to_stage=to_stage, reason="synthetic catalog lifecycle example"))
    tables["suppliers"] = [
        _row("suppliers", id="sup-studio", name="Synthetic Studio Textiles"),
        _row("suppliers", id="sup-grip", name="Synthetic Grip Goods"),
        _row("suppliers", id="sup-move", name="Synthetic Move Manufacturing"),
    ]

    # Campaigns and assets are declared before any event that references them.
    campaign_specs = [
        ("camp-studio", "Studio Stories", "Instagram", "synthetic sock discovery"),
        ("camp-move", "Move Sessions", "Paid Social", "synthetic sportswear consideration"),
        ("camp-private", "Private Community", "DM", "synthetic repeat-customer nurture"),
        ("organic", "Organic Discovery", "Organic", "synthetic non-paid discovery"),
    ]
    campaign_by_id: dict[str, dict[str, Any]] = {}
    for index, (cid, name, channel, objective) in enumerate(campaign_specs):
        # Every campaign spans the snapshot so an early synthetic order or
        # anonymous session cannot fall outside its declared campaign window.
        c_start = first
        campaign = _row("campaigns", id=cid, name=name, channel=channel, objective=objective, start_date=_iso(c_start), end_date=_iso(AS_OF))
        tables["campaigns"].append(campaign)
        campaign_by_id[cid] = campaign
        asset_variant = next((v["id"] for v in variants if v["product_id"] == "prod-socks"), None) if cid in {"camp-studio", "organic"} else None
        tables["content_assets"].append(_row("content_assets", id=f"asset-{index+1:02d}", campaign_id=cid, format="reel" if index % 2 == 0 else "photo", theme="synthetic studio movement", published_date=_iso(c_start), variant_id=asset_variant))
    asset_by_campaign = {row["campaign_id"]: row["id"] for row in tables["content_assets"]}

    # Repeated synthetic customers.  Acquisition is always before their order.
    customer_count = max(8, min(480, max(8, order_count // 3)))
    customers: list[dict[str, Any]] = []
    for index in range(customer_count):
        # Reserve a mature seed cohort so the default snapshot always covers
        # every v1 order status, including delivered and cancelled examples.
        acquired = first if index < 5 else first + timedelta(days=rng.randrange(max(1, days)))
        customers.append(_row("customers", id=f"cust-{index+1:04d}", acquired_date=_iso(acquired)))
    tables["customers"] = customers
    customer_by_id = {row["id"]: row for row in customers}

    sock_bias = {"normal": 0.58, "stock_pressure": 0.62, "promotion_illusion": 0.54, "cash_squeeze": 0.56, "missing_cost": 0.58, "broken_link": 0.58}[scenario]
    order_rows: list[dict[str, Any]] = []
    order_items: list[dict[str, Any]] = []
    order_item_variants: dict[str, dict[str, Any]] = {}
    order_total: dict[str, int] = {}
    order_sale_day: dict[str, date] = {}
    order_delivery: dict[str, date | None] = {}
    customer_orders: defaultdict[str, int] = defaultdict(int)

    for index in range(order_count):
        # Earlier orders establish customers; later rows intentionally repeat.
        customer = customers[index] if index < customer_count else customers[rng.randrange(customer_count)]
        acquired = date.fromisoformat(customer["acquired_date"])
        target = first + timedelta(days=rng.randrange(max(1, days)))
        order_day = _bounded(max(acquired, target), first, AS_OF)
        if index < 5 and days >= 7:
            order_day = first + timedelta(days=index)
        age = (AS_OF - order_day).days
        channel = rng.choices(["Instagram", "Paid Social", "DM", "Organic"], weights=[36, 22, 17, 25], k=1)[0]
        campaign_id = {"Instagram": "camp-studio", "Paid Social": "camp-move", "DM": "camp-private", "Organic": "organic"}[channel]
        # A seasonal pulse is encoded in order intensity (the row date is the
        # evidence, while the interpretation remains explicitly synthetic).
        if age < 4:
            status = rng.choice(["paid", "pending", "shipped"])
        else:
            status = rng.choices(["delivered", "shipped", "paid", "pending", "cancelled"], weights=[64, 13, 9, 9, 5], k=1)[0]
        # Guarantee coverage of all v1 order statuses for the default shape.
        if index < 5 and age >= 6:
            status = ["delivered", "shipped", "paid", "pending", "cancelled"][index]
        if status == "delivered":
            delivery = _bounded(order_day + timedelta(days=2 + rng.randrange(4)), first, AS_OF)
            if delivery <= order_day:
                status = "shipped"
                delivery = None
        else:
            delivery = None
        order_id = f"ord-{index+1:05d}"
        order_rows.append(_row("orders", id=order_id, customer_id=customer["id"], channel=channel, campaign_id=campaign_id, date=_iso(order_day), delivered_date=_iso(delivery) if delivery else None, status=status))
        order_delivery[order_id] = delivery
        item_count = 1 if order_count < 20 else (2 if rng.random() < (0.58 if scenario == "promotion_illusion" else 0.42) else 1)
        if index % 17 == 0 and len(sellable) >= 3:
            item_count = 3
        selected: set[str] = set()
        for line_index in range(item_count):
            candidate = _weighted_variant(rng, sellable, sock_bias)
            while candidate["id"] in selected:
                candidate = rng.choice(sellable)
            selected.add(candidate["id"])
            quantity = 1 + rng.randrange(4 if scenario == "promotion_illusion" else 3)
            gross = quantity * candidate["price_cents"]
            if scenario == "promotion_illusion":
                discount_ratio = 0.22 + rng.random() * 0.18
            else:
                discount_ratio = 0.02 + rng.random() * 0.07
            discount = min(gross - 1, int(gross * discount_ratio)) if gross > 1 else 0
            item_id = f"item-{len(order_items)+1:06d}"
            item = _row("order_items", id=item_id, order_id=order_id, variant_id=candidate["id"], quantity=quantity, unit_price_cents=candidate["price_cents"], discount_cents=discount, unit_cost_cents=candidate["cost_cents"])
            order_items.append(item)
            order_item_variants[item_id] = candidate
            order_total[order_id] = order_total.get(order_id, 0) + gross - discount
        customer_orders[customer["id"]] += 1
    tables["orders"] = order_rows
    tables["order_items"] = order_items

    # Sale date is after payment and before delivery.  Non-shipped states have
    # no sale movement, but still carry a reservation when paid/pending.
    payments: list[dict[str, Any]] = []
    refunds: list[dict[str, Any]] = []
    returns: list[dict[str, Any]] = []
    credits: list[dict[str, Any]] = []
    reservations: list[dict[str, Any]] = []
    paid_by_order: defaultdict[str, int] = defaultdict(int)
    for index, order in enumerate(order_rows):
        oid = order["id"]
        total = order_total[oid]
        order_day = date.fromisoformat(order["date"])
        if order["status"] in {"delivered", "shipped", "paid"}:
            first_amount = total if index % 3 else max(1, total // 2)
            second_amount = total - first_amount
            payments.append(_row("payments", id=f"pay-{len(payments)+1:06d}", order_id=oid, date=_iso(order_day), amount_cents=first_amount, status="settled"))
            if second_amount:
                pday = _bounded(order_day + timedelta(days=1), first, AS_OF)
                payments.append(_row("payments", id=f"pay-{len(payments)+1:06d}", order_id=oid, date=_iso(pday), amount_cents=second_amount, status="settled"))
            sale_day = _bounded(order_day + timedelta(days=1 if second_amount else 0), first, AS_OF)
            order_sale_day[oid] = sale_day
        elif order["status"] == "pending":
            partial = total // 3
            payments.append(_row("payments", id=f"pay-{len(payments)+1:06d}", order_id=oid, date=_iso(order_day), amount_cents=partial, status="pending"))
        # Reservations are explicit for all lines, released after shipment.
        for item in [row for row in order_items if row["order_id"] == oid]:
            reservation_status = "active" if order["status"] in {"paid", "pending"} else "released"
            reservations.append(_row("reservations", id=f"reservation-{len(reservations)+1:06d}", order_item_id=item["id"], quantity=item["quantity"], status=reservation_status))
    tables["payments"] = payments

    # Returns are only attached to mature delivered orders; both physical
    # restock and write-off paths are represented in every default snapshot.
    mature_lines = [item for item in order_items if next(row for row in order_rows if row["id"] == item["order_id"])["status"] == "delivered" and order_delivery[item["order_id"]] and (AS_OF - order_delivery[item["order_id"]]).days >= 5]
    for index, item in enumerate(mature_lines):
        if index % 19 != 0:
            continue
        delivery = order_delivery[item["order_id"]]
        assert delivery is not None
        return_day = _bounded(delivery + timedelta(days=3 + index % 5), first, AS_OF)
        qty = max(1, item["quantity"] // 2)
        restock = 1 if index % 2 == 0 else 0
        return_id = f"return-{len(returns)+1:05d}"
        returns.append(_row("returns", id=return_id, order_item_id=item["id"], date=_iso(return_day), quantity=qty, restock=restock))
        line_value = item["unit_price_cents"] * qty - min(item["discount_cents"], item["unit_price_cents"] * qty)
        credits.append(_row("credit_notes", id=f"credit-{len(credits)+1:05d}", order_item_id=item["id"], date=_iso(return_day), amount_cents=max(1, line_value), reason="synthetic return adjustment"))
        refunds.append(_row("refunds", id=f"refund-{len(refunds)+1:05d}", order_id=item["order_id"], date=_iso(return_day), amount_cents=max(1, min(order_total[item["order_id"]], line_value)), status="settled"))
    # Small shapes still need both return treatments for contract examples.
    if len(mature_lines) >= 2 and len({r["restock"] for r in returns}) < 2:
        item = mature_lines[-1]
        delivery = order_delivery[item["order_id"]]
        assert delivery is not None
        day = _bounded(delivery + timedelta(days=2), first, AS_OF)
        rid = f"return-{len(returns)+1:05d}"
        returns.append(_row("returns", id=rid, order_item_id=item["id"], date=_iso(day), quantity=1, restock=0))
    tables["refunds"] = refunds
    tables["returns"] = returns
    tables["credit_notes"] = credits
    tables["reservations"] = reservations

    # Procurement and stock ledger.  Opening stock is calculated from total
    # sold quantities so no valid scenario can go negative mid-period.
    sold_qty: defaultdict[str, int] = defaultdict(int)
    reserve_qty: defaultdict[str, int] = defaultdict(int)
    return_qty: defaultdict[str, int] = defaultdict(int)
    for item in order_items:
        order = next(row for row in order_rows if row["id"] == item["order_id"])
        if order["status"] in {"delivered", "shipped"}:
            sold_qty[item["variant_id"]] += item["quantity"]
        if order["status"] in {"paid", "pending"}:
            reserve_qty[item["variant_id"]] += item["quantity"]
    for ret in returns:
        if ret["restock"]:
            return_qty[next(row for row in order_items if row["id"] == ret["order_item_id"])["variant_id"]] += ret["quantity"]

    purchase_orders: list[dict[str, Any]] = []
    purchase_receipts: list[dict[str, Any]] = []
    supplier_payments: list[dict[str, Any]] = []
    movements: list[dict[str, Any]] = []
    onhand_before_adjustment: defaultdict[str, int] = defaultdict(int)
    for index, variant in enumerate(variants):
        vid = variant["id"]
        cost = variant["cost_cents"] if variant["cost_cents"] is not None else {"prod-socks": 4200, "prod-leggings": 11200, "prod-tops": 8200, "prod-shorts": 7100, "prod-wrap": 9800}[variant["product_id"]]
        sold = sold_qty[vid]
        if sold:
            received = max(1, int(sold * (0.06 if scenario == "stock_pressure" else 0.22)) + (index % 4))
            pending = max(4, int(sold * 0.12))
        else:
            received = 0
            pending = 12 if variant["product_id"] == "prod-wrap" else 4
        ordered = received + pending
        po_day = first + timedelta(days=min(days - 1, 3 + index % max(4, min(days, 23))))
        po_id = f"po-{index+1:05d}"
        paid = ordered * cost if scenario == "cash_squeeze" else received * cost
        po_status = "received" if received == ordered else ("partial" if received else "in_transit")
        purchase_orders.append(_row("purchase_orders", id=po_id, supplier_id=["sup-grip", "sup-studio", "sup-move"][index % 3], variant_id=vid, ordered_qty=ordered, received_qty=received, unit_cost_cents=cost, status=po_status, date=_iso(po_day), paid_cents=paid))
        # A split receipt is a source event, with ledger movements per event.
        if received:
            first_part = max(1, received // 2)
            parts = [received] if index % 5 or received == 1 else [first_part, received - first_part]
            for part_index, part in enumerate(parts):
                receipt_day = _bounded(po_day + timedelta(days=4 + part_index * 3), first, AS_OF)
                purchase_receipts.append(_row("purchase_receipts", id=f"receipt-{len(purchase_receipts)+1:05d}", purchase_order_id=po_id, date=_iso(receipt_day), quantity=part))
                movements.append(_row("movements", id=f"mov-receipt-{len(movements)+1:06d}", variant_id=vid, date=_iso(receipt_day), kind="receipt", quantity=part, reference_id=po_id))
        # Keep enough opening stock for early sales and active reservations;
        # final stock is intentionally tighter under stock pressure.
        safety = 8 if scenario == "stock_pressure" else 28
        opening = max(0, sold + reserve_qty[vid] + safety - received - return_qty[vid])
        opening_day = first
        movements.append(_row("movements", id=f"mov-opening-{vid}", variant_id=vid, date=_iso(opening_day), kind="opening", quantity=opening, reference_id=f"opening-{vid}"))
        onhand_before_adjustment[vid] = opening + received - sold + return_qty[vid]
        supplier_paid = paid
        if supplier_paid:
            pay_day = po_day if scenario == "cash_squeeze" else _bounded(po_day + timedelta(days=6), first, AS_OF)
            first_pay = supplier_paid if index % 4 else max(1, supplier_paid // 2)
            supplier_payments.append(_row("supplier_payments", id=f"supplier-pay-{len(supplier_payments)+1:05d}", purchase_order_id=po_id, date=_iso(pay_day), amount_cents=first_pay))
            if first_pay < supplier_paid:
                supplier_payments.append(_row("supplier_payments", id=f"supplier-pay-{len(supplier_payments)+1:05d}", purchase_order_id=po_id, date=_iso(_bounded(pay_day + timedelta(days=2), first, AS_OF)), amount_cents=supplier_paid - first_pay))
    # Sales and returns are appended after opening/receipts, then sorted by
    # event date for a legible ledger (the validator also sorts defensively).
    for item in order_items:
        order = next(row for row in order_rows if row["id"] == item["order_id"])
        if order["status"] in {"delivered", "shipped"}:
            sale_day = order_sale_day[item["order_id"]]
            movements.append(_row("movements", id=f"mov-sale-{item['id']}", variant_id=item["variant_id"], date=_iso(sale_day), kind="sale", quantity=-item["quantity"], reference_id=item["id"]))
    for ret in returns:
        if ret["restock"]:
            item = next(row for row in order_items if row["id"] == ret["order_item_id"])
            movements.append(_row("movements", id=f"mov-return-{ret['id']}", variant_id=item["variant_id"], date=ret["date"], kind="return", quantity=ret["quantity"], reference_id=ret["id"]))
    if scenario == "stock_pressure":
        for index, variant in enumerate(variants):
            if index % 7 == 0 and onhand_before_adjustment[variant["id"]] > 2:
                movements.append(_row("movements", id=f"mov-adjustment-{index+1:05d}", variant_id=variant["id"], date=_iso(AS_OF), kind="adjustment", quantity=-1, reference_id=f"count-{index+1:05d}"))
    movements.sort(key=lambda row: (row["date"], 0 if row["quantity"] >= 0 else 1, row["id"]))
    tables["purchase_orders"] = purchase_orders
    tables["purchase_receipts"] = purchase_receipts
    tables["supplier_payments"] = supplier_payments
    tables["movements"] = movements

    # Event-date shipments and management invoices are intentionally separate
    # from the core orders table.
    shipments: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []
    for order in order_rows:
        if order["status"] not in {"shipped", "delivered"}:
            continue
        event_day = order_sale_day.get(order["id"], date.fromisoformat(order["date"]))
        shipments.append(_row("shipments", id=f"shipment-{order['id']}", order_id=order["id"], date=_iso(event_day), status="delivered" if order["status"] == "delivered" else "in_transit", delivered_date=order["delivered_date"]))
        invoices.append(_row("invoices", id=f"invoice-{order['id']}", order_id=order["id"], date=order["date"], amount_cents=order_total[order["id"]], status="issued", kind="management_statement"))
    for order in order_rows:
        if order["status"] == "cancelled":
            invoices.append(_row("invoices", id=f"invoice-{order['id']}", order_id=order["id"], date=order["date"], amount_cents=0, status="void", kind="management_statement"))
    tables["shipments"] = shipments
    tables["invoices"] = invoices

    # Marketing expenses and funnel are independently represented but reconcile
    # exactly on spend.  Dates are payment/event dates, never inferred zeros.
    expenses: list[dict[str, Any]] = []
    expense_payments: list[dict[str, Any]] = []
    funnel: list[dict[str, Any]] = []
    month_starts = _month_starts(first, AS_OF)
    if len(month_starts) < 12 and days >= 300:
        month_starts.extend(first + timedelta(days=30 * i) for i in range(12 - len(month_starts)))
    for index, month_day in enumerate(month_starts):
        month_day = _bounded(month_day, first, AS_OF)
        marketing = 9000 + rng.randrange(5000)
        expense_id = f"expense-marketing-{index+1:03d}"
        expenses.append(_row("expenses", id=expense_id, date=_iso(month_day), category="marketing", amount_cents=marketing, paid_cents=marketing, variable=1))
        funnel.append(_row("funnel", id=f"funnel-{index+1:03d}", date=_iso(month_day), channel=["Instagram", "Paid Social", "DM", "Organic"][index % 4], campaign_id=["camp-studio", "camp-move", "camp-private", "organic"][index % 4], visits=None if index % 4 == 2 else 260 + rng.randrange(240), leads=None if index % 4 == 2 else 20 + rng.randrange(50), spend_cents=marketing))
        expense_payments.append(_row("expense_payments", id=f"expense-pay-{index+1:03d}", expense_id=expense_id, date=_iso(month_day), amount_cents=marketing))
        other_amount = 12000 + rng.randrange(7000)
        other_id = f"expense-operations-{index+1:03d}"
        paid_other = other_amount if index % 4 else other_amount // 2
        expenses.append(_row("expenses", id=other_id, date=_iso(month_day), category="operations", amount_cents=other_amount, paid_cents=paid_other, variable=0))
        expense_payments.append(_row("expense_payments", id=f"expense-pay-{index+1:03d}-ops", expense_id=other_id, date=_iso(_bounded(month_day + timedelta(days=2), first, AS_OF)), amount_cents=paid_other))
    tables["expenses"] = expenses
    tables["expense_payments"] = expense_payments
    tables["funnel"] = funnel

    # Every order gets a linked session and a lead.  A few additional open/lost
    # leads preserve funnel states without inventing an order.
    sessions: list[dict[str, Any]] = []
    leads: list[dict[str, Any]] = []
    for index, order in enumerate(order_rows):
        order_day = date.fromisoformat(order["date"])
        acquired_day = date.fromisoformat(customer_by_id[order["customer_id"]]["acquired_date"])
        session_day = _bounded(max(acquired_day, order_day - timedelta(days=min(5, index % 6))), first, order_day)
        sid = f"session-{index+1:05d}"
        sessions.append(_row("sessions", id=sid, customer_id=order["customer_id"], channel=order["channel"], campaign_id=order["campaign_id"], date=_iso(session_day), content_asset_id=asset_by_campaign[order["campaign_id"]]))
        first_item = next(item for item in order_items if item["order_id"] == order["id"])
        lead_status = "lost" if order["status"] == "cancelled" else "converted"
        leads.append(_row("leads", id=f"lead-{index+1:05d}", customer_id=order["customer_id"], session_id=sid, channel=order["channel"], campaign_id=order["campaign_id"], date=order["date"], intent="purchase" if lead_status == "converted" else "browse", status=lead_status, order_id=order["id"] if lead_status == "converted" else None, variant_id=first_item["variant_id"] if lead_status == "converted" else None))
    # Public, non-converting exposure is deliberately much larger than the
    # order-linked path.  Nullable customer IDs model anonymous visits without
    # turning unknown identity into a known zero or a fake customer.
    public_sessions = max(800, min(8000, order_count * 20 // 3))
    public_session_ids: list[str] = []
    public_session_dates: dict[str, date] = {}
    public_session_campaigns: dict[str, str] = {}
    for index in range(public_sessions):
        campaign_id = ["camp-studio", "camp-move", "camp-private", "organic"][index % 4]
        session_day = _bounded(first + timedelta(days=rng.randrange(max(1, days))), first, AS_OF)
        sid = f"session-public-{index+1:05d}"
        public_session_ids.append(sid)
        public_session_dates[sid] = session_day
        public_session_campaigns[sid] = campaign_id
        sessions.append(_row("sessions", id=sid, customer_id=None, channel=campaign_by_id[campaign_id]["channel"], campaign_id=campaign_id, date=_iso(session_day), content_asset_id=None if index % 9 == 0 else asset_by_campaign[campaign_id]))
    public_leads = max(120, min(1800, order_count + order_count // 3))
    for index in range(public_leads):
        customer = customers[(index * 7) % len(customers)]
        acquired = date.fromisoformat(customer["acquired_date"])
        sid = public_session_ids[(index * 11) % len(public_session_ids)]
        campaign_id = public_session_campaigns[sid]
        lead_day = _bounded(max(acquired, public_session_dates[sid]), first, AS_OF)
        leads.append(_row("leads", id=f"lead-public-{index+1:05d}", customer_id=customer["id"], session_id=sid, channel=campaign_by_id[campaign_id]["channel"], campaign_id=campaign_id, date=_iso(lead_day), intent="browse" if index % 3 else "consider", status="open" if index % 4 else "lost", order_id=None, variant_id=None))
    for index in range(max(4, order_count // 40)):
        campaign_id = ["camp-studio", "camp-move", "camp-private", "organic"][index % 4]
        customer = customers[index % len(customers)]
        day = _bounded(date.fromisoformat(customer["acquired_date"]) + timedelta(days=1), first, AS_OF)
        sid = f"session-extra-{index+1:04d}"
        sessions.append(_row("sessions", id=sid, customer_id=customer["id"], channel=campaign_by_id[campaign_id]["channel"], campaign_id=campaign_id, date=_iso(day), content_asset_id=asset_by_campaign[campaign_id]))
        leads.append(_row("leads", id=f"lead-extra-{index+1:04d}", customer_id=customer["id"], session_id=sid, channel=campaign_by_id[campaign_id]["channel"], campaign_id=campaign_id, date=_iso(day), intent="interest", status="open", order_id=None, variant_id=None))
    tables["sessions"] = sessions
    tables["leads"] = leads

    # Physical counts are deliberately allowed to disagree with the ledger in
    # stock_pressure; the discrepancy is a business alert, not a contract fail.
    physical: defaultdict[str, int] = defaultdict(int)
    for movement in movements:
        physical[movement["variant_id"]] += movement["quantity"]
    inventory_counts: list[dict[str, Any]] = []
    for index, variant in enumerate(variants):
        discrepancy = 1 if scenario == "stock_pressure" and index % 5 == 0 else 0
        inventory_counts.append(_row("inventory_counts", id=f"count-{index+1:05d}", variant_id=variant["id"], date=_iso(AS_OF), counted_qty=max(0, physical[variant["id"]] + discrepancy)))
    tables["inventory_counts"] = inventory_counts
    unmet: list[dict[str, Any]] = []
    for index, variant in enumerate(sellable):
        if scenario == "stock_pressure" or index % 7 == 0:
            unmet.append(_row("unmet_demand", id=f"unmet-{index+1:05d}", date=_iso(_bounded(first + timedelta(days=days - 1 - index % max(1, min(days, 30))), first, AS_OF)), variant_id=variant["id"], quantity=2 + index % 6, reason="synthetic availability request; not observed demand"))
    tables["unmet_demand"] = unmet

    # Randomized synthetic experiment, separate from order conversion evidence.
    experiment_start = first
    experiment_end = _bounded(first + timedelta(days=min(days - 1, 56)), first, AS_OF)
    followup_days = min(7, max(0, (experiment_end - experiment_start).days))
    enrollment_end = experiment_end - timedelta(days=followup_days)
    experiment_id = "exp-socks-01"
    tables["experiments"] = [_row("experiments", id=experiment_id, name="Synthetic Pilates socks vignette", hypothesis="A socks-led creative may improve contribution per eligible visit.", primary_metric="contribution_cents_per_visit", guardrail="return_rate_under_10_percent", start_date=_iso(experiment_start), end_date=_iso(experiment_end), status="completed" if experiment_end < AS_OF else "running")]
    assignments: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    # Enrollment closes before the fixed follow-up window so outcomes retain
    # their generated 1-7 day lag without extending the experiment window.
    eligible_experiment_customers = [customer for customer in customers if date.fromisoformat(customer["acquired_date"]) <= enrollment_end]
    for index, customer in enumerate(eligible_experiment_customers[: max(8, min(len(eligible_experiment_customers), 180))]):
        acquired = date.fromisoformat(customer["acquired_date"])
        assigned = _bounded(max(acquired, experiment_start + timedelta(days=index % max(1, min(days, 14)))), first, enrollment_end)
        assignment_id = f"assignment-{index+1:05d}"
        arm = "treatment" if (rng.randrange(2) == 1) else "control"
        assignments.append(_row("experiment_assignments", id=assignment_id, experiment_id=experiment_id, customer_id=customer["id"], arm=arm, assigned_date=_iso(assigned)))
        lag_days = 0 if followup_days == 0 else 1 + index % followup_days
        outcome_day = assigned + timedelta(days=lag_days)
        converted = 1 if rng.random() < (0.40 if arm == "treatment" else 0.35) else 0
        revenue = (4500 + rng.randrange(9000)) if converted else 0
        contribution = revenue - (1800 + rng.randrange(4000)) if converted else 0
        outcomes.append(_row("experiment_outcomes", id=f"outcome-{index+1:05d}", assignment_id=assignment_id, date=_iso(outcome_day), converted=converted, net_revenue_cents=revenue, contribution_cents=contribution, returned=1 if converted and rng.random() < 0.08 else 0))
    tables["experiment_assignments"] = assignments
    tables["experiment_outcomes"] = outcomes

    # Apply the intentionally invalid link last, after all valid row derivation.
    if scenario == "broken_link":
        tables["order_items"][0]["variant_id"] = "variant-missing"
        tables["leads"][0]["variant_id"] = "variant-missing"

    metadata = {
        "synthetic": True,
        "seed": seed,
        "as_of": _iso(AS_OF),
        "start_date": _iso(first),
        "scenario": scenario,
        "scenario_mechanism": SCENARIO_MECHANISMS[scenario],
        "currency": "MXN",
        "contract_version": "2.0",
        "coverage": {name: bool(tables[name]) for name in ALL_TABLES},
        "hypotheses": {
            "seasonality": "Synthetic order intensity varies by date to exercise monthly trend calculations.",
            "sock_preference": "Pilates sock color and size mix is a generated hypothesis signal, not observed preference.",
            "discount_pressure": "Promotion scenarios intentionally trade discount depth for contribution.",
        },
        "limitations": "Every row is simulated; experiment outcomes and scenario mechanisms are not evidence of real lift, demand, cash, or customer behavior.",
    }
    return {"metadata": metadata, "tables": tables}


def core_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Return only the strict v1 schema and its 17-table coverage map."""
    if not isinstance(data, dict) or not isinstance(data.get("metadata"), dict) or not isinstance(data.get("tables"), dict):
        raise ValueError("Expected simulation data with metadata and tables")
    metadata = dict(data["metadata"])
    metadata["coverage"] = {name: bool(data["metadata"].get("coverage", {}).get(name, False)) for name in CORE_TABLES}
    tables = {name: [dict(row) for row in data["tables"].get(name, [])] for name in CORE_TABLES}
    return {"metadata": metadata, "tables": tables}


__all__ = ["ADDITIONAL_SCHEMA", "ALL_TABLES", "AS_OF", "CORE_TABLES", "TABLE_COLUMNS", "VALID_SCENARIOS", "core_projection", "generate"]
