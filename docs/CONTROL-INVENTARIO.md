# Control operativo de inventario

Alma OS puede generar un tablero privado e inmutable por corte a partir del libro operativo o del pack canónico de 22 tablas. El tablero usa el mismo kardex del sistema; no crea un inventario paralelo.

## Uso semanal

1. En una copia privada de `client/v1/Alma_de_Lujo_OPERACION_PLANTILLA.xlsx`, mantén estas hojas:
   - `sku_catalog`: una fila por variante, color y talla.
   - `inventory_movements`: cada entrada o salida física con identificador único.
   - `inventory_reservations`: apartados y liberaciones; no alteran la existencia física.
   - `inventory_counts`: conteo físico por SKU al cierre, incluida mercancía no vendible y tránsito observado.
   - `purchase_orders` y `purchase_receipts`: ordenado, recibido, inspección, aceptado y rechazado.
   - `loans`: producto prestado o bajo custodia externa.
2. Guarda el libro dentro de `.local`, por ejemplo `.local/Alma_OPERACION_SEMANA_01.xlsx`.
3. Ejecuta:

```powershell
.\run.ps1 inventory --source .local\Alma_OPERACION_SEMANA_01.xlsx --output-root .local\inventory-runs
```

También acepta directamente un source pack:

```powershell
.\run.ps1 inventory --source client\source-packs\v1\synthetic --output-root .local\inventory-runs
```

La prueba sintética sirve para aprender el flujo; no representa inventario real.

## Qué entrega

Cada corte queda en `.local/inventory-runs/<cut_id>/` y no se sobrescribe:

- `inventory-control.html`: tablero que puede abrirse sin servidor.
- `inventory-control.csv`: control por SKU para filtrar o compartir dentro del equipo autorizado.
- `inventory-control.json`: salida estructurada y cobertura de los datos.
- `receipt.json`: hashes de entrada y salida para verificar que el corte no cambió.
- `operating-cuts/`: copia verificada del registro relacional usado en el cálculo.

Por SKU muestra existencia física, existencia vendible, reservado, disponible, tránsito registrado, compra pendiente de recibir, inspección, no vendible, préstamos, fecha del último conteo, variación y salida neta observada de 30 días.

## Acciones y cierre

| Acción | Qué significa | Cierre esperado |
| --- | --- | --- |
| `COUNT_REQUIRED` | No existe un conteo físico válido. | Capturar el conteo y emitir un corte nuevo. |
| `RECONCILE_COUNT` | El kardex y el conteo no coinciden. | Investigar movimientos faltantes; registrar el ajuste aprobado como evento nuevo. |
| `COUNT_DUE` | El último conteo excede la antigüedad configurada. | Recontar el SKU. |
| `STOCKOUT_REVIEW` | Disponible conocido igual a cero. | Revisar demanda, tránsito y decisión de compra con responsable. |
| `RECONCILE_TRANSIT` | El tránsito observado no coincide con órdenes abiertas. | Corregir recepción, cancelación o conteo en el siguiente corte. |
| `REVIEW_COVERAGE` | La posición existe, pero alguna fuente no tiene cobertura completa. | Completar la fuente antes de aprobar una decisión. |
| `MONITOR` | Las conciliaciones del corte pasan. | Mantener el registro al día. |

El comando detecta y prioriza; no genera ajustes, compras ni promesas de venta. Tampoco propone cantidades de reabasto hasta que exista una política aprobada de cobertura objetivo, tiempo de entrega, lote mínimo y responsable.

Para exigir conteos más frecuentes, cambia el máximo permitido:

```powershell
.\run.ps1 inventory --source .local\Alma_OPERACION_SEMANA_01.xlsx --count-max-age-days 3
```
