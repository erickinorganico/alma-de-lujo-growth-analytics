# Costos y operación v0.3

## Propósito

Esta ampliación vuelve trazable la decisión de comprar, recibir, aceptar, pagar y preservar caja. Extiende el sistema analítico existente; no crea una tienda, ERP, contabilidad fiscal ni ejecución autónoma.

## Estado de la ampliación

| Capacidad solicitada | Estado en el repositorio | Evidencia o límite |
|---|---|---|
| Variantes, compras, recepciones, pagos y gastos base | EXISTENTE | Tablas base, 11 marts y paquetes de decisión v0.2 |
| Versiones y componentes de costo | IMPLEMENTADO LOCAL | `cost_versions.csv`, `cost_components.csv` |
| Asignación reconciliada de costos | IMPLEMENTADO LOCAL | `cost_allocations.csv`; asignado + remanente = fuente |
| Compra, recepción, inspección y aceptación | IMPLEMENTADO LOCAL | `purchase_orders_ops.csv`, `purchase_receipts_ops.csv` |
| Obligaciones canónicas y pagos aplicados | IMPLEMENTADO LOCAL | `obligations.csv`, `obligation_payments.csv` |
| Caja de 8 semanas por escenario | IMPLEMENTADO LOCAL | `cash_scenario_events.csv`; BASE separado de REINVESTIR_TOP |
| Aplicación transaccional React/Supabase | CONFLICTO DE ALCANCE | El contrato vigente exige CLI, datos relacionales y reportes analíticos |
| Banco, impuestos, clientes y operación reales | PENDIENTE | Requiere fuentes y autorización; la entrega pública usa datos sintéticos |
| Presupuestos por drop/canal, préstamos y cierres fiscales | PARCIAL/PENDIENTE | El modelo deja puntos de extensión sin fabricar evidencia |

## Contratos de datos

Las ocho tablas de la ampliación declaran grano, clave primaria, campos, cantidad de filas, uso de decisión, referencias de evidencia y SHA-256 en `client/costs-operations-manifest.json`. Todos los importes son centavos MXN enteros. Cada fila pública lleva `synthetic=1`.

El costo de gestión pertenece a una versión con fecha efectiva. Sus componentes tienen clasificación, calidad (`documented`, `estimate`, `missing`) y referencia. Una suma conocida puede mostrarse cuando la cobertura es parcial, pero el costo unitario completo, margen y ganancia sobre costo quedan pendientes.

## Métricas

Cada definición incluye fórmula, unidad, grano, ventana, tablas fuente, comportamiento ante desconocidos, guardrail y uso de decisión.

- `known_cost_sum`: suma de componentes conocidos sin duplicar inclusiones.
- `contribution_margin`: `(precio - comisión - costo unitario completo) / precio`.
- `markup_on_cost`: `(precio - comisión - costo unitario completo) / costo unitario completo`.
- `purchase_receipt_bridge`: pedido = recibido + por recibir; recibido = aceptado + inspección + rechazado.
- `obligation_balance`: obligación original menos pagos observados aplicados.
- `cash_scenario_closing`: apertura más entradas fechadas menos salidas fechadas durante ocho semanas.

Margen y ganancia sobre costo son razones distintas. Mientras la base fiscal esté pendiente, la entrega no denomina a ninguna de ellas “margen neto”.

## Reglas operativas

1. Sólo unidades aceptadas pasan a disponibilidad desde una recepción.
2. Una orden comercial, una recepción física, una obligación y un pago son hechos separados.
3. La obligación es el hecho económico canónico; su origen no se vuelve a sumar como deuda.
4. BASE, esperado y escenario no autorizado permanecen separados.
5. Ningún resultado aprueba compras, cambia precios, mueve dinero ni publica contenido.
6. Las simulaciones son comparaciones inmutables y siempre conservan su etiqueta sintética.

## Vertical slice verificable

`python scripts/build_costs_operations.py` genera ocho CSV, el manifiesto y `client/COSTOS_Y_OPERACION.html`. El ejemplo incluye una compra de 20 unidades, 18 recibidas, 16 aceptadas, 2 en inspección y 2 aún por recibir; una obligación de $1,800 que cuadra con la orden, con $1,000 pagados y $800 pendientes; un saldo inicial supuesto y no conciliado; y un escenario de reinversión separado de la caja base. Los SKU se resuelven contra `client/example-input.json` mediante un puente explícito y verificable.
