# Aceptación del sistema analítico del cliente

Estado: **PASS_WITH_LIMITS**, validado el 2026-09-22. La aceptación técnica cubre estructura, hashes, linaje, cálculos y uso offline con datos sintéticos. No prueba adopción ni autoriza decisiones reales.

## Propósito

El cliente necesita tomar decisiones semanales para ropa deportiva y calcetines de Pilates: reponer por color y talla, ajustar o sostener precio, proteger caja, reducir devoluciones y distinguir canales, cohortes y experimentos. El sistema sólo es útil si cada conclusión lleva a evidencia local verificable y explicita qué dato falta. Los números del almacén v0.2 son sintéticos; la aceptación técnica no prueba demanda, margen ni adopción reales.

## Criterios verificables del paquete cliente

La manifestación `client/system-manifest.json` debe declarar inventario de entidades, modelos, procesos, roles y recursos del cockpit. La prueba contrasta cada entidad con fuentes autoritativas del repo y con hashes SHA-256; un `count` escrito a mano no constituye evidencia. Los conteos esperados del contrato actual son exactamente 30 fuentes, 11 marts, 6 procesos de negocio y 7 roles. Los seis procesos analíticos son una capa adicional: no deben contarse como sustitutos de los procesos de negocio.

Cada fuente debe resolver a una relación existente y documentar grano, clave primaria, campos, conteo de filas, marcador sintético y uso para decisiones. El conteo debe concordar con `evidence/v0.2/workspace/workspace.json` o con una fuente equivalente declarada y cuyo hash se valide. Ningún valor personal identificable ni secreto puede aparecer en metadatos o extractos del cockpit.

Cada mart debe enlazar a SQL existente y tener fórmula/definición calculable, unidad, grano, ventana temporal, fuentes upstream, significado de unknown/null, guardrail y decisiones que informa. Los once nombres deben coincidir con `models/marts/*.sql` y la evidencia de lineage. La atribución de canal es descriptiva; cohortes inmaduras son desconocidas; resultados de experimento no son inferencia causal. Caja es movimiento, no saldo bancario. Una devolución, una nota de crédito y un reembolso tienen hechos y fechas distintos.

El linaje debe formar una cadena resoluble desde fuente a mart, y de mart a proceso/rol/cockpit cuando se muestre una conclusión. Debe detectar referencias rotas, ciclos no explicados, campos sin fuente y hashes ausentes o divergentes. El HTML no puede declarar una métrica que no aparezca en el linaje declarado.

Cada rol de agente debe informar propósito/role, inputs, outputs, autoridad, revisión independiente y evidencia. La autoridad nunca permite ejecutar pedidos, pagos, reembolsos, cambios de precio ni publicaciones. El rol reviewer debe ser distinto del analista revisado. La evidencia debe ser un archivo o puntero local comprobable; «IA» o el nombre de un agente no son evidencia.

Cada proceso debe informar trigger, estados legales, controles, excepciones y decisión/artefacto resultante, todos ligados a su definición normativa. Las recomendaciones son condicionales y necesitan responsable humano; la interfaz no debe representarlas como aprobación o acción ejecutada.

Todos los enlaces locales del HTML y del manifiesto deben resolver dentro del paquete/repo esperado. Bloquear URLs externas, recursos remotos, llamadas de red, píxeles, scripts externos o dependencias que impidan el uso offline. El cockpit debe indicar claramente «datos sintéticos» en su contexto de apertura y en cada vista o cifra con apariencia de dato observado. No mezclar investigación pública de mercado con ventas de Alma.

## Adenda candidata de costos y operación v0.3/v0.4

La adenda `ALMA_OS_Handoff_Ampliacion_Costos_y_Operacion_v0_3.md` sirve como fuente candidata de requisitos, no como evidencia de implementación. El cliente de costos puede sumar una extensión `client/costs-operations-manifest.json` y tablas CSV. Debe validar las 30 fuentes base por separado; las entidades/métricas propuestas nuevas se cuentan y etiquetan en un grupo de extensión, nunca se usan para inflar ni redefinir el conteo base.

Para cada capacidad propuesta, el reporte de brecha registra uno de estos estados con evidencia y referencia/version/hash: `EXISTS` (implementación verificable), `SPECIFIED` (contrato explícito, sin prueba de código), `PARTIAL` (parte verificable y brecha citada), `MISSING` (no se encontró evidencia en el ámbito inspeccionado) o `CONFLICT` (evidencia normativa/técnica contradictoria). Distinguir código, contrato, datos/demo y uso real; un mock o pantalla de demo no es persistencia. La matriz cubre al menos ficha y versión de costos, líneas/asignaciones compartidas, compras/recepciones, obligaciones y pagos, caja real/comprometida/escenario, calidad, permisos, historial y reconciliación.

Las métricas deben definir por separado markup/ganancia sobre costo = (precio − costo) / costo y margen bruto = (venta neta − COGS) / venta neta. Por ejemplo, costo 100 y precio 150 da markup 50% y margen 33.33%; no intercambiar etiquetas ni activar la meta de «50%» sin definición aprobada. Contribución antes/después de adquisición también son medidas distintas. Costos o impuestos faltantes deben permanecer UNKNOWN; no presentar utilidad/margen final sin el tratamiento que corresponda.

Costos necesitan componentes con origen, moneda/FX si aplica, fecha, cobertura, método de asignación, redondeo reconciliado, aprobación/versionado y snapshot histórico. Una versión posterior no reescribe lo que se sabía al vender; todo recálculo identifica versión anterior/nueva, fecha y motivo. Suma asignada debe reconciliar con fuente compartida sin duplicar el total global.

Compra, recibido físico, pago aplicado y obligación restante son hechos separados. Un recibo no duplica movimiento de inventario. Un pago reduce saldo de obligación y caja cuando liquida; una factura/orden/comprobante referidos a la misma obligación no multiplican el compromiso. La caja presenta tres capas sin sumar doble: hechos liquidados, obligaciones/entradas esperadas respaldadas y supuestos de escenarios. Fechas desconocidas no reciben una fecha inventada. Un cambio de ventas supuesto sólo cambia proyección, nunca venta o stock real.

La extensión puede documentar visión de costos/operación con estado `SPECIFIED`, pero no afirmar que React, Supabase, autenticación, persistencia transaccional o una app web están implementados si sólo existe un HTML estático o contrato. Cada capacidad y riesgo conserva su estado y evidencia independiente.

## Prueba orientada a decisiones

La inspección cualitativa debe mostrar que se puede responder con evidencia y límites a estas preguntas:

- ¿Qué variante color/talla amerita reposición? Usar disponibilidad (on-hand menos reservas), conteo y fecha, tránsito, ventas netas en ventana, stockout/prelaunch, demanda no atendida, MOQ/paquete, costo y caja. Si cobertura, costo o conteo está ausente/viejo, bloquear la cantidad sugerida o marcarla desconocida.
- ¿Qué precio cubre costo y margen objetivo? Mostrar unidad MXN, fórmula de contribución y el supuesto de costos variables; separar precio observado sintético de política aprobada. Si faltan costos, no publicar margen como cero.
- ¿La caja alcanza para el plan? Distinguir cobros/reembolsos/pagos por fecha, obligaciones, compras planeadas y piso protegido. No llamar saldo a movimientos; señalar que intradía no se observa.
- ¿Dónde revisar devoluciones? Separar unidades devueltas, condición de reingreso, nota de crédito e importe reembolsado. No asumir que devolución física y flujo de efectivo ocurren juntas.
- ¿Qué canal/funnel/cohorte/experimento merece revisar? Exponer denominadores, cobertura y ventanas; mantener sesiones agregadas aparte de leads vinculados, cohortes inmaduras como UNKNOWN y experimentos como sintéticos/descriptivos sin lift causal.

La demostración no debe forzar una recomendación cuando las restricciones son insuficientes. Debe permitir seguir cada cifra hasta su fuente o ver UNKNOWN/REVIEW con causa y próximo dato requerido.

## Revisión y dictamen

`tests/test_client_system.py` valida estructura y contenido contra evidencia, no sólo contra autorreportes del manifiesto. Debe incluir controles negativos con manifiestos mutados para conteo sin fuente/hash, ruta rota, fórmula vacía, lineage incompleto, autoridad de ejecución, URL externa y ausencia de marca sintética. La evaluación final informa PASS/FAIL/BLOCKED por criterio y hallazgos accionables. Mientras falten el manifiesto o el HTML final, el estado es BLOCKED; un test todavía no ejecutado no equivale a PASS.

La aceptación de este contrato permite considerar revisable el sistema de información. Aún requiere verificar la hoja Excel en motor compatible, operación con datos privados, y evidencia real de adopción/decisiones para afirmar utilidad comercial.

## Recibo de ejecución v0.3

La entrega publicada se comprobó con las siguientes puertas independientes:

- `scripts/build_client_system.py --check`: PASS, con 30 fuentes base, 22,844 filas, 11 marts, 137 columnas de métricas, 6 procesos, 7 roles, 6 paquetes de decisión, 49 hechos cotejados y 60 controles sin hallazgos.
- `tests.test_client_system`: 6/6; `tests.test_costs_operations`: 9/9; `tests.test_client_review`: 28/28.
- suite completa: 110 pruebas, seis escenarios y cero fallos/errores.
- 28 workbooks adversariales recalculados en Microsoft Excel 16.0 build 20326: 5,349 comparaciones contra el oráculo Decimal, cero diferencias.
- los dos libros entregados fueron recalculados por el mismo motor y verificados contra sus hashes exactos; el ejemplo aprobó 345 controles y la plantilla 8 controles de estructura/privacidad.
- seis exportaciones PDF de `INICIO`, `DECISIONES` y `FLUJO_13_SEMANAS` se revisaron como páginas completas, sin cortes visibles.
- el ZIP offline contiene 152 entradas; el atlas incluye 140 archivos con hash y sus 189 enlaces locales resuelven después de extraerlo.

El dictamen permanece `PASS_WITH_LIMITS`: las 30 fuentes base, las ocho tablas de ampliación y los saldos son sintéticos. La caja inicial de la ampliación es un supuesto sin conciliación bancaria y la base fiscal está pendiente, por lo que el margen mostrado no es utilidad neta. Estos límites están visibles en el producto y bloquean cualquier lectura como operación real.
