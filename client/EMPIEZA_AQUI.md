# Alma de Lujo v0.3: empieza aquí

Este kit es una interfaz de Excel para revisar cada semana inventario, precios,
ventas agregadas y caja. Está pensado para una persona no técnica: no necesitas
Python, GitHub, una base de datos, un servidor ni una suscripción de IA. Trabaja
con datos propios agregados, sin nombres, teléfonos, correos, direcciones ni
credenciales.

Antes de capturar datos, abre [SISTEMA_ANALITICO.html](SISTEMA_ANALITICO.html)
para recorrer las fuentes, métricas, procesos, agentes y evidencia. La vista
[COSTOS_Y_OPERACION.html](COSTOS_Y_OPERACION.html) explica el costo unitario,
la recepción física, las obligaciones y la caja por escenario. Ambos funcionan
sin servidor; todos los datos visibles de la demostración son sintéticos.

Los dos libros se usan sin conexión:

- [Libro plantilla para tus datos](Alma_de_Lujo_PLANTILLA.xlsx)
- [Libro de ejemplo sintético](Alma_de_Lujo_EJEMPLO.xlsx)

Practica con [la sesión resuelta](DECISIONES_DEL_EJEMPLO.md): cambia una compra
del ejemplo y observa cuánto efectivo conserva el plan de 13 semanas.

El segundo libro es sólo una demostración didáctica con calcetines de Pilates y
otros productos deportivos. Sus cifras no son ventas, precios, inventario,
costos ni caja reales de Alma de Lujo.

## Tu primera semana: 15 a 25 minutos

### 1. Define el corte en `CONFIG` (2 minutos)

Usa una copia del libro plantilla. En `CONFIG` completa estas celdas; las
etiquetas visibles están en español y el nombre técnico entre paréntesis sólo
ayuda a ubicar la lógica:

- `CONFIG!B5` **Fecha de corte** (`as_of`).
- `CONFIG!B6` **Días de observación** (`observation_days`).
- `CONFIG!B7` **Días de seguridad** (`safety_days`).
- `CONFIG!B8` **Margen contribución objetivo** (`target_margin`).
- `CONFIG!B9` **Caja inicial** (`opening_cash`), sólo si la conoces y la usas como dato de gestión.
- `CONFIG!B10` **Piso protegido** (`cash_floor`).
- `CONFIG!B11` **Tope de compras elegido para el escenario** (`purchase_cap`).
- `CONFIG!B12` **Política revisada** (`policy_reviewed`).
- `CONFIG!B13` **Plan de caja completo** (`cash_plan_complete`).
- `CONFIG!B14` **Ventas completas** (`sales_complete`).

En las tres celdas de estado (`B12:B14`), usa `SI` únicamente cuando la fuente
correspondiente esté completa y revisada para el corte; usa `NO` si falta algo.

La moneda es MXN y los importes están en pesos. El libro no es una
conciliación fiscal ni bancaria. `CAJA` proyecta cierres diarios durante 91
días; no observa movimientos intradía.

### 2. Completa `CATALOGO` (3 a 5 minutos)

Agrega una fila por SKU. Para calcetines usa un SKU distinto para cada
combinación relevante de color y talla, por ejemplo `SOCK-ROSA-M`. Completa:

`sku`, producto, categoría, color, talla, estado, precio de lista, costo de
compra, flete de entrada, empaque, comisión, otro costo variable, días de
entrega, MOQ y múltiplo de empaque.

Los estados permitidos son `ACTIVO`, `PRELANZAMIENTO` y `PAUSADO`. Una idea, una
muestra o un producto no activo no se mezcla automáticamente con la cobertura
operativa de un SKU activo.

Los costos actuales y los históricos no deben mezclarse. Si el costo cambió,
conserva la referencia de origen y usa el costo que corresponde al escenario y
periodo que estás revisando. El precio objetivo es una simulación de gestión:
no incluye una conclusión fiscal, impuestos ni elasticidad de demanda.

### 3. Pega ventas diarias agregadas en `VENTAS` (3 a 5 minutos)

Usa una fila por combinación de fecha y SKU. Completa:

`date`, `sku`, unidades entregadas, unidades devueltas, unidades físicamente
reingresadas, ingreso neto después de descuentos/créditos, costo variable real
si lo tienes y `source_ref`.

Una devolución y un reingreso no son lo mismo. La devolución describe lo que
regresó; el reingreso describe lo que volvió físicamente a inventario. El
reembolso en efectivo va por separado en `CAJA`. No conviertas una celda vacía
en cero: cero significa que observaste explícitamente cero.

### 4. Toma el inventario en `STOCK` (3 a 5 minutos)

Usa un conteo correcto al corte, no una cifra recordada. Completa SKU, fecha de
conteo, existencia física, reservado, tránsito, ETA, confirmación de tránsito,
días disponibles, cantidad planeada y fecha de pago.

La existencia disponible es `on_hand - reserved`. El tránsito no es existencia
disponible. Sólo se considera tránsito elegible cuando su ETA está dentro del
horizonte y la confirmación es `SI` porque existe una fuente completa. Si la ETA
está vencida, queda para revisión. No agregues el mismo pedido abierto y el
mismo tránsito dos veces.

Una propuesta positiva es condicional: requiere SKU activo, conteo al corte,
ventana de ventas completa, política revisada, costo conocido, plazo, MOQ,
múltiplo, fecha de recepción y tope elegido para el escenario. La propuesta nunca crea ni envía
una orden.

### 5. Registra sólo el plan de caja existente en `CAJA` (2 a 4 minutos)

Usa una fila por movimiento planeado o confirmado: fecha, `ENTRADA` o `SALIDA`,
categoría, importe y `source_ref`. Incluye obligaciones de proveedores que ya
existen, cobros esperados, gastos y reembolsos de efectivo con su fecha.

Una cantidad que estás evaluando en `STOCK` se proyecta en `FLUJO_13_SEMANAS` con
la cantidad y fecha de pago elegidas. No la vuelvas a escribir en `CAJA`: eso
duplicaría la salida. Las propuestas de compra elegidas y las obligaciones ya
existentes son cosas distintas.

El plan muestra los cierres diarios y los agrupa en 13 semanas. Es una prueba de
capacidad bajo supuestos declarados, no el saldo intradía del banco.

### 6. Lee `DECISIONES` y `FLUJO_13_SEMANAS` (2 a 4 minutos)

Empieza por las filas con `REVISAR`, `DESCONOCIDO`, `BLOQUEADO` o
`INCONCLUSO`. Para cada propuesta, confirma:

1. qué decisión concreta se está considerando;
2. qué evidencia la respalda y qué dato falta;
3. cuál es la métrica principal;
4. cuál es el guardrail que no debe romperse;
5. quién es la persona responsable;
6. cuándo se revisará;
7. qué condición permite cerrarla.

Si una sugerencia está pendiente, puedes corregir o completar la fuente,
revisar el supuesto, registrar una decisión de mantenerla abierta, cambiar el
responsable o fijar una fecha de revisión. No puedes usar el libro para comprar,
pagar, reembolsar, publicar, enviar mensajes o cambiar una campaña.

## Reglas que evitan errores costosos

### Vacío no es cero

Una celda vacía significa que no hay evidencia suficiente. El número `0` sólo
significa cero observado. Esto aplica a ventas, stock, tránsito, costos,
atribución, caja y devoluciones.

### `SI` exige una fuente completa

Marca `SI` sólo cuando la fuente está completa para la ventana declarada y fue
revisada. Si faltan días de ventas, fechas de entrega, una cuenta de caja o una
confirmación de tránsito, deja `NO` y lee la propuesta como revisión pendiente.

### Margen, resultado y caja son lecturas diferentes

El margen de contribución usa costos variables del escenario. La caja usa
movimientos fechados. Un precio rentable en el papel no demuestra que haya
efectivo para pagar una compra. Un movimiento acumulado positivo no demuestra
saldo bancario disponible.

### Devolución, reingreso y reembolso tienen relojes distintos

No supongas que un reembolso implica reingreso físico. No repartas un reembolso
que sólo existe a nivel de pedido entre varias líneas sin una asignación
explícita.

### La sugerencia de compra depende de datos actuales

El resultado combina consumo observado, existencia disponible, tránsito elegible,
plazo, días de seguridad, MOQ, múltiplo, costo y tope elegido para el escenario. Un umbral de días
es una política provisional, no una garantía de servicio.

## Ejemplo corto, calculado y sintético

Estos números son inventados para explicar el flujo; no describen a la marca.

SKU `SOCK-ROSA-M`, estado `ACTIVO`:

| Dato | Valor |
| --- | ---: |
| Fecha de corte / días disponibles | 2026-09-21 / 14 días |
| Precio de lista | $520.00 |
| Costo de compra + flete + empaque + otro variable | $180.00 + $20.00 + $10.00 + $0.00 = $210.00 |
| Comisión | 5% |
| Margen objetivo | 50% |
| Ventas observadas | 14 entregadas, 1 devuelta, 1 reingresada en 14 días |
| Existencia / reservado | 12 / 2 |
| Tránsito confirmado | 3 unidades, ETA 2026-09-28; elegible con plazo de 14 días |
| Plazo / seguridad | 14 / 7 días |
| MOQ / múltiplo | 12 / 6 |

Consumo diario = `(14 entregadas - 1 reingresada) / 14 = 0.9286` unidades.
Disponibilidad = `12 - 2 = 10`. El tránsito es elegible porque `2026-09-21 <
2026-09-28 <= 2026-10-05` (corte más el plazo de 14 días). El horizonte de
consumo es `14 + 7 = 21` días; no se usa para ampliar la regla de elegibilidad
del tránsito. La necesidad antes de MOQ es:

`ceil(0.9286 × 21 - 10 - 3) = ceil(6.5) = 7` unidades.

El MOQ eleva 7 a 12 y el múltiplo de 6 mantiene 12. El libro muestra una
propuesta condicional de 12 unidades, no una orden.

Precio objetivo de gestión = `210 / (1 - 0.05 - 0.50) = 466.666...`, redondeado
hacia arriba a **$466.67**. Es un precio de escenario con costo conocido; no es
un precio fiscal ni prueba de demanda.

Si esas 12 unidades se pagan juntas a $200.00 de compra más flete por unidad,
el ejemplo carga `12 × $200.00 = $2,400.00` en la fecha elegida de pago dentro
del flujo de 91 días. Esa propuesta no se vuelve a capturar como salida en
`CAJA`.

## Límites del libro

El contrato admite hasta 100 SKU, 1,000 agregados de ventas por fecha y SKU,
250 entradas de plan de caja y 13 semanas de proyección. Si tus datos superan
esa capacidad, no borres filas ni dejes que el libro recorte silenciosamente el
periodo: conserva el corte completo y consulta al responsable del análisis.

El kit usa sólo agregados operativos. No contiene clientes identificables ni
ejecuta ninguna acción externa. La adopción real y la calidad de los datos
entregados sólo pueden confirmarse cuando el cliente use su propio corte.
