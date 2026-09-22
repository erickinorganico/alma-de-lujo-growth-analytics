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
    # Fully escaped plain-text companion is deliberate: the rich tables live in Markdown/CSV.
    html='<!doctype html><html lang="es"><meta charset="utf-8"><title>Alma de Lujo · Dossier</title><style>body{max-width:1300px;margin:40px auto;padding:0 24px;background:#faf8f3;color:#18372e;font:16px/1.55 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.55 monospace}h1{font-size:38px}a{color:#18372e}</style><h1>Alma de Lujo · Dossier analítico</h1><p>Simulación comercial. Tablas completas en los archivos CSV del entregable.</p><pre>'+escape('\n'.join(lines))+'</pre></html>'
    (folder/'DOSSIER.html').write_text(html,encoding='utf-8')
