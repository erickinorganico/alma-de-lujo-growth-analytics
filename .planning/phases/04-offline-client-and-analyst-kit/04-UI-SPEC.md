---
phase: 4
slug: offline-client-and-analyst-kit
status: approved
revision: executive-offline-portal-2026-09-23
shadcn_initialized: false
preset: none
created: 2026-09-22
reviewed_at: 2026-09-24T00:25:14Z
---

# Phase 4 — UI Design Contract

> Visual and interaction contract for the offline portal, source workbooks, and analyst kit. This draft revises the portal presentation after inspection of the current public/private captures and the supplied Vestra references. The verified Phase 4 analytical, privacy, workbook and launcher contracts below remain binding. A new browser receipt is required after implementation.

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none; semantic HTML and the existing Excel workbook patterns |
| Icon library | none; use text labels and simple inline shapes only |
| Font | System sans-serif for body and data; Georgia for editorial page and section headings. No remote fonts. |

The product is an offline analytical system built from local Python/SQLite/CSV/JSON/XLSX and static HTML. Use the existing local CSS, native controls and generated HTML; no application framework, server, login, CDN, remote asset or third-party component registry. Retain Alma's forest/cream/teal identity and Spanish client-guide voice. Replace the oversized hero, six equal fact cards and first-screen hash table with a compact executive workspace. The Vestra captures inform density, persistent navigation, a clear metric row and operational tables; they are a layout reference, not a source of finance data, icons, features or brand styling.

## Spacing Scale

Declared values are all multiples of four. Use this tighter rhythm for the portal; workbook spacing remains governed by the existing template:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon/label gaps, inline metadata |
| sm | 8px | Compact controls, status chips |
| md | 16px | Card padding, body content spacing |
| lg | 24px | Main gutter, chart/card groups and section padding |
| xl | 32px | Major section separation |
| 2xl | 48px | Long-form evidence separation only |
| 3xl | 64px | Print/guide chapter break only; never portal hero padding |

Exceptions: interactive targets have at least 44px height/width where practical and a 3px visible focus outline with 4px offset. The outline is a stroke; the offset follows the four-pixel spacing scale.

## Typography

Use exactly four sizes and two weights throughout the portal. Map the roles to existing workbook styles without changing formula/input semantics.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Metadata / table / status label | 14px | Regular (400) or semibold (600) | 1.4 |
| Body / control | 16px | Regular (400) | 1.5 |
| Section heading / numeric KPI | 20px | Semibold (600) | 1.2 |
| Page title | 28px; 20px at 320–599px | Regular (400) | 1.2 |

Use system sans for controls and data, Georgia only for the 28px page title and 20px editorial section titles. Use tabular numerals for measures and dates; right-align numeric table cells. Long IDs/hashes use a local monospace fallback at 14px and wrap at safe boundaries. Preserve selectable full values. Limit prose to 72 characters per line on desktop. Do not use all-caps eyebrow labels over every heading. The workbook may retain its existing font family and bold cells for input/formula clarity.

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F5F3EC` | Page canvas and broad work area |
| Secondary (30%) | `#FFFEFA` and `#113F3B` | White cards/tables and forest navigation/header |
| Accent (10%) | `#0D7167` | One primary action, active navigation marker and evidence links only |
| Destructive | `#9B4839` | Validation errors and destructive/reset confirmations only |

Accent reserved for: the single entry action where applicable, current navigation item, and links to source/lineage evidence. Focus is contextual: use a dark forest outline `#0B5D55` on cream or white surfaces and amber `#F2B84B` only on the forest rail; each rendered pair must meet the 3:1 graphical contrast threshold. Do not turn numeric gains, every pill or every control teal. Use `#745323` for REVIEW text on white/cream and `#9B4839` for BLOCKED/ERROR text; neutral ink is `#17312E`, muted text `#526B67`, border `#CCD8D2`. The 60/30/10 split is a visual-area guideline, not a data encoding.

Status must never be communicated by color alone. Pair every color or icon with a visible word: `LISTO`, `REVISAR`, `DESCONOCIDO`, `BLOQUEADO`, `PENDIENTE`, or `CERRADO`. Meet WCAG AA text contrast for foreground/background combinations; preserve visible keyboard focus. In Excel, keep the established blue fill for editable input cells, pair it with an “Entrada” legend and cell comments/instructions, and use text/status labels for output state.

## Copywriting Contract

All client-facing headings and actions are Spanish, consistent with the current client guide. Keep command names, field identifiers, source IDs, and metric names literal where needed; explain them in Spanish. Short copy names evidence and next action without presenting a recommendation as executed.

| Element | Copy |
|---------|------|
| Primary CTA | `Abrir corte actual` only when a verified current cut is selected; otherwise `Abrir ejemplo sintético`. Each opens an explicitly labelled local document. |
| Empty state heading | `Todavía no hay un corte actual` |
| Empty state body | `Elige un paquete de fuentes local y ejecútalo con la guía del analista. Mientras tanto puedes explorar el ejemplo, marcado como sintético.` |
| Error state | `No se pudo validar este corte. Corrige las filas indicadas y vuelve a ejecutar el flujo; no se publicaron métricas para este corte.` |
| No chartable series | `No hay una serie comparable para este corte. Consulta los valores y su cobertura en la tabla de métricas.` |
| Pending analysis | `Análisis pendiente. Hay solicitudes preparadas; falta una respuesta nativa verificada.` |
| Destructive confirmation | `Restablecer esta plantilla: se borrarán los valores capturados en esta copia. Guarda primero una copia si necesitas conservarlos. Escribe RESTABLECER para continuar.` |

The portal has no destructive operation on private evidence. The reset text applies only if a workbook/kit offers an explicit reset control; do not add a reset control without preserving an untouched blank copy. Validation errors must identify the file/sheet/table and row/field, state the reason, and give the next correction step. Never use “0” to describe a missing value; render missing or incomplete evidence as `DESCONOCIDO` with a reason.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | Not applicable; project has no React app or `components.json`. |
| Third-party | none | Not applicable. |

## Phase 4 Interaction Contract

### Portal information architecture

Use a single static HTML portal. Preserve these eight section IDs and anchor destinations in this order. On desktop, their primary navigation is a left sidebar; on small screens it becomes a compact horizontal anchor strip.

1. **Inicio / corte seleccionado** — identify the active dataset, its role and provenance before showing numbers. Its first screen contains a compact context strip, one status-led overview row, a verified coverage visualization and the next actionable exception/decision. Put full cut ID and hashes in an immediately reachable `Detalles del corte y procedencia` disclosure and lineage section, with a selectable full value and local artifact link. The header still shows context, cutoff, status and a shortened cut ID. If no private cut was selected, say so and offer the historical synthetic demo as a separate labelled entry.
2. **Recorrido semanal** — show the ordered stages `Fuentes → Validación → Marts y métricas → Análisis → Revisión independiente → Decisión del responsable → Próximo corte`. Each stage shows a truthful state, timestamp/receipt if available, and next local artifact. `PENDIENTE`/`ESPERANDO_RESPUESTA` must remain visible when human/native work has not occurred.
3. **Decisiones** — list owner-ready packets and their review state. Expand a packet into four visibly separate groups: `Hechos`, `Desconocidos`, `Hipótesis`, and `Recomendaciones`; every recommendation displays its metric, guardrail, population, window, closure rule, owner and due date. Show evidence references next to the claim they support. Label advice as advisory; owner registration and later closure remain separate events.
4. **Excepciones y calidad** — put blocking/review/unknown items before passing checks. Each row names affected source/metric, exact reason, severity/state, next required evidence and a local evidence link. Preserve coverage gaps and failed reconciliations as unknown/blocked; do not hide them behind an overall green badge.
5. **Fuentes** — searchable, expandable source inventory grouped by v1 business domain. Every source exposes exact contract version, grain, keys, required/nullable fields, units, provenance, coverage, synthetic flag and its incoming/outgoing relationships. Search filters the inventory without hiding the total or current query; preserve anchor navigation when opening a source. The exact zero-result copy is heading `Sin coincidencias para “{consulta}”` and body `Borra el filtro o busca por fuente, campo, proceso o decisión. El inventario completo sigue disponible.`
6. **Métricas** — metric dictionary grouped by decision use (cost/price, purchasing/inventory, cash/obligations, sales/product learning, quality/readiness, budget/channel). Show formula, unit, grain, window, inputs, unknown rule, guardrail, owner and decision use. Link each metric to its registered mart and upstream sources. Keep management proxies distinct from statutory/tax outcomes and cash movement distinct from a bank balance.
7. **Procesos y roles** — show process trigger, states, gates, exceptions and resulting artifact; show each native role's purpose, permitted inputs, output schema, review partner, dispatch state/receipt and `PROHIBITED` authority boundary. Distinguish actual native Codex dispatch from a request bundle or deterministic analysis.
8. **Linaje y exportación** — provide a readable source → mart/metric → process/role → packet chain and local links to source/manifest/hash evidence. Include links to downloadable CSV/JSON/printable report artifacts when present and an offline operating guide. Never offer a network share, upload or publish action.

On wide screens, constrain the whole workspace to 1600px and the main content to 1320px. Use a 232px sidebar, 24px main gutter, and a two-column evidence grid. At 1440×900, the visible first screen must show the context strip, status and up to three other summary cards, plus the beginning of the coverage and action modules; no full SHA-256 row appears before those modules. The sidebar stays visible while scrolling on desktop. Below 1200px, move navigation above the content; below 600px use one column and 16px outer gutters. Only labelled table containers may scroll horizontally. Every section target needs scroll margin so navigation cannot cover its heading.

Use semantic `header`, labelled `nav`, `main`, `section`, headings in order, table captions and scoped column headers, native links and `<details>/<summary>` for optional source/packet detail. Every search field has an accessible label and a visible result count/zero-result message. All interactions work by keyboard with visible focus and without hover. Do not rely on script for critical content or navigation: printable/no-script content remains complete. Use no auto-playing or load animation; anchor scrolling may be smooth only when reduced motion is not requested.

### Executive portal visual contract — 2026-09-23 revision

This section is the visual source of truth for the portal redesign. It supersedes earlier Phase 4 guidance that places a large hero, six equal fact cards, full hashes or the eight-link row above the analytical overview. It does not supersede source, parity, package or approval boundaries.

**Desktop composition.** The left rail is 232px wide with an Alma OS wordmark, `Portal offline` subtitle, visible context label (`Ejemplo sintético` or `Corte privado`), and the eight existing destinations grouped as `Panorama` (Inicio, Recorrido, Decisiones, Excepciones) and `Explorar evidencia` (Fuentes, Métricas, Procesos, Linaje). Group labels are plain sentence case. The active item has a 3px accent rule and a tinted background, plus `aria-current="location"` when applicable. A bottom rail note says `Archivo local · Sin sincronización`. Do not copy Vestra's investor functions, search chrome, profile controls or iconography. The main header is at most 88px high at 1440px: `Alma de Lujo`, the 28px `Corte semanal` title, a small context/status line, and one local action (`Ver procedencia` or `Abrir ejemplo sintético`); no two-line marketing headline.

**First-screen order.** (1) A full-width 48–64px provenance strip shows the exact public/private/synthetic role, cutoff with timezone when known, process state and a 10–12 character cut-ID prefix; the full ID is selectable in its disclosure. (2) A row of four unequal cards shows `Estado del corte`, `Cobertura de fuentes`, `Excepciones que requieren atención`, and `Decisiones del responsable`. The state card is visually dominant and always carries a word plus the next unmet gate. Source coverage uses `n con cobertura verificada / N fuentes del contrato` only if the selected context has the complete v1 registry; the historical demo uses its own `n de N fuentes históricas` denominator. Exception and decision counts are counts of verified rows and include their status qualifier; zero only means a verified empty set. (3) A 2:1 row shows `Cobertura por dominio` and `Siguiente paso`. (4) A compact operating table starts with the most important exception or owner packet; lower sections hold the complete registry and deep lineage. The page must remain useful when the public historical fixture has no metric rows.

**Component inventory.** Use one restrained card family: 1px `#CCD8D2` border, 8px outer radius, white `#FFFEFA` surface, no repeated floating shadows. The sidebar is forest `#113F3B`; main canvas is `#F5F3EC`. Summary cards have a 14px label, 20px value, one 14px coverage/state line and a descriptive local anchor. Status chips contain words; `PASS`, `MEASURED`, `READY_FOR_OWNER`, `REVIEW`, `PARTIAL`, `UNKNOWN`, `BLOCKED`, `ESPERANDO_RESPUESTA`, `PENDIENTE` and `ADVISORY` remain distinct. For client readability, show a Spanish label with the exact machine state available in adjacent text or `title`, never collapse waiting into passing. Tables use a visible caption, 14px headers/body, 44px minimum row target where a row is interactive, numeric right alignment, tabular numerals, and a quiet row separator. Reserve `<details>` for expandable evidence and use local links for actual artifacts; no visual control may imply an action the static portal cannot perform. The optional search filters only source inventory and reports `x de N fuentes`; core content remains in HTML before script runs.

**Chart contract.** Generate charts from the already verified portal model during the Python build and emit inline SVG plus a visible semantic HTML table. No CDN, canvas library, external font, remote image, runtime fetch or server. `Cobertura por dominio` is the always-available visual: one horizontal stacked bar per canonical v1 source domain, with segment length equal to the count of sources in each reported coverage state. A legend names every state and its evidence limit. For a v1 cut, the paired table lists `dominio`, `COMPLETE`, `ZERO`, `PARTIAL`, `ESTIMATED`, `MISSING`, `ERROR`, `NOT_APPLICABLE` and `total` as separate integer columns; it must reconcile each segment and row total exactly, without combining states. On the historical fixture, group only sources actually present, preserve each actual historical status as its own table/legend column, and label the chart `Inventario histórico sintético`; never imply it covers the 22 v1 relations. Use integer source counts, start bars at zero, and include the denominator in text. Do not use green bars for an overall PASS when a dependent metric or policy is REVIEW/BLOCKED.

The v1 source-domain grouping is a presentation-only map, not a change to the 22-relation intake contract:

| Display domain | Source IDs | Total |
| --- | --- | ---: |
| Producto y ventas | `sku_catalog`, `sales_aggregates`, `availability_daily`, `unmet_demand`, `sales_readiness` | 5 |
| Inventario y calidad | `inventory_counts`, `inventory_movements`, `inventory_reservations`, `quality_events`, `loans` | 5 |
| Costos y compras | `cost_versions`, `cost_components`, `cost_allocations`, `purchase_orders`, `purchase_receipts` | 5 |
| Caja y obligaciones | `obligations`, `obligation_payments`, `cash_events`, `cash_balance_evidence` | 4 |
| Presupuesto y gastos | `budgets`, `budget_allocations`, `expenses` | 3 |

For v1 coverage, `COMPLETE` and verified `ZERO` count as verified but remain separate legend segments, so observed zero cannot be confused with absence. `PARTIAL` and `ESTIMATED` each have a separate limited-evidence segment. `MISSING` is unknown; `ERROR` is blocked; `NOT_APPLICABLE` remains an explicit segment in the denominator and does not count as verified. Do not merge these source states into the distinct metric or weekly-process state vocabulary. If a source ID has no known display domain, fail the chart build instead of silently dropping it. Historical v0.2 sources use their actual available status words and their own source count; do not force them through this v1 map.

A second `Métricas comparables` visual is conditional. It may show horizontal bars for at least two verified rows only when they share an explicit unit, population/grain, window and cut, and the metric definitions permit comparison. Preserve signs with a zero baseline and direct value labels. A time-series line may appear only when at least three independently verified dated observations of the same metric and comparable scope are present; the current single-cut model does not itself establish a trend. Never interpolate missing dates, turn null into 0, combine MXN cents with MXN, or label synthetic data as actual performance. If the gate fails, show the exact `No hay una serie comparable...` copy and the ordinary metric table. All plotted values must exactly match the rendered metric table and CSV/JSON exports, including status, source hash, unit and cut identity. Decorative sparklines, invented weekly movement and percentage deltas are prohibited.

**Table and decision density.** Below the overview, put `Excepciones y calidad` ahead of passing checks: columns are `Estado`, `Fuente o métrica`, `Motivo`, `Qué falta`, `Evidencia`. Do not hide unknowns in a count only. `Recorrido semanal` is a seven-stage vertical rail on desktop and a one-column ordered list on mobile; each stage shows state, artifact/receipt and next requirement, with no completed checkmark for a prepared native request. `Decisiones` has a compact register with owner/due/status/packet link, and its expanded packet retains separate `Hechos`, `Desconocidos`, `Hipótesis`, `Recomendaciones`. The complete metric table stays available even when a chart is shown. Source/metric IDs, formulas and hashes can live in secondary columns or disclosures, but remain selectable and printable.

**Content and state matrix.** The public landing shows `EJEMPLO SINTÉTICO · HISTÓRICO v0.2`, `Ejemplo informativo. No representa un corte actual ni una aprobación.`, historical source coverage and `Sin métricas actuales en este ejemplo` where relevant. A selected private synthetic cut shows both `CORTE PRIVADO ACTUAL` and `SINTÉTICO`, the exact cutoff/timezone and actual process state; its values are labelled synthetic. A selected private non-synthetic cut never appears in the public package. Unselected private view shows `SIN CORTE PRIVADO SELECCIONADO`, no numeric KPI derived from another context, and `Abre un corte local verificado o consulta el ejemplo sintético.` An invalid/hash-mismatched cut fails before a normal dashboard is rendered and shows `CORTE BLOQUEADO · NO USAR PARA DECISIONES` with the failed evidence and local correction path; do not show stale values. For a metric: observed zero renders `0` with `MEASURED`; null/unknown renders `DESCONOCIDO` plus missing-coverage reason; `PARTIAL` displays the value only with its partial scope; `REVIEW` and `BLOCKED` visibly limit decision use. A zero-row verified exception set says `No hay excepciones registradas para este corte`; absent/unverified exceptions say `No se pudo verificar el estado de excepciones`.

**Responsive and zoom.** At ≥1200px use the 232px rail, four overview cards and 2:1 chart/action row. At 960–1199px use a horizontal labelled anchor strip, a 2×2 card grid and 1:1 chart/action row. At 600–959px retain the horizontal strip and 2×2 cards but use one-column lower modules. At 320–599px, use 16px page gutters, one-column cards, a horizontally scrollable navigation strip with visible overflow cue, and stacked chart/decision sections. Do not set a fixed 390px body width. Long IDs wrap in their own disclosure; no page-level horizontal scrolling at 320px or 200% zoom. The chart SVG uses a responsive `viewBox` and shows direct labels/table at small sizes; status legend wraps. Tables may scroll within a bordered region that is keyboard focusable and labelled `Desplazar tabla de …`. Keep nav and cards readable with browser text enlargement; neither sticky sidebar nor fixed heights may cover content.

**Accessibility and print.** Provide a skip link, one H1, ordered H2s, visible focus on every link/summary/control, semantic table headers, and `role="img"`/`aria-labelledby` on each SVG with title/description describing scope and provenance. The paired table is in the same section and is available when CSS or SVG fails. Status meaning appears in text outside color. Normal body and status text must meet 4.5:1, large text 3:1 and essential graphical boundaries 3:1 against rendered surfaces. Motion is unnecessary; if anchor scrolling is retained, disable it under `prefers-reduced-motion: reduce`. Print on A4/letter landscape for wide evidence tables, with a repeated short provenance/cutoff/status header on every page and the full hashes in an appendix/lineage block. Hide sidebar, filters and buttons; keep chart text, paired tables, unknown/review warnings, source names and local artifact names. SVG must render in grayscale and not rely on fill hue. Avoid forcing every `<details>` closed in print; print all evidence content. No clipped row, graph, hash or packet is acceptable.

**Verification gates for this visual revision.** Capture exact final public and safe synthetic-current `file://` HTML at 1440×900, 960px, 390px, 320px, and at 200% browser zoom, plus all printed pages. Inspect the first screen for the order and density above, keyboard Tab/Enter through nav/disclosures/table scroll, no-JavaScript content, reduced motion, and local links after package extraction. Reuse the mart→portal→CSV→JSON parity oracle and add chart→table parity for source-count segments and any optional metric bars. Bind generated HTML/CSS and screenshot/PDF hashes to a new bounded visual receipt; the prior 2026-09-23 PASS receipt proves the former layout only. Public packaging must consume the new receipt hash and continue excluding private HTML/captures. The redesign is accepted only when both contexts have unmistakable provenance, no page overflow at 320px or 200% zoom, complete print evidence and no invented chart values.

### Evidence provenance: private current cut and synthetic demo

Treat “current vs historical/demo” and “private vs synthetic” as separate facts. The portal must derive its label from the selected cut manifest and its declared role, not its folder name or a hard-coded UI default. Use these exact persistent labels:

- Historical public fixture: `EJEMPLO SINTÉTICO · HISTÓRICO v0.2`.
- Selected private current cut: `CORTE PRIVADO ACTUAL · {cutoff} · {cut_id}`; add `SINTÉTICO` too if its manifest says synthetic.
- No selected private cut: `SIN CORTE PRIVADO SELECCIONADO`; the historical demo remains a separate labelled view.
- Invalid, stale or unverified cut: `CORTE BLOQUEADO · NO USAR PARA DECISIONES`.

Keep the provenance badge, cutoff, and status in the page header, browser print header, every decision packet, and every metric/evidence table that displays measured-looking data. All displayed figures link back to the selected evidence. Never mix demo values into private-cut metrics or use a single selector that silently swaps the underlying numbers. Switching dataset context requires an explicit labelled action and updates the entire view; browser Back/hash links retain the correct context. A private current cut may itself be marked synthetic; preserve both labels instead of relabelling it as observed client evidence. Unknown is shown as `DESCONOCIDO`/`Sin datos` with coverage reason, never blank-as-zero.

### Source workbooks and spreadsheet usability

Deliver paired blank and synthetic-example workbooks/source packs covering every v1 source relation/domain in the versioned intake contract, including the canonical product/catalog, sales/commerce, returns/refunds/payments, inventory/receipts, procurement/costs, obligations/finance/cash, budgets/drop/channel, quality/readiness/loans, and growth/experiment sources wherever declared by the contract. The generated source inventory is authoritative: every required relation appears exactly once in each pack; no hand-maintained shortlist may omit a v1 domain. The example pack has a prominent synthetic marker in its opening sheet, metadata and every domain/table; examples use invented aggregate data, contain no PII, and never resemble a private cut label.

Alongside those 22-source materials, provide two separate versioned management-policy files: an unapproved blank template with status `REVIEW`, and a verified `SYNTHETIC_EXAMPLE` policy for the synthetic walkthrough. A policy file is a Phase 2 input and must never be counted as a Phase 1 source relation. The synthetic policy cannot authorize a private real-data cut, and the public template must not contain an owner approval reference.

Use a clear `INICIO` index to orient the analyst, identify the pack version/cutoff/timezone and link to the glossary/field dictionary. Group table sheets by business domain and order them in weekly-entry order. Each sheet starts with an immutable, exact schema header and a short above-table note naming purpose, row grain, key, units, required/optional fields and source/provenance rules. Include one realistic synthetic example row per sheet only in the example pack; keep blank template data rows empty. Put completeness and unknown-vs-zero instructions beside the relevant fields. Preserve exact headers and values required by the CSV import contract; help text belongs in sheet instructions/notes, not altered column names.

Retain v0.3 workbook strengths: editable input cells filled blue and listed in an input legend; formulas/calculated cells visually distinct and protected from accidental edits; dropdown/data validation for enumerations; date/number limits and duplicate-key checks; frozen title/header rows; filters; readable column widths and wrapped headings; no macros, external workbook links, external data connections or embedded credentials. A validation export must point to workbook/sheet/row/field and explain whether the correction is structural, key/relationship, unit/date, coverage or provenance-related. Preserve the original source values when correcting through a proposed/copy workflow; do not silently truncate rows, coerce blank to zero, or rewrite previous immutable cuts.

Open both workbooks in supported desktop Excel without scripts or network. The release support boundary is desktop Excel plus the independent OOXML/Decimal validator; do not claim verified LibreOffice or other spreadsheet-engine behavior without a separate engine receipt. Canonical CSV source packs are the reader-neutral fallback and authoritative interchange for non-Excel users. This narrower boundary is deliberate because validation lists, protected cells, formula caches and print layout vary across spreadsheet engines; claiming broad compatibility without executing those engines would be misleading. Provide a data dictionary and one workbook navigation index. Set landscape/page-fit-to-width print settings for wide sheets, repeat title/header rows, avoid clipped columns, show page numbers and workbook/cut labels, and place print breaks between independent tables. CSV/JSON exports preserve canonical exact columns, order, units and unknown/null representation; include a manifest with hashes and relation/domain mapping. The XLSX is a user-friendly editing surface, not the canonical audit history.

### One-command analyst journey

The analyst kit presents one copyable command from the repository root as the supported weekly entrypoint:

```powershell
.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs [--prior-register <register-dir> --prior-anchor <anchor.json>]
```

After the first command reaches a truthful `WAITING` boundary, continuation stays under the same launcher with this exact action contract:

```powershell
.\run.ps1 weekly-resume --run <private-run-dir> --action record --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
.\run.ps1 weekly-resume --run <private-run-dir> --action submit --role <role> --response <response.json> --query-trace <trace.json> --dispatch-receipt <receipt.json>
.\run.ps1 weekly-resume --run <private-run-dir> --action resume
.\run.ps1 weekly-resume --run <private-run-dir> --action packet
.\run.ps1 weekly-resume --run <private-run-dir> --action register --register <register-dir> --decision-event <owner-decision.json>
```

`record` and `submit` require exactly the role/response/query-trace/dispatch-receipt group; `resume` and `packet` reject action-only arguments; `register` requires exactly the register and explicit owner-decision event. The decision event names recommendation ID, allowlisted owner role, due date, owner choice and typed closure check and is never generated automatically. These actions map directly to the final Phase 3 record, submit, resume, packet and decision-register APIs and preserve every earlier immutable receipt.

Use the exact creation and continuation invocations in `EMPIEZA_AQUI` and the offline analyst guide; both `weekly --help` and `weekly-resume --help` plus validation output must match the documented names byte for byte. When `--source-pack` points to an XLSX workbook, the workbook adapter first exports a canonical v1 CSV source pack and the weekly pipeline consumes that pack. `--policy` is the separate, versioned Phase 2 policy input. The system derives `cut_id` from the validated immutable input and creates `.local/client-runs/<cut_id>/` beneath `--output-root`; the caller never supplies or predicts that child path. `--prior-register` and `--prior-anchor` are optional, but must be supplied together and independently verified before carry-forward. Blank initialization is an explicit preparation action outside the weekly build and never publishes metrics. The creation command validates the full contract and privacy rules, builds a new immutable cut, calculates marts/reports and hashes, prepares and validates the analyst/reviewer task bundles, verifies/carries forward the prior decision register when the optional pair is present, and emits the public blank/example package plus a private run index under `.local/client-runs/`. The continuation command is the only supported restart surface after WAITING. The page/guide show this sequence as progress receipts with per-stage PASS/REVIEW/BLOCKED/WAITING states and local output paths. Repeated creation must not overwrite a prior immutable cut.

The command line may request live native Codex work only through the authorized native task bridge and must retain the actual dispatch receipt, task/model metadata and response hashes. If a native analyst or independent reviewer has not actually run, show a precise waiting state and next authorized continuation step; never simulate a response, turn a prepared request into a completed review, or issue an owner-ready packet from missing/stale evidence. After actual reviewer acceptance, carry-forward remains owner-controlled and records the original cut/source hash, owner, due date and closure evidence. Packaging is for the sanitized client kit only; private filled workbook, source pack, report, decision events and native responses remain in ignored `.local/` paths.

The guide has two clearly separated journeys: (1) client: open the blank template, fill required source tables, preserve empty vs zero, save a private local copy, return it to the analyst through their established local process; (2) analyst: execute the creation command, inspect validation exceptions, use the exact `weekly-resume` actions to record actual analyst and reviewer receipts, present the owner packet, register an explicit owner decision, close/carry it to the next cut, and package only the blank/example offline kit. Keep the language plain and task-first. State that the client ZIP is informational/synthetic and contains no analyst runtime; restart acceptance runs from a fresh clean repository or `git archive` checkout with pinned dependencies and an explicitly supplied ignored private run. Do not imply that opening the portal uploads, synchronizes or executes a workbook.

### Accessibility, print, export and package boundaries

- Meet WCAG AA contrast, full keyboard access, visible focus, meaningful link names, semantic tables/headings, labelled controls, text equivalents for status marks and reduced-motion support. Aim for 44px pointer targets. No data meaning is encoded only by color, hover, icon or graph shape.
- The HTML portal and guide must print legibly in black and white on letter/A4 portrait or landscape as content requires. Hide navigation, search controls and screen-only buttons in print; keep provenance, cut ID, cutoff, statuses, source/hash references and limitations. Repeat table headers, allow rows to break safely, and print visible local artifact names (never a private absolute filesystem path). Charts require text/table equivalents and must not crop negative/unknown values.
- Provide explicit local `Descargar CSV`, `Descargar JSON`, `Imprimir / Guardar PDF`, and workbook links only for artifacts actually present and verified. Every downloaded report/export retains cut ID, cutoff, provenance, units, null/coverage state, source hashes and applicable warnings. Do not describe a printable page as a saved PDF until the file exists.
- The distributable client ZIP contains only the offline portal, its required local assets/evidence, blank and synthetic-example workbooks/packs, the unapproved `REVIEW` policy template, the verified synthetic policy example, data dictionary, weekly guide, resolved/example decision walkthrough and package manifest/hash list. Include no filled private cuts, approved/private policy instances, owner approval references, private reports, native requests/responses/drafts, private decision register/events, credentials, `.local/`, or customer PII. Its first-open state is labelled historical synthetic demo with no private current cut selected. This static package opens through a local file URL with no server and no network access.
- Provide a separate private current-cut portal/run directory only under ignored `.local/`; do not place it beside public kit files or give it an ambiguous “demo” label. A manifest/inventory lists every packaged path/hash and allows local links to resolve after ZIP extraction. Display the offline/no-upload boundary and no-external-execution rule in `INICIO` and guide; business actions remain explicit human decisions.
- Before the redesigned public kit is accepted, render the public demo and a safe synthetic-current private fixture through `file://` at 1440×900, 960px, 390px and 320px, at 200% zoom, and in print/PDF. Inspect every captured page and bind exact HTML/image/PDF hashes, browser/version, viewport, timestamp and per-surface disposition in a new bounded visual receipt. Missing pages, clipped tables, hidden provenance/warnings, unresolved links or an unexpected evidence member block Phase 4. The package manifest records the new receipt hash as a verification input; private/current-cut captures are never copied into the client ZIP.

## Upstream decisions used

| Source | Contract decisions |
|--------|-------------------|
| `.planning/ROADMAP.md`, Phase 4 | Offline portal, complete client and analyst workflow, blank/example material, no server. |
| `.planning/REQUIREMENTS.md`, CLIENT-01..04 | Every v1 source domain; distinguish current private cut from demo; one documented command; exclude private cuts and responses from the client package. |
| `.planning/PROJECT.md`, `AGENTS.md` | Local analytical system; Python/SQLite/CSV/JSON/XLSX/HTML; no frontend/server/CRM/ERP, no PII, synthetic public examples, human authority for external action. |
| `.planning/phases/03-governed-weekly-decision-cycle/03-RESEARCH.md` | Bind requests/packets to exact current-cut bytes; report actual native dispatch/response/reviewer states; decisions and carry-forward are separate owner-controlled events. |
| `client/SISTEMA_ANALITICO.html`, `client/GUIA_SEMANAL.html`, `specs/CLIENT-v3.md` | Cream/forest/teal palette, Georgia headings/system body, responsive cards and navigation, Spanish tone, blue workbook inputs, frozen headers, validation, filters, print setup. |
| `docs/CLIENT-SYSTEM-ACCEPTANCE.md`, `.planning/codebase/CONCERNS.md` | Provenance on every data view, local links and no remote assets, visible unknowns, clear v0.2 historical/demo boundary, private data confined to `.local/`. |
| Defaults for unanswered details | No component registry, spacing set to 4px multiples, four type sizes/two weights, explicit Spanish empty/error labels, WCAG AA/keyboard/print contract. |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-09-24T00:25:14Z for the 2026-09-23 executive offline portal visual revision. The design contract is ready for planning and implementation. Acceptance of the redesigned portal still requires the new hash-bound browser and print receipt specified above.
