# Alma de Lujo · Growth & Business Analytics

Un sistema analítico para ropa deportiva y calcetines de Pilates: datos relacionados, procesos ejecutables, análisis SQL y agentes nativos con evidencia y revisión independiente.

**Los datos comerciales son sintéticos.** Las fuentes públicas de mercado están atribuidas por separado. Este proyecto no demuestra ventas o rentabilidad reales de Alma de Lujo.

[Ver dossier analítico](evidence/v0.2/workspace/DOSSIER.md) · [Explorar las tablas](evidence/v0.2/workspace/tables) · [Consultar SQL](models/marts) · [Leer los procesos](specs/PROCESS-CATALOG.md) · [Sistema de agentes](specs/AGENT-SYSTEM.md)

## Qué contiene

| Componente | Implementación y evidencia |
| --- | --- |
| **30 tablas fuente** | SQLite STRICT, claves primarias/foráneas, restricciones, índices y catálogo por columna. [Diccionario](specs/DATA-DICTIONARY.md) |
| **11 modelos SQL** | Ventas, inventario, antigüedad, compras, caja, finanzas, canales, cohortes, experimentos, conversión y conciliaciones. [Métricas y linaje](specs/METRIC-CATALOG.md) |
| **6 procesos de negocio** | Transiciones legales, controles, excepciones, aprobaciones sintéticas, idempotencia y eventos inmutables. [Definiciones](processes/business) |
| **6 procesos analíticos** | Estados persistentes, solicitudes de agentes, respuestas vinculadas a evidencia, revisión y paquetes de decisión. [Motor](alma/process_engine.py) |
| **7 roles de agente** | Inventario, comercio, devoluciones, finanzas, growth, mercado y revisión. [Contratos](agents) |
| **Escenarios y experimentos** | Un año, 1,200 pedidos, 46 variantes, 22,844 registros; presión de inventario, descuentos, caja, costos faltantes y vínculos rotos. [Comparación](evidence/v0.2/SCENARIO-COMPARISON.md) |
| **Especificaciones verificables** | PRD, matriz de aceptación, arquitectura, procesos, datos, métricas y autoridad. [Specs](specs) |

Es un sistema de análisis con archivos, CLI y reportes exportables. No contiene una aplicación web, servidor, CRM/ERP ni ejecución de compras, pagos o reembolsos.

## Ejecutarlo

Python 3.11+ con SQLite moderno. El núcleo usa sólo la biblioteca estándar; no necesita API keys ni dependencias de pago.

```powershell
python -m alma workspace --output build/cycle-001
python -m alma process status --workspace build/cycle-001
python -m alma query --workspace build/cycle-001 --mart finance_monthly
python scripts/verify_v2.py --output build/verification-v2
```

En Windows también puede usarse `./run.ps1 -Command workspace -Output build/cycle-001`.

El workspace incluye el SQLite, CSV de todas las tablas, JSON, modelos derivados, linaje, controles, intervalos de experimentación, el dossier Markdown/HTML y el replay de procesos. Los procesos analíticos quedan en `WAITING_AGENT` hasta que los agentes nativos ejecutan sus tareas.

Para ejecutar la parte cognitiva dentro de Codex, seguir [RUN-NATIVE-CYCLE.md](agents/RUN-NATIVE-CYCLE.md). El código prepara y valida el intercambio de tareas; no presenta respuestas de reglas como si fueran llamadas a un modelo. Las ejecuciones reales del proyecto conservan su modelo, tarea, esfuerzo, tiempos, trazas, hashes y revisión. No hay un proveedor de inferencia facturable adicional ni un worker de terminal autónomo oculto.

Para importar las mismas tablas por CSV:

```powershell
python -m alma workspace --input build/cycle-001/tables --output build/imported-cycle
```

El importador exige el contrato exacto y el marcador sintético. Se preservan carpetas existentes; un cambio de datos o contrato usa un nuevo workspace. [Runbook completo](docs/RUNBOOK-v2.md).

## Cómo protege las conclusiones

- Ingreso y costo se reconocen por entrega; notas de crédito, devoluciones y reembolsos conservan efectos y fechas distintos. Caja usa eventos reales de la simulación de cobro/pago, sin inventar saldo bancario inicial.
- Inventario separa existencia, reservado, disponible, tránsito y conteo. Muestras y conceptos permanecen PRELAUNCH. El reabasto es una propuesta con supuestos.
- Las cohortes usan primera entrega y ventanas de recompra comparables. El embudo distingue sesiones vinculadas, leads sin sesión y pedidos; conserva campañas con gasto y cero órdenes.
- Una fuente incompleta produce UNKNOWN/NULL. Un vínculo roto bloquea la carga; un lote repetido es no-op; un duplicado contradictorio preserva los datos aceptados.
- Un agente cita valores exactos del snapshot. El motor rechaza solicitudes sustituidas, hashes viejos y paquetes alterados. Un agente diferente revisa las inferencias; los permisos externos permanecen prohibidos.

## Verificación

La verificación v0.2 reúne **67 pruebas automáticas**, seis escenarios, mecanismos de estrés y replay, integridad de importación, oráculos financieros y revisión adversarial independiente. [Resultados](evidence/v0.2/verification.json) · [Revisión Astra](docs/ADVERSARIAL-REVIEW-v2.md) · [CSV roundtrip](evidence/v0.2/interchange.json).

Los estados de aceptación, las ejecuciones de agentes y la publicación se verifican como evidencias separadas. La consistencia de una simulación no prueba adopción, exactitud de datos externos ni impacto comercial.

## Límites y continuidad

El usuario confirmó ropa deportiva y calcetines de Pilates de varios colores. La hipótesis de producto ganador permanece sin validar con ventas reales. El registro de mercado incluye observaciones públicas de INEGI con población y fecha; el acceso a las últimas prendas de Instagram no se pudo verificar. Ninguna fotografía, precio o existencia de la marca fue inventada como observada.

Las integraciones de Instagram, pagos, inventario y datos reales, así como políticas definitivas y contabilidad fiscal, requieren una fase posterior específica. El núcleo está preparado para nuevos snapshots y análisis dentro de Codex. [Arquitectura](specs/ARCHITECTURE.md) · [Investigación](research/source-register.json) · [Eficiencia de modelos](PROJECT-EFFICIENCY.md).

## English overview

A local Growth & Business Analytics system for sportswear and Pilates socks. It provides 30 typed relational source tables, 11 SQL marts, six executable synthetic business lifecycles, six durable analytical processes, and seven native Codex role contracts. The seeded 365-day case contains 1,200 orders and 46 variants. All commercial data is simulated; attributed public research is kept separate.

The native task bridge binds evidence, validates exact-value citations and requires an independent reviewer. It does not call a separately billed API or pretend that deterministic calculations are agents. The terminal build is reproducible offline; cognition runs in a native Codex task. See the [operating procedure](agents/RUN-NATIVE-CYCLE.md), [specification](specs/PRD.md), [SQL](models/marts), and [verification](evidence/v0.2/verification.json).

## License and provenance

Project code and synthetic fixtures: [MIT](LICENSE). Public sources retain their own terms and attribution. GitHub access is isolated to `erickinorganico` for this repository; no global account switch is required. [Access documentation](docs/GITHUB-ACCESS.md).

The compact v0.1 baseline remains available under tag `v0.1.0` and through `python -m alma demo` for regression comparison.
