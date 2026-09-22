"""Deterministic synthetic data for the Alma de Lujo demo.

The data is intentionally small enough to inspect by hand while containing the
relationships that the analytics contract needs.  All money values are integer
MXN cents and all identifiers are synthetic.
"""

from __future__ import annotations

from datetime import date, timedelta
import random
from typing import Any


AS_OF = date(2026, 9, 21)
TABLE_COLUMNS = {
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
}


def _d(offset: int) -> str:
    return (AS_OF - timedelta(days=offset)).isoformat()


def _row(columns: tuple[str, ...], **values: Any) -> dict[str, Any]:
    return {column: values.get(column) for column in columns}


def generate(seed: int = 42, scenario: str = "normal") -> dict[str, Any]:
    """Return a reproducible 90-day synthetic fixture.

    ``scenario`` is one of ``normal``, ``missing_cost``, ``negative_stock``,
    ``missing_payment`` and ``duplicate_event``.  Failure scenarios are
    deliberate integrity-test inputs and should not be interpreted as business
    observations.
    """
    valid = {"normal", "missing_cost", "negative_stock", "missing_payment", "duplicate_event"}
    if scenario not in valid:
        raise ValueError(f"unknown scenario: {scenario!r}")
    rng = random.Random(seed)

    products = [
        _row(TABLE_COLUMNS["products"], id="prod-socks", name="Grip Pilates Socks", category="Pilates socks", collection="Studio Essentials", lifecycle="launched"),
        _row(TABLE_COLUMNS["products"], id="prod-leggings", name="Flow Leggings", category="Sportswear", collection="Flow", lifecycle="launched"),
        _row(TABLE_COLUMNS["products"], id="prod-tops", name="Sculpt Studio Top", category="Sportswear", collection="Studio Essentials", lifecycle="sample"),
        _row(TABLE_COLUMNS["products"], id="prod-shorts", name="Move Biker Shorts", category="Sportswear", collection="Move", lifecycle="clearance"),
        _row(TABLE_COLUMNS["products"], id="prod-wrap", name="Recovery Wrap Concept", category="Sportswear", collection="Future Concepts", lifecycle="idea"),
    ]
    variants = []
    def add_variants(product_id: str, prefix: str, size: str, colors: list[str], price: int, cost: int) -> None:
        for color in colors:
            variants.append(_row(TABLE_COLUMNS["variants"], id=f"var-{prefix}-{color.lower()}", product_id=product_id, size=size, color=color, price_cents=price, cost_cents=cost))
    add_variants("prod-socks", "sock", "M", ["Black", "Ivory", "Rose", "Sage", "Lilac"], 28900, 9200)
    add_variants("prod-leggings", "legging", "M", ["Black", "Navy"], 89900, 35500)
    add_variants("prod-tops", "top", "M", ["Black", "Sand"], 64900, 24500)
    add_variants("prod-shorts", "short", "M", ["Black", "Coral"], 49900, 19800)
    add_variants("prod-wrap", "wrap", "M", ["Sand"], 72900, 29000)

    suppliers = [
        _row(TABLE_COLUMNS["suppliers"], id="sup-textiles", name="Synthetic Studio Textiles"),
        _row(TABLE_COLUMNS["suppliers"], id="sup-grip", name="Synthetic Grip Goods"),
    ]
    variant_by_id = {row["id"]: row for row in variants}
    purchase_orders = [
        _row(TABLE_COLUMNS["purchase_orders"], id="po-001", supplier_id="sup-grip", variant_id="var-sock-rose", ordered_qty=40, received_qty=40, unit_cost_cents=9200, status="received", date=_d(78), paid_cents=368000),
        _row(TABLE_COLUMNS["purchase_orders"], id="po-002", supplier_id="sup-textiles", variant_id="var-legging-black", ordered_qty=24, received_qty=18, unit_cost_cents=35500, status="partial", date=_d(36), paid_cents=319500),
        _row(TABLE_COLUMNS["purchase_orders"], id="po-003", supplier_id="sup-textiles", variant_id="var-short-coral", ordered_qty=30, received_qty=0, unit_cost_cents=19800, status="in_transit", date=_d(9), paid_cents=0),
    ]
    customers = [_row(TABLE_COLUMNS["customers"], id=f"cust-{i:03d}", acquired_date=_d(88 - i * 9)) for i in range(1, 9)]

    orders = [
        _row(TABLE_COLUMNS["orders"], id="ord-001", customer_id="cust-001", channel="Instagram", campaign_id="camp-studio", date=_d(82), delivered_date=_d(78), status="delivered"),
        _row(TABLE_COLUMNS["orders"], id="ord-002", customer_id="cust-002", channel="Organic", campaign_id="organic", date=_d(65), delivered_date=_d(61), status="delivered"),
        _row(TABLE_COLUMNS["orders"], id="ord-003", customer_id="cust-003", channel="Instagram", campaign_id="camp-color", date=_d(48), delivered_date=_d(44), status="delivered"),
        _row(TABLE_COLUMNS["orders"], id="ord-004", customer_id="cust-004", channel="DM", campaign_id="camp-private", date=_d(32), delivered_date=None, status="shipped"),
        _row(TABLE_COLUMNS["orders"], id="ord-005", customer_id="cust-005", channel="Paid Social", campaign_id="camp-move", date=_d(24), delivered_date=None, status="paid"),
        _row(TABLE_COLUMNS["orders"], id="ord-006", customer_id="cust-006", channel="DM", campaign_id="camp-private", date=_d(14), delivered_date=None, status="pending"),
        _row(TABLE_COLUMNS["orders"], id="ord-007", customer_id="cust-007", channel="Organic", campaign_id="organic", date=_d(10), delivered_date=None, status="cancelled"),
        _row(TABLE_COLUMNS["orders"], id="ord-008", customer_id="cust-001", channel="Instagram", campaign_id="camp-studio", date=_d(5), delivered_date=_d(2), status="delivered"),
    ]
    item_specs = [
        ("ord-001", "var-sock-rose", 2, 0), ("ord-001", "var-legging-black", 1, 1000),
        ("ord-002", "var-sock-black", 1, 0), ("ord-002", "var-legging-navy", 1, 0),
        ("ord-003", "var-sock-lilac", 2, 500), ("ord-003", "var-short-black", 1, 0),
        ("ord-004", "var-sock-sage", 1, 0), ("ord-004", "var-legging-navy", 1, 0),
        ("ord-005", "var-short-coral", 2, 0), ("ord-006", "var-sock-ivory", 1, 0),
        ("ord-007", "var-sock-black", 1, 0), ("ord-008", "var-sock-rose", 1, 0),
    ]
    order_by_id = {row["id"]: row for row in orders}
    order_items = []
    for index, (order_id, variant_id, quantity, discount) in enumerate(item_specs, 1):
        variant = variant_by_id[variant_id]
        order_items.append(_row(TABLE_COLUMNS["order_items"], id=f"item-{index:03d}", order_id=order_id, variant_id=variant_id, quantity=quantity, unit_price_cents=variant["price_cents"], discount_cents=discount, unit_cost_cents=variant["cost_cents"]))

    payments = [
        _row(TABLE_COLUMNS["payments"], id="pay-001", order_id="ord-001", date=_d(81), amount_cents=order_total(order_items, "ord-001"), status="settled"),
        _row(TABLE_COLUMNS["payments"], id="pay-002", order_id="ord-002", date=_d(64), amount_cents=order_total(order_items, "ord-002"), status="settled"),
        _row(TABLE_COLUMNS["payments"], id="pay-003", order_id="ord-003", date=_d(47), amount_cents=order_total(order_items, "ord-003"), status="settled"),
        _row(TABLE_COLUMNS["payments"], id="pay-004", order_id="ord-004", date=_d(31), amount_cents=order_total(order_items, "ord-004"), status="settled"),
        _row(TABLE_COLUMNS["payments"], id="pay-005", order_id="ord-005", date=_d(23), amount_cents=order_total(order_items, "ord-005"), status="settled"),
        _row(TABLE_COLUMNS["payments"], id="pay-006", order_id="ord-006", date=_d(13), amount_cents=order_total(order_items, "ord-006"), status="pending"),
        _row(TABLE_COLUMNS["payments"], id="pay-008", order_id="ord-008", date=_d(4), amount_cents=order_total(order_items, "ord-008"), status="settled"),
    ]
    refunds = [_row(TABLE_COLUMNS["refunds"], id="refund-001", order_id="ord-001", date=_d(72), amount_cents=18900, status="settled")]
    returns = [_row(TABLE_COLUMNS["returns"], id="return-001", order_item_id="item-001", date=_d(70), quantity=1, restock=1), _row(TABLE_COLUMNS["returns"], id="return-002", order_item_id="item-005", date=_d(38), quantity=1, restock=0)]
    credit_notes = [_row(TABLE_COLUMNS["credit_notes"], id="credit-001", order_item_id="item-001", date=_d(70), amount_cents=10000, reason="fit adjustment")]

    movements = []
    for variant in variants:
        opening = 0 if variant["id"] == "var-wrap-sand" else 24 if variant["id"].startswith("var-sock") else 12
        movements.append(_row(TABLE_COLUMNS["movements"], id=f"mov-opening-{variant['id']}", variant_id=variant["id"], date=_d(89), kind="opening", quantity=opening, reference_id=f"opening-{variant['id']}"))
    for po in purchase_orders:
        if po["received_qty"]:
            movements.append(_row(TABLE_COLUMNS["movements"], id=f"mov-{po['id']}", variant_id=po["variant_id"], date=po["date"], kind="receipt", quantity=po["received_qty"], reference_id=po["id"]))
    for item in order_items:
        if order_by_id[item["order_id"]]["status"] in ("shipped", "delivered"):
            order = order_by_id[item["order_id"]]
            settled_dates = [payment["date"] for payment in payments if payment["order_id"] == order["id"] and payment["status"] == "settled"]
            sale_date = max([order["date"], *settled_dates])
            movements.append(_row(TABLE_COLUMNS["movements"], id=f"mov-sale-{item['id']}", variant_id=item["variant_id"], date=sale_date, kind="sale", quantity=-item["quantity"], reference_id=item["id"]))
    item_by_id = {row["id"]: row for row in order_items}
    for ret in returns:
        if ret["restock"]:
            item = item_by_id[ret["order_item_id"]]
            movements.append(_row(TABLE_COLUMNS["movements"], id=f"mov-{ret['id']}", variant_id=item["variant_id"], date=ret["date"], kind="return", quantity=ret["quantity"], reference_id=ret["id"]))
    if scenario == "negative_stock":
        movements.append(_row(TABLE_COLUMNS["movements"], id="mov-adjustment-failure", variant_id="var-sock-lilac", date=_d(1), kind="adjustment", quantity=-999, reference_id="adjustment-failure"))
    if scenario == "duplicate_event":
        movements.append(dict(movements[0]))
    reservations = [_row(TABLE_COLUMNS["reservations"], id="reservation-001", order_item_id="item-009", quantity=2, status="active"), _row(TABLE_COLUMNS["reservations"], id="reservation-002", order_item_id="item-010", quantity=1, status="active"), _row(TABLE_COLUMNS["reservations"], id="reservation-003", order_item_id="item-007", quantity=1, status="released"), _row(TABLE_COLUMNS["reservations"], id="reservation-004", order_item_id="item-008", quantity=1, status="released")]
    expenses = [_row(TABLE_COLUMNS["expenses"], id="expense-001", date=_d(75), category="packaging", amount_cents=24000, paid_cents=24000, variable=1), _row(TABLE_COLUMNS["expenses"], id="expense-002", date=_d(45), category="photography", amount_cents=85000, paid_cents=0, variable=0), _row(TABLE_COLUMNS["expenses"], id="expense-003", date=_d(12), category="shipping", amount_cents=31000, paid_cents=18000, variable=1), _row(TABLE_COLUMNS["expenses"], id="expense-004", date=_d(60), category="marketing", amount_cents=42000, paid_cents=42000, variable=1), _row(TABLE_COLUMNS["expenses"], id="expense-005", date=_d(40), category="marketing", amount_cents=38000, paid_cents=38000, variable=1)]
    funnel = [_row(TABLE_COLUMNS["funnel"], id="funnel-001", date=_d(60), channel="Instagram", campaign_id="camp-studio", visits=620, leads=74, spend_cents=42000), _row(TABLE_COLUMNS["funnel"], id="funnel-002", date=_d(40), channel="Paid Social", campaign_id="camp-move", visits=410, leads=31, spend_cents=38000), _row(TABLE_COLUMNS["funnel"], id="funnel-003", date=_d(20), channel="DM", campaign_id="camp-private", visits=None, leads=None, spend_cents=0), _row(TABLE_COLUMNS["funnel"], id="funnel-004", date=_d(15), channel="Organic", campaign_id="organic", visits=300, leads=28, spend_cents=0)]
    unmet_demand = [_row(TABLE_COLUMNS["unmet_demand"], id="unmet-001", date=_d(3), variant_id="var-sock-lilac", quantity=7, reason="historical hypothetical demand signal; availability not observed"), _row(TABLE_COLUMNS["unmet_demand"], id="unmet-002", date=_d(1), variant_id="var-wrap-sand", quantity=5, reason="concept request; no opening stock")]

    if scenario == "missing_cost":
        variant_by_id["var-sock-lilac"]["cost_cents"] = None
        for item in order_items:
            if item["variant_id"] == "var-sock-lilac":
                item["unit_cost_cents"] = None
    if scenario == "missing_payment":
        payments = [payment for payment in payments if payment["id"] != "pay-003"]

    tables = {"products": products, "variants": variants, "suppliers": suppliers, "purchase_orders": purchase_orders, "customers": customers, "orders": orders, "order_items": order_items, "payments": payments, "refunds": refunds, "credit_notes": credit_notes, "returns": returns, "movements": movements, "reservations": reservations, "expenses": expenses, "funnel": funnel, "unmet_demand": unmet_demand}
    coverage = {name: bool(rows) for name, rows in tables.items()}
    return {"metadata": {"synthetic": True, "seed": seed, "as_of": AS_OF.isoformat(), "scenario": scenario, "currency": "MXN", "coverage": coverage}, "tables": tables}


def order_total(items: list[dict[str, Any]], order_id: str) -> int:
    """Compute an order's gross less line discounts from locked item prices."""
    return sum(item["quantity"] * item["unit_price_cents"] - item["discount_cents"] for item in items if item["order_id"] == order_id)
