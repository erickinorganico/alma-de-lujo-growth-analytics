"""Offline, deterministic reporting artifacts for synthetic Alma de Lujo data."""
from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlparse


def _rows(value): return value if isinstance(value, list) else []
def _known(value): return isinstance(value, (int, float)) and not isinstance(value, bool)
def _text(value): return "Sin datos" if value is None or value == "" else str(value)
def _money(value): return "Sin datos" if not _known(value) else f"MXN ${value / 100:,.2f}"
def _number(value): return "Sin datos" if not _known(value) else f"{value:,.0f}"
def _pct(value): return "Sin datos" if not _known(value) else f"{value:.2f}%"
def _safe_url(value):
    parsed = urlparse(value) if isinstance(value, str) else None
    return value if parsed and parsed.scheme == "https" and parsed.netloc else None
def _svg_text(value): return escape(_text(value), quote=True)

def _coverage(meta, quality, name):
    """Absent source coverage is unknown, never an empty business result."""
    coverage=meta.get('coverage') if isinstance(meta.get('coverage'),dict) else None
    if coverage is not None: return coverage.get(name) is True
    row=next((x for x in quality if x.get('id')==f'coverage_{name}'),None)
    return not row or row.get('status') == 'PASS'


def _svg_frame(title, width=900, height=360):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
            f'<title id="title">{_svg_text(title)}</title><desc id="desc">Gráfico generado de datos sintéticos; valores desconocidos se indican como Sin datos.</desc>'
            '<rect width="100%" height="100%" fill="#fffdf8"/><style>text{font-family:Arial,sans-serif;fill:#20231d}.muted{fill:#686b61;font-size:12px}.label{font-size:12px}.axis{stroke:#c9c7bd;stroke-width:1}</style>')


def _signed_scale(values, top=60, bottom=300):
    low, high = min(0, min(values)), max(0, max(values))
    span = max(1, high - low)
    y = lambda value: bottom - (value - low) * (bottom - top) / span
    return low, high, y(0), y


def _monthly_chart(trend):
    rows = _rows(trend); fields = [('net_revenue_cents', '#556249', 'Ingreso neto'), ('cogs_cents', '#a15a47', 'COGS'), ('opex_cents', '#b39760', 'OPEX')]
    values = [r.get(key) for r in rows for key, _, _ in fields if _known(r.get(key))]
    out = [_svg_frame('Ingreso neto, COGS y OPEX mensual'), '<text x="45" y="28" font-size="18">Finanzas por mes · MXN</text>']
    if not rows or not values: return ''.join(out + ['<text x="450" y="180" text-anchor="middle" class="muted">Sin datos para trazar este gráfico</text></svg>'])
    left,bottom,top=65,300,60; low,high,zero,y=_signed_scale(values,top,bottom)
    out += [f'<line x1="{left}" y1="{zero:.1f}" x2="850" y2="{zero:.1f}" class="axis"/>', f'<text x="{left}" y="{top-12}" class="muted">Máx. {_svg_text(_money(high))} · 0 · mín. {_svg_text(_money(low))}</text>']
    group=740/max(1,len(rows)); bar=group/4
    for i,r in enumerate(rows):
        x=left+i*group
        out.append(f'<text x="{x+group/2}" y="322" text-anchor="middle" class="label">{_svg_text(r.get("month"))}</text>')
        for j,(key,color,label) in enumerate(fields):
            v=r.get(key)
            if _known(v):
                if v != 0:
                    yy=y(v); h=abs(yy-zero); out.append(f'<rect x="{x+j*bar+8}" y="{min(yy,zero):.1f}" width="{bar-5}" height="{h:.1f}" fill="{color}"><title>{_svg_text(label)}: {_svg_text(_money(v))}</title></rect>')
                else: out.append(f'<text x="{x+j*bar+8}" y="{zero-5:.1f}" class="muted">0</text>')
            else: out.append(f'<text x="{x+j*bar+8}" y="{bottom-6}" class="muted">?</text>')
    for i,(_,color,label) in enumerate(fields):
        out.append(f'<rect x="650" y="{18+i*16}" width="8" height="8" fill="{color}"/><text x="664" y="{26+i*16}" class="muted">{_svg_text(label)}</text>')
    out.append('</svg>')
    return ''.join(out)


def _color_chart(inventory):
    grouped=defaultdict(list)
    for row in _rows(inventory):
        if 'pilates' in _text(row.get('category')).lower() and 'sock' in _text(row.get('category')).lower(): grouped[_text(row.get('color'))].append(row.get('available'))
    vals={color: None if any(not _known(v) for v in items) else sum(items) for color,items in grouped.items()}
    known=[v for v in vals.values() if _known(v)]; out=[_svg_frame('Disponible por color de calcetines de Pilates'), '<text x="45" y="28" font-size="18">Calcetines de Pilates: disponibilidad por color · unidades</text>']
    if not known: return ''.join(out+['<text x="450" y="180" text-anchor="middle" class="muted">Sin datos para comparar colores</text></svg>'])
    low,high,zero,y=_signed_scale(known); group=740/max(1,len(vals)); out += [f'<line x1="65" y1="{zero:.1f}" x2="850" y2="{zero:.1f}" class="axis"/>',f'<text x="65" y="48" class="muted">Máx. {high:.0f} · 0 · mín. {low:.0f}</text>']
    for i,(color,value) in enumerate(sorted(vals.items())):
        x=65+i*group
        if _known(value):
            if value != 0:
                yy=y(value); h=abs(yy-zero); out.append(f'<rect x="{x+18}" y="{min(yy,zero):.1f}" width="{max(12,group-35)}" height="{h:.1f}" fill="#77886b"><title>{_svg_text(color)}: {_svg_text(_number(value))} unidades</title></rect>')
            out.append(f'<text x="{x+group/2}" y="{y(value)-8 if value>=0 else y(value)+16:.1f}" text-anchor="middle" class="label">{_svg_text(_number(value))}</text>')
        else: out.append(f'<text x="{x+group/2}" y="180" text-anchor="middle" class="muted">Sin datos</text>')
        out.append(f'<text x="{x+group/2}" y="322" text-anchor="middle" class="label">{_svg_text(color)}</text>')
    return ''.join(out)+ '</svg>'


def _cash_chart(kpis):
    entries=[('Cobros observados',kpis.get('cash_in_cents'),'#556249'),('Salidas observadas',-kpis['cash_out_cents'] if _known(kpis.get('cash_out_cents')) else None,'#a15a47'),('Caja neta',kpis.get('net_cash_cents'),'#b39760')]; known=[v for _,v,_ in entries if _known(v)]
    out=[_svg_frame('Puente de efectivo observado'), '<text x="45" y="28" font-size="18">Puente de efectivo observado · MXN</text>']
    if not known:return ''.join(out+['<text x="450" y="180" text-anchor="middle" class="muted">Sin datos de efectivo observado</text></svg>'])
    low,high,zero,y=_signed_scale(known); out += [f'<line x1="65" y1="{zero:.1f}" x2="850" y2="{zero:.1f}" class="axis"/>',f'<text x="65" y="48" class="muted">Salidas se muestran negativas · Máx. {_svg_text(_money(high))} · mín. {_svg_text(_money(low))}</text>']
    for i,(label,value,color) in enumerate(entries):
        x=130+i*235
        if _known(value):
            if value != 0:
                yy=y(value); h=abs(yy-zero); out.append(f'<rect x="{x}" y="{min(yy,zero):.1f}" width="110" height="{h:.1f}" fill="{color}"><title>{_svg_text(label)}: {_svg_text(_money(value))}</title></rect>')
            out.append(f'<text x="{x+55}" y="{y(value)-8 if value>=0 else y(value)+16:.1f}" text-anchor="middle" class="label">{_svg_text(_money(value))}</text>')
        else:out.append(f'<text x="{x+55}" y="170" text-anchor="middle" class="muted">Sin datos</text>')
        out.append(f'<text x="{x+55}" y="325" text-anchor="middle" class="label">{_svg_text(label)}</text>')
    return ''.join(out)+'</svg>'


def _table(headers, values):
    head=''.join(f'<th>{escape(h)}</th>' for h in headers)
    body=''.join('<tr>'+''.join(f'<td>{escape(_text(v))}</td>' for v in row)+'</tr>' for row in values) or f'<tr><td colspan="{len(headers)}">Sin datos</td></tr>'
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _markdown_table(headers, values):
    def cell(value):
        return _text(value).replace('\\', '\\\\').replace('|', '\\|').replace('\n', ' ')
    rows = list(values)
    if not rows: rows = [('Sin datos',) + ('',)*(len(headers)-1)]
    return '| ' + ' | '.join(cell(h) for h in headers) + ' |\n| ' + ' | '.join('---' for _ in headers) + ' |\n' + '\n'.join('| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows)


def write_reports(report, output_dir):
    """Write deterministic Markdown, printable HTML and SVG report artifacts."""
    output=Path(output_dir); charts=output/'charts'; charts.mkdir(parents=True,exist_ok=True)
    meta=report.get('meta') if isinstance(report,dict) else {}; meta=meta if isinstance(meta,dict) else {}
    kpis=report.get('kpis') if isinstance(report,dict) and isinstance(report.get('kpis'),dict) else {}
    artifacts={'charts/monthly_finance.svg':_monthly_chart(report.get('trend')),'charts/color_stock.svg':_color_chart(report.get('inventory')),'charts/cash_bridge.svg':_cash_chart(kpis)}
    for name,content in artifacts.items():(output/name).write_text(content,encoding='utf-8', newline='\n')
    quality=_rows(report.get('quality')); inv=_rows(report.get('inventory')); channels=_rows(report.get('channels')); cohorts=_rows(report.get('cohorts')); purchases=_rows(report.get('purchases')); products=_rows(report.get('products'))
    inventory_known=all(_coverage(meta,quality,n) for n in ('variants','products','movements','order_items','orders','reservations')) and all(x.get('available') is not None and x.get('cost_cents') is not None for x in inv); purchases_known=_coverage(meta,quality,'purchase_orders'); products_known=_coverage(meta,quality,'products'); orders_known=_coverage(meta,quality,'orders')
    colors=sorted({_text(x.get('color')) for x in inv}) if inventory_known else []
    opportunity=[x for x in inv if x.get('status') in ('REORDER','STOCKOUT','REVIEW')] if inventory_known else []
    findings=[f"Ingresos netos reconocidos: {_money(kpis.get('net_revenue_cents'))}.",f"Valor de inventario a costo: {_money(kpis.get('inventory_value_cents'))}.",f"{len(opportunity) if inventory_known else 'Sin datos'} SKU(s) con estado de revisión, reposición o agotado en este escenario sintético.",f"{len(colors) if inventory_known else 'Sin datos'} color(es) presentes en el inventario sintético."]
    source_lines=[]
    for s in _rows(report.get('market')):
        link=_safe_url(s.get('url')); title=_text(s.get('title')); source_lines.append(f"- {title} · autoridad: {_text(s.get('publisher'))}; cobertura: {_text(s.get('coverage'))}; límite: {_text(s.get('limitation'))}; enlace: {link or 'Sin enlace HTTPS seguro'}")
    decisions=[]
    for d in _rows(report.get('decisions')): decisions.extend([f"- {_text(a.get('description'))} (ejecución: {_text(a.get('execution'))}; aprobación humana: {_text(a.get('approval_required'))})" for a in _rows(d.get('actions'))])
    experiment_lines=[]
    for e in _rows(report.get('experiments')):experiment_lines.append(f"### {_text(e.get('id'))}: {_text(e.get('title'))}\nHipótesis: {_text(e.get('hypothesis'))}\n\nMétrica primaria: {_text(e.get('primary_metric'))}. Guardarraíl: {_text(e.get('guardrail'))}. Ventana: {_text(e.get('window'))}. Población: {_text(e.get('population'))}. Cierre: {_text(e.get('close_criterion'))}.")
    mature='Sin datos' if not orders_known else f"{sum(1 for x in cohorts if _known(x.get('mature_30d')) and x['mature_30d']>0)} de {len(cohorts)}"
    md=f"# Alma de Lujo — reporte analítico\n\n> **DATOS SINTÉTICOS.** Este documento es reproducible y no describe ventas, demanda ni operación real.\n\nCorte: {_text(meta.get('as_of'))} · escenario: {_text(meta.get('scenario'))} · estado: {_text(meta.get('status'))} · política: {_text(meta.get('policy'))}.\n\n## Hallazgos calculados\n"+'\n'.join(f'- {x}' for x in findings)+f"\n\n## Finanzas\nIngreso bruto: {_money(kpis.get('gross_revenue_cents'))}; descuentos: {_money(kpis.get('discounts_cents'))}; notas de crédito: {_money(kpis.get('credits_cents'))}; COGS: {_money(kpis.get('cogs_cents'))}; OPEX: {_money(kpis.get('opex_cents'))}; caja neta observada: {_money(kpis.get('net_cash_cents'))}.\n\n![Finanzas](charts/monthly_finance.svg)\n![Caja](charts/cash_bridge.svg)\n\n## Inventario y color\nOportunidades de escenario: {', '.join(_text(x.get('sku')) for x in opportunity) if inventory_known else 'Sin datos'}. Los colores observados son: {', '.join(colors) if inventory_known else 'Sin datos'}. Esto no prueba una preferencia de compra.\n\n![Stock por color](charts/color_stock.svg)\n\n## Canales y cohortes\n"+_markdown_table(['Canal','Visitas','Órdenes','Conversión'],[(_text(x.get('channel')),_number(x.get('visits')),_number(x.get('orders')),_pct(x.get('conversion_pct'))) for x in channels])+f"\n\nCohortes con madurez de 30 días: {mature}.\n\n## Compras y catálogo\nCompras: {len(purchases) if purchases_known else 'Sin datos'} · productos: {len(products) if products_known else 'Sin datos'}.\n\n## Fuentes, autoridad y límites\n"+'\n'.join(source_lines or ['- Sin datos'])+"\n\n## Experimentos\n"+'\n\n'.join(experiment_lines or ['Sin datos'])+"\n\n## Decisiones y evidencia\n"+'\n'.join(decisions or ['- Sin acciones registradas.'])+"\n\nLas referencias de evidencia se conservan en `report.json`; los enlaces externos no se descargan ni ejecutan.\n"
    md += "\n## Puente financiero completo\n" + _markdown_table(
        ['Componente', 'Valor'],
        [('Ingreso bruto', _money(kpis.get('gross_revenue_cents'))), ('Descuentos', _money(kpis.get('discounts_cents'))),
         ('Notas de crédito', _money(kpis.get('credits_cents'))), ('Ingreso neto reconocido', _money(kpis.get('net_revenue_cents'))),
         ('COGS', _money(kpis.get('cogs_cents'))), ('Utilidad bruta', _money(kpis.get('gross_profit_cents'))),
         ('Margen bruto', _pct(kpis.get('gross_margin_pct'))), ('OPEX', _money(kpis.get('opex_cents'))),
         ('Contribución', _money(kpis.get('contribution_cents'))), ('Proxy operativo', _money(kpis.get('operating_proxy_cents'))),
         ('Cobros observados', _money(kpis.get('cash_in_cents'))), ('Salidas observadas', _money(kpis.get('cash_out_cents'))),
         ('Caja neta observada', _money(kpis.get('net_cash_cents')))])
    md += "\n\n## Detalle de inventario, compras y catálogo\n" + _markdown_table(
        ['SKU', 'Color', 'Disponible', 'En tránsito', 'Estado'],
        [(_text(x.get('sku')), _text(x.get('color')), _number(x.get('available')), _number(x.get('in_transit')), _text(x.get('status'))) for x in inv])
    md += "\n\n" + _markdown_table(['Compra', 'Proveedor', 'SKU', 'Pedidas', 'Recibidas', 'Estado'],
        [(_text(x.get('id')), _text(x.get('supplier')), _text(x.get('sku')), _number(x.get('ordered_qty')), _number(x.get('received_qty')), _text(x.get('status'))) for x in purchases])
    md += "\n\n" + _markdown_table(['Producto', 'Categoría', 'Colección', 'Ciclo'],
        [(_text(x.get('name')), _text(x.get('category')), _text(x.get('collection')), _text(x.get('lifecycle'))) for x in products]) + "\n"
    # Markdown is plain text here; report-derived markup is never restored.
    md=escape(md)
    (output/'report.md').write_text(md,encoding='utf-8', newline='\n')
    h=lambda value: escape(_text(value))
    finance=_table(['Componente','Valor'],[('Ingreso bruto',_money(kpis.get('gross_revenue_cents'))),('Descuentos',_money(kpis.get('discounts_cents'))),('Notas de crédito',_money(kpis.get('credits_cents'))),('Ingreso neto',_money(kpis.get('net_revenue_cents'))),('COGS',_money(kpis.get('cogs_cents'))),('Utilidad bruta',_money(kpis.get('gross_profit_cents'))),('Margen bruto',_pct(kpis.get('gross_margin_pct'))),('OPEX',_money(kpis.get('opex_cents'))),('Gastos variables',_money(kpis.get('variable_expenses_cents'))),('Contribución',_money(kpis.get('contribution_cents'))),('Proxy operativo',_money(kpis.get('operating_proxy_cents'))),('Cobros observados',_money(kpis.get('cash_in_cents'))),('Salidas observadas',_money(kpis.get('cash_out_cents'))),('Caja neta',_money(kpis.get('net_cash_cents')))])
    inventory_table=_table(['SKU','Color','En mano','Reservado','Disponible','Tránsito','Estado'],[(x.get('sku'),x.get('color'),_number(x.get('on_hand')),_number(x.get('reserved')),_number(x.get('available')),_number(x.get('in_transit')),x.get('status')) for x in inv])
    cohort_table=_table(['Cohorte','Clientes','Maduros 30d','Recompra','Tasa'],[(x.get('month'),_number(x.get('customers')),_number(x.get('mature_30d')),_number(x.get('repeat_customers')),_pct(x.get('repeat_rate_pct'))) for x in cohorts])
    purchase_table=_table(['Compra','Proveedor','SKU','Pedidas','Recibidas','Estado'],[(x.get('id'),x.get('supplier'),x.get('sku'),_number(x.get('ordered_qty')),_number(x.get('received_qty')),x.get('status')) for x in purchases])
    sources=''.join(f'<li><b>{h(s.get("title"))}</b> · autoridad: {h(s.get("publisher"))}; cobertura: {h(s.get("coverage"))}; límite: {h(s.get("limitation"))}; '+(f'<a href="{escape(_safe_url(s.get("url")),quote=True)}">enlace HTTPS</a>' if _safe_url(s.get('url')) else 'Sin enlace HTTPS seguro')+'</li>' for s in _rows(report.get('market'))) or '<li>Sin datos</li>'
    experiments=''.join(f'<section class="experiment"><h3>{h(e.get("id"))}: {h(e.get("title"))}</h3><p><b>Hipótesis:</b> {h(e.get("hypothesis"))}</p><p><b>Métrica primaria:</b> {h(e.get("primary_metric"))}<br><b>Guardarraíl:</b> {h(e.get("guardrail"))}<br><b>Ventana:</b> {h(e.get("window"))}<br><b>Población:</b> {h(e.get("population"))}<br><b>Criterio de cierre:</b> {h(e.get("close_criterion"))}</p><p><b>Referencias:</b> {h(", ".join(_rows(e.get("evidence_refs"))))}</p></section>' for e in _rows(report.get('experiments'))) or '<p>Sin datos</p>'
    packets=''.join(f'<section class="packet"><h3>{h(d.get("id"))} · {h(d.get("status"))}</h3><p><b>Hechos y evidencia:</b></p><ul>'+''.join(f'<li>{h(f.get("text"))} — {h(", ".join(_rows(f.get("evidence_refs"))))}</li>' for f in _rows(d.get('facts')))+f'</ul><p><b>Desconocidos:</b> {h(" · ".join(_rows(d.get("unknowns"))))}</p><p><b>Hipótesis:</b> {h(" · ".join(_rows(d.get("hypotheses"))))}</p></section>' for d in _rows(report.get('decisions'))) or '<p>Sin datos</p>'
    html=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Alma de Lujo — reporte sintético</title><style>body{{font:16px/1.5 Georgia,serif;max-width:960px;margin:36px auto;color:#20231d}}.banner{{background:#20231d;color:#fff;padding:12px}}h1,h2,h3{{font-family:Arial,sans-serif}}table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{padding:8px;border-bottom:1px solid #ccc;text-align:left}}img{{max-width:100%;margin:18px 0}}.experiment,.packet{{border-top:1px solid #ccc;margin-top:16px}}@media print{{body{{margin:12mm}}}}</style><body><p class="banner"><b>DATOS SINTÉTICOS</b> · reporte reproducible, no hechos de negocio real</p><article><h1>Alma de Lujo — reporte analítico</h1><p>Corte: {h(meta.get('as_of'))} · escenario: {h(meta.get('scenario'))} · estado: {h(meta.get('status'))}</p><h2>Hallazgos calculados</h2><ul>{''.join(f'<li>{h(x)}</li>' for x in findings)}</ul><h2>Puente financiero</h2>{finance}<img src="charts/monthly_finance.svg" alt="Finanzas mensuales"><img src="charts/cash_bridge.svg" alt="Puente de efectivo"><h2>Inventario y color</h2>{inventory_table}<img src="charts/color_stock.svg" alt="Disponibilidad de calcetines de Pilates por color"><h2>Canales y cohortes</h2>{_table(['Canal','Visitas','Órdenes','Conversión'],[(x.get('channel'),_number(x.get('visits')),_number(x.get('orders')),_pct(x.get('conversion_pct'))) for x in channels])}{cohort_table}<h2>Compras y catálogo</h2>{purchase_table}{_table(['Producto','Categoría','Colección','Ciclo'],[(x.get('name'),x.get('category'),x.get('collection'),x.get('lifecycle')) for x in products])}<h2>Fuentes, autoridad y límites</h2><ul>{sources}</ul><h2>Experimentos</h2>{experiments}<h2>Decisiones y evidencia</h2>{packets}</article></body></html>'''
    (output/'report.html').write_text(html,encoding='utf-8', newline='\n')
    return ['report.md','report.html',*artifacts]
