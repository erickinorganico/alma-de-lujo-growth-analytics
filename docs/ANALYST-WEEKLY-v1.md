# Operación semanal de Alma OS para analistas

Este runbook prepara y continúa un corte privado verificable. Los cálculos son deterministas; los roles nativos producen análisis y revisión mediante el contrato de `agents/RUN-NATIVE-CYCLE.md`. Los límites son explícitos: no upload, no sync y no external business execution.

## Preparación

1. Trabaja desde un checkout limpio del repositorio, con Python y las dependencias fijadas ya disponibles. Usa `git archive HEAD` para probar un checkout sin metadatos Git cuando necesites validar portabilidad.
2. Recibe un workbook lleno o un source pack canónico y el archivo de política separado. Una política ausente o vencida produce BLOCKED. Una política real sin aprobación conserva REVIEW. `SYNTHETIC_EXAMPLE` no autoriza un corte real.
3. Conserva las entradas privadas fuera del área pública. Todos los resultados quedan bajo `.local/`, que no se carga ni se sincroniza.
4. Consulta la interfaz actual con `.\run.ps1 weekly --help` y `.\run.ps1 weekly-resume --help`.

## Crear el corte

Ejecuta exactamente:

```powershell
.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs [--prior-register <register-dir> --prior-anchor <anchor.json>]
```

Si la entrada es XLSX, el adaptador crea y valida primero un **canonical source pack** privado. El sistema deriva el identificador y crea únicamente `<output-root>/<cut_id>/`; el usuario no asigna el `cut_id`. Un directorio existente nunca se sobrescribe.

`--prior-register` y `--prior-anchor` se entregan **both or neither**. El par se verifica de forma independiente antes del carry-forward; conserva el hash y la fecha originales y marca los elementos vencidos. El registro nunca se infiere desde una recomendación.

La creación escribe **stage receipts** para fuente, marts y espera nativa, además de `run-index.json`. WAITING indica que las solicitudes están listas pero no existe aún una respuesta aceptada. BLOCKED indica que debe corregirse la entrada, la política, el hash o el contrato. REVIEW indica que se puede inspeccionar el resultado sin tratarlo como aprobado.

## Ejecutar los roles nativos

Sigue `agents/RUN-NATIVE-CYCLE.md`. Terra analiza inventario y finanzas; Luna cubre comercio y devoluciones; Sol sintetiza crecimiento y mercado. Astra ejecuta la revisión independiente y debe usar una identidad distinta. El archivo de solicitud por sí solo no acredita ejecución.

Cada entrega necesita la respuesta JSON, query trace y dispatch receipt reales. Los hashes y referencias deben coincidir exactamente con la solicitud. No edites recibos anteriores y no fabriques evidencia para avanzar el estado.

## Continuar desde otro proceso

La continuación lee el corte privado existente. Puede ejecutarse después de cerrar el proceso original o desde un checkout/`git archive` limpio, siempre que se suministre explícitamente el mismo directorio privado y estén presentes los mismos bytes comprometidos del código.

### Registrar evidencia recibida

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action record --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
```

### Validar y enviar una respuesta al ciclo

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action submit --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
```

`record` y `submit` requieren los cuatro argumentos de evidencia. No aceptan una combinación parcial.

### Recalcular sólo el estado de continuación

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action resume
```

### Construir o leer el packet listo para owner

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action packet
```

`resume` y `packet` no aceptan `--role`, `--response`, `--query-trace`, `--dispatch-receipt`, `--register` ni `--decision-event`. El packet sólo alcanza `READY_FOR_OWNER` después de las tres respuestas analíticas y la revisión independiente aceptadas.

### Registrar una decisión explícita del owner

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action register --register <register-dir> --decision-event <owner-decision.json>
```

El **decision-event** lo crea una persona autorizada e incluye recommendation ID, owner role permitido, due date, owner choice y typed closure check. `register` rechaza argumentos de respuesta nativa. El sistema no genera la decisión automáticamente.

## Corrección, cierre y siguiente semana

Ante BLOCKED, conserva el diagnóstico y corrige la fuente o política fuera del corte; después crea un nuevo hijo inmutable. No borres ni reescribas el corte fallido. Ante WAITING, entrega sólo la evidencia faltante mediante la acción correspondiente. Ante REVIEW, solicita aprobación humana sin presentar el resultado como autorización.

Para cerrar una decisión, registra evidencia que satisfaga el closure check tipado. Las decisiones abiertas pueden pasar a la semana siguiente sólo mediante el par verificado de register y anchor; ese carry-forward mantiene su origen, vencimiento y estado. Una recomendación, por sí sola, no es una decisión.

## Paquete público

El paquete sanitizado se construye por separado con `python scripts/package_client_v1.py --output <alma-os-client-v1.zip>`. Contiene plantillas vacías, ejemplo sintético, políticas REVIEW/SYNTHETIC_EXAMPLE, diccionario, walkthrough y demo pública. No contiene un corte, respuestas nativas, recibos privados, decision events ni runtime de analistas. No puede ejecutar un corte privado.
