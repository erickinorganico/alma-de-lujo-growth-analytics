"""Offline, private customer report. No scripts, analytics, network or execution."""
from html import escape

LABELS = {
    'REVISAR': 'Revisión pendiente',
    'DATOS_PENDIENTES': 'Faltan datos',
    'CORREGIR_CAPTURA': 'Corrige la captura antes de analizar',
    'PROPUESTA_CONDICIONAL': 'Cantidad para revisar',
    'SIN_REPOSICION': 'Sin reposición en este escenario',
    'EXCEDE_LIMITE': 'Rebasa el límite de compra o el piso de caja',
    'DENTRO_DEL_ESCENARIO': 'El plan cabe en el escenario capturado',
    'PRODUCTO_NO_ACTIVO': 'Producto en pausa o pre lanzamiento: evaluar por separado.',
    'POLITICA_POR_REVISAR': 'Revisa plazo, colchón, margen, mínimo y múltiplo con el proveedor.',
    'VENTAS_INCOMPLETAS': 'Completa y confirma las ventas de toda la ventana.',
    'ACTUALIZAR_CONTEO': 'Actualiza el conteo físico a la fecha de corte.',
    'DISPONIBILIDAD_NO_OBSERVADA_COMPLETA': 'Hubo días sin disponibilidad o falta observarlos; las ventas no miden toda la demanda.',
    'DATOS_FALTANTES': 'Completa costos, cantidades y condiciones que faltan; usa cero sólo si está comprobado.',
    'MARGEN_OBJETIVO_INVIABLE': 'Comisión y margen consumen todo el precio. Revisa esos supuestos.',
    'REVISAR_PRECIO_O_COSTO': 'El precio actual no alcanza el margen objetivo; revisa precio o costos.',
    'REVISAR_TRANSITO': 'Confirma fecha de llegada: está ausente o ya venció.',
    'TRANSITO_NO_CONFIRMADO': 'Verifica con el proveedor que el envío está confirmado.',
    'TRANSITO_FUERA_DEL_PLAZO': 'El envío llega después del plazo: revisa la cobertura y evita duplicar la compra.',
    'CORREGIR_PLAN_DE_COMPRA': 'Revisa cantidad mínima, múltiplo, costo y fecha de pago de la compra elegida.',
}


def label(value):
    return LABELS.get(value, value)


def money(value):
    return 'Pendiente' if value is None else f'${value:,.2f}'


def quantity(value):
    return 'Pendiente' if value is None else f'{value:,.2f}'.rstrip('0').rstrip('.')


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+escape(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows) + '</tbody></table></div>'


def render(report, digest):
    lines = ['''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Alma de Lujo · Corte semanal</title>
<style>
*{box-sizing:border-box}body{font:16px/1.6 Calibri,Arial,sans-serif;margin:0;background:#f6f3eb;color:#193b34}
main{max-width:1200px;margin:auto;padding:48px 28px}header{border-top:8px solid #193b34;padding-top:30px}
.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:2px}h1{font:48px Georgia,serif;margin:8px 0}
h2{font:28px Georgia,serif;margin-top:42px}h3{font-size:15px}p{max-width:950px}.note{padding:18px;background:#e7eddd;border-left:4px solid #678270}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.tile{padding:20px;background:white;border:1px solid #d6ded2}.number{font-size:27px;font-variant-numeric:tabular-nums}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin:18px 0;background:white}td,th{text-align:left;border-bottom:1px solid #d7ded5;padding:12px;vertical-align:top}th{background:#193b34;color:white}td{font-variant-numeric:tabular-nums}
footer{font-size:12px;color:#54665e;margin-top:50px;overflow-wrap:anywhere}.small{font-size:13px}
@media(max-width:700px){main{padding:28px 16px}.tiles{grid-template-columns:1fr}h1{font-size:36px}}
@media print{body{background:white}main{padding:0}h2{break-after:avoid}tr,.tile{break-inside:avoid}.scroll{overflow:visible}th{color:#193b34;background:#e7eddd}table{font-size:10px}td,th{padding:7px}}
</style></head><body><main><header><div class="eyebrow">Alma de Lujo / Sesión semanal · Privado</div><h1>Tres decisiones, un corte.</h1>''',
             f'<p>{escape(str(report.get("as_of") or "Fecha pendiente"))} · {escape(label(report["status"]))} · Importes en MXN, pesos.</p></header>',
             '<p class="note">Este informe usa los agregados capturados. No acredita una conciliación bancaria ni autoriza compras, pagos o cambios de precio. Si falta un dato, primero resuelve la captura.</p>']
    if report.get('metadata', {}).get('workbook_marker') == 'EJEMPLO_SINTETICO':
        lines.append('<p class="note"><strong>EJEMPLO SINTÉTICO.</strong> Estos números permiten practicar; no describen las ventas, el inventario ni la caja reales de Alma de Lujo.</p>')
    b = report.get('budget')
    if b:
        lines.append('<h2>1. ¿Cabe la compra elegida en caja?</h2><div class="tiles">')
        for title, value in [('Presupuesto conservador antes de propuestas', b['available_before_proposals_mxn']), ('Compra elegida · costo puesto en almacén', b['planned_purchase_mxn']), ('Menor cierre diario con compras', b['min_daily_cash_after_mxn'])]:
            lines.append(f'<div class="tile"><h3>{title}</h3><div class="number">{money(value)}</div></div>')
        lines.append(f'</div><p><strong>{escape(label(b["status"]))}.</strong> Piso protegido: {money(b["cash_floor_mxn"])}. Revisa el importe y la fecha de cada pago antes de comprometerte.</p>')
        lines.append('<p class="small">El presupuesto previo es conservador; el resultado final también depende de las fechas elegidas. Se evalúan 91 cierres diarios. La hora de cobros y pagos dentro del mismo día permanece desconocida.</p>')
    lines.append('<h2>2. ¿Qué variantes conviene revisar para reponer?</h2>')
    lines.append(table(['Variante','Estado','Disponible','Cantidad propuesta','Cantidad elegida','Siguiente paso'], [
        [r['sku']+' · '+str(r.get('color') or '')+' · '+str(r.get('size') or ''), label(r['status']), quantity(r['available_units']), quantity(r['suggested_qty']), quantity(r['planned_qty']), ' '.join(label(x) for x in r['reasons']) or 'Confirma el escenario de caja y registra tu decisión.'] for r in report['skus']]))
    lines.append('<h2>3. ¿El precio deja la contribución esperada?</h2><p>El precio objetivo es un escenario con los costos actuales del catálogo; no predice cuántas personas comprarán. La contribución observada usa únicamente los costos históricos capturados.</p>')
    lines.append(table(['SKU','Costo variable unitario','Precio objetivo','Margen unitario actual','Ingreso neto observado','Contribución observada'], [
        [r['sku'], money(r['unit_variable_cost_mxn']), money(r['target_price_mxn']), 'Pendiente' if r['unit_margin'] is None else f'{r["unit_margin"]:.1%}', money(r['net_revenue_mxn']), money(r['contribution_mxn'])] for r in report['skus']]))
    if report.get('cash_weeks'):
        lines.append('<h2>Agenda de caja · próximas 13 semanas</h2>')
        lines.append(table(['Semana / fechas','Entradas','Salidas existentes','Compras elegidas','Cierre con compras','Mínimo diario con compras','Piso'], [
            [f'{w["week"]} · {w["start"]} / {w["end"]}',money(w['in_mxn']),money(w['out_existing_mxn']),money(w['planned_purchases_mxn']),money(w['planned_closing_mxn']),money(w['min_daily_after_mxn']),'Pendiente' if w['below_floor'] is None else 'Rebasa piso' if w['below_floor'] else 'Dentro del escenario'] for w in report['cash_weeks']]))
    lines.append('<h2>Correcciones y datos por completar</h2>')
    if report['issues']:
        lines.append(table(['Ubicación','Qué corregir'], [[x['cell'],x['message']] for x in report['issues']]))
    else:
        lines.append('<p>No se detectaron errores estructurales. La exactitud de las fuentes y las condiciones comerciales debe comprobarla quien prepara el corte.</p>')
    lines.append('<h2>Cierra la sesión con un compromiso concreto</h2><p>Registra hasta tres decisiones: variante, decisión, responsable, fecha de revisión, resultado esperado y condición para detenerla. Una cantidad propuesta permanece pendiente hasta que el responsable confirme la caja y las condiciones del proveedor.</p>')
    lines.append('<ul>'+''.join('<li>'+escape(x)+'</li>' for x in report.get('limits', []))+'</ul>')
    lines.append('<footer>Informe privado · conserva este archivo junto a su libro de origen. SHA-256 de informe.json: '+escape(digest)+'</footer></main></body></html>')
    return '\n'.join(lines)
