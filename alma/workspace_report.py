"""Readable, exportable analytical dossier; no application or server."""
from html import escape
from pathlib import Path
from .storage import canonical


def cell(v):
    if v is None:return 'UNKNOWN'
    return str(v).replace('|','\\|').replace('\n',' ')


def table(rows,limit=15):
    if not rows:return '_Sin filas; consultar cobertura antes de interpretar._\n'
    cols=list(rows[0]);out=['| '+' | '.join(cols)+' |','| '+' | '.join('---' for _ in cols)+' |']
    out+=['| '+' | '.join(cell(r[c]) for c in cols)+' |' for r in rows[:limit]]
    if len(rows)>limit:out+=['',f'Muestra de {limit} de {len(rows)} filas. Tabla completa en el CSV/JSON correspondiente.']
    return '\n'.join(out)+'\n'


def write_report(data,marts,quality,folder):
    folder=Path(folder)
    lines=['# Alma de Lujo — dossier analítico v0.2','',
      '**DATOS COMERCIALES SINTÉTICOS.** Esta simulación verifica procesos y decisiones; no describe ventas, clientas o rentabilidad reales.',
      '',f"Corte: {data['metadata']['as_of']} · escenario: {data['metadata']['scenario']} · semilla: {data['metadata']['seed']} · moneda: MXN (campos monetarios en centavos).",'',
      '## Mapa de datos','',table([{'tabla':t,'filas':len(rows),'cobertura':data['metadata']['coverage'].get(t)} for t,rows in data['tables'].items()],40),
      '## Cómo leer el resultado','',
      'Las tablas detalladas se encuentran en `tables/`, los modelos consultables en `marts/` y sus consultas SQL en `lineage.json`. El almacén SQLite contiene claves y relaciones. `quality.json` contiene los resultados de validación. Los seis procesos generan solicitudes para agentes nativos y conservan sus estados y transiciones en `processes/`. Un proceso esperando agente todavía no tiene una decisión revisada.', '',
      'La utilidad y la caja tienen bases diferentes: entrega y créditos para ingresos de gestión; eventos de cobro, reembolso y pago para efectivo. El stock físico, reservas y tránsito tampoco son intercambiables. Los valores UNKNOWN permanecen desconocidos.', '',
      '## Control de calidad','',table([q for q in quality if q['status']!='PASS'] or [{'status':'PASS','resultado':'Contratos base conciliados; consultar warehouse-load.json para controles relacionales.'}]),'']
    explanations={
      'sales_daily':'Ventas reconocidas por fecha de entrega y créditos en su fecha; no pedidos captados ni efectivo cobrado.',
      'inventory_position':'Existencia del ledger, reservas, disponible y tránsito por variante. Revisar discrepancias de conteo antes de decidir compra.',
      'inventory_aging':'Actividad y antigüedad por SKU; la fecha más reciente de entrada no equivale a edad exacta por lote. Consultar definición.',
      'procurement':'Compras comprometidas, recibidas y pagos; el valor pendiente no es una nueva salida automática.',
      'cash_daily':'Eventos de caja en fechas efectivas. Flujo acumulado parte de cero, no constituye saldo bancario conocido.',
      'finance_monthly':'Reconocimiento, descuentos, créditos, costo y gastos de gestión. Márgenes retienen costos faltantes; no es contabilidad fiscal.',
      'channel_performance':'Atribución descriptiva de pedidos y resultados por canal; no representa incremento causal por publicidad.',
      'customer_cohorts':'Cohortes de primera entrega y maduración. Una cohorte reciente no tiene la misma ventana de oportunidad para recomprar.',
      'experiment_results':'Asignación y resultados simulados por brazo. Evaluar incertidumbre y guardrails, nunca tratarlos como prueba de demanda real.',
      'funnel_conversion':'Eventos identificados por sesión, lead y pedido. Interpretar solo denominadores compatibles; no dividir totales independientes.',
      'reconciliation':'Conciliación entre documentos, eventos y ledger. Las divergencias de conteo son problemas de negocio y requieren revisión.'}
    for name,rows in marts.items():
        lines+=['## '+name,'',explanations.get(name,''),'',table(rows),f'Tabla completa: [CSV](marts/{name}.csv) · [JSON](marts/{name}.json)','']
    lines+=['## Investigación y decisión','',
      'El registro `research.json` conserva fuentes públicas, población, fecha, acceso y límites. MOPRADEF sirve de contexto; no estima compras de calcetines. El producto ganador sigue siendo una hipótesis del negocio. La revisión de agentes debe proponer pruebas con métrica primaria, guardrail, población, ventana y cierre.', '',
      '## Procesos y responsabilidades','',
      '| Proceso | Responsable funcional | Entregable |','| --- | --- | --- |',
      '| procure-to-stock | Compras e inventario | Propuesta por variante y capital requerido |',
      '| lead-to-delivery | Operación comercial | Diagnóstico de conversión y entrega |',
      '| return-to-refund | Postventa | Conciliación de devolución, crédito y reembolso |',
      '| finance-close | Finanzas de gestión | Puente de utilidad y caja |',
      '| weekly-growth-review | Crecimiento | Aprendizaje de cohortes y experimentos |',
      '| market-to-experiment | Investigación | Prueba de demanda con regla de abandono |','']
    (folder/'DOSSIER.md').write_text('\n'.join(lines),encoding='utf-8')
    from .reporting import _table, _monthly_chart, _color_chart, _cash_chart
    chart_dir=folder/'charts';chart_dir.mkdir(exist_ok=True)
    finance=[{**r,'opex_cents':r.get('expense_accrual_cents')} for r in marts.get('finance_monthly',[])]
    variants={v['id']:v for v in data['tables']['variants']};products={p['id']:p for p in data['tables']['products']}
    inventory=[]
    for row in marts.get('inventory_position',[]):
        v=variants[row['variant_id']];product=products[v['product_id']]
        inventory.append({'category':product['category'],'color':v['color'],'available':row.get('available_qty')})
    def total(rows,key):
        values=[r.get(key) for r in rows]
        return sum(values) if values and all(isinstance(v,(int,float)) for v in values) else None
    cash=marts.get('cash_daily',[]);ci=total(cash,'cash_in_cents');co=[total(cash,k) for k in ('refund_out_cents','supplier_out_cents','expense_out_cents')]
    kpis={'cash_in_cents':ci,'cash_out_cents':sum(co) if all(v is not None for v in co) else None,'net_cash_cents':total(cash,'net_cash_change_cents')}
    charts={'finance.svg':_monthly_chart(finance),'sock-colors.svg':_color_chart(inventory),'cash.svg':_cash_chart(kpis)}
    for name,svg in charts.items():(chart_dir/name).write_text(svg,encoding='utf-8')
    count_rows=[{'table':name,'rows':len(rows),'coverage':data['metadata']['coverage'].get(name)} for name,rows in data['tables'].items()]
    blocks=[]
    for name,rows in marts.items():
        headings=list(rows[0]) if rows else ['status']
        body=[[('UNKNOWN' if r[h] is None else str(r[h])) for h in headings] for r in rows[:24]]
        blocks.append('<section><div class="eyebrow">SQL MART · '+escape(name)+'</div><h2>'+escape(name.replace('_',' '))+'</h2><p>'+escape(explanations.get(name,''))+'</p><div class="table-wrap">'+_table(headings,body)+'</div><p class="caption">'+str(min(24,len(rows)))+' de '+str(len(rows))+' filas · <a href="marts/'+escape(name)+'.csv">CSV completo</a> · <a href="marts/'+escape(name)+'.json">JSON completo</a></p></section>')
    toc=''.join('<span>'+escape(name.replace('_',' '))+'</span>' for name in marts)
    style="""body{margin:0;background:#f4f1e9;color:#243d34;font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1180px;margin:auto;padding:48px 32px}header{border-bottom:2px solid #243d34;padding:20px 0 40px}h1{font:64px/1.05 Georgia,serif;margin:24px 0}h2{font:32px/1.2 Georgia,serif;text-transform:capitalize;margin:10px 0 18px}p{max-width:850px}.eyebrow{font-size:11px;letter-spacing:.2em;font-weight:700;text-transform:uppercase}.notice{background:#e5cdaa;padding:12px 18px;margin-top:24px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;padding:24px 0}.metric strong{display:block;font:40px Georgia,serif}.metric span{font-size:12px;text-transform:uppercase;letter-spacing:.12em}section{padding:38px 0;border-bottom:1px solid #c6c6b7}.table-wrap{max-width:100%;overflow-x:auto;background:#fffdf8;border:1px solid #d6d6ca}table{border-collapse:collapse;font-size:12px;white-space:nowrap;width:100%}th{background:#e3e7dd;text-align:left;font-size:11px;padding:10px}td{padding:9px 10px;border-bottom:1px solid #e8e8df}tr:nth-child(even){background:#f7f6ef}.caption{font-size:12px;color:#57645a}a{color:inherit}figure{margin:24px 0}figure img{width:100%;height:auto}.toc{display:flex;flex-wrap:wrap;gap:8px}.toc span{border:1px solid #aeb8a8;padding:3px 8px;font-size:11px}footer{padding:40px 0;font-size:12px}@media(max-width:680px){main{padding:20px}h1{font-size:45px}.metrics{grid-template-columns:repeat(2,1fr)}}@media print{body{background:white}main{max-width:none;padding:0}section{break-inside:avoid}.table-wrap{overflow:visible}table{white-space:normal;font-size:8px}header{break-after:page}}"""
    html='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alma de Lujo · Business Analytics</title><style>'+style+'</style></head><body><main><header><div class="eyebrow">Alma de Lujo / Growth & Business Analytics / v0.2</div><h1>Del dato a una<br>decisión revisada.</h1><p>Inventario, comercio, finanzas y crecimiento en un mismo expediente: tablas relacionadas, consultas reproducibles y procesos con responsables.</p><div class="notice"><strong>SIMULACIÓN COMERCIAL</strong> · Escenario '+escape(data['metadata']['scenario'])+' · Corte '+escape(data['metadata']['as_of'])+'. No representa resultados reales de Alma de Lujo.</div></header><div class="metrics">'+''.join('<div class="metric"><strong>'+str(n)+'</strong><span>'+label+'</span></div>' for n,label in [(len(data['tables']),'tablas fuente'),(len(data['tables']['orders']),'pedidos sintéticos'),(len(data['tables']['variants']),'variantes'),(6,'procesos analíticos')])+'</div><div class="toc">'+toc+'</div><section><h2>Rendimiento y capital</h2><p>Los ingresos se reconocen por entrega; la caja usa eventos de pago. Los campos monetarios en las tablas están expresados en centavos MXN. UNKNOWN conserva información faltante.</p>' + ''.join('<figure><img src="charts/'+name+'" alt="'+escape(label)+'"><figcaption class="caption">'+escape(label)+' · datos sintéticos, consulte las tablas para valores exactos.</figcaption></figure>' for name,label in [('finance.svg','Ingreso, costo y gasto por mes'),('cash.svg','Puente de efectivo observado'),('sock-colors.svg','Disponible de calcetines de Pilates por color')])+'</section><section><h2>Tablas fuente</h2><p>Relaciones tipadas y conciliadas. Los archivos completos están en tables/ y el catálogo técnico en lineage.json.</p><div class="table-wrap">'+_table(['Tabla','Filas','Cobertura'],[[r['table'],str(r['rows']),str(r['coverage'])] for r in count_rows])+'</div></section>'+''.join(blocks)+'<section><h2>De la consulta al agente</h2><p>Cada proceso genera una solicitud con evidencia inmutable. El agente nativo produce observaciones, hipótesis y propuestas; un agente distinto revisa el resultado. Consulte processes/ para estados, respuestas y decision-packet.json cuando exista. Una solicitud pendiente todavía no es un análisis ejecutado.</p><p>Compras → inventario · Contacto → entrega · Devolución → reembolso · Cierre financiero · Revisión de crecimiento · Mercado → experimento.</p></section><footer>Reporte estático y exportable. Sin servidor ni aplicación. Las decisiones propuestas requieren criterio del responsable del negocio. Las fuentes públicas y sus limitaciones se conservan en research.json.</footer></main></body></html>'
    (folder/'DOSSIER.html').write_text(html,encoding='utf-8')
    with (folder/'DOSSIER.md').open('a',encoding='utf-8') as stream:
        stream.write('\n## Gráficos reproducibles\n\n'+'\n\n'.join('!['+name+'](charts/'+name+')' for name in charts)+'\n')
