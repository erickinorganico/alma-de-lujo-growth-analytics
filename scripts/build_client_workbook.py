from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import xlsxwriter


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "client" / "contract.json"

CREAM = "#F7F1E7"
CREAM_DARK = "#E8DDCA"
INK = "#17252A"
TEAL = "#0F6B68"
TEAL_LIGHT = "#D8ECE8"
GOLD = "#C99A3D"
GOLD_LIGHT = "#F5E7BF"
RED = "#A63D40"
RED_LIGHT = "#F6D8D7"
BLUE = "#0000FF"
GREEN = "#008000"
GRAY = "#66706F"
WHITE = "#FFFFFF"


def d(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iso(value):
    return value.isoformat() if isinstance(value, date) else value


def distribute(total: int, n: int) -> list[int]:
    q, r = divmod(total, n)
    return [q + (1 if i < r else 0) for i in range(n)]


def example_payload(contract: dict) -> dict:
    cutoff = d("2026-09-21")
    catalog = [
        {"sku": "PIL-NEGRO", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Negro", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-ARENA", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Arena", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-ROSA", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Rosa", "size": "Unitalla", "status": "PRELANZAMIENTO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-LILA", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Lila", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": None, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-VERDE", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Verde salvia", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-AZUL", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Azul noche", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-VINO", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Vino", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 24, "pack_multiple": 12},
        {"sku": "PIL-GRIS", "product": "Calcetín Pilates Grip", "category": "Calcetines Pilates", "color": "Gris", "size": "Unitalla", "status": "ACTIVO", "list_price": 299, "purchase_cost": 82, "inbound_freight": 8, "packaging": 9, "commission_rate": 0.08, "other_variable": 5, "lead_days": 14, "moq": 12, "pack_multiple": 6},
        {"sku": "TOP-NEGRO-S", "product": "Top deportivo Aura", "category": "Ropa deportiva", "color": "Negro", "size": "S", "status": "ACTIVO", "list_price": 899, "purchase_cost": 330, "inbound_freight": 20, "packaging": 18, "commission_rate": 0.08, "other_variable": 12, "lead_days": 21, "moq": 12, "pack_multiple": 6},
        {"sku": "LEG-NEGRO-M", "product": "Legging Esencia", "category": "Ropa deportiva", "color": "Negro", "size": "M", "status": "PAUSADO", "list_price": 1299, "purchase_cost": 470, "inbound_freight": 25, "packaging": 20, "commission_rate": 0.08, "other_variable": 15, "lead_days": 28, "moq": 12, "pack_multiple": 6},
    ]
    totals = {
        "PIL-NEGRO": (60, 5, 4), "PIL-ARENA": (28, 1, 0), "PIL-ROSA": (0, 0, 0),
        "PIL-LILA": (35, 2, 1), "PIL-VERDE": (42, 2, 1), "PIL-AZUL": (32, 1, 1),
        "PIL-VINO": (30, 1, 0), "PIL-GRIS": (42, 3, 2), "TOP-NEGRO-S": (12, 1, 1),
        "LEG-NEGRO-M": (8, 1, 1),
    }
    by_sku = {row["sku"]: row for row in catalog}
    sales = []
    for sku, (delivered_total, returned_total, restocked_total) in totals.items():
        delivered = distribute(delivered_total, 28)
        returned = distribute(returned_total, 28)
        restocked = distribute(restocked_total, 28)
        item = by_sku[sku]
        unit_actual = None if item["purchase_cost"] is None else item["purchase_cost"] + item["inbound_freight"] + item["packaging"] + item["other_variable"]
        for i in range(28):
            dt = cutoff - timedelta(days=27 - i)
            net_units = max(0, delivered[i] - restocked[i])
            sales.append({
                "date": dt, "sku": sku, "delivered_units": delivered[i], "returned_units": returned[i],
                "restocked_units": restocked[i], "net_revenue": (delivered[i] - returned[i]) * item["list_price"],
                "variable_cost": None if unit_actual is None else net_units * unit_actual,
                "source_ref": f"SYNTH-{dt:%Y%m%d}",
            })
    stock = [
        {"sku": "PIL-NEGRO", "count_date": cutoff, "on_hand": 12, "reserved": 2, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 36, "payment_date": cutoff + timedelta(days=10)},
        {"sku": "PIL-ARENA", "count_date": cutoff, "on_hand": 63, "reserved": 3, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-ROSA", "count_date": cutoff, "on_hand": 0, "reserved": 0, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-LILA", "count_date": cutoff, "on_hand": 8, "reserved": 1, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-VERDE", "count_date": cutoff, "on_hand": 9, "reserved": 1, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 14, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-AZUL", "count_date": cutoff, "on_hand": 7, "reserved": 1, "in_transit": 24, "eta": cutoff + timedelta(days=30), "transit_confirmed": "SI", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-VINO", "count_date": cutoff, "on_hand": 8, "reserved": 2, "in_transit": 24, "eta": cutoff + timedelta(days=8), "transit_confirmed": "NO", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "PIL-GRIS", "count_date": cutoff, "on_hand": 12, "reserved": 2, "in_transit": 12, "eta": cutoff + timedelta(days=10), "transit_confirmed": "SI", "available_days": 28, "planned_qty": 0, "payment_date": None},
        {"sku": "TOP-NEGRO-S", "count_date": cutoff, "on_hand": 9, "reserved": 1, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 60, "payment_date": cutoff + timedelta(days=65)},
        {"sku": "LEG-NEGRO-M", "count_date": cutoff - timedelta(days=3), "on_hand": 20, "reserved": 2, "in_transit": 0, "eta": None, "transit_confirmed": "NO", "available_days": 28, "planned_qty": 0, "payment_date": None},
    ]
    cash = [
        {"date": cutoff + timedelta(days=3), "direction": "ENTRADA", "category": "Cobros agregados", "amount": 15000, "source_ref": "SYNTH-CASH-01"},
        {"date": cutoff + timedelta(days=5), "direction": "SALIDA", "category": "Operación", "amount": 18000, "source_ref": "SYNTH-CASH-02"},
        {"date": cutoff + timedelta(days=10), "direction": "ENTRADA", "category": "Cobros agregados", "amount": 12000, "source_ref": "SYNTH-CASH-03"},
        {"date": cutoff + timedelta(days=13), "direction": "SALIDA", "category": "Operación", "amount": 14000, "source_ref": "SYNTH-CASH-04"},
        {"date": cutoff + timedelta(days=20), "direction": "SALIDA", "category": "Marketing comprometido", "amount": 6000, "source_ref": "SYNTH-CASH-05"},
        {"date": cutoff + timedelta(days=31), "direction": "ENTRADA", "category": "Cobros agregados", "amount": 9000, "source_ref": "SYNTH-CASH-06"},
        {"date": cutoff + timedelta(days=38), "direction": "SALIDA", "category": "Operación", "amount": 11000, "source_ref": "SYNTH-CASH-07"},
        {"date": cutoff + timedelta(days=54), "direction": "SALIDA", "category": "Operación", "amount": 8000, "source_ref": "SYNTH-CASH-08"},
        {"date": cutoff + timedelta(days=78), "direction": "SALIDA", "category": "Operación", "amount": 2000, "source_ref": "SYNTH-CASH-09"},
    ]
    return {
        "contract_version": contract["version"],
        "workbook_type": "EJEMPLO_SINTETICO",
        "parameters": {
            "as_of": cutoff, "observation_days": 28, "safety_days": 7, "target_margin": 0.45,
            "opening_cash": 80000, "cash_floor": 40000, "purchase_cap": 30000,
            "policy_reviewed": "SI", "cash_plan_complete": "SI", "sales_complete": "SI",
        },
        "CATALOGO": catalog, "VENTAS": sales, "STOCK": stock, "CAJA": cash,
    }


def template_payload(contract: dict) -> dict:
    return {
        "contract_version": contract["version"],
        "workbook_type": "PLANTILLA_CLIENTE",
        "parameters": {
            "as_of": None, "observation_days": 28, "safety_days": 7, "target_margin": 0.45,
            "opening_cash": None, "cash_floor": None, "purchase_cap": None,
            "policy_reviewed": "NO", "cash_plan_complete": "NO", "sales_complete": "NO",
        },
        "CATALOGO": [], "VENTAS": [], "STOCK": [], "CAJA": [],
    }


def formats(wb):
    base = {"font_name": "Arial", "font_size": 10, "font_color": INK}
    return {
        "title": wb.add_format({**base, "font_size": 22, "bold": True, "font_color": WHITE, "bg_color": TEAL, "align": "left", "valign": "vcenter"}),
        "subtitle": wb.add_format({**base, "font_size": 10, "font_color": WHITE, "bg_color": TEAL, "text_wrap": True, "valign": "vcenter"}),
        "section": wb.add_format({**base, "font_size": 12, "bold": True, "font_color": TEAL, "bg_color": CREAM_DARK, "bottom": 1, "bottom_color": TEAL}),
        "note": wb.add_format({**base, "font_color": GRAY, "bg_color": CREAM, "text_wrap": True, "valign": "top"}),
        "notice": wb.add_format({**base, "bold": True, "font_color": RED, "bg_color": GOLD_LIGHT, "border": 1, "border_color": GOLD, "text_wrap": True, "valign": "vcenter"}),
        "label": wb.add_format({**base, "bold": True, "bg_color": CREAM_DARK, "border": 1, "border_color": CREAM_DARK}),
        "input": wb.add_format({**base, "font_color": BLUE, "bg_color": "#EEF5FF", "border": 1, "border_color": "#D5DFE8", "locked": False}),
        "input_date": wb.add_format({**base, "font_color": BLUE, "bg_color": "#EEF5FF", "border": 1, "border_color": "#D5DFE8", "locked": False, "num_format": "dd-mmm-yyyy"}),
        "input_int": wb.add_format({**base, "font_color": BLUE, "bg_color": "#EEF5FF", "border": 1, "border_color": "#D5DFE8", "locked": False, "num_format": "#,##0;(#,##0);-"}),
        "input_money": wb.add_format({**base, "font_color": BLUE, "bg_color": "#EEF5FF", "border": 1, "border_color": "#D5DFE8", "locked": False, "num_format": "$#,##0.00;($#,##0.00);-"}),
        "input_pct": wb.add_format({**base, "font_color": BLUE, "bg_color": "#EEF5FF", "border": 1, "border_color": "#D5DFE8", "locked": False, "num_format": "0.0%;(0.0%);-"}),
        "calc": wb.add_format({**base, "font_color": INK, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB"}),
        "calc_int": wb.add_format({**base, "font_color": INK, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "#,##0;(#,##0);-"}),
        "calc_money": wb.add_format({**base, "font_color": INK, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "$#,##0.00;($#,##0.00);-"}),
        "calc_pct": wb.add_format({**base, "font_color": INK, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "0.0%;(0.0%);-"}),
        "link": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB"}),
        "link_int": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "#,##0;(#,##0);-"}),
        "link_money": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "$#,##0.00;($#,##0.00);-"}),
        "link_pct": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "0.0%;(0.0%);-"}),
        "link_date": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "num_format": "dd-mmm-yyyy"}),
        "wrap_link": wb.add_format({**base, "font_color": GREEN, "bg_color": WHITE, "border": 1, "border_color": "#E6E2DB", "text_wrap": True, "valign": "top"}),
        "summary_label": wb.add_format({**base, "bold": True, "font_color": WHITE, "bg_color": TEAL, "border": 1, "border_color": TEAL}),
        "summary_value": wb.add_format({**base, "bold": True, "font_size": 12, "font_color": INK, "bg_color": TEAL_LIGHT, "border": 1, "border_color": TEAL, "num_format": "$#,##0.00;($#,##0.00);-"}),
        "summary_text": wb.add_format({**base, "bold": True, "font_color": INK, "bg_color": TEAL_LIGHT, "border": 1, "border_color": TEAL, "text_wrap": True}),
    }


def setup_sheet(ws, title, note, f, last_col):
    ws.hide_gridlines(2)
    ws.set_tab_color(TEAL)
    ws.set_row(0, 30)
    ws.set_row(1, 32)
    ws.merge_range(0, 0, 0, last_col, title, f["title"])
    ws.merge_range(1, 0, 1, last_col, note, f["subtitle"])
    ws.freeze_panes(5, 0)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.set_margins(0.3, 0.3, 0.45, 0.45)
    ws.set_header("&LAlma de Lujo | &A&RConfidencial · agregados no personales")
    ws.set_footer("&LVersión 0.3&C&P / &N&RFecha de impresión: &D")
    ws.protect("", {"select_locked_cells": True, "select_unlocked_cells": True, "format_columns": True, "sort": True, "autofilter": True})


def write_value(ws, row, col, value, fmt, date_fmt=None):
    if value is None:
        ws.write_blank(row, col, None, fmt)
    elif isinstance(value, date):
        ws.write_datetime(row, col, datetime.combine(value, datetime.min.time()), date_fmt or fmt)
    else:
        ws.write(row, col, value, fmt)


def add_table(ws, last_row, last_col, headers, name):
    ws.add_table(4, 0, last_row - 1, last_col - 1, {
        "name": name,
        "style": "Table Style Medium 2",
        "columns": [{"header": h} for h in headers],
        "autofilter": True,
    })


def validation_common(ws, contract):
    ws.data_validation(5, 0, 104, 0, {"validate": "length", "criteria": "<=", "value": 40, "input_title": "SKU", "input_message": "Clave única; máximo 40 caracteres."})


def build_workbook(path: Path, payload: dict, contract: dict):
    wb = xlsxwriter.Workbook(path)
    wb.set_properties({"title": "Alma de Lujo · Kit de decisiones v0.3", "subject": "Inventario, precios y flujo de caja", "author": "Alma de Lujo", "comments": "Modelo local sin macros ni vínculos externos."})
    wb.set_calc_mode("auto")
    f = formats(wb)
    wb.define_name("SKU_LIST", "=CATALOGO!$A$6:$A$105")
    yes_no = contract["enums"]["yes_no"]
    input_note = "Azul = captura editable · Verde = vínculo entre hojas · Negro = cálculo. Blanco significa desconocido; cero es un valor explícito."

    ws = wb.add_worksheet("INICIO")
    setup_sheet(ws, "KIT DE DECISIONES · v0.3", "Uso semanal para inventario, precio y caja. Funciona sin Python, red ni suscripciones.", f, 7)
    ws.set_column("A:A", 3)
    ws.set_column("B:B", 24)
    ws.set_column("C:H", 18)
    marker = payload["workbook_type"]
    notice = ("EJEMPLO SINTÉTICO · Todos los productos, importes y referencias son ficticios y no han sido aprobados por un cliente real."
              if marker == "EJEMPLO_SINTETICO" else
              "PLANTILLA CLIENTE · Los parámetros iniciales son provisionales. No contiene productos, ventas, stock ni movimientos inventados.")
    ws.merge_range("B4:H5", notice, f["notice"])
    sections = [
        (7, "1 · CONFIGURA", "Define fecha de corte, ventanas, objetivo de margen y límites de caja. Confirma SI solo después de revisar cada política y la cobertura completa."),
        (10, "2 · CAPTURA", "CATALOGO: economía por SKU. VENTAS: un agregado por fecha y SKU. STOCK: conteo, tránsito y escenario elegido. CAJA: obligaciones existentes; no dupliques compras propuestas."),
        (13, "3 · REVISA", "DECISIONES explica por SKU qué falta, la propuesta condicional y la acción. FLUJO_13_SEMANAS muestra el pago completo de cada compra elegida en su semana."),
        (16, "4 · DECIDE EN REUNIÓN", "La hoja nunca ordena. Revisa evidencia, margen, cantidad, fecha de pago, presupuesto y piso protegido; documenta fuera del archivo quién aprueba."),
    ]
    for row, heading, body in sections:
        ws.merge_range(row - 1, 1, row - 1, 2, heading, f["section"])
        ws.merge_range(row, 1, row + 1, 7, body, f["note"])
    ws.merge_range("B21:H21", "LÍMITES Y USO SEGURO", f["section"])
    ws.merge_range("B22:H26", "Capacidad: 100 SKUs, 1,000 agregados fecha-SKU, 250 movimientos de caja y 13 semanas. Si tus datos exceden un límite, no omitas ni pegues fuera de la tabla: conserva el archivo fuente y solicita una ampliación o un proceso revisado. No captures nombres, correos, teléfonos, domicilios, credenciales ni datos de clientes. Los importes monetarios están en pesos MXN. La proyección muestra cierres semanales; el saldo dentro de la semana puede ser peor. Cada compra se paga completa en una fecha; concilia por separado los pagos divididos.", f["note"])
    ws.merge_range("B28:H30", "Alcance: herramienta analítica para conversación y preparación de decisiones. No es ERP, CRM, contabilidad, conciliación bancaria ni orden de compra. No estima elasticidad, impuestos ni causalidad de ventas. Una propuesta depende de los datos y declaraciones visibles.", f["notice"])
    ws.print_area("A1:H30")

    ws = wb.add_worksheet("CONFIG")
    setup_sheet(ws, "CONFIGURACIÓN", input_note, f, 4)
    ws.set_column("A:A", 29)
    ws.set_column("B:B", 21)
    ws.set_column("C:C", 54)
    ws.set_column("D:E", 15)
    ws.write("A3", "Tipo de archivo", f["label"])
    ws.write("B3", marker, f["calc"])
    ws.write("C3", "Marcador técnico; no modificar.", f["note"])
    params = [
        ("as_of", "Fecha de corte", "Último día incluido. El flujo inicia al día siguiente.", "date"),
        ("observation_days", "Días de observación", "Ventana completa de disponibilidad y ventas.", "int"),
        ("safety_days", "Días de seguridad", "Política provisional; revisar antes de confirmar SI.", "int"),
        ("target_margin", "Margen contribución objetivo", "Sobre precio, después de comisión y costos variables capturados.", "pct"),
        ("opening_cash", "Caja inicial (MXN pesos)", "Saldo reconciliado a la fecha de corte.", "money"),
        ("cash_floor", "Piso protegido (MXN pesos)", "Mínimo de cierre semanal aceptado.", "money"),
        ("purchase_cap", "Tope de compras (MXN pesos)", "Tope adicional antes de propuestas.", "money"),
        ("policy_reviewed", "Política revisada", "SI confirma que lead time, seguridad, MOQ y múltiplos fueron revisados.", "text"),
        ("cash_plan_complete", "Plan de caja completo", "SI confirma cobertura de obligaciones conocidas para 91 días.", "text"),
        ("sales_complete", "Ventas completas", "SI confirma cobertura de ventas para toda la ventana.", "text"),
    ]
    for i, (key, label, note, kind) in enumerate(params, start=4):
        value = payload["parameters"][key]
        ws.write(i, 0, label, f["label"])
        fmt = f[{"date": "input_date", "int": "input_int", "pct": "input_pct", "money": "input_money", "text": "input"}[kind]]
        write_value(ws, i, 1, value, fmt, f["input_date"])
        ws.write(i, 2, note, f["note"])
    ws.data_validation("B5", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("B6", {"validate": "integer", "criteria": "between", "minimum": 1, "maximum": 365})
    ws.data_validation("B7", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 3650})
    ws.data_validation("B8", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 0.99})
    ws.data_validation("B9", {"validate": "decimal", "criteria": "between", "minimum": -1000000000, "maximum": 1000000000})
    ws.data_validation("B10:B11", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1000000000})
    ws.data_validation("B12:B14", {"validate": "list", "source": yes_no})
    ws.conditional_format("B12:B14", {"type": "text", "criteria": "containing", "value": "NO", "format": wb.add_format({"bg_color": GOLD_LIGHT, "font_color": RED})})
    ws.merge_range("A17:C19", "Confirmar SI es una declaración del operador, no una inferencia de la hoja. Si un dato monetario o de cobertura es desconocido, déjalo en blanco o conserva NO; nunca uses cero como sustituto.", f["notice"])
    ws.print_area("A1:C19")

    cat_inputs = contract["sheets"]["CATALOGO"]
    cat_headers = ["SKU", "Producto", "Categoría", "Color", "Talla", "Estado", "Precio lista (MXN pesos)", "Costo compra/u (MXN pesos)", "Flete entrada/u (MXN pesos)", "Empaque/u (MXN pesos)", "Comisión", "Otro variable/u (MXN pesos)", "Lead días", "MOQ", "Múltiplo pack", "Costo variable/u (MXN pesos)", "Contribución/u (MXN pesos)", "Margen contribución", "Precio objetivo (MXN pesos)", "Calidad fila", "Estado precio"]
    ws = wb.add_worksheet("CATALOGO")
    setup_sheet(ws, "CATÁLOGO Y ECONOMÍA UNITARIA", input_note + " El precio objetivo no incorpora impuestos ni elasticidad.", f, len(cat_headers) - 1)
    widths = [18, 28, 22, 16, 12, 18, 18, 19, 19, 17, 12, 20, 11, 10, 13, 20, 20, 18, 20, 20, 24]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    add_table(ws, 105, len(cat_headers), cat_headers, "tblCatalogo")
    data = payload["CATALOGO"]
    for r in range(6, 106):
        row = data[r - 6] if r - 6 < len(data) else {}
        for c, key in enumerate(cat_inputs):
            kind = "input"
            if key in {"list_price", "purchase_cost", "inbound_freight", "packaging", "other_variable"}: kind = "input_money"
            elif key == "commission_rate": kind = "input_pct"
            elif key in {"lead_days", "moq", "pack_multiple"}: kind = "input_int"
            write_value(ws, r - 1, c, row.get(key), f[kind], f["input_date"])
        xr = r
        ws.write_formula(r - 1, 15, f'=IFERROR(IF(A{xr}="","",IF(OR(COUNT(H{xr}:J{xr})+COUNT(L{xr})<4,H{xr}<0,I{xr}<0,J{xr}<0,L{xr}<0,ABS(H{xr})>1000000000,ABS(I{xr})>1000000000,ABS(J{xr})>1000000000,ABS(L{xr})>1000000000),"",SUM(H{xr}:J{xr},L{xr}))),"")', f["calc_money"], "")
        ws.write_formula(r - 1, 16, f'=IF(T{xr}<>"OK","",G{xr}*(1-K{xr})-P{xr})', f["calc_money"], "")
        ws.write_formula(r - 1, 17, f'=IF(OR(G{xr}="",G{xr}=0,Q{xr}=""),"",Q{xr}/G{xr})', f["calc_pct"], "")
        ws.write_formula(r - 1, 18, f'=IF(OR(T{xr}<>"OK",P{xr}="",K{xr}="",CONFIG!$B$8="",CONFIG!$B$8<0,CONFIG!$B$8>=1),"",IF(1-K{xr}-CONFIG!$B$8<=0,"",ROUNDUP(ROUND(P{xr}/(1-K{xr}-CONFIG!$B$8),10),2)))', f["link_money"], "")
        ws.write_formula(r - 1, 19, f'=IFERROR(IF(A{xr}="","",IF(COUNTIF($A$6:$A$105,A{xr})>1,"DUPLICADO SKU",IF(OR(B{xr}="",C{xr}="",F{xr}="",G{xr}="",K{xr}="",M{xr}="",N{xr}="",O{xr}=""),"FALTA CAMPO",IF(COUNT(H{xr}:J{xr})+COUNT(L{xr})<4,"COSTO INCOMPLETO",IF(OR(G{xr}<=0,H{xr}<0,I{xr}<0,J{xr}<0,L{xr}<0,ABS(G{xr})>1000000000,ABS(H{xr})>1000000000,ABS(I{xr})>1000000000,ABS(J{xr})>1000000000,ABS(L{xr})>1000000000,ROUND(G{xr},2)<>G{xr},ROUND(H{xr},2)<>H{xr},ROUND(I{xr},2)<>I{xr},ROUND(J{xr},2)<>J{xr},ROUND(L{xr},2)<>L{xr},K{xr}<0,K{xr}>=1,M{xr}<0,M{xr}>3650,N{xr}<=0,N{xr}>1000000,O{xr}<=0,O{xr}>1000000),"REVISAR VALOR","OK"))))),"REVISAR VALOR")', f["calc"], "")
        ws.write_formula(r - 1, 20, f'=IF(A{xr}="","",IF(OR(P{xr}="",K{xr}="",CONFIG!$B$8=""),"FALTA COSTO O SUPUESTO",IF(1-K{xr}-CONFIG!$B$8<=0,"MARGEN INVIABLE","CALCULADO")))', f["link"], "")
    ws.data_validation("F6:F105", {"validate": "list", "source": contract["enums"]["product_status"]})
    for rng in ["G6:J105", "L6:L105"]: ws.data_validation(rng, {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1000000000})
    ws.data_validation("K6:K105", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 0.9999})
    ws.data_validation("M6:M105", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 3650})
    ws.data_validation("N6:O105", {"validate": "integer", "criteria": "between", "minimum": 1, "maximum": 1000000})
    ws.conditional_format("T6:U105", {"type": "text", "criteria": "not containing", "value": "OK", "format": wb.add_format({"bg_color": GOLD_LIGHT, "font_color": RED})})
    ws.print_area(0, 0, max(20, 5 + len(data)) - 1, len(cat_headers) - 1)
    ws.repeat_rows(0, 4)

    sales_inputs = contract["sheets"]["VENTAS"]
    sales_headers = ["Fecha", "SKU", "Unidades entregadas", "Unidades devueltas", "Unidades reingresadas", "Ingreso neto (MXN pesos)", "Costo variable real (MXN pesos, opcional)", "Referencia no personal", "Calidad fila"]
    ws = wb.add_worksheet("VENTAS")
    setup_sheet(ws, "VENTAS DIARIAS AGREGADAS", input_note + " Un renglón por fecha y SKU; devolución, reingreso físico y reembolso de caja son hechos distintos.", f, len(sales_headers) - 1)
    widths = [15, 18, 18, 18, 21, 20, 28, 24, 22]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    add_table(ws, 1005, len(sales_headers), sales_headers, "tblVentas")
    data = payload["VENTAS"]
    for r in range(6, 1006):
        row = data[r - 6] if r - 6 < len(data) else {}
        for c, key in enumerate(sales_inputs):
            kind = "input"
            if key == "date": kind = "input_date"
            elif key in {"delivered_units", "returned_units", "restocked_units"}: kind = "input_int"
            elif key in {"net_revenue", "variable_cost"}: kind = "input_money"
            write_value(ws, r - 1, c, row.get(key), f[kind], f["input_date"])
        xr = r
        ws.write_formula(r - 1, 8, f'=IFERROR(IF(COUNTA(A{xr}:H{xr})=0,"",IF(OR(A{xr}="",B{xr}="",C{xr}="",D{xr}="",E{xr}="",F{xr}=""),"FALTA CAMPO",IF(COUNTIFS($A$6:$A$1005,A{xr},$B$6:$B$1005,B{xr})>1,"DUPLICADO FECHA-SKU",IF(COUNTIF(CATALOGO!$A$6:$A$105,B{xr})<>1,"SKU NO VALIDO",IF(OR(A{xr}<DATE(1900,1,1),A{xr}>DATE(2100,12,31),A{xr}>CONFIG!$B$5,C{xr}<0,C{xr}>1000000,D{xr}<0,D{xr}>1000000,E{xr}<0,E{xr}>1000000,E{xr}>D{xr},ABS(F{xr})>1000000000,ABS(G{xr})>1000000000,ROUND(F{xr},2)<>F{xr},AND(G{xr}<>"",ROUND(G{xr},2)<>G{xr})),"REVISAR VALOR","OK"))))),"REVISAR VALOR")', f["link"], "")
    ws.data_validation("B6:B1005", {"validate": "list", "source": "=SKU_LIST"})
    ws.data_validation("A6:A1005", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("C6:E1005", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 1000000})
    ws.data_validation("F6:G1005", {"validate": "decimal", "criteria": "between", "minimum": -1000000000, "maximum": 1000000000})
    ws.conditional_format("I6:I1005", {"type": "text", "criteria": "not containing", "value": "OK", "format": wb.add_format({"bg_color": RED_LIGHT, "font_color": RED})})
    ws.print_area(0, 0, max(20, 5 + len(data)) - 1, len(sales_headers) - 1)
    ws.repeat_rows(0, 4)

    stock_inputs = contract["sheets"]["STOCK"]
    stock_headers = ["SKU", "Fecha conteo", "Existencia", "Reservado", "En tránsito", "ETA", "Tránsito confirmado", "Días disponibilidad observada", "Cantidad elegida", "Fecha pago", "Estado evidencia", "Disponible", "Consumo diario", "Tránsito elegible", "Necesidad", "Propuesta condicional", "Costo compra+flete/u (MXN pesos)", "Efectivo compra (MXN pesos)", "Estado plan"]
    ws = wb.add_worksheet("STOCK")
    setup_sheet(ws, "STOCK Y ESCENARIO DE COMPRA", input_note + " La propuesta es condicional y nunca crea una orden. El efectivo usa compra + flete de entrada, sin empaque.", f, len(stock_headers) - 1)
    widths = [18, 15, 13, 13, 13, 15, 18, 20, 17, 15, 27, 13, 15, 17, 14, 20, 22, 20, 22]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    add_table(ws, 105, len(stock_headers), stock_headers, "tblStock")
    data = payload["STOCK"]
    for r in range(6, 106):
        row = data[r - 6] if r - 6 < len(data) else {}
        for c, key in enumerate(stock_inputs):
            kind = "input"
            if key in {"count_date", "eta", "payment_date"}: kind = "input_date"
            elif key in {"on_hand", "reserved", "in_transit", "available_days", "planned_qty"}: kind = "input_int"
            write_value(ws, r - 1, c, row.get(key), f[kind], f["input_date"])
        xr = r
        lead = f'INDEX(CATALOGO!$M$6:$M$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        status = f'INDEX(CATALOGO!$F$6:$F$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        purch = f'INDEX(CATALOGO!$H$6:$H$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        freight = f'INDEX(CATALOGO!$I$6:$I$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        moq = f'INDEX(CATALOGO!$N$6:$N$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        pack = f'INDEX(CATALOGO!$O$6:$O$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        cat_quality = f'INDEX(CATALOGO!$T$6:$T$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        cat_margin = f'INDEX(CATALOGO!$R$6:$R$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        commission = f'INDEX(CATALOGO!$K$6:$K$105,MATCH(A{xr},CATALOGO!$A$6:$A$105,0))'
        ws.write_formula(r - 1, 10, f'=IFERROR(IF(A{xr}="","",IF(COUNTIF($A$6:$A$105,A{xr})>1,"DUPLICADO STOCK",IF(COUNTIF(CATALOGO!$A$6:$A$105,A{xr})<>1,"SKU NO VALIDO",IF(OR(CONFIG!$B$5="",CONFIG!$B$6="",CONFIG!$B$7="",CONFIG!$B$8="",CONFIG!$B$6<1,CONFIG!$B$6>365,CONFIG!$B$6<>INT(CONFIG!$B$6),CONFIG!$B$7<0,CONFIG!$B$7>3650,CONFIG!$B$7<>INT(CONFIG!$B$7),CONFIG!$B$8<0,CONFIG!$B$8>=1),"CONFIG INVALIDA",IF({status}<>"ACTIVO",{status},IF(OR(B{xr}="",B{xr}<>CONFIG!$B$5),"CONTEO NO VIGENTE",IF(OR(C{xr}="",D{xr}="",E{xr}="",H{xr}=""),"FALTA CAMPO",IF(OR(C{xr}<0,C{xr}>1000000,D{xr}<0,D{xr}>1000000,E{xr}<0,E{xr}>1000000,D{xr}>C{xr}),"REVISAR VALOR",IF(H{xr}>CONFIG!$B$6,"EXPOSICION FUERA DE RANGO",IF(H{xr}<>CONFIG!$B$6,"DISPONIBILIDAD INCOMPLETA",IF(CONFIG!$B$14<>"SI","VENTAS INCOMPLETAS",IF(CONFIG!$B$12<>"SI","POLITICA SIN REVISAR",IF(SUMPRODUCT(--(VENTAS!$B$6:$B$1005=A{xr}),--(VENTAS!$A$6:$A$1005>=CONFIG!$B$5-CONFIG!$B$6+1),--(VENTAS!$A$6:$A$1005<=CONFIG!$B$5),--(VENTAS!$I$6:$I$1005<>""),--(VENTAS!$I$6:$I$1005<>"OK"))>0,"VENTAS A REVISAR",IF(AND(E{xr}>0,OR(F{xr}="",G{xr}<>"SI")),"TRANSITO SIN CONFIRMAR",IF(AND(E{xr}>0,G{xr}="SI",OR(F{xr}<=CONFIG!$B$5,F{xr}>CONFIG!$B$5+{lead})),"TRANSITO FUERA DEL PLAZO",IF({cat_quality}<>"OK","CATALOGO A REVISAR",IF(1-{commission}-CONFIG!$B$8<=0,"MARGEN OBJETIVO INVIABLE",IF({cat_margin}<CONFIG!$B$8,"REVISAR PRECIO O COSTO","ELEGIBLE")))))))))))))))))),"CONFIG INVALIDA")', f["link"], "")
        ws.write_formula(r - 1, 11, f'=IF(OR(C{xr}="",D{xr}="",C{xr}<0,C{xr}>1000000,D{xr}<0,D{xr}>1000000,D{xr}>C{xr}),"",C{xr}-D{xr})', f["calc_int"], "")
        ws.write_formula(r - 1, 12, f'=IFERROR(IF(OR(A{xr}="",CONFIG!$B$14<>"SI",CONFIG!$B$6<1,CONFIG!$B$6>365,CONFIG!$B$6<>INT(CONFIG!$B$6),SUMPRODUCT(--(VENTAS!$B$6:$B$1005=A{xr}),--(VENTAS!$A$6:$A$1005>=CONFIG!$B$5-CONFIG!$B$6+1),--(VENTAS!$A$6:$A$1005<=CONFIG!$B$5),--(VENTAS!$I$6:$I$1005<>""),--(VENTAS!$I$6:$I$1005<>"OK"))>0),"",MAX(0,(SUMIFS(VENTAS!$C$6:$C$1005,VENTAS!$B$6:$B$1005,A{xr},VENTAS!$A$6:$A$1005,">="&CONFIG!$B$5-CONFIG!$B$6+1,VENTAS!$A$6:$A$1005,"<="&CONFIG!$B$5)-SUMIFS(VENTAS!$E$6:$E$1005,VENTAS!$B$6:$B$1005,A{xr},VENTAS!$A$6:$A$1005,">="&CONFIG!$B$5-CONFIG!$B$6+1,VENTAS!$A$6:$A$1005,"<="&CONFIG!$B$5))/CONFIG!$B$6)),"")', f["link"], "")
        ws.write_formula(r - 1, 13, f'=IF(K{xr}<>"ELEGIBLE","",IF(AND(E{xr}>0,G{xr}="SI",F{xr}>CONFIG!$B$5,F{xr}<=CONFIG!$B$5+{lead}),E{xr},0))', f["link_int"], "")
        ws.write_formula(r - 1, 14, f'=IF(K{xr}<>"ELEGIBLE","",MAX(0,ROUNDUP(ROUND(M{xr}*({lead}+CONFIG!$B$7)-L{xr}-N{xr},10),0)))', f["link_int"], "")
        ws.write_formula(r - 1, 15, f'=IF(O{xr}="","",IF(O{xr}=0,0,ROUNDUP(MAX(O{xr},{moq})/{pack},0)*{pack}))', f["link_int"], "")
        ws.write_formula(r - 1, 16, f'=IFERROR(IF(OR(A{xr}="",COUNTIF(CATALOGO!$A$6:$A$105,A{xr})<>1),"",IF(OR({purch}="",{freight}="",ABS({purch})>1000000000,ABS({freight})>1000000000),"",{purch}+{freight})),"")', f["link_money"], "")
        ws.write_formula(r - 1, 17, f'=IF(OR(A{xr}="",I{xr}="",COUNTIF(CATALOGO!$A$6:$A$105,A{xr})<>1),"",IF(I{xr}=0,0,IF(OR(Q{xr}="",{moq}="",{pack}="",{pack}<=0),"",IF(OR(I{xr}<{moq},MOD(I{xr},{pack})<>0,J{xr}="",J{xr}<=CONFIG!$B$5,J{xr}>CONFIG!$B$5+91),"",I{xr}*Q{xr}))))', f["calc_money"], "")
        ws.write_formula(r - 1, 18, f'=IF(A{xr}="","",IF(COUNTIF(CATALOGO!$A$6:$A$105,A{xr})<>1,"SKU NO VALIDO",IF(I{xr}="","CANTIDAD DESCONOCIDA",IF(I{xr}=0,"SIN COMPRA ELEGIDA",IF(OR(I{xr}<0,I{xr}>1000000),"CANTIDAD INVALIDA",IF(OR({moq}="",{pack}="",{pack}<=0),"CATALOGO A REVISAR",IF(OR(I{xr}<{moq},MOD(I{xr},{pack})<>0),"NO RESPETA MOQ/PACK",IF(J{xr}="","FALTA FECHA PAGO",IF(Q{xr}="","COSTO DESCONOCIDO",IF(OR(J{xr}<=CONFIG!$B$5,J{xr}>CONFIG!$B$5+91),"FUERA DE 91 DIAS",IF(AND(P{xr}<>"",I{xr}>P{xr}),"EN MODELO · SUPERA PROPUESTA","EN MODELO")))))))))))', f["link"], "")
    ws.data_validation("A6:A105", {"validate": "list", "source": "=SKU_LIST"})
    ws.data_validation("B6:B105", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("F6:F105", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("J6:J105", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("C6:E105", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 1000000})
    ws.data_validation("G6:G105", {"validate": "list", "source": yes_no})
    ws.data_validation("H6:H105", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 365})
    ws.data_validation("I6:I105", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 1000000})
    ws.conditional_format("K6:K105", {"type": "text", "criteria": "not containing", "value": "ELEGIBLE", "format": wb.add_format({"bg_color": GOLD_LIGHT, "font_color": RED})})
    ws.conditional_format("S6:S105", {"type": "text", "criteria": "containing", "value": "FALTA", "format": wb.add_format({"bg_color": RED_LIGHT, "font_color": RED})})
    ws.print_area(0, 0, max(20, 5 + len(data)) - 1, len(stock_headers) - 1)
    ws.repeat_rows(0, 4)

    cash_inputs = contract["sheets"]["CAJA"]
    cash_headers = ["Fecha", "Dirección", "Categoría", "Importe (MXN pesos)", "Referencia no personal", "Calidad fila"]
    ws = wb.add_worksheet("CAJA")
    setup_sheet(ws, "PLAN DE CAJA EXISTENTE", input_note + " Captura obligaciones ya planeadas. No dupliques compras elegidas en STOCK.", f, len(cash_headers) - 1)
    widths = [16, 15, 28, 21, 24, 22]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    add_table(ws, 255, len(cash_headers), cash_headers, "tblCaja")
    data = payload["CAJA"]
    for r in range(6, 256):
        row = data[r - 6] if r - 6 < len(data) else {}
        for c, key in enumerate(cash_inputs):
            kind = "input_date" if key == "date" else "input_money" if key == "amount" else "input"
            write_value(ws, r - 1, c, row.get(key), f[kind], f["input_date"])
        xr = r
        ws.write_formula(r - 1, 5, f'=IFERROR(IF(COUNTA(A{xr}:E{xr})=0,"",IF(OR(A{xr}="",B{xr}="",C{xr}="",D{xr}=""),"FALTA CAMPO",IF(AND(B{xr}<>"ENTRADA",B{xr}<>"SALIDA"),"DIRECCION INVALIDA",IF(OR(D{xr}<=0,ABS(D{xr})>1000000000,ROUND(D{xr},2)<>D{xr}),"MONTO INVALIDO",IF(OR(A{xr}<DATE(1900,1,1),A{xr}>DATE(2100,12,31),A{xr}<=CONFIG!$B$5,A{xr}>CONFIG!$B$5+91),"FUERA DE HORIZONTE","OK"))))),"MONTO INVALIDO")', f["link"], "")
    ws.data_validation("B6:B255", {"validate": "list", "source": contract["enums"]["cash_direction"]})
    ws.data_validation("A6:A255", {"validate": "date", "criteria": "between", "minimum": datetime(1900, 1, 1), "maximum": datetime(2100, 12, 31)})
    ws.data_validation("D6:D255", {"validate": "decimal", "criteria": "between", "minimum": 0.01, "maximum": 1000000000})
    ws.conditional_format("F6:F255", {"type": "text", "criteria": "not containing", "value": "OK", "format": wb.add_format({"bg_color": GOLD_LIGHT, "font_color": RED})})
    ws.print_area(0, 0, max(20, 5 + len(data)) - 1, len(cash_headers) - 1)
    ws.repeat_rows(0, 4)

    dec_headers = ["SKU", "Producto", "Estado", "Precio lista (MXN pesos)", "Costo variable/u (MXN pesos)", "Precio objetivo (MXN pesos)", "Margen actual", "Estado evidencia", "Consumo diario", "Disponible", "Tránsito elegible", "Necesidad", "Propuesta condicional", "Cantidad elegida", "Fecha pago", "Efectivo compra (MXN pesos)", "Decisión", "Razón", "Acción siguiente"]
    ws = wb.add_worksheet("DECISIONES")
    setup_sheet(ws, "DECISIONES POR SKU", "Lectura preparada para reunión. Cada cantidad es condicional; la hoja nunca ejecuta ni aprueba una compra. Las métricas de apoyo están en CATALOGO y STOCK.", f, len(dec_headers) - 1)
    widths = [18, 27, 17, 18, 20, 20, 14, 27, 15, 13, 17, 13, 19, 17, 15, 20, 24, 50, 50]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    ws.set_column("C:L", None, None, {"hidden": True, "level": 1})
    ws.set_paper(8)
    add_table(ws, 105, len(dec_headers), dec_headers, "tblDecisiones")
    for r in range(6, 106):
        i = r
        stock_match = f'MATCH(A{i},STOCK!$A$6:$A$105,0)'
        links = [
            f'=IF(CATALOGO!A{i}="","",CATALOGO!A{i})', f'=IF(A{i}="","",CATALOGO!B{i})', f'=IF(A{i}="","",CATALOGO!F{i})',
            f'=IF(A{i}="","",CATALOGO!G{i})', f'=IF(A{i}="","",CATALOGO!P{i})', f'=IF(A{i}="","",CATALOGO!S{i})', f'=IF(A{i}="","",CATALOGO!R{i})',
        ]
        for c, formula in enumerate(links):
            fmt = f["link_money"] if c in {3, 4, 5} else f["link_pct"] if c == 6 else f["link"]
            ws.write_formula(r - 1, c, formula, fmt, "")
        ws.write_formula(r - 1, 7, f'=IF(A{i}="","",IF(COUNTIF(STOCK!$A$6:$A$105,A{i})<>1,"SIN STOCK UNICO",INDEX(STOCK!$K$6:$K$105,{stock_match})))', f["link"], "")
        for c, source_col, fmt in [(8, "M", "link"), (9, "L", "link_int"), (10, "N", "link_int"), (11, "O", "link_int"), (12, "P", "link_int"), (13, "I", "link_int"), (14, "J", "link_date"), (15, "R", "link_money")]:
            value = f'INDEX(STOCK!${source_col}$6:${source_col}$105,{stock_match})'
            ws.write_formula(r - 1, c, f'=IF(OR(A{i}="",COUNTIF(STOCK!$A$6:$A$105,A{i})<>1),"",IF({value}="","",{value}))', f[fmt], "")
        ws.write_formula(r - 1, 16, f'=IF(A{i}="","",IF(C{i}="PRELANZAMIENTO","REVISAR PRELANZAMIENTO",IF(C{i}="PAUSADO","SKU PAUSADO",IF(H{i}<>"ELEGIBLE","EVIDENCIA PENDIENTE",IF(M{i}>0,"PROPUESTA CONDICIONAL","SIN COMPRA SUGERIDA")))))', f["link"], "")
        ws.write_formula(r - 1, 17, f'=IF(A{i}="","",IF(H{i}<>"ELEGIBLE","Se retiene la propuesta: "&H{i}&"."&CHAR(10)&"Blanco significa desconocido; resolver la evidencia antes de decidir.",IF(M{i}=0,"Disponible + tránsito elegible cubren el horizonte de lead + seguridad."&CHAR(10)&"Consumo diario: "&TEXT(I{i},"0.00")&"; disponible: "&TEXT(J{i},"0")&".","Necesidad neta: "&TEXT(L{i},"0")&" unidades."&CHAR(10)&"MOQ y múltiplo elevan la propuesta a "&TEXT(M{i},"0")&" unidades.")))', f["wrap_link"], "")
        ws.write_formula(r - 1, 18, f'=IF(A{i}="","",IF(H{i}<>"ELEGIBLE","Corregir o confirmar la evidencia señalada en STOCK / CONFIG; no comprar con esta hoja todavía.",IF(M{i}=0,"No elegir compra por reposición. Vigilar la siguiente semana y confirmar que la cobertura siga completa.","Revisar la propuesta; no es una orden."&CHAR(10)&"Si se decide comprar, capturar cantidad y fecha de pago en STOCK y revisar el piso de caja.")))', f["wrap_link"], "")
        ws.set_row(r - 1, 42)
    ws.conditional_format("Q6:Q105", {"type": "text", "criteria": "containing", "value": "EVIDENCIA", "format": wb.add_format({"bg_color": GOLD_LIGHT, "font_color": RED})})
    chart = wb.add_chart({"type": "column"})
    chart.add_series({"name": "Propuesta condicional", "categories": "=DECISIONES!$A$6:$A$15", "values": "=DECISIONES!$M$6:$M$15", "fill": {"color": TEAL}})
    chart.add_series({"name": "Cantidad elegida", "categories": "=DECISIONES!$A$6:$A$15", "values": "=DECISIONES!$N$6:$N$15", "fill": {"color": GOLD}})
    chart.set_title({"name": "Primeros 10 SKU · propuesta vs elección"})
    chart.set_y_axis({"name": "Unidades", "major_gridlines": {"visible": False}})
    chart.set_legend({"position": "bottom"})
    chart.set_style(10)
    ws.insert_chart("U5", chart, {"x_scale": 1.35, "y_scale": 1.05})
    print_end = max(20, 5 + len(payload["CATALOGO"]))
    ws.print_area(0, 0, print_end - 1, len(dec_headers) - 1)
    ws.repeat_rows(0, 4)

    aux = wb.add_worksheet("AUX_CALC_91D")
    setup_sheet(aux, "CÁLCULO DIARIO · 91 DÍAS", "Soporte protegido del modelo semanal. Conserva cierres diarios para detectar pagos anteriores a cobros dentro de una misma semana.", f, 5)
    aux_headers = ["Fecha", "Entradas base (MXN pesos)", "Salidas base (MXN pesos)", "Cierre base (MXN pesos)", "Compras elegidas (MXN pesos)", "Cierre con plan (MXN pesos)"]
    add_table(aux, 96, len(aux_headers), aux_headers, "tblAux91")
    for c, width in enumerate([15, 20, 20, 20, 22, 22]): aux.set_column(c, c, width)
    purchase_plan_unknown_raw = 'OR(CONFIG!$B$5="",COUNT(CONFIG!$B$6:$B$8)<3,CONFIG!$B$6<1,CONFIG!$B$6>365,CONFIG!$B$6<>INT(CONFIG!$B$6),CONFIG!$B$7<0,CONFIG!$B$7>3650,CONFIG!$B$7<>INT(CONFIG!$B$7),CONFIG!$B$8<0,CONFIG!$B$8>=1,COUNTIF(CATALOGO!$A$6:$A$105,"<>")=0,SUMPRODUCT(--(CATALOGO!$A$6:$A$105<>""),--(COUNTIF(CATALOGO!$A$6:$A$105,CATALOGO!$A$6:$A$105)<>1))>0,SUMPRODUCT(--(CATALOGO!$A$6:$A$105<>""),--(COUNTIF(STOCK!$A$6:$A$105,CATALOGO!$A$6:$A$105)<>1))>0,SUMPRODUCT(--(STOCK!$A$6:$A$105<>""),--(COUNTIF(CATALOGO!$A$6:$A$105,STOCK!$A$6:$A$105)<>1))>0,SUMPRODUCT(--(CATALOGO!$A$6:$A$105<>""),--(CATALOGO!$T$6:$T$105<>"OK"))>0,COUNTIF(STOCK!$S$6:$S$105,"SIN COMPRA ELEGIDA")+COUNTIF(STOCK!$S$6:$S$105,"EN MODELO*")<>COUNTIF(CATALOGO!$A$6:$A$105,"<>"),SUMPRODUCT(--(STOCK!$A$6:$A$105<>""),--(STOCK!$C$6:$C$105<>""),--(STOCK!$D$6:$D$105<>""),--(STOCK!$D$6:$D$105>STOCK!$C$6:$C$105))>0,SUMPRODUCT(--(VENTAS!$I$6:$I$1005<>""),--(VENTAS!$I$6:$I$1005<>"OK"))>0)'
    plan_unknown_raw = f'OR({purchase_plan_unknown_raw},COUNT(CONFIG!$B$9:$B$11)<3,ABS(CONFIG!$B$9)>1000000000,CONFIG!$B$10<0,CONFIG!$B$11<0,ABS(CONFIG!$B$10)>1000000000,ABS(CONFIG!$B$11)>1000000000,ROUND(CONFIG!$B$9,2)<>CONFIG!$B$9,ROUND(CONFIG!$B$10,2)<>CONFIG!$B$10,ROUND(CONFIG!$B$11,2)<>CONFIG!$B$11)'
    aux.write("H2", "Estado plan global", f["summary_label"])
    aux.write_formula("H3", f'=IFERROR(IF({plan_unknown_raw},"PENDIENTE","OK"),"PENDIENTE")', f["summary_text"], "PENDIENTE")
    aux.write_formula("H4", f'=IFERROR(IF({purchase_plan_unknown_raw},"PENDIENTE","OK"),"PENDIENTE")', f["summary_text"], "PENDIENTE")
    aux.set_column("H:H", 22, None, {"hidden": True})
    plan_unknown = 'AUX_CALC_91D!$H$3<>"OK"'
    purchase_plan_unknown = 'AUX_CALC_91D!$H$4<>"OK"'
    for r in range(6, 97):
        day = r - 5
        aux.write_formula(r - 1, 0, f'=IF(CONFIG!$B$5="","",CONFIG!$B$5+{day})', f["link_date"], "")
        aux.write_formula(r - 1, 1, f'=IF(A{r}="","",SUMIFS(CAJA!$D$6:$D$255,CAJA!$B$6:$B$255,"ENTRADA",CAJA!$A$6:$A$255,A{r},CAJA!$F$6:$F$255,"OK"))', f["link_money"], 0)
        aux.write_formula(r - 1, 2, f'=IF(A{r}="","",SUMIFS(CAJA!$D$6:$D$255,CAJA!$B$6:$B$255,"SALIDA",CAJA!$A$6:$A$255,A{r},CAJA!$F$6:$F$255,"OK"))', f["link_money"], 0)
        base_open = "CONFIG!$B$9" if r == 6 else f"D{r-1}"
        aux.write_formula(r - 1, 3, f'=IFERROR(IF(OR({base_open}="",A{r}=""),"",{base_open}+B{r}-C{r}),"")', f["link_money"], "")
        aux.write_formula(r - 1, 4, f'=IF(OR(A{r}="",{plan_unknown}),"",SUMIFS(STOCK!$R$6:$R$105,STOCK!$J$6:$J$105,A{r}))', f["link_money"], "")
        plan_open = "CONFIG!$B$9" if r == 6 else f"F{r-1}"
        aux.write_formula(r - 1, 5, f'=IFERROR(IF(OR({plan_open}="",A{r}="",E{r}=""),"",{plan_open}+B{r}-C{r}-E{r}),"")', f["link_money"], "")
    aux.print_area("A1:F96")
    aux.repeat_rows(0, 4)
    aux.hide()

    flow_headers = ["Semana", "Desde", "Hasta", "Entradas base (MXN pesos)", "Salidas base (MXN pesos)", "Cierre base (MXN pesos)", "Compras elegidas (MXN pesos)", "Cierre con plan (MXN pesos)", "Mínimo diario base (MXN pesos)", "Mínimo diario con plan (MXN pesos)", "Piso (MXN pesos)", "Estado"]
    ws = wb.add_worksheet("FLUJO_13_SEMANAS")
    setup_sheet(ws, "FLUJO DE CAJA · 13 SEMANAS", "Cierres semanales desde el día posterior al corte. El momento dentro de cada semana puede producir un saldo menor.", f, 15)
    widths = [10, 15, 15, 20, 20, 20, 22, 22, 22, 24, 18, 24]
    for idx, width in enumerate(widths): ws.set_column(idx, idx, width)
    ws.set_column("M:M", 32)
    ws.set_column("N:N", 25)
    add_table(ws, 18, len(flow_headers), flow_headers, "tblFlujo13")
    for r in range(6, 19):
        week = r - 5
        ws.write_number(r - 1, 0, week, f["calc_int"])
        ws.write_formula(r - 1, 1, f'=IF(CONFIG!$B$5="","",CONFIG!$B$5+{(week - 1) * 7 + 1})', f["link_date"], "")
        ws.write_formula(r - 1, 2, f'=IF(B{r}="","",B{r}+6)', f["calc"] , "")
        a0 = 6 + (week - 1) * 7
        a1 = a0 + 6
        ws.write_formula(r - 1, 3, f'=IF(B{r}="","",SUM(AUX_CALC_91D!B{a0}:B{a1}))', f["link_money"], 0)
        ws.write_formula(r - 1, 4, f'=IF(B{r}="","",SUM(AUX_CALC_91D!C{a0}:C{a1}))', f["link_money"], 0)
        ws.write_formula(r - 1, 5, f'=IF(B{r}="","",AUX_CALC_91D!D{a1})', f["link_money"], "")
        ws.write_formula(r - 1, 6, f'=IF(COUNT(AUX_CALC_91D!E{a0}:E{a1})<7,"",SUM(AUX_CALC_91D!E{a0}:E{a1}))', f["link_money"], "")
        ws.write_formula(r - 1, 7, f'=IF(B{r}="","",AUX_CALC_91D!F{a1})', f["link_money"], "")
        ws.write_formula(r - 1, 8, f'=IF(COUNT(AUX_CALC_91D!D{a0}:D{a1})<7,"",MIN(AUX_CALC_91D!D{a0}:D{a1}))', f["link_money"], "")
        ws.write_formula(r - 1, 9, f'=IF(COUNT(AUX_CALC_91D!F{a0}:F{a1})<7,"",MIN(AUX_CALC_91D!F{a0}:F{a1}))', f["link_money"], "")
        ws.write_formula(r - 1, 10, '=IF(CONFIG!$B$10="","",CONFIG!$B$10)', f["link_money"], "")
        ws.write_formula(r - 1, 11, f'=IF(J{r}="","SIN BASE",IF(CONFIG!$B$13<>"SI","PLAN CAJA INCOMPLETO",IF(J{r}<K{r},"BRECHA PISO","SOBRE PISO")))', f["link"], "")
    ws.write("M3", "Lectura del plan", f["summary_label"])
    ws.write_formula("N3", f'=IFERROR(IF(OR(CONFIG!$B$13<>"SI",COUNT(CONFIG!$B$9:$B$11)<3),"PLAN CAJA INCOMPLETO",IF(OR(CONFIG!$B$10<0,CONFIG!$B$11<0,ABS(CONFIG!$B$9)>1000000000,ABS(CONFIG!$B$10)>1000000000,ABS(CONFIG!$B$11)>1000000000,ROUND(CONFIG!$B$9,2)<>CONFIG!$B$9,ROUND(CONFIG!$B$10,2)<>CONFIG!$B$10,ROUND(CONFIG!$B$11,2)<>CONFIG!$B$11),"CONFIG INVALIDA",IF(SUMPRODUCT(--(CAJA!$F$6:$F$255<>""),--(CAJA!$F$6:$F$255<>"OK"))>0,"REVISAR CAJA",IF({plan_unknown},"PLAN DE COMPRA PENDIENTE",IF(N6>CONFIG!$B$11,"EXCEDE TOPE DE COMPRA",IF(MIN(CONFIG!$B$9,MIN(AUX_CALC_91D!$F$6:$F$96))<CONFIG!$B$10,"BRECHA DE PISO","PLAN SOBRE PISO")))))),"CONFIG INVALIDA")', f["summary_text"], "")
    ws.write("M4", "Mínimo diario base (incluye apertura)", f["summary_label"])
    ws.write_formula("N4", '=IF(COUNT(AUX_CALC_91D!$D$6:$D$96)<91,"",MIN(CONFIG!$B$9,MIN(AUX_CALC_91D!$D$6:$D$96)))', f["summary_value"], "")
    ws.write("M5", "Presupuesto disponible antes de propuestas", f["summary_label"])
    ws.write_formula("N5", '=IFERROR(IF(OR(CONFIG!$B$13<>"SI",COUNT(CONFIG!$B$9:$B$11)<3,CONFIG!$B$10<0,CONFIG!$B$11<0,ABS(CONFIG!$B$9)>1000000000,ABS(CONFIG!$B$10)>1000000000,ABS(CONFIG!$B$11)>1000000000,ROUND(CONFIG!$B$9,2)<>CONFIG!$B$9,ROUND(CONFIG!$B$10,2)<>CONFIG!$B$10,ROUND(CONFIG!$B$11,2)<>CONFIG!$B$11,SUMPRODUCT(--(CAJA!$F$6:$F$255<>""),--(CAJA!$F$6:$F$255<>"OK"))>0),"",MAX(0,MIN(CONFIG!$B$11,N4-CONFIG!$B$10))),"")', f["summary_value"], "")
    ws.write("M6", "Compras elegidas en 91 días", f["summary_label"])
    ws.write_formula("N6", f'=IF({purchase_plan_unknown},"",SUMIFS(STOCK!$R$6:$R$105,STOCK!$S$6:$S$105,"EN MODELO*"))', f["summary_value"], "")
    ws.write("M7", "Holgura vs presupuesto", f["summary_label"])
    ws.write_formula("N7", '=IF(OR(N5="",N6=""),"",N5-N6)', f["summary_value"], "")
    ws.write("M8", "Mínimo cierre con plan", f["summary_label"])
    ws.write_formula("N8", '=IF(COUNT(AUX_CALC_91D!$F$6:$F$96)<91,"",MIN(CONFIG!$B$9,MIN(AUX_CALC_91D!$F$6:$F$96)))', f["summary_value"], "")
    ws.merge_range("M10:N12", "Presupuesto = máximo de cero entre el menor del tope y el mínimo cierre diario base (incluida caja inicial) menos el piso. Se retiene si el plan de caja o sus filas están incompletos. La fecha ordena entradas y salidas sólo al cierre diario; el movimiento intradía sigue sin observarse.", f["notice"])
    ws.conditional_format("L6:L18", {"type": "text", "criteria": "containing", "value": "BRECHA", "format": wb.add_format({"bg_color": RED_LIGHT, "font_color": RED})})
    chart = wb.add_chart({"type": "line"})
    chart.add_series({"name": "Cierre base", "categories": "=FLUJO_13_SEMANAS!$A$6:$A$18", "values": "=FLUJO_13_SEMANAS!$F$6:$F$18", "line": {"color": TEAL, "width": 2.25}})
    chart.add_series({"name": "Cierre con plan", "categories": "=FLUJO_13_SEMANAS!$A$6:$A$18", "values": "=FLUJO_13_SEMANAS!$H$6:$H$18", "line": {"color": GOLD, "width": 2.25}})
    chart.add_series({"name": "Piso", "categories": "=FLUJO_13_SEMANAS!$A$6:$A$18", "values": "=FLUJO_13_SEMANAS!$K$6:$K$18", "line": {"color": RED, "dash_type": "dash"}})
    chart.set_title({"name": "Caja semanal · MXN pesos"})
    chart.set_x_axis({"name": "Semana"})
    chart.set_y_axis({"name": "MXN pesos", "num_format": "$#,##0", "major_gridlines": {"visible": True, "line": {"color": "#E5E1DA"}}})
    chart.set_legend({"position": "bottom"})
    chart.set_style(10)
    ws.insert_chart("M14", chart, {"x_scale": 1.2, "y_scale": 1.0})
    ws.print_area("A1:N31")
    ws.repeat_rows(0, 4)

    wb.close()


def json_ready(payload: dict) -> dict:
    return json.loads(json.dumps(payload, default=iso, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Construye el kit Excel de cliente Alma de Lujo v0.3.")
    parser.add_argument("--output", type=Path, default=ROOT / "client", help="Directorio de salida (predeterminado: client).")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    example = example_payload(contract)
    template = template_payload(contract)
    build_workbook(args.output / "Alma_de_Lujo_EJEMPLO.xlsx", example, contract)
    build_workbook(args.output / "Alma_de_Lujo_PLANTILLA.xlsx", template, contract)
    (args.output / "example-input.json").write_text(json.dumps(json_ready(example), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "ok", "output": str(args.output), "files": ["Alma_de_Lujo_EJEMPLO.xlsx", "Alma_de_Lujo_PLANTILLA.xlsx", "example-input.json"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
