"""Read-only deterministic analyst policies; no model or external tool access."""
import hashlib
import json


def market_sources():
    return [
      dict(id='instagram-brand',title='Catálogo público Alma de Lujo',publisher='Alma de Lujo',url='https://www.instagram.com/almadelujooo/',observed_at='2026-09-22',coverage='Usuario confirmó ropa deportiva y calcetines de Pilates multicolor.',license='No concedida: no se copian fotos ni publicaciones.',limitation='Acceso automático sin contenido verificable. Prendas, precios y colores exactos pendientes de confirmación.',status='UNVERIFIED'),
      dict(id='inegi-mopradef',title='MOPRADEF 2025',publisher='INEGI',url='https://www.inegi.org.mx/programas/mopradef/default.html?init=1',observed_at='2026-09-22',coverage='Contexto nacional de actividad física; cambio conceptual y metodológico en 2025.',license='Consultar términos de libre uso INEGI; aquí se enlaza, no se redistribuye el dataset.',limitation='No mide demanda ni ventas de Alma o calcetines de Pilates. Comparabilidad temporal requiere revisar metodología.',status='CONTEXT'),
      dict(id='amvo-evo',title='Estudio de Venta Online 2026',publisher='AMVO',url='https://amvo.org.mx/descarga-evo-2026',observed_at='2026-09-22',coverage='Página pública del estudio de comercio electrónico mexicano.',license='Contenido de AMVO. Enlace únicamente; reporte sujeto a condiciones y formulario.',limitation='Resumen descargable requiere formulario; no se descargó ni se usaron cifras. Mercado agregado no demuestra oportunidad específica.',status='CONTEXT'),
      dict(id='trends-candidate',title='Interés de búsqueda: Pilates y calcetines',publisher='Google Trends',url='https://trends.google.com/trends/',observed_at=None,coverage='Fuente candidata; sin extracción ni observación realizada.',license='Revisar términos y método permitido antes de usar.',limitation='Interés relativo no equivale a demanda, tamaño de mercado ni ventas.',status='CANDIDATE')
    ]


def experiments():
    return [
      dict(id='EXP-SOCKS-01',title='Validar calcetines de Pilates como producto principal',hypothesis='La preferencia expresada por la dueña podría traducirse en contribución por visita superior al resto del catálogo.',primary_metric='Contribución por visita elegible con costo y atribución completos',guardrail='Tasa de devolución <= 10%, ningún SKU sobrevendido; costos y tráfico conocidos',window='28 días desde aprobación; no detener por resultados favorables tempranos',population='Visitas nuevas elegibles asignadas aleatoriamente 1:1 a dos vitrinas con igual precio y exposición',close_criterion='Antes de iniciar: fijar MDE y muestra con baseline. Cerrar a 28 días; si falta muestra o trazabilidad => INCONCLUSO. Sin baseline no lanzar ni afirmar causalidad.',status='DRAFT_APPROVAL_REQUIRED',evidence_refs=['market/instagram-brand','inventory']),
      dict(id='EXP-COLOR-02',title='Preferencia de color de calcetines',hypothesis='Las solicitudes de color pueden orientar un siguiente lote pequeño.',primary_metric='Proporción de intención explícita por color entre respuestas válidas',guardrail='Una respuesta por participante sintético; registrar sin preferencia y faltantes; no comprar automáticamente',window='14 días desde aprobación',population='Participantes que voluntariamente responden una encuesta; sesgo de autoselección explícito',close_criterion='Consolidar conteos y cobertura al día 14; menos de 30 respuestas => INCONCLUSO. Intención no demuestra compra.',status='DRAFT_APPROVAL_REQUIRED',evidence_refs=['inventory','market/instagram-brand'])
    ]


def execute_action(action):
    raise PermissionError('External actions are not implemented. A human must act in an authorized system.')


def build_decisions(report):
    blocked=report['meta']['status']!='PASS'
    low=[r['sku'] for r in report['inventory'] if r['status'] in ('REORDER','STOCKOUT')]
    packet=dict(id='decision-'+hashlib.sha256(json.dumps({'meta':report['meta'],'quality':report['quality'],'kpis':report['kpis'],'inventory':report['inventory']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16],version='1.0',status='BLOCKED' if blocked else 'REVIEW',facts=[dict(text='El conjunto es sintético y no representa ventas reales.',evidence_refs=['meta/synthetic']),dict(text='Estado de reconciliación: '+report['meta']['status'],evidence_refs=['quality'])],unknowns=['Demanda real, costos y precios reales, operación de la dueña y catálogo exacto pendientes.','No existe baseline para atribuir impacto incremental.'],hypotheses=['Calcetines de Pilates: candidato a producto principal, según el usuario; pendiente de validación.'],actions=[dict(description='Revisar y corregir evidencia faltante antes de usar indicadores.' if blocked else 'Revisar cobertura por color y diseñar un lote piloto; aprobación humana antes de comprar.',approval_required=True,execution='BLOCKED')])
    if low and not blocked:
        packet['facts'].append(dict(text='SKUs con umbral demo de reposición o agotados: '+', '.join(low),evidence_refs=['inventory/'+sku for sku in low]))
    # Each analyst consumes the same immutable report; no analyst owns arithmetic.
    from copy import deepcopy
    finance=deepcopy(packet);finance['id']=packet['id']+'-finance'
    finance['facts']=[dict(text='El resultado operativo y el efectivo observado son medidas separadas en este caso sintético.',evidence_refs=['kpis/operating_proxy_cents','kpis/net_cash_cents']),dict(text='El costo de venta usa costos estándar de artículos entregados, con reversión de restock.',evidence_refs=['kpis/cogs_cents'])]
    finance['hypotheses']=['El calendario de compras y cobros puede explicar diferencias entre resultado y efectivo; requiere revisar eventos.']
    finance['actions']=[dict(description='Revisar el puente ingreso-costo-gastos-efectivo y la política provisional con la dueña.',approval_required=True,execution='BLOCKED')]
    growth=deepcopy(packet);growth['id']=packet['id']+'-growth'
    growth['facts']=[dict(text='Existen diseños de experimento pendientes de aprobación; no hay resultados de experimentos reales.',evidence_refs=['experiments']),dict(text='El tráfico por canal conserva los denominadores desconocidos.',evidence_refs=['channels'])]
    growth['hypotheses']=['Calcetines de Pilates multicolor: candidato a producto principal comunicado por el usuario.']
    growth['actions']=[dict(description='Revisar la población, métrica, guardrail, ventana y criterio de cierre de EXP-SOCKS-01 y EXP-COLOR-02 antes de aprobar cualquier ejecución.',approval_required=True,execution='BLOCKED')]
    packets=[packet,finance,growth]
    for result in packets: validate_packet(result,report)
    return packets


def resolve_ref(report, ref):
    if not isinstance(ref,str) or not ref or len(ref)>200: return False
    value=report
    for part in ref.split('/'):
        if isinstance(value,dict):
            if part not in value:return False
            value=value[part]
        elif isinstance(value,list):
            match=next((r for r in value if isinstance(r,dict) and (r.get('id')==part or r.get('sku')==part)),None)
            if match is None:return False
            value=match
        else:return False
    return True


def validate_packet(packet, report):
    required={'id','version','status','facts','unknowns','hypotheses','actions'}
    if not isinstance(packet,dict) or set(packet)!=required:raise ValueError('Invalid decision packet fields')
    if not isinstance(packet['id'],str) or not packet['id'] or packet['version']!='1.0' or packet['status'] not in ('REVIEW','BLOCKED'):raise ValueError('Invalid decision identity/state')
    if report['meta']['status']!='PASS' and packet['status']!='BLOCKED':raise ValueError('Quality failures must block decisions')
    for key in ('facts','unknowns','hypotheses','actions'):
        if not isinstance(packet[key],list) or not packet[key]:raise ValueError('Packet lists required')
    for fact in packet['facts']:
        if not isinstance(fact,dict) or set(fact)!={'text','evidence_refs'} or not isinstance(fact['text'],str) or not fact['text']:raise ValueError('Invalid fact')
        if not isinstance(fact['evidence_refs'],list) or not fact['evidence_refs'] or not all(resolve_ref(report,r) for r in fact['evidence_refs']):raise ValueError('Unresolved evidence')
    for key in ('unknowns','hypotheses'):
        if not all(isinstance(v,str) and v for v in packet[key]):raise ValueError('Invalid narrative list')
    for action in packet['actions']:
        if not isinstance(action,dict) or set(action)!={'description','approval_required','execution'} or not isinstance(action['description'],str) or not action['description'] or action['approval_required'] is not True or action['execution']!='BLOCKED':raise ValueError('Unsafe action')
    return True
