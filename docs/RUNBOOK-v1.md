# Guía rápida de operación de Alma OS v1.0.0

Esta guía está pensada para quien recibe el paquete. Los pasos de consulta del portal no ejecutan análisis ni requieren conexión a internet. El runtime de analistas es un checkout del repositorio con `run.ps1` y el módulo `alma`; esos archivos no forman parte del ZIP para clientes.

## 1. Verificar y extraer

Conserva juntos `Alma_OS_v1.0.0.zip` y `Alma_OS_v1.0.0.zip.sha256`. En PowerShell, desde la carpeta donde guardaste ambos archivos, calcula y compara el SHA-256 antes de extraer:

```powershell
$expected = (Get-Content .\Alma_OS_v1.0.0.zip.sha256 -Raw).Split(' ')[0].Trim()
$actual = (Get-FileHash .\Alma_OS_v1.0.0.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'El ZIP no coincide con su checksum.' }
Expand-Archive -LiteralPath .\Alma_OS_v1.0.0.zip -DestinationPath .\Alma_OS_v1.0.0 -ErrorAction Stop
```

Extrae cada versión en una carpeta nueva y hermana de la anterior, por ejemplo `Alma_OS_v1.0.0` y `Alma_OS_v1.0.1`. No extraigas encima de una instalación existente. Guarda el ZIP y su checksum original para recuperación.

## 2. Abrir el material sin conexión

Abre `Alma_OS_v1.0.0\PORTAL\index.html` en un navegador. El portal y sus enlaces son archivos locales; no necesitan servidor ni recursos remotos. `INICIO\EMPIEZA_AQUI.md` describe el recorrido. Las dos hojas Excel están en `FUENTES`:

- `operating-v1-blank.xlsx` es una plantilla vacía para captura; por sí sola no representa un corte analítico.
- `operating-v1-synthetic.xlsx` contiene un ejemplo enteramente sintético para inspeccionar estructura y cálculos.

No cargues datos reales en la copia pública ni compartas una hoja rellenada como si fuera el ejemplo. Trabaja con una copia privada bajo un directorio de trabajo que controles y excluye esa carpeta de sincronización o publicación.

## 3. Validar una instalación o restauración

La comprobación del archivo local puede hacerse sin conexión. Sustituye la ruta por la carpeta recién extraída:

```powershell
$portal = Resolve-Path .\Alma_OS_v1.0.0\PORTAL\index.html
if (-not (Test-Path -LiteralPath $portal -PathType Leaf)) { throw 'No se encontró el portal offline.' }
Get-Content -LiteralPath $portal -TotalCount 1
```

Confirma que el portal abre y que su navegación local responde. Para validar de nuevo el manifiesto desde un checkout de desarrollo, usa los comandos de [RELEASE-v1.md](RELEASE-v1.md). Este ZIP público es una guía y un conjunto de materiales; no contiene `run.ps1`, `alma` ni el motor que prepara cortes. El comando de ayuda y el ciclo analítico requieren el checkout del analista.

## 4. Operación semanal privada (analistas)

Requisitos: checkout confiable del repositorio, PowerShell, Python 3.11 o posterior, una fuente preparada (workbook o source pack canónico) y una política vigente. En el checkout del analista, consulta primero los parámetros disponibles:

```powershell
.\run.ps1 weekly --help
.\run.ps1 weekly-resume --help
```

Prepara una fuente privada y guarda los resultados bajo `.local/client-runs`. El sistema deriva un identificador inmutable para el corte; nunca reutiliza ni sobrescribe un corte existente.

```powershell
.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs
```

Si existe una decisión previa que debe continuar, proporciona el registro y el ancla verificados juntos:

```powershell
.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs --prior-register <register-dir> --prior-anchor <anchor.json>
```

Ambas opciones de continuidad se entregan juntas o se omiten juntas. Mantén las fuentes privadas, solicitudes, respuestas nativas, query traces, recibos, decisiones y exportaciones fuera del paquete público. Conserva intactos los archivos `receipts/` y `run-index.json`: cada etapa se liga a hashes y el proceso detiene la continuación si cambian.

Los estados describen límites diferentes: `WAITING` significa que falta evidencia nativa aceptada; `BLOCKED` requiere corregir entradas o contratos antes de crear un corte nuevo; `REVIEW` requiere inspección humana; `READY_FOR_OWNER` prepara una propuesta para que la persona responsable decida. Ningún estado registra la respuesta del owner por sí mismo.

## 5. Continuar evidencia nativa y decisión del owner

Los analistas responden a solicitudes mediante la interfaz Codex autorizada y conservan la respuesta JSON, query trace y dispatch receipt. El recibo debe identificar la ejecución real y enlazar los hashes de solicitud, respuesta y traza. No escribas ni reconstruyas recibos manualmente. Registra y valida una respuesta con:

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action record --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
.\run.ps1 weekly-resume --run <private-run-dir> --action submit --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
```

Recalcula el estado o construye el paquete de decisión con un proceso nuevo:

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action resume
.\run.ps1 weekly-resume --run <private-run-dir> --action packet
```

Sólo una persona autorizada crea un evento de decisión explícito. El evento debe incluir una recomendación, rol owner permitido, fecha límite, elección y criterio tipado de cierre. Registra el evento con el registro destino:

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action register --register <register-dir> --decision-event <owner-decision.json>
```

Una recomendación no equivale a decisión ni aprobación para actuar. El siguiente corte sólo hereda decisiones abiertas cuando registro y ancla coinciden en identidad y hashes. Cierra una decisión posterior únicamente cuando existe evidencia que satisface su condición explícita de cierre; conserva el origen y la fecha límite.

## 6. Respaldo, exportación y recuperación

Respalda la carpeta privada completa junto con el identificador del corte y los archivos de evidencia originales. Verifica los hashes antes de restaurarla. Restaura a una carpeta privada nueva fuera del ZIP y fuera de las carpetas del paquete; nunca escribas información privada dentro de `PORTAL` o `FUENTES`. Ante entradas inválidas, guarda los recibos de diagnóstico y prepara un nuevo corte inmutable después de corregir la causa. No borres evidencia para convertir un estado fallido en aprobado.

Una actualización conserva la versión anterior hasta validar la nueva. Verifica el checksum del ZIP anterior, extrae la nueva versión en una carpeta hermana y completa el smoke offline de la sección 3. Para rollback, vuelve a abrir el portal de la versión anterior y repite el smoke. Para desinstalar, elimina solamente la carpeta de paquete elegida después de comprobar su ruta; nunca elimines, muevas ni sobrescribas `.local` o cualquier raíz privada seleccionada. La prueba automatizada de este contrato vive en `ReleaseDocumentationTests`.

## 7. Alcance y límites

Los materiales de negocio del ejemplo son sintéticos; no demuestran rendimiento real. Pilates socks sigue siendo una hipótesis bajo revisión y no una selección de producto validada. Las cifras sirven para analítica gerencial, no para asesoría fiscal. `EXT-01` (adopción real) y `EXT-02` (política) permanecen `UNKNOWN`; `EXT-03` permanece `REVIEW`. Toda ejecución externa de negocio está `PROHIBITED`.
