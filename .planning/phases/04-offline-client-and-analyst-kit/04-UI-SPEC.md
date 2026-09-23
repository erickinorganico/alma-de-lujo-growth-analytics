---
phase: 4
slug: offline-client-and-analyst-kit
status: approved
reviewed_at: 2026-09-22
shadcn_initialized: false
preset: none
created: 2026-09-22
---

# Phase 4 — UI Design Contract

> Visual and interaction contract for the offline portal, source workbooks, and analyst kit. Derived from the Phase 4 roadmap and CLIENT-01..04; the GSD UI checker should verify this contract before implementation.

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none; semantic HTML and the existing Excel workbook patterns |
| Icon library | none; use text labels and simple inline shapes only |
| Font | System sans-serif for body and data; Georgia for editorial page and section headings. No remote fonts. |

The product is an offline analytical system built from local Python/SQLite/CSV/JSON/XLSX and static HTML. Do not introduce a JavaScript application framework, server, login surface, CDN, remote asset, or third-party component registry. Reuse the existing portal's cream canvas, dark forest header, teal links, serif headings, expandable evidence cards, responsive tables, and Spanish client-guide language. Bring the portal and kit into one consistent system; keep the compact, task-first tone of the workbook guide.

## Spacing Scale

Declared values are all multiples of four and preserve the portal's existing density while regularizing its gaps:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon/label gaps, inline metadata |
| sm | 8px | Compact controls, status chips |
| md | 16px | Card padding, body content spacing |
| lg | 24px | Card groups and compact section padding |
| xl | 32px | Main content gutter and wide layout gaps |
| 2xl | 48px | Major section separation |
| 3xl | 64px | Page-level breathing room and portal hero |

Exceptions: maintain a 44px minimum hit area for pointer/touch controls and 24px minimum visible focus outline offset where needed; both are accessible target/outline sizes rather than spacing tokens.

## Typography

Use exactly these four sizes and two weights throughout the portal. In the workbook, map the same four semantic roles to the existing workbook styles without introducing an additional type-size token; retain existing formula/input emphasis.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Label / compact metadata | 12px | Semibold (600) | 1.4 |
| Body / tables | 16px | Regular (400) | 1.55 |
| Section heading | 32px | Regular (400) | 1.2 |
| Display heading | 48px; reuse the 32px section-heading token below 600px | Regular (400) | 1.05 |

Use tabular numerals for measures, dates, and IDs. Keep long source IDs and paths in a local monospace fallback at body size; wrap them rather than allowing horizontal page overflow. The workbook can use bold/semibold for labels and headers only; reserve regular for values and prose.

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F5F3EC` | Page canvas, broad neutral background |
| Secondary (30%) | `#FFFEFA` and `#113F3B` | Evidence cards, tables and panels; forest header/footer and selected dark navigation surface |
| Accent (10%) | `#0D7167` | Primary CTA, active navigation marker, keyboard focus ring, and source/lineage links only |
| Destructive | `#9B4839` | Validation errors and destructive/reset confirmations only |

Accent reserved for: the primary “Abrir corte actual”/“Abrir ejemplo sintético” entry action where applicable, the selected navigation item, keyboard focus indicator, and links that open source or lineage evidence. Do not color every control teal. Reserve `#B98236` for borders, fills and non-text accents. Use `#745323` for normal REVIEW/attention text on cream or white (6.30:1 on the cream canvas), always retaining the visible status word. Use neutral gray-green for ordinary statuses. Keep the existing 60/30/10 visual balance, with an ample cream canvas and white evidence cards.

Status must never be communicated by color alone. Pair every color or icon with a visible word: `LISTO`, `REVISAR`, `DESCONOCIDO`, `BLOQUEADO`, `PENDIENTE`, or `CERRADO`. Meet WCAG AA text contrast for foreground/background combinations; preserve visible keyboard focus. In Excel, keep the established blue fill for editable input cells, pair it with an “Entrada” legend and cell comments/instructions, and use text/status labels for output state.

## Copywriting Contract

All client-facing headings and actions are Spanish, consistent with the current client guide. Keep command names, field identifiers, source IDs, and metric names literal where needed; explain them in Spanish. Short copy names evidence and next action without presenting a recommendation as executed.

| Element | Copy |
|---------|------|
| Primary CTA | `Abrir corte actual` (only when a verified current cut is selected); otherwise `Abrir ejemplo sintético` |
| Empty state heading | `Todavía no hay un corte actual` |
| Empty state body | `Elige un paquete de fuentes local y ejecútalo con la guía del analista. Mientras tanto puedes explorar el ejemplo, marcado como sintético.` |
| Error state | `No se pudo validar este corte. Corrige las filas indicadas y vuelve a ejecutar el flujo; no se publicaron métricas para este corte.` |
| Destructive confirmation | `Restablecer esta plantilla: se borrarán los valores capturados en esta copia. Guarda primero una copia si necesitas conservarlos. Escribe RESTABLECER para continuar.` |

The portal has no destructive operation on private evidence. The reset text applies only if a workbook/kit offers an explicit reset control; do not add a reset control without preserving an untouched blank copy. Validation errors must identify the file/sheet/table and row/field, state the reason, and give the next correction step. Never use “0” to describe a missing value; render missing or incomplete evidence as `DESCONOCIDO` with a reason.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | Not applicable; project has no React app or `components.json`. |
| Third-party | none | Not applicable. |

## Phase 4 Interaction Contract

### Portal information architecture

Use a single static HTML portal with a compact sticky in-page navigation and these sections in this order:

1. **Inicio / corte seleccionado** — identify the active dataset, its role and provenance before showing numbers. Show cut ID, cutoff and timezone, source/report hash prefix with a copyable or selectable full hash, coverage/quality state, and the exact input manifest/report artifact links. If no private cut was selected, say so and offer the historical synthetic demo as a separate entry.
2. **Recorrido semanal** — show the ordered stages `Fuentes → Validación → Marts y métricas → Análisis → Revisión independiente → Decisión del responsable → Próximo corte`. Each stage shows a truthful state, timestamp/receipt if available, and next local artifact. `PENDIENTE`/`ESPERANDO_RESPUESTA` must remain visible when human/native work has not occurred.
3. **Decisiones** — list owner-ready packets and their review state. Expand a packet into four visibly separate groups: `Hechos`, `Desconocidos`, `Hipótesis`, and `Recomendaciones`; every recommendation displays its metric, guardrail, population, window, closure rule, owner and due date. Show evidence references next to the claim they support. Label advice as advisory; owner registration and later closure remain separate events.
4. **Excepciones y calidad** — put blocking/review/unknown items before passing checks. Each row names affected source/metric, exact reason, severity/state, next required evidence and a local evidence link. Preserve coverage gaps and failed reconciliations as unknown/blocked; do not hide them behind an overall green badge.
5. **Fuentes** — searchable, expandable source inventory grouped by v1 business domain. Every source exposes exact contract version, grain, keys, required/nullable fields, units, provenance, coverage, synthetic flag and its incoming/outgoing relationships. Search filters the inventory without hiding the total or current query; preserve anchor navigation when opening a source. The exact zero-result copy is heading `Sin coincidencias para “{consulta}”` and body `Borra el filtro o busca por fuente, campo, proceso o decisión. El inventario completo sigue disponible.`
6. **Métricas** — metric dictionary grouped by decision use (cost/price, purchasing/inventory, cash/obligations, sales/product learning, quality/readiness, budget/channel). Show formula, unit, grain, window, inputs, unknown rule, guardrail, owner and decision use. Link each metric to its registered mart and upstream sources. Keep management proxies distinct from statutory/tax outcomes and cash movement distinct from a bank balance.
7. **Procesos y roles** — show process trigger, states, gates, exceptions and resulting artifact; show each native role's purpose, permitted inputs, output schema, review partner, dispatch state/receipt and `PROHIBITED` authority boundary. Distinguish actual native Codex dispatch from a request bundle or deterministic analysis.
8. **Linaje y exportación** — provide a readable source → mart/metric → process/role → packet chain and local links to source/manifest/hash evidence. Include links to downloadable CSV/JSON/printable report artifacts when present and an offline operating guide. Never offer a network share, upload or publish action.

On wide screens, constrain reading width to 1480px, use a 32px page gutter, two-column evidence grids and horizontally scrollable bounded data tables. The overview may show up to six summary facts, with one primary status; do not turn the first screen into a wall of KPI tiles. On widths below 900px, collapse evidence grids to one column and source/process flows to two columns; below 600px use one column, 16px outer gutters, wrap long identifiers, and retain horizontal overflow only inside labelled tables. Sticky navigation scrolls horizontally on narrow screens and must remain keyboard operable. Each target section uses sufficient scroll margin that the sticky bar never covers its heading.

Use semantic `header`, labelled `nav`, `main`, `section`, headings in order, table captions and scoped column headers, native links and `<details>/<summary>` for optional source/packet detail. Every search field has an accessible label and a visible result count/zero-result message. All interactions work by keyboard with visible focus and without hover. Do not rely on script for critical content or navigation: printable/no-script content remains complete. Avoid animation except optional reduced-motion-aware anchor scrolling.

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

Open both workbooks in desktop Excel and common compatible spreadsheet readers without scripts or network. Provide a data dictionary and one workbook navigation index. Set landscape/page-fit-to-width print settings for wide sheets, repeat title/header rows, avoid clipped columns, show page numbers and workbook/cut labels, and place print breaks between independent tables. CSV/JSON exports preserve canonical exact columns, order, units and unknown/null representation; include a manifest with hashes and relation/domain mapping. The XLSX is a user-friendly editing surface, not the canonical audit history.

### One-command analyst journey

The analyst kit presents one copyable command from the repository root as the supported weekly entrypoint:

```powershell
.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs [--prior-register <register-dir> --prior-anchor <anchor.json>]
```

Use that exact invocation in `EMPIEZA_AQUI` and the offline analyst guide; `--help` and validation output must match the documented names byte for byte. When `--source-pack` points to an XLSX workbook, the workbook adapter first exports a canonical v1 CSV source pack and the weekly pipeline consumes that pack. `--policy` is the separate, versioned Phase 2 policy input. The system derives `cut_id` from the validated immutable input and creates `.local/client-runs/<cut_id>/` beneath `--output-root`; the caller never supplies or predicts that child path. `--prior-register` and `--prior-anchor` are optional, but must be supplied together and independently verified before carry-forward. Blank initialization is an explicit preparation action outside the weekly build and never publishes metrics. The command validates the full contract and privacy rules, builds a new immutable cut, calculates marts/reports and hashes, prepares and validates the analyst/reviewer task bundles, verifies/carries forward the prior decision register when the optional pair is present, and emits the public blank/example package plus a private run index under `.local/client-runs/`. The page/guide show this sequence as progress receipts with per-stage PASS/REVIEW/BLOCKED/WAITING states and local output paths. Repeated execution must not overwrite a prior immutable cut.

The command line may request live native Codex work only through the authorized native task bridge and must retain the actual dispatch receipt, task/model metadata and response hashes. If a native analyst or independent reviewer has not actually run, show a precise waiting state and next authorized continuation step; never simulate a response, turn a prepared request into a completed review, or issue an owner-ready packet from missing/stale evidence. After actual reviewer acceptance, carry-forward remains owner-controlled and records the original cut/source hash, owner, due date and closure evidence. Packaging is for the sanitized client kit only; private filled workbook, source pack, report, decision events and native responses remain in ignored `.local/` paths.

The guide has two clearly separated journeys: (1) client: open the blank template, fill required source tables, preserve empty vs zero, save a private local copy, return it to the analyst through their established local process; (2) analyst: execute the one command, inspect validation exceptions, wait for/record actual analyst and reviewer dispatches, present the owner packet, register an explicit owner decision, close/carry it to the next cut, and package only the blank/example offline kit. Keep the language plain and task-first. Do not imply that opening the portal uploads or synchronizes a workbook.

### Accessibility, print, export and package boundaries

- Meet WCAG AA contrast, full keyboard access, visible focus, meaningful link names, semantic tables/headings, labelled controls, text equivalents for status marks and reduced-motion support. Aim for 44px pointer targets. No data meaning is encoded only by color, hover, icon or graph shape.
- The HTML portal and guide must print legibly in black and white on letter/A4 portrait or landscape as content requires. Hide navigation, search controls and screen-only buttons in print; keep provenance, cut ID, cutoff, statuses, source/hash references and limitations. Repeat table headers, allow rows to break safely, and print visible local artifact names (never a private absolute filesystem path). Charts require text/table equivalents and must not crop negative/unknown values.
- Provide explicit local `Descargar CSV`, `Descargar JSON`, `Imprimir / Guardar PDF`, and workbook links only for artifacts actually present and verified. Every downloaded report/export retains cut ID, cutoff, provenance, units, null/coverage state, source hashes and applicable warnings. Do not describe a printable page as a saved PDF until the file exists.
- The distributable client ZIP contains only the offline portal, its required local assets/evidence, blank and synthetic-example workbooks/packs, the unapproved `REVIEW` policy template, the verified synthetic policy example, data dictionary, weekly guide, resolved/example decision walkthrough and package manifest/hash list. Include no filled private cuts, approved/private policy instances, owner approval references, private reports, native requests/responses/drafts, private decision register/events, credentials, `.local/`, or customer PII. Its first-open state is labelled historical synthetic demo with no private current cut selected. This static package opens through a local file URL with no server and no network access.
- Provide a separate private current-cut portal/run directory only under ignored `.local/`; do not place it beside public kit files or give it an ambiguous “demo” label. A manifest/inventory lists every packaged path/hash and allows local links to resolve after ZIP extraction. Display the offline/no-upload boundary and no-external-execution rule in `INICIO` and guide; business actions remain explicit human decisions.

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

**Approval:** approved 2026-09-22
