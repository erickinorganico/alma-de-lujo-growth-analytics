# Instrucciones completas de Alma OS

Esta es la guía principal para instalar, consultar y operar Alma OS. Elige el recorrido que corresponda:

| Necesidad | Recorrido |
| --- | --- |
| Consultar la entrega sin instalar Python | [Abrir el paquete público](#1-consultar-la-entrega-sin-python) |
| Registrar y controlar inventario real | [Preparar el checkout operativo](#2-preparar-el-checkout-operativo) y [controlar inventario](#4-generar-el-control-de-inventario) |
| Preparar análisis, agentes y decisiones semanales | [Ejecutar el ciclo semanal](#6-ejecutar-el-ciclo-analítico-semanal) |

Los ejemplos comerciales del repositorio son sintéticos. Los archivos con datos reales deben permanecer en `.local/`, carpeta ignorada por Git.

## 1. Consultar la entrega sin Python

La versión pública está en [GitHub Releases](https://github.com/erickinorganico/alma-de-lujo-growth-analytics/releases/tag/v1.0.0). Descarga el ZIP y su archivo `.sha256`, guárdalos juntos y ejecuta en PowerShell:

```powershell
$expected = (Get-Content .\Alma_OS_v1.0.0.zip.sha256 -Raw).Split(' ')[0].Trim()
$actual = (Get-FileHash .\Alma_OS_v1.0.0.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'El ZIP no coincide con su checksum.' }
Expand-Archive -LiteralPath .\Alma_OS_v1.0.0.zip -DestinationPath .\Alma_OS_v1.0.0 -ErrorAction Stop
```

Abre `Alma_OS_v1.0.0\PORTAL\index.html`. El portal funciona sin servidor y no envía información a internet. La plantilla y el ejemplo están en `FUENTES`.

El ZIP v1.0.0 es material de consulta. No contiene el runtime necesario para generar controles de inventario o ciclos nuevos; esas funciones se ejecutan desde el repositorio.

## 2. Preparar el checkout operativo

Requisitos: Windows PowerShell, Git y Python 3.11 o posterior. Python 3.12 es la versión usada por CI.

```powershell
git clone https://github.com/erickinorganico/alma-de-lujo-growth-analytics.git
cd alma-de-lujo-growth-analytics
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-client.txt
.\run.ps1 inventory --help
```

Si `py -3.12` no existe, instala Python 3.11 o posterior y crea `.venv` con el ejecutable disponible. `run.ps1` usa primero `.venv\Scripts\python.exe`, por lo que no depende de otro Python configurado globalmente.

Prepara el área privada y copia la plantilla operativa:

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
Copy-Item .\client\v1\Alma_de_Lujo_OPERACION_PLANTILLA.xlsx .\.local\Alma_OPERACION_SEMANA_01.xlsx
```

Antes de capturar hechos, actualiza en `INICIO`:

- `Clase`: cambia `BLANK` por `PRIVATE`.
- `Corte`: escribe fecha, hora y desplazamiento ISO, por ejemplo `2026-09-28T23:59:59-07:00`.
- `Zona horaria`: usa `America/Tijuana`; el desplazamiento del corte debe corresponder a esa fecha.
- `Moneda`: conserva `MXN`.

En `COMPLETITUD`, declara para cada tabla su `coverage_status` y ventana observada. Usa `COMPLETE` cuando la ventana está completa, `PARTIAL` o `ESTIMATED` cuando no lo está, `ZERO` sólo si observaste cero registros en una ventana válida y `MISSING` o `NOT_APPLICABLE` sin fechas cuando no existe cobertura. Nunca cambies desconocido por cero.

No cambies los nombres de las hojas ni los encabezados. No muevas un libro lleno a `client/`, `docs/`, `evidence/` u otra carpeta versionada.

## 3. Capturar el inventario correctamente

El libro operativo es la fuente única. Estas tablas controlan inventario:

| Hoja | Qué se registra |
| --- | --- |
| `sku_catalog` | Una variante por SKU, color y talla. |
| `inventory_movements` | Entradas y salidas físicas inmutables. |
| `inventory_reservations` | Apartados y liberaciones; no cambian la existencia física. |
| `inventory_counts` | Conteo observado al cierre; detecta diferencias, no ajusta el kardex. |
| `purchase_orders` | Unidades ordenadas y fecha prometida. |
| `purchase_receipts` | Recibido, inspección, aceptado y rechazado. |
| `loans` | Unidades prestadas o bajo custodia externa. |
| `sales_aggregates` | Ventas entregadas, devoluciones y unidades reingresadas. |

Usa un identificador nuevo y estable para cada evento. Registra los movimientos físicos con estas reglas:

- `OPENING`: existencia inicial verificada.
- `RECEIPT_ACCEPTED`: unidades aceptadas de una recepción. Debe referir el `receipt_id` y coincidir exactamente con `accepted_units`.
- `SALE_OUT`: salida física por venta.
- `RETURN_RESTOCK`: devolución recibida, inspeccionada y apta para regresar a stock. Una solicitud de devolución no basta.
- `LOAN_OUT` y `LOAN_IN`: salida y regreso de préstamo.
- `ADJUSTMENT_IN` y `ADJUSTMENT_OUT`: ajuste aprobado después de investigar una diferencia.

Una orden de compra no aumenta existencia. Una recepción sólo aumenta existencia mediante su movimiento `RECEIPT_ACCEPTED`. Un conteo tampoco modifica existencia: compara lo observado contra el kardex. No reutilices un `movement_id`, `receipt_id`, `count_id` o `reservation_event_id`.

Para una reserva usa `PLACE`; para liberarla usa `RELEASE`. Nunca registres unidades negativas: el sentido lo define el tipo de evento.

## 4. Generar el control de inventario

Guarda el libro y ejecuta desde la raíz del repositorio:

```powershell
.\run.ps1 inventory --source .local\Alma_OPERACION_SEMANA_01.xlsx --output-root .local\inventory-runs
```

Para practicar primero con datos sintéticos:

```powershell
.\run.ps1 inventory --source client\source-packs\v1\synthetic --output-root .local\inventory-runs
```

Cada combinación exacta de fuentes genera un `cut_id`. La carpeta `.local\inventory-runs\<cut_id>\` contiene:

- `inventory-control.html`: tablero local para revisión.
- `inventory-control.csv`: una fila de control por SKU.
- `inventory-control.json`: resultado estructurado, cobertura y límites.
- `receipt.json`: hashes de entradas y salidas.
- `operating-cuts/`: corte relacional verificado utilizado en el cálculo.

El sistema no sobrescribe cortes. Si aparece `inventory cut already exists`, los datos son idénticos a un corte ya creado: abre su tablero existente. Después de capturar hechos nuevos, el libro producirá otro `cut_id`.

Puedes exigir un conteo más reciente:

```powershell
.\run.ps1 inventory --source .local\Alma_OPERACION_SEMANA_01.xlsx --count-max-age-days 3
```

## 5. Resolver los estados del control

| Acción | Qué hacer |
| --- | --- |
| `COUNT_REQUIRED` | Captura un conteo físico y genera un corte nuevo. |
| `RECONCILE_COUNT` | Investiga movimientos faltantes. Registra un ajuste sólo con aprobación y como evento nuevo. |
| `COUNT_DUE` | Recuenta el SKU porque el conteo excedió la antigüedad permitida. |
| `STOCKOUT_REVIEW` | Revisa demanda, compras abiertas y responsable antes de decidir una compra. |
| `RECONCILE_TRANSIT` | Concilia tránsito contra órdenes, recepciones y cancelaciones. |
| `REVIEW_COVERAGE` | Completa las fuentes requeridas antes de aprobar una decisión. |
| `MONITOR` | Las conciliaciones del corte pasan; continúa registrando hechos. |

`BLOCKED` impide usar la posición para decidir. `REVIEW` exige inspección humana. `PASS` confirma las conciliaciones del corte, pero no autoriza compras ni ajustes. El comando nunca crea órdenes, pagos, publicaciones o promesas de venta.

## 6. Ejecutar el ciclo analítico semanal

El control de inventario es rápido y determinista. El ciclo semanal agrega marts, solicitudes para agentes, revisión independiente y paquetes de decisión.

Para preparar un ciclo con la política de revisión incluida:

```powershell
.\run.ps1 weekly --source-pack .local\Alma_OPERACION_SEMANA_01.xlsx --policy client\v1\policies\operating-metrics-review-template-v1.json --output-root .local\client-runs
```

El resultado queda en `.local\client-runs\<cut_id>\`. La política incluida permanece en `REVIEW`; no representa aprobación del owner. La política sintética sólo se usa con el ejemplo sintético.

Estados principales:

- `WAITING_ANALYSTS`: las solicitudes están listas y faltan ejecuciones nativas aceptadas.
- `BLOCKED`: hay que corregir la fuente, política, cobertura o contrato y crear un corte nuevo.
- `REVIEW`: existe evidencia para inspección, pero falta autoridad humana.
- `READY_FOR_OWNER`: existe un paquete revisado para que la persona responsable decida.

La ejecución cognitiva requiere Codex y sigue [agents/RUN-NATIVE-CYCLE-v1.md](agents/RUN-NATIVE-CYCLE-v1.md). El ciclo de aceptación completo usa seis roles por cada uno de dos cortes y una revisión Astra independiente por corte. No fabriques respuestas, trazas ni recibos manualmente.

Para continuar un ciclo existente, consulta la interfaz exacta:

```powershell
.\run.ps1 weekly-resume --help
```

La referencia completa para analistas está en [docs/ANALYST-WEEKLY-v1.md](docs/ANALYST-WEEKLY-v1.md).

## 7. Privacidad y respaldos

- Mantén libros llenos, source packs reales, reportes, respuestas de agentes y decisiones en `.local/`.
- Antes de publicar, ejecuta `git status --short` y confirma que ningún archivo privado aparece.
- Respalda cada carpeta de corte completa; no edites `receipt.json`, `run-index.json` ni archivos dentro de `operating-cuts/`.
- Corrige los datos en una copia del libro y genera un corte nuevo. No repares evidencia publicada en sitio.
- Vacío, cero y desconocido tienen significados distintos. No escribas cero para completar un dato que no conoces.
- No copies `.local/` dentro de un ZIP público ni a otra carpeta versionada.

## 8. Actualizar, recuperar o desinstalar

Actualiza el checkout sólo cuando el estado de Git esté limpio:

```powershell
git status --short
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m pip install -r requirements-client.txt
```

`.local/` está fuera del control de versiones y debe conservarse. Para recuperar una operación, usa una copia completa del corte y sus hashes en una carpeta privada nueva. No extraigas una versión encima de otra.

Para retirar el software, elimina únicamente el checkout o la carpeta de una versión pública después de verificar su ruta. Respalda `.local/` por separado si necesitas conservar los cortes históricos.

## 9. Solución rápida de problemas

| Mensaje o síntoma | Resolución |
| --- | --- |
| `Python 3.11+ required` | Crea `.venv` con Python 3.11 o posterior. |
| `output root must end in .local/inventory-runs` | Usa exactamente una ruta privada con ese sufijo. |
| `inventory cut already exists` | Abre el corte existente o captura hechos nuevos; no borres evidencia para repetirlo. |
| `RECONCILE_COUNT` | Compara movimientos contra el conteo y documenta cualquier ajuste aprobado. |
| `REVIEW_COVERAGE` | Revisa las ventanas y estados de cobertura del libro. |
| El libro es rechazado | Conserva el diagnóstico, corrige una copia y vuelve a ejecutar. No cambies hojas o encabezados. |
| `python` abre `pyenv` sin versión | Usa `.\.venv\Scripts\python.exe` o ejecuta mediante `run.ps1`. |

Documentación especializada: [control de inventario](docs/CONTROL-INVENTARIO.md), [runbook del release](docs/RUNBOOK-v1.md), [operación semanal](docs/ANALYST-WEEKLY-v1.md), [acceso GitHub](docs/GITHUB-ACCESS.md) y [arquitectura](specs/ARCHITECTURE.md).
