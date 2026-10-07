# Conciliación de unidades de la app

El exportador `app/scripts/export_analytics.py` de `alma-de-lujo-system` conserva
dos dimensiones: líneas comerciales y componentes físicos. Un conjunto puede
consumir A + B; una venta individual puede consumir A. Importar ambos productos
como existencias independientes duplicaría A.

`alma.app_inventory_reconciliation` verifica esa relación sobre un intercambio
privado de una revisión concreta. No abre SQLite ni cambia la app.

```powershell
python -m alma.app_inventory_reconciliation --handoff .local/handoff.private.json --output .local/inventory-reconciliation.private.json
```

El directorio debe existir y el archivo de salida debe ser nuevo. Un error de
integridad ocurre antes de crear el informe; un archivo existente no se sustituye.
La salida sigue siendo privada aunque sólo incluya identificadores internos.
No subir intercambios ni informes reales a GitHub. Sólo un marcador explícito
`SYNTHETIC_EXAMPLE` se conserva como sintético.

## Qué comprueba

- Hash del intercambio, UUID de instalación y revisión; el hash comprueba
  integridad, no autenticidad ni exactitud de los datos de origen.
- Identidades únicas, cantidades enteras, total de cada pedido y ciclo de estados.
- Requerimientos derivados de los componentes guardados en cada línea histórica.
  Si el catálogo actual cambió, conserva la composición histórica y lo señala.
- Una salida física por componente y pedido entregado; un reingreso por componente
  sólo si la devolución completa declara `restocked=true`. Cobros y reembolsos
  no cambian existencias ni se reinterpretan como ventas.
- Secuencia íntegra de movimientos y vínculo exacto de cantidad, fecha y pedido.
  Dos movimientos duplicados no se aceptan aunque sumen la cantidad esperada.
- Existencia = último conteo + movimientos con secuencia mayor que su `cursor`.
  Un reconteo en el mismo día absorbe los movimientos anteriores al cursor.
- Reservado = reserva externa del conteo + pedidos actualmente apartados.
  Sin conteo o sin reserva conocida, el valor correspondiente sigue siendo `null`.

Las cantidades físicas son **unidades de la app**. `pieces_per_unit` se conserva
como metadato: un par con dos piezas sigue descontando una unidad, no dos.
Se incluyen las cinco tallas admitidas por la app para cada componente; la falta
de conteo de una talla aparece expresamente, aunque no tenga movimientos.
Los estados negativos, cronologías incompatibles o relaciones incompletas bloquean
el informe. El comando no rellena ni repara el registro.

## Cómo leer el resultado

`reconciliation_status=PASS` confirma consistencia de las relaciones comprobadas.
`scope=app_revision_snapshot` es una foto de la revisión exportada, no una
reconstrucción a una fecha arbitraria. `commercial_lines` conserva cantidades
pedidas, entregadas, devueltas y reingresadas con sus fechas; el importe pedido
no se presenta como ingreso reconocido. `component_links` explica cómo cada
línea consume componentes. `physical_positions` conserva conteo, cursor,
movimientos aplicados, reservas activas y disponibilidad.

El informe se vincula al hash del estado y del intercambio; su propio
`report_sha256` se calcula sobre todo el contenido excepto ese campo.
Una revisión distinta produce un informe distinto. No importar ni sumar informes
de revisiones sucesivas como si fueran movimientos nuevos.

## Pendiente para operating-v1

`import_ready=false` y `coverage=UNDECLARED` permanecen siempre. El contrato nativo
actual exige que `sales_aggregates` y `SALE_OUT` compartan SKU; la app distingue
SKU comercial de componentes físicos. Hace falta un puente explícito en el
contrato y sus cálculos, además del mapeo de canales, ventana/corte, política de
reconocimiento de devoluciones y costos históricos. No se fabrican movimientos
comerciales para superar el validador ni se recalculan costos con precios actuales.

Este informe complementa el [adaptador de caja](APP-CASH-INTAKE.md). No es un
paquete `operating-v1`, respaldo, prueba de saldo real o ciclo analítico con agentes.

Pruebas sintéticas:

```powershell
python -B -m unittest tests.test_app_inventory_reconciliation -v
```
