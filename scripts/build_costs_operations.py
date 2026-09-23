"""Build a transparent synthetic costs-and-operations vertical slice.

This is a deterministic analytical module. It never approves costs, places a
purchase, moves money, changes prices, or turns scenarios into business facts.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from html import escape
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'client' / 'operating-data'
AS_OF = date(2026, 9, 21)

TABLES = {
    'cost_versions': [
        dict(cost_version_id='CV-PIL-NEGRO-1', sku='PIL-NEGRO', effective_date='2026-09-01', lifecycle='approved', quantity_basis=100, public_price_cents=29900, selling_fee_bps=800, tax_basis='PENDIENTE', source_ref='SYN-COST-01', synthetic=1),
        dict(cost_version_id='CV-PIL-LILA-1', sku='PIL-LILA', effective_date='2026-09-01', lifecycle='draft', quantity_basis=100, public_price_cents=29900, selling_fee_bps=800, tax_basis='PENDIENTE', source_ref='SYN-COST-02', synthetic=1),
        dict(cost_version_id='CV-TOP-NEGRO-S-1', sku='TOP-NEGRO-S', effective_date='2026-09-01', lifecycle='approved', quantity_basis=20, public_price_cents=89900, selling_fee_bps=800, tax_basis='PENDIENTE', source_ref='SYN-COST-03', synthetic=1),
    ],
    'cost_components': [
        dict(component_id='CC-001', cost_version_id='CV-PIL-NEGRO-1', component='COMPRA_PROVEEDOR', classification='INVENTARIO', amount_cents=820000, required=1, quality='documented', included_in_component_id='', source_ref='SYN-DOC-01', synthetic=1),
        dict(component_id='CC-002', cost_version_id='CV-PIL-NEGRO-1', component='FLETE_ENTRADA', classification='INVENTARIO', amount_cents=80000, required=1, quality='documented', included_in_component_id='', source_ref='SYN-DOC-02', synthetic=1),
        dict(component_id='CC-003', cost_version_id='CV-PIL-NEGRO-1', component='EMPAQUE_PRODUCTO', classification='VARIABLE_VENTA', amount_cents=90000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-01', synthetic=1),
        dict(component_id='CC-004', cost_version_id='CV-PIL-NEGRO-1', component='OTRO_VARIABLE', classification='VARIABLE_VENTA', amount_cents=50000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-02', synthetic=1),
        dict(component_id='CC-005', cost_version_id='CV-PIL-LILA-1', component='COMPRA_PROVEEDOR', classification='INVENTARIO', amount_cents='', required=1, quality='missing', included_in_component_id='', source_ref='', synthetic=1),
        dict(component_id='CC-006', cost_version_id='CV-PIL-LILA-1', component='FLETE_ENTRADA', classification='INVENTARIO', amount_cents=80000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-03', synthetic=1),
        dict(component_id='CC-007', cost_version_id='CV-PIL-LILA-1', component='EMPAQUE_PRODUCTO', classification='VARIABLE_VENTA', amount_cents=90000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-04', synthetic=1),
        dict(component_id='CC-008', cost_version_id='CV-PIL-LILA-1', component='OTRO_VARIABLE', classification='VARIABLE_VENTA', amount_cents=50000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-05', synthetic=1),
        dict(component_id='CC-009', cost_version_id='CV-TOP-NEGRO-S-1', component='COMPRA_PROVEEDOR', classification='INVENTARIO', amount_cents=660000, required=1, quality='documented', included_in_component_id='', source_ref='SYN-DOC-03', synthetic=1),
        dict(component_id='CC-010', cost_version_id='CV-TOP-NEGRO-S-1', component='FLETE_ENTRADA', classification='INVENTARIO', amount_cents=40000, required=1, quality='documented', included_in_component_id='', source_ref='SYN-DOC-04', synthetic=1),
        dict(component_id='CC-011', cost_version_id='CV-TOP-NEGRO-S-1', component='EMPAQUE_PRODUCTO', classification='VARIABLE_VENTA', amount_cents=36000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-06', synthetic=1),
        dict(component_id='CC-012', cost_version_id='CV-TOP-NEGRO-S-1', component='OTRO_VARIABLE', classification='VARIABLE_VENTA', amount_cents=24000, required=1, quality='estimate', included_in_component_id='', source_ref='SYN-EST-07', synthetic=1),
    ],
    'cost_allocations': [
        dict(allocation_id='CA-001', component_id='CC-002', sku='PIL-NEGRO', method='units', allocated_cents=80000, remainder_cents=0, source_ref='SYN-ALLOC-01', synthetic=1),
        dict(allocation_id='CA-002', component_id='CC-010', sku='TOP-NEGRO-S', method='units', allocated_cents=40000, remainder_cents=0, source_ref='SYN-ALLOC-02', synthetic=1),
    ],
    'purchase_orders_ops': [
        dict(purchase_order_id='PO-OPS-001', supplier_ref='SUP-SYN-01', sku='PIL-NEGRO', ordered_qty=20, agreed_unit_cents=9000, order_date='2026-09-10', promised_date='2026-09-18', commercial_status='AUTHORIZED_SYNTHETIC', source_ref='SYN-PO-01', synthetic=1),
        dict(purchase_order_id='PO-OPS-002', supplier_ref='SUP-SYN-02', sku='TOP-NEGRO-S', ordered_qty=12, agreed_unit_cents=35000, order_date='2026-09-18', promised_date='2026-10-10', commercial_status='PROPOSED_SCENARIO', source_ref='SYN-PO-02', synthetic=1),
    ],
    'purchase_receipts_ops': [
        dict(receipt_id='RCV-OPS-001', purchase_order_id='PO-OPS-001', received_date='2026-09-18', received_qty=18, inspection_qty=2, accepted_qty=16, rejected_qty=0, preparation_status='PARTIAL_INSPECTION', source_ref='SYN-RCV-01', synthetic=1),
    ],
    'obligations': [
        dict(obligation_id='OBL-001', origin_type='PURCHASE_ORDER', origin_id='PO-OPS-001', concept='Compra sintética calcetín negro', due_date='2026-09-28', original_cents=180000, currency='MXN', status='OPEN', source_ref='SYN-OBL-01', synthetic=1),
        dict(obligation_id='OBL-002', origin_type='FIXED_EXPENSE', origin_id='SYN-RENT-01', concept='Renta sintética de ejemplo', due_date='2026-10-01', original_cents=160000, currency='MXN', status='OPEN', source_ref='SYN-OBL-02', synthetic=1),
    ],
    'obligation_payments': [
        dict(obligation_payment_id='OPAY-001', obligation_id='OBL-001', paid_date='2026-09-15', amount_cents=100000, source_ref='SYN-PAY-01', synthetic=1),
    ],
    'cash_scenario_events': [
        dict(scenario_id='BASE', event_id='CE-000', event_date='2026-09-22', level='ASSUMPTION_UNRECONCILED', direction='OPENING', amount_cents=8000000, concept='Saldo inicial sintético; no conciliado con banco', source_ref='SYN-OPENING-01', synthetic=1),
        dict(scenario_id='BASE', event_id='CE-001', event_date='2026-09-22', level='EXPECTED', direction='IN', amount_cents=1500000, concept='Cobros agregados sintéticos', source_ref='SYN-CASH-01', synthetic=1),
        dict(scenario_id='BASE', event_id='CE-002', event_date='2026-09-28', level='COMMITTED', direction='OUT', amount_cents=80000, concept='Saldo obligación OBL-001', source_ref='OBL-001', synthetic=1),
        dict(scenario_id='BASE', event_id='CE-003', event_date='2026-10-01', level='COMMITTED', direction='OUT', amount_cents=160000, concept='Obligación OBL-002', source_ref='OBL-002', synthetic=1),
        dict(scenario_id='REINVESTIR_TOP', event_id='CE-004', event_date='2026-10-05', level='SCENARIO', direction='OUT', amount_cents=420000, concept='Compra propuesta; no autorizada', source_ref='PO-OPS-002', synthetic=1),
    ],
}

CONTRACT = {
    'cost_versions': ('one version of management cost per SKU/effective date', 'cost_version_id'),
    'cost_components': ('one cost component within a cost version', 'component_id'),
    'cost_allocations': ('one allocation of a shared cost component', 'allocation_id'),
    'purchase_orders_ops': ('one internal purchase intent per supplier and SKU', 'purchase_order_id'),
    'purchase_receipts_ops': ('one physical receipt event for a purchase order', 'receipt_id'),
    'obligations': ('one economic obligation, never an invoice/payment duplicate', 'obligation_id'),
    'obligation_payments': ('one observed payment applied to an obligation', 'obligation_payment_id'),
    'cash_scenario_events': ('one dated cash fact/expectation/scenario event', 'scenario_id + event_id'),
}


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def evidence_ref(relative_path):
    relative_path = relative_path.replace('\\', '/')
    path = ROOT / relative_path
    return {'path': relative_path, 'sha256': sha256(path.read_bytes()).hexdigest()}


def calculate():
    versions={r['cost_version_id']:r for r in TABLES['cost_versions']}
    by_version=defaultdict(list)
    for row in TABLES['cost_components']:by_version[row['cost_version_id']].append(row)
    costs=[]
    for version_id,version in versions.items():
        components=by_version[version_id]
        known=sum(r['amount_cents'] for r in components if isinstance(r['amount_cents'],int) and not r['included_in_component_id'])
        missing=[r['component'] for r in components if r['required'] and r['quality']=='missing']
        documented=all(r['quality']=='documented' for r in components if r['required'])
        complete=not missing
        unit=known//version['quantity_basis'] if complete and known%version['quantity_basis']==0 else None
        price=version['public_price_cents'];fee=(price*version['selling_fee_bps']+9999)//10000
        margin=None if unit is None or not price else (Decimal(price-fee-unit)/Decimal(price)).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
        markup=None if unit in (None,0) else (Decimal(price-fee-unit)/Decimal(unit)).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
        costs.append(dict(cost_version_id=version_id,sku=version['sku'],status='COMPLETE_DOCUMENTED' if documented else 'COMPLETE_ESTIMATED' if complete else 'PARTIAL',known_total_cents=known,missing_components=missing,unit_management_cost_cents=unit,public_price_cents=price,selling_fee_unit_cents=fee,contribution_before_fixed_unit_cents=None if unit is None else price-fee-unit,contribution_margin=margin,markup_on_cost=markup,tax_basis=version['tax_basis'],price_changed=False,decision='REVIEW_COST_SOURCE' if not documented else 'AVAILABLE_FOR_MANAGEMENT_REVIEW'))
    allocations=[]
    components={r['component_id']:r for r in TABLES['cost_components']}
    by_component=defaultdict(list)
    for row in TABLES['cost_allocations']:by_component[row['component_id']].append(row)
    for component_id,rows in by_component.items():
        source=components[component_id];allocated=sum(r['allocated_cents'] for r in rows);remainder=max(r['remainder_cents'] for r in rows)
        allocations.append(dict(component_id=component_id,source_cents=source['amount_cents'],allocated_cents=allocated,remainder_cents=remainder,reconciles=isinstance(source['amount_cents'],int) and allocated+remainder==source['amount_cents'],method=rows[0]['method']))
    receipts=defaultdict(lambda:dict(received=0,inspection=0,accepted=0,rejected=0))
    for row in TABLES['purchase_receipts_ops']:
        r=receipts[row['purchase_order_id']]
        for key in r:r[key]+=row[key+'_qty']
    purchase=[]
    for po in TABLES['purchase_orders_ops']:
        r=receipts[po['purchase_order_id']]
        purchase.append(dict(purchase_order_id=po['purchase_order_id'],sku=po['sku'],ordered_qty=po['ordered_qty'],received_qty=r['received'],accepted_qty=r['accepted'],inspection_qty=r['inspection'],rejected_qty=r['rejected'],still_to_receive_qty=po['ordered_qty']-r['received'],available_from_receipt_qty=r['accepted'],cash_commitment_cents=po['ordered_qty']*po['agreed_unit_cents'],commercial_status=po['commercial_status'],decision='REVIEW_RECEIPT_DISCREPANCY' if r['received'] and r['received']<po['ordered_qty'] else 'PENDING_RECEIPT' if not r['received'] else 'RECEIPT_COMPLETE'))
    paid=defaultdict(int)
    for row in TABLES['obligation_payments']:paid[row['obligation_id']]+=row['amount_cents']
    obligations=[]
    for row in TABLES['obligations']:
        balance=row['original_cents']-paid[row['obligation_id']]
        obligations.append(dict(obligation_id=row['obligation_id'],origin_type=row['origin_type'],origin_id=row['origin_id'],due_date=row['due_date'],original_cents=row['original_cents'],paid_cents=paid[row['obligation_id']],outstanding_cents=balance,status='PAID' if balance==0 else 'OPEN',decision='SCHEDULE_PAYMENT_REVIEW' if balance else 'CLOSED'))
    cash=[]
    opening_rows=[r for r in TABLES['cash_scenario_events'] if r['direction']=='OPENING']
    if len(opening_rows) != 1: raise ValueError('Cash scenarios require exactly one sourced opening assumption.')
    opening=opening_rows[0]['amount_cents']
    for scenario in ('BASE','REINVESTIR_TOP'):
        balance=opening;minimum=opening;weeks=[]
        relevant=[r for r in TABLES['cash_scenario_events'] if r['scenario_id'] in ('BASE',scenario)]
        for week in range(8):
            start=AS_OF+timedelta(days=week*7+1);end=start+timedelta(days=6)
            incoming=sum(r['amount_cents'] for r in relevant if start<=date.fromisoformat(r['event_date'])<=end and r['direction']=='IN')
            outgoing=sum(r['amount_cents'] for r in relevant if start<=date.fromisoformat(r['event_date'])<=end and r['direction']=='OUT')
            balance+=incoming-outgoing;minimum=min(minimum,balance)
            weeks.append(dict(week=week+1,start=start.isoformat(),end=end.isoformat(),in_cents=incoming,out_cents=outgoing,closing_cents=balance))
        cash.append(dict(scenario_id=scenario,opening_cents=opening,opening_level=opening_rows[0]['level'],opening_status=opening_rows[0]['level'],opening_source_ref=opening_rows[0]['source_ref'],minimum_weekly_closing_cents=minimum,closing_cents=balance,level='ASSUMED_OPENING_PLUS_EXPECTED_AND_COMMITTED' if scenario=='BASE' else 'ASSUMED_OPENING_INCLUDES_UNAPPROVED_SCENARIO',weeks=weeks,decision='COMPARE_ONLY_NO_EXECUTION'))
    return dict(cost_metrics=costs,allocation_controls=allocations,purchase_metrics=purchase,obligation_metrics=obligations,cash_scenarios=cash)


def money(cents):return 'PENDIENTE' if cents is None else f'${cents/100:,.2f}'


def percent(value):
    return 'PENDIENTE' if value is None else f'{value:.2%}'


def render(manifest):
    metrics=manifest['metrics'];sources=manifest['sources']
    cost_rows=''.join(f"<tr><td>{escape(r['sku'])}</td><td>{escape(r['status'])}</td><td>{money(r['known_total_cents'])}</td><td>{money(r['unit_management_cost_cents'])}</td><td>{money(r['public_price_cents'])}</td><td>{percent(r['contribution_margin'])}</td><td>{percent(r['markup_on_cost'])}</td><td>{escape(', '.join(r['missing_components']) or r['decision'])}</td></tr>" for r in metrics['cost_metrics'])
    source_rows=''.join(f"<tr><td><a href='operating-data/{escape(r['file'])}'>{escape(r['name'])}</a></td><td>{escape(r['grain'])}</td><td>{escape(r['primary_key'])}</td><td>{r['rows']}</td><td>{escape(r['purpose'])}</td></tr>" for r in sources)
    purchase_rows=''.join(f"<tr><td>{r['purchase_order_id']}</td><td>{r['sku']}</td><td>{r['ordered_qty']}</td><td>{r['received_qty']}</td><td>{r['inspection_qty']}</td><td>{r['accepted_qty']}</td><td>{r['still_to_receive_qty']}</td><td>{money(r['cash_commitment_cents'])}</td><td>{r['decision']}</td></tr>" for r in metrics['purchase_metrics'])
    obligation_rows=''.join(f"<tr><td>{r['obligation_id']}</td><td>{r['origin_type']}</td><td>{money(r['original_cents'])}</td><td>{money(r['paid_cents'])}</td><td>{money(r['outstanding_cents'])}</td><td>{r['due_date']}</td><td>{r['decision']}</td></tr>" for r in metrics['obligation_metrics'])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alma OS · Costos y operación</title><style>
body{{margin:0;background:#f5f1e8;color:#183a32;font:16px/1.55 Arial,sans-serif}}main{{max-width:1250px;margin:auto;padding:44px 26px}}h1{{font:52px Georgia,serif;max-width:900px}}h2{{font:30px Georgia,serif;margin-top:48px}}.hero,.note{{padding:24px;background:#173b33;color:white}}.note{{background:#e6eddc;color:#183a32;border-left:5px solid #bd8c38}}table{{border-collapse:collapse;width:100%;background:white;font-size:13px}}th,td{{padding:11px;border-bottom:1px solid #d7ded7;text-align:left;vertical-align:top}}th{{background:#173b33;color:white;position:sticky;top:0}}.scroll{{overflow:auto}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{background:white;padding:18px;border:1px solid #d8ddd7}}code{{background:#e8eee8;padding:2px 5px}}a{{color:#155d56}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}h1{{font-size:38px}}}}@media print{{body{{background:white}}main{{padding:0}}tr,.card{{break-inside:avoid}}}}
</style></head><body><main><section class="hero"><div>ALMA OS / MÓDULO ANALÍTICO v0.3</div><h1>Del costo documentado a una decisión que conserva caja.</h1><p>Datos 100% sintéticos. Este módulo muestra el recorrido; no aprueba costos, compras, pagos ni precios.</p></section>
<p class="note"><strong>Estado real:</strong> bloque vertical local y verificable. No es la aplicación React/Supabase descrita en la adenda candidata; tampoco es contabilidad fiscal. Los campos pendientes permanecen pendientes.</p>
<h2>1. Las tablas fuente están visibles</h2><div class="scroll"><table><thead><tr><th>Tabla/CSV</th><th>Grano</th><th>Clave</th><th>Filas</th><th>Decisión que alimenta</th></tr></thead><tbody>{source_rows}</tbody></table></div>
<h2>2. Costo, margen y ganancia sobre costo son distintos</h2><p>Contribución antes de fijos = precio − comisión aplicable − costo unitario completo. El margen divide entre precio; la ganancia sobre costo divide entre costo. Si falta un componente, ambos quedan pendientes.</p><div class="scroll"><table><thead><tr><th>SKU</th><th>Cobertura</th><th>Suma conocida lote</th><th>Costo unitario</th><th>Precio</th><th>Margen contribución</th><th>Ganancia/costo</th><th>Qué revisar</th></tr></thead><tbody>{cost_rows}</tbody></table></div>
<h2>3. Compra, recepción y disponibilidad no son el mismo hecho</h2><div class="scroll"><table><thead><tr><th>Compra</th><th>SKU</th><th>Pedidas</th><th>Recibidas</th><th>En inspección</th><th>Aceptadas</th><th>Por recibir</th><th>Compromiso</th><th>Decisión</th></tr></thead><tbody>{purchase_rows}</tbody></table></div>
<h2>4. Una obligación se paga una vez</h2><div class="scroll"><table><thead><tr><th>Obligación</th><th>Origen</th><th>Original</th><th>Pagado</th><th>Pendiente</th><th>Vence</th><th>Acción</th></tr></thead><tbody>{obligation_rows}</tbody></table></div>
<h2>5. Caja base y reinversión son escenarios separados</h2><div class="grid">{''.join(f"<div class='card'><strong>{s['scenario_id']}</strong><p>Apertura {money(s['opening_cents'])}<br>Mínimo semanal {money(s['minimum_weekly_closing_cents'])}<br>Cierre 8 semanas {money(s['closing_cents'])}</p><small>{s['level']} · {s['decision']}</small></div>" for s in metrics['cash_scenarios'])}</div>
<h2>Controles que sostienen la lectura</h2><div class="grid"><div class="card"><strong>Costos parciales</strong><p>Suma conocida visible, total y margen pendientes. Cero no sustituye lo desconocido.</p></div><div class="card"><strong>Asignaciones</strong><p>El monto asignado más remanente reconcilia con la partida fuente; no se duplica.</p></div><div class="card"><strong>Autoridad</strong><p>Todo resultado termina en revisión. Ninguna salida ejecuta una decisión externa.</p></div></div>
<p><a href="SISTEMA_ANALITICO.html">Abrir mapa completo de fuentes, métricas, procesos y agentes</a> · <a href="FUENTES_METRICAS_AGENTES.md">Leer recorrido técnico en lenguaje cliente</a> · <a href="GUIA_SEMANAL.html">Abrir guía semanal</a></p></main></body></html>'''


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,rows in TABLES.items():write_csv(OUT/(name+'.csv'),rows)
    metrics=calculate()
    sources=[]
    purposes={
      'cost_versions':'precio y versión de costo vigente sin reescribir historia','cost_components':'cobertura y procedencia de cada componente','cost_allocations':'reconciliar costos compartidos sin duplicar','purchase_orders_ops':'compromiso comercial y unidades solicitadas','purchase_receipts_ops':'separar recibido, inspección y aceptado','obligations':'importe, vencimiento y saldo de una obligación','obligation_payments':'pago observado aplicado una sola vez','cash_scenario_events':'separar esperado, comprometido y escenario'}
    for name,rows in TABLES.items():
        path=OUT/(name+'.csv');grain,key=CONTRACT[name]
        sources.append(dict(name=name,table=name,file=name+'.csv',source_path='operating-data/'+name+'.csv',grain=grain,primary_key=key,fields=list(rows[0]),rows=len(rows),row_count=len(rows),synthetic=True,purpose=purposes[name],decision_use=purposes[name],evidence_refs=[r.get('source_ref') for r in rows if r.get('source_ref')],sha256=sha256(path.read_bytes()).hexdigest()))
    client_catalog=json.loads((ROOT/'client/example-input.json').read_text(encoding='utf-8'))
    catalog_skus={r['sku'] for r in client_catalog['CATALOGO']}
    local_skus={r['sku'] for r in TABLES['cost_versions']} | {r['sku'] for r in TABLES['purchase_orders_ops']}
    unresolved_skus=sorted(local_skus-catalog_skus)
    if unresolved_skus: raise ValueError('Cost/operations SKUs not present in client catalog: '+', '.join(unresolved_skus))
    manifest=dict(version='0.3.0',as_of=AS_OF.isoformat(),synthetic=True,status='IMPLEMENTED_LOCAL_VERTICAL_SLICE',external_execution='PROHIBITED',currency='MXN cents',catalog_bridge=dict(source_path='client/example-input.json',source_collection='CATALOGO',source_key='sku',local_tables=['cost_versions.sku','purchase_orders_ops.sku','cost_allocations.sku'],status='EXPLICIT_SYNTHETIC_SKU_CONTRACT',unresolved_skus=unresolved_skus),sources=sources,metrics=metrics,metric_definitions=[
      dict(id='known_cost_sum',formula='sum known, non-duplicated cost components',unit='MXN cents',grain='cost version',window='effective cost version',sources=['cost_versions','cost_components','cost_allocations'],unknown='partial sum remains labeled PARTIAL',guardrail='never replace missing components with zero',decision='complete missing component or review source'),
      dict(id='contribution_margin',formula='(price - selling fee - complete unit management cost) / price',unit='ratio',grain='cost version / SKU',window='effective cost version',sources=['cost_versions','cost_components'],unknown='NULL when cost incomplete or price zero',guardrail='not net margin while tax basis is pending',decision='compare price/cost; not net profit'),
      dict(id='markup_on_cost',formula='(price - selling fee - complete unit management cost) / complete unit management cost',unit='ratio',grain='cost version / SKU',window='effective cost version',sources=['cost_versions','cost_components'],unknown='NULL when cost incomplete or zero',guardrail='kept distinct from contribution margin',decision='review commercial economics'),
      dict(id='purchase_receipt_bridge',formula='ordered = received + still_to_receive; received = accepted + inspection + rejected',unit='units',grain='purchase order',window='order through latest receipt',sources=['purchase_orders_ops','purchase_receipts_ops'],unknown='no receipt stays pending',guardrail='only accepted units are available from the receipt',decision='review discrepancy/preparation before availability'),
      dict(id='obligation_balance',formula='original obligation - applied observed payments',unit='MXN cents',grain='obligation',window='through as_of date',sources=['obligations','obligation_payments'],unknown='unknown payment coverage blocks closure',guardrail='one canonical obligation; do not double count its origin',decision='schedule review; never execute payment'),
      dict(id='cash_scenario_closing',formula='opening + dated incoming - dated outgoing, carried for 8 weeks',unit='MXN cents',grain='scenario / week',window='next 8 weeks',sources=['cash_scenario_events','obligations','obligation_payments'],unknown='UNKNOWN coverage: undated or uncovered obligations remain outside and disclosed',guardrail='base, expected and unapproved scenario remain visibly separate',decision='compare consequences; never call it free cash'),
    ],lineage=[
      dict(from_table='cost_versions',to_metric='known_cost_sum'),dict(from_table='cost_components',to_metric='known_cost_sum'),dict(from_table='cost_allocations',to_metric='known_cost_sum'),
      dict(from_table='cost_versions',to_metric='contribution_margin'),dict(from_table='cost_components',to_metric='contribution_margin'),
      dict(from_table='cost_versions',to_metric='markup_on_cost'),dict(from_table='cost_components',to_metric='markup_on_cost'),
      dict(from_table='purchase_orders_ops',to_metric='purchase_receipt_bridge'),dict(from_table='purchase_receipts_ops',to_metric='purchase_receipt_bridge'),
      dict(from_table='obligations',to_metric='obligation_balance'),dict(from_table='obligation_payments',to_metric='obligation_balance'),
      dict(from_table='cash_scenario_events',to_metric='cash_scenario_closing'),dict(from_table='obligations',to_metric='cash_scenario_closing'),dict(from_table='obligation_payments',to_metric='cash_scenario_closing')
    ],capabilities=['versioned management costs','cost coverage and provenance','receipt-to-availability bridge','canonical obligations','8-week scenario comparison'],status_mapping={
      'EXISTS':'EXISTS','SPECIFIED':'SPECIFIED','PARTIAL':'PARTIAL','MISSING':'MISSING','CONFLICT':'CONFLICT','IMPLEMENTED_LOCAL':'EXISTS','SPECIFIED_NOT_IMPLEMENTED':'SPECIFIED','PENDING_AUTHORIZED_DATA':'MISSING','CONFLICT_OUT_OF_SCOPE':'CONFLICT'
    },extension_matrix=[
      dict(capability='visible cost sources and cost coverage',status='IMPLEMENTED_LOCAL',canonical_status='EXISTS',evidence='8 CSV sources + cost metrics',evidence_refs=[evidence_ref('client/operating-data/cost_versions.csv'),evidence_ref('client/operating-data/cost_components.csv')]),
      dict(capability='purchase receipt and accepted availability',status='IMPLEMENTED_LOCAL',canonical_status='EXISTS',evidence='purchase_orders_ops + purchase_receipts_ops',evidence_refs=[evidence_ref('client/operating-data/purchase_orders_ops.csv'),evidence_ref('client/operating-data/purchase_receipts_ops.csv')]),
      dict(capability='canonical obligations without double counting',status='IMPLEMENTED_LOCAL',canonical_status='EXISTS',evidence='obligations + obligation_payments',evidence_refs=[evidence_ref('client/operating-data/obligations.csv'),evidence_ref('client/operating-data/obligation_payments.csv')]),
      dict(capability='8-week cash scenarios',status='IMPLEMENTED_LOCAL',canonical_status='EXISTS',evidence='BASE and REINVESTIR_TOP remain separate',evidence_refs=[evidence_ref('client/operating-data/cash_scenario_events.csv')]),
      dict(capability='React/Supabase transactional application',status='CONFLICT_OUT_OF_SCOPE',canonical_status='CONFLICT',evidence='current repository contract is analytical CLI/files/reports',evidence_refs=[evidence_ref('AGENTS.md'),evidence_ref('specs/COSTS-OPERATIONS-v3.md')]),
      dict(capability='real bank, tax and customer integrations',status='PENDING_AUTHORIZED_DATA',canonical_status='MISSING',evidence='synthetic fixture only',evidence_refs=[evidence_ref('specs/COSTS-OPERATIONS-v3.md')])
    ],source='candidate handoff integrated against current repository; React/Supabase claims not implemented',limitations=['Synthetic fixture only','Tax basis pending; no net margin','Weekly scenario does not reconcile a real bank','No autonomous purchase, payment, price change or publication'])
    manifest_path=ROOT/'client/costs-operations-manifest.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    (ROOT/'client/COSTOS_Y_OPERACION.html').write_text(render(manifest),encoding='utf-8')
    print(json.dumps({'status':'ok','sources':len(sources),'metrics':len(manifest['metric_definitions']),'manifest':str(manifest_path),'html':'client/COSTOS_Y_OPERACION.html'},ensure_ascii=False))


if __name__=='__main__':main()
