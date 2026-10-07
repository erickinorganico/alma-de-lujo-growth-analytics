# Caja de la app al contrato operating-v1

El adaptador recibe `alma.app-analytics-handoff.v1` producido por el
[exportador de la app](https://github.com/erickinorganico/alma-de-lujo-system/pull/8).
Prepara un paquete nativo de **caja conciliada**, validado con `parse_pack` y
compatible con `build_operating_workspace`. No ejecuta el ciclo de agentes.

## Alcance

- Los cobros parciales siguen siendo eventos distintos, incluso en un pedido.
- Cobro es entrada; reembolso y gasto revisado como pagado son salidas.
- Cada evento conserva una identidad estable derivada de instalación + ID de
  caja. Cambiar la revisión no cambia el ID. Otro negocio utiliza otra identidad.
- `receipt.json` vincula IDs de caja con IDs analíticos y conserva huellas de
  entrada, revisión y CSV. La trazabilidad al pedido permanece en el handoff.
- Una anulación `expense_reverse` corrige el registro; no demuestra recepción
  de dinero. Se excluye junto con su gasto original, con ambos IDs en el recibo.
  Si solo uno cae dentro del periodo, el adaptador rechaza ese corte: debe
  resolverse la corrección antes de conciliarlo. No inventa un reembolso.
- Solo se habilitan `cash_events` y `cash_balance_evidence`, con cobertura
  `PARTIAL`. Las otras veinte fuentes quedan `MISSING`, nunca cero implícito.
- No convierte cobros en ventas ni componentes físicos en SKU vendibles.
  Ventas, conjuntos, inventario y costos siguen pendientes de otro adaptador.

## Preparar la revisión privada

Crear una revisión `alma.app-cash-review.v1` con exactamente estos campos:

| Campo | Contenido requerido |
| --- | --- |
| `schema` | `alma.app-cash-review.v1` |
| `handoff_sha256` | Huella exacta del handoff revisado |
| `source_instance_id` | UUID de la instalación, igual al exportador |
| `window_start`, `window_end` | Fechas ISO del periodo incluido |
| `cutoff_at`, `timezone` | Corte con offset e IANA coherentes; por ejemplo America/Tijuana |
| `opening_balance_cents`, `closing_balance_cents` | Saldos observados enteros en centavos MXN; no estimados |
| `opening_observed_at` | Inicio del primer día, 00:00:00, con offset |
| `closing_observed_at` | Cierre del último día, 23:59:59, con offset |
| `evidence_ref` | Código opaco de evidencia privada, hasta 64 caracteres, empezando por letra |
| `reviewed_cash_ids` | Lista exacta y sin repetidos de todos los IDs de caja del periodo |

Revisar estos IDs significa comprobar que los movimientos son caja observada
y que las correcciones son anulaciones de registro, no pagos bancarios nuevos.
La evidencia que respalda los saldos se conserva privadamente bajo el código
de referencia. La herramienta valida consistencia, no la autenticidad de un
estado de cuenta. No rellenar los saldos a partir de la suma del ledger para
hacer pasar la conciliación.

La app solo guarda fecha, sin hora del movimiento: se exige un periodo de días
completos. Corte y cierre deben estar en el último día; cierre no puede superar
el corte. Los offsets de las tres marcas se verifican contra la zona IANA.
Se rechazan saldos incompatibles, huellas modificadas, revisiones de otra fuente,
IDs duplicados, importes no enteros y correcciones sin pareja. Se conserva la
clase PRIVATE o SYNTHETIC_EXAMPLE, sin reclasificar datos privados.

## Ejecutar desde el checkout de analytics

```powershell
New-Item -ItemType Directory -Force .local/app-cash | Out-Null
python -m alma.app_cash_intake --handoff .local/operaciones.private.json --review .local/caja-review.private.json --output-root .local/app-cash
```

El resultado es `.local/app-cash/<huella>/pack/` (metadata y 22 CSV nativos)
y `receipt.json`. El validador completo debe pasar antes de crear el destino.
Repetir la misma entrada y revisión comprueba todos los bytes y reutiliza el
resultado. Una carpeta existente alterada o incompleta se rechaza, no se repara
ni se sobrescribe. El recibo se escribe al final; un fallo de disco puede dejar
una carpeta incompleta que debe conservarse para diagnóstico.

Para cargar el paquete con el motor existente se usa
`alma.operating_workspace.build_operating_workspace(ruta_pack, private_root=raiz_privada)`.
La prueba de integración ejecuta este paso sobre datos sintéticos, incluida
la validación de relaciones de la base generada. El CLI prepara el paquete y
no activa por sí mismo una base analítica.

Cada resultado representa un corte; no concatenar exportaciones superpuestas.
Una revisión nueva puede cambiar el corte conservando IDs de hechos, pero no
autoriza sumar dos veces los movimientos ni modificar un corte histórico.
Todos los handoffs, revisiones, CSV y recibos del negocio quedan fuera de Git.

## Verificación

`python -B -m unittest tests.test_app_cash_intake tests.test_operating_contracts tests.test_operating_intake tests.test_operating_marts_finance -v`

Estas suites usan datos sintéticos, el parser real y el constructor nativo de
workspace. Los saldos y los movimientos reales necesitan su propia evidencia.
