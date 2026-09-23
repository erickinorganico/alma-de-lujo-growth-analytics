"""Build the offline, synthetic v0.2 analytical-system atlas for the client.

Uses only release contracts and immutable evidence. No network, inference, or
warehouse mutation is involved. Run from any directory with Python 3.11+.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "evidence/v0.2/workspace"
OUT = ROOT / "client"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def link(path: Path) -> str:
    return "../" + rel(path)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def a(path: Path, label: str) -> str:
    return f'<a href="{esc(link(path))}">{esc(label)}</a>'


def norm_space(value: str) -> str:
    return " ".join(value.split())


def domain_map(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 4 or not cells[1] or cells[1] in {"Domain", "---"}:
            continue
        for name in re.findall(r"`([a-z_]+)`", cells[2]):
            result[name] = cells[1]
    result.setdefault("expenses", "Finance / expenses")
    result.setdefault("expense_payments", "Finance / expenses")
    return result


def mart_docs(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        match = re.match(r"\|\s*`([a-z_]+)`\s*\|[^|]*\|\s*(.*?)\s*\|\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).replace("`", "")
    return result


def purpose_map(text: str) -> dict[str, dict]:
    result = {}
    blocks = re.split(r"(?=^## `(?:PTS|LTD|RTR|FCL|WGR|MTE)-\d+`)", text, flags=re.M)
    for block in blocks:
        header = re.match(r"## `([^`]+)` — ([a-z-]+)", block)
        if not header:
            continue
        purpose = re.search(r"^Purpose:\s*(.+)$", block, re.M)
        decision = re.search(r"\| Decision product \|\s*(.*?)\s*\|", block)
        exceptions = sorted(set(re.findall(r"`([A-Z][A-Z0-9_]+)`", block)))
        result[header.group(2)] = {
            "contract_id": header.group(1),
            "purpose": purpose.group(1) if purpose else "",
            "decision_product": decision.group(1) if decision else "",
            "exceptions": [x for x in exceptions if "_" in x],
        }
    return result


def top_level_select(sql: str) -> str:
    """Return final SELECT projection, preserving exact SQL expressions."""
    depth = 0
    select_at = None
    in_quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            if in_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and re.match(r"SELECT\b", sql[i:], re.I):
                select_at = i + 6
            elif depth == 0 and select_at is not None and re.match(r"FROM\b", sql[i:], re.I):
                return sql[select_at:i]
        i += 1
    return ""


def final_expressions(sql: str) -> dict[str, str]:
    projection = top_level_select(sql)
    parts = []
    start = 0
    depth = 0
    quote = False
    for i, ch in enumerate(projection):
        if ch == "'":
            quote = not quote
        elif not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(projection[start:i].strip())
                start = i + 1
    parts.append(projection[start:].strip())
    result = {}
    for part in parts:
        alias = re.search(r"(?:\s+AS\s+|\s+)([a-z][a-z0-9_]*)$", part, re.I)
        if alias:
            result[alias.group(1)] = norm_space(part)
        elif re.fullmatch(r"[a-z][a-z0-9_]*", part, re.I):
            result[part] = part
    return result


def unit(name: str, mart: str) -> str:
    if name.endswith("_cents"):
        return "centavos MXN" if not (mart == "reconciliation" and name in {"source_cents", "mart_cents"}) else "según check_id: centavos MXN o unidades"
    if name.endswith("_qty") or name.endswith("_units"):
        return "unidades"
    if name.endswith("_rate"):
        return "ratio (0–1)"
    if name.endswith("_days"):
        return "días"
    if name.endswith("_known") or name.startswith("unknown_"):
        return "indicador 0/1"
    if name in {"date", "count_date"}:
        return "fecha ISO"
    if name == "month" or name.endswith("_month"):
        return "mes YYYY-MM"
    if name.endswith("_id") or name in {"channel", "arm", "stock_status", "check_id"}:
        return "dimensión"
    return "conteo / dimensión según SQL"


def render_list(items, empty="Sin registros"):
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>" if items else f"<p>{esc(empty)}</p>"


def json_pointer(document, pointer: str):
    assert pointer.startswith("/"), f"invalid evidence pointer: {pointer}"
    value = document
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def build() -> tuple[str, dict]:
    used: set[Path] = set()

    def j(path: Path):
        used.add(path)
        return read_json(path)

    def t(path: Path):
        used.add(path)
        return path.read_text(encoding="utf-8")

    workspace = j(WORK / "workspace.json")
    lineage = j(WORK / "lineage.json")
    quality = j(WORK / "quality.json")
    dictionary_path = ROOT / "specs/DATA-DICTIONARY.md"
    metrics_path = ROOT / "specs/METRIC-CATALOG.md"
    process_path = ROOT / "specs/PROCESS-CATALOG.md"
    agent_path = ROOT / "specs/AGENT-SYSTEM.md"
    domains = domain_map(t(dictionary_path))
    descriptions = mart_docs(t(metrics_path))
    process_docs = purpose_map(t(process_path))
    t(agent_path)

    counts = workspace["counts"]
    coverage = workspace["metadata"]["coverage"]
    source_names = sorted(counts)
    mart_names = lineage["schema"]["manifest"]["marts"]
    assert len(source_names) == 30 and len(mart_names) == 11
    assert set(source_names) == set(coverage)
    assert all(lineage["schema"]["catalog"][n]["relation_type"] == "source" for n in source_names)
    assert all(lineage["schema"]["catalog"][n]["relation_type"] == "materialized mart" for n in mart_names)

    marts = {}
    source_to_marts: dict[str, list[str]] = {x: [] for x in source_names}
    for name in mart_names:
        path = WORK / "marts" / (name + ".json")
        rows = j(path)
        sql_path = ROOT / "models/marts" / (name + ".sql")
        sql = t(sql_path)
        sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        recorded = lineage["sql"][name + ".sql"]["sha256"]
        assert sql_hash == recorded, f"SQL drift: {name}"
        dependencies = [s for s in source_names if re.search(r"\b(?:FROM|JOIN)\s+" + re.escape(s) + r"\b", sql, re.I)]
        upstream_marts = [s for s in mart_names if s != name and re.search(r"\b(?:FROM|JOIN)\s+" + re.escape(s) + r"\b", sql, re.I)]
        for source in dependencies:
            source_to_marts[source].append(name)
        marts[name] = {
            "rows": len(rows), "path": path, "sql_path": sql_path,
            "sql_text": sql,
            "grain": lineage["schema"]["catalog"][name]["grain"],
            "description": descriptions.get(name, ""),
            "columns": lineage["schema"]["tables"][name]["columns"],
            "expressions": final_expressions(sql),
            "dependencies": dependencies,
            "upstream_marts": upstream_marts,
            "coverage_dependencies": sorted(set(re.findall(r"\{\{coverage:([a-z_]+)\}\}", sql))),
        }

    processes = {}
    mart_to_processes = {x: [] for x in mart_names}
    for state_path in sorted((WORK / "processes").glob("*/state.json")):
        pid = state_path.parent.name
        state = j(state_path)
        packet_path = state_path.parent / "decision-packet.json"
        packet = j(packet_path)
        definition_path = ROOT / "processes/business" / (pid + ".json")
        definition = j(definition_path)
        assert state["process_id"] == packet["process_id"] == definition["id"] == pid
        assert packet["synthetic"] is True and packet["external_execution"] == "PROHIBITED"
        refs = []
        for fact in packet["facts"]:
            refs.extend(fact.get("evidence_refs", []))
        for rec in packet["recommendations"]:
            refs.extend(rec.get("evidence_refs", []))
        linked_marts = [x for x in mart_names if any(ref.startswith("/marts/" + x + "/") for ref in refs)]
        for mart in linked_marts:
            mart_to_processes[mart].append(pid)
        # Requests and responses are the actual role-to-process evidence.
        task_files = sorted((state_path.parent / "tasks").glob("*.request.json"))
        analyst_evidence = None
        for task_file in task_files:
            request = j(task_file)
            if task_file.name != "evidence_reviewer.request.json":
                analyst_evidence = request["evidence"]
            response = task_file.with_name(task_file.name.replace(".request.json", ".response.json"))
            dispatch = task_file.with_name(task_file.name.replace(".request.json", ".dispatch.json"))
            if response.exists():
                j(response)
            if dispatch.exists():
                j(dispatch)
        assert analyst_evidence is not None, f"missing analyst evidence: {pid}"
        for fact in packet["facts"]:
            resolved = [json_pointer(analyst_evidence, ref) for ref in fact["evidence_refs"]]
            if fact["value"] is not None:
                assert any(value == fact["value"] for value in resolved), f"fact not bound to exact evidence: {pid}/{fact['id']}"
        processes[pid] = {
            "state": state, "packet": packet, "definition": definition,
            "state_path": state_path, "packet_path": packet_path,
            "definition_path": definition_path,
            "docs": process_docs.get(pid, {}), "marts": linked_marts,
        }
    assert len(processes) == 6

    agents = {}
    for path in sorted((ROOT / "agents").glob("*.json")):
        contract = j(path)
        if "id" not in contract:
            continue
        executions = []
        for pid, p in processes.items():
            receipt = p["state"]["responses"].get(contract["id"])
            if receipt:
                executions.append({"process_id": pid, "receipt": receipt})
        agents[contract["id"]] = {"contract": contract, "path": path, "executions": executions}
    assert len(agents) == 7
    task_runs_path = ROOT / "evidence/v0.2/agents/task-runs.json"
    model_provenance_path = ROOT / "evidence/v0.2/agents/model-provenance.json"
    task_runs = j(task_runs_path)
    j(model_provenance_path)

    # A later local cost/operations extension is a separate release surface.
    # It is folded into this static file at build time, since file:// browsers
    # cannot reliably fetch adjacent JSON without a local server.
    extension_path = OUT / "costs-operations-manifest.json"
    extension = j(extension_path) if extension_path.exists() else None
    extension_page = OUT / "COSTOS_Y_OPERACION.html"
    if extension_page.exists():
        used.add(extension_page)
    if extension is not None:
        assert extension.get("synthetic") is True, "cost/operations extension must be explicitly synthetic"
        for gap in extension.get("extension_matrix", []):
            for ref in gap.get("evidence_refs", []):
                evidence_path = (ROOT / ref["path"]).resolve()
                assert evidence_path.is_relative_to(ROOT.resolve()), "gap evidence outside repository"
                assert sha(evidence_path) == ref["sha256"], f"stale gap evidence: {ref['path']}"
                used.add(evidence_path)
        bridge = extension.get("catalog_bridge")
        if bridge:
            catalog_path = ROOT / bridge["source_path"]
            catalog = j(catalog_path)
            known_skus = {row[bridge["source_key"]] for row in catalog[bridge["source_collection"]]}
            unresolved = set()
            for ref in bridge["local_tables"]:
                table_name, field = ref.split(".", 1)
                local_csv = OUT / "operating-data" / (table_name + ".csv")
                with local_csv.open(encoding="utf-8-sig", newline="") as handle:
                    unresolved.update(row[field] for row in csv.DictReader(handle) if row[field] not in known_skus)
            assert sorted(unresolved) == bridge["unresolved_skus"], "extension catalog bridge drift"
    ext_tables_raw = (extension or {}).get("sources", (extension or {}).get("tables", (extension or {}).get("extension_tables", [])))
    if isinstance(ext_tables_raw, dict):
        ext_tables = [dict(value, id=key) if isinstance(value, dict) else {"id": key, "value": value} for key, value in ext_tables_raw.items()]
    elif isinstance(ext_tables_raw, list):
        ext_tables = [x if isinstance(x, dict) else {"id": str(x)} for x in ext_tables_raw]
    else:
        ext_tables = []
    for table in ext_tables:
        if "file" not in table:
            continue
        file_path = (OUT / "operating-data" / table["file"]).resolve()
        assert file_path.is_relative_to(OUT.resolve()), "extension file outside client directory"
        assert file_path.is_file(), f"missing extension CSV: {file_path}"
        if "sha256" in table:
            assert sha(file_path) == table["sha256"], f"stale extension CSV: {file_path}"
        used.add(file_path)
        if "rows" in table:
            with file_path.open(encoding="utf-8-sig", newline="") as handle:
                assert sum(1 for _ in csv.DictReader(handle)) == table["rows"], f"extension row mismatch: {file_path}"
    ext_capabilities_raw = (extension or {}).get("capabilities", [])
    if isinstance(ext_capabilities_raw, dict):
        ext_capabilities = [dict(value, id=key) if isinstance(value, dict) else {"id": key, "status": str(value)} for key, value in ext_capabilities_raw.items()]
    elif isinstance(ext_capabilities_raw, list):
        ext_capabilities = [x if isinstance(x, dict) else {"id": str(x)} for x in ext_capabilities_raw]
    else:
        ext_capabilities = []

    # Source CSVs establish that manifest counts match the delivered synthetic rows.
    for name in source_names:
        path = WORK / "tables" / (name + ".csv")
        used.add(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            observed = sum(1 for _ in csv.DictReader(handle))
        assert observed == counts[name], f"count drift: {name}"

    issues = [x for x in quality if x.get("status") != "PASS"]
    sections = {
        "sources": len(source_names), "source_rows": sum(counts.values()),
        "marts": len(mart_names), "mart_rows": sum(m["rows"] for m in marts.values()),
        "metric_columns": sum(len(m["columns"]) for m in marts.values()),
        "processes": len(processes), "agents": len(agents),
        "decision_packets": sum(1 for p in processes.values() if p["packet"]),
        "quality_checks": len(quality), "quality_non_pass": len(issues),
        "extension_tables": len(ext_tables),
        "packet_facts_validated": sum(len(p["packet"]["facts"]) for p in processes.values()),
    }

    def evidence_ref(path: Path) -> dict:
        used.add(path)
        return {"path": rel(path), "sha256": sha(path)}

    base_sources = []
    for name in source_names:
        struct = lineage["schema"]["tables"][name]
        downstream = source_to_marts[name]
        decisions = sorted({pid for mart in downstream for pid in mart_to_processes[mart]})
        base_sources.append({
            "table": name, "domain": domains.get(name, "Fuente"),
            "grain": lineage["schema"]["catalog"][name]["grain"],
            "primary_key": [c["name"] for c in struct["columns"] if c["pk"]],
            "fields": [c["name"] for c in struct["columns"]],
            "row_count": counts[name], "synthetic": True,
            "decision_use": (" → ".join(downstream) + (" → " + ", ".join(decisions) if decisions else ""))
                            if downstream else "Fuente contextual del snapshot; sin JOIN directo en los marts publicados",
            "evidence_refs": [evidence_ref(WORK / "tables" / (name + ".csv")), evidence_ref(WORK / "workspace.json")],
        })
    metric_records = []
    lineage_edges = []
    for name in mart_names:
        m = marts[name]
        upstream = m["dependencies"]
        decision = ", ".join(mart_to_processes[name]) or "Lectura y control del warehouse"
        measure_units = sorted({unit(c["name"], name) for c in m["columns"]})
        metric_records.append({
            "id": name, "formula": m["sql_text"],
            "definition": m["description"] or "Definido por SQL registrado",
            "unit": ", ".join(measure_units), "grain": m["grain"],
            "window": "según fecha/mes del grano; trailing_30d cuando se indica en columna",
            "sources": upstream, "unknown": "NULL/UNKNOWN cuando cobertura o denominador no permite medir; no sustituir por cero",
            "guardrail": "Cobertura requerida: " + (", ".join(m["coverage_dependencies"]) or "controles de calidad y SQL"),
            "decision": decision, "sql": rel(m["sql_path"]),
            "fields": [{"name": c["name"], "type": c["type"], "unit": unit(c["name"], name),
                        "definition_sql": m["expressions"].get(c["name"]),
                        "nullable_in_materialized_schema": not bool(c["notnull"])} for c in m["columns"]],
            "evidence_refs": [evidence_ref(m["sql_path"]), evidence_ref(m["path"])],
        })
        lineage_edges.extend({"source": src, "target": name, "kind": "SQL FROM/JOIN"} for src in upstream)
        lineage_edges.extend({"source": src, "target": name, "kind": "SQL mart dependency"} for src in m["upstream_marts"])
    for mart, consumer_ids in mart_to_processes.items():
        lineage_edges.extend({"source": mart, "target": pid, "kind": "packet evidence reference"} for pid in consumer_ids)
    for pid, p in processes.items():
        lineage_edges.extend({"source": pid, "target": aid, "kind": "accepted native response"} for aid in p["state"]["responses"])
        lineage_edges.append({"source": pid, "target": "decision-packet:" + pid, "kind": "reviewed packet"})
    process_records = []
    for pid, p in processes.items():
        definition = p["definition"]
        states = sorted({definition["initial_state"], *definition["terminal_states"], *(state for tr in definition["transitions"] for state in tr["from"]), *(tr["to"] for tr in definition["transitions"])})
        process_records.append({
            "id": pid, "trigger": definition["transitions"][0]["event"], "states": states,
            "controls": sorted({tr["gate"] for tr in definition["transitions"]}),
            "exceptions": p["docs"].get("exceptions", []),
            "decision": p["docs"].get("decision_product", "Paquete de decisión para responsable"),
            "status": p["state"]["status"], "marts": p["marts"],
            "evidence_refs": [evidence_ref(p["definition_path"]), evidence_ref(p["state_path"]), evidence_ref(p["packet_path"])],
        })
    role_records = []
    for aid, item in agents.items():
        c = item["contract"]
        role_records.append({
            "id": aid, "role": c["name"], "inputs": c["authority"]["read"],
            "outputs": c["output"],
            "authority": {"read": c["authority"]["read"], "write": c["authority"]["write"], "external": "PROHIBITED"},
            "reviewer": "independent_evidence_review" if aid != "evidence_reviewer" else "independent reviewer of analyst response",
            "processes": [x["process_id"] for x in item["executions"]],
            "evidence_refs": [evidence_ref(item["path"])],
        })
    matrix = []
    for title, current, status, pending in [
        ("Ficha y versiones de costos", "Costo unitario y COGS con cobertura", "PARTIAL", "Partidas, versión y autorización financiera"),
        ("Asignaciones y redondeo", "Sin contrato de reparto documentado en v0.2", "MISSING", "Reparto compartido reconciliado"),
        ("Compras y recepciones", "PO, receipt, payment y movimiento sintéticos", "PARTIAL", "Inspección/preparación operativa"),
        ("Obligaciones y pagos", "Pagos de proveedor/gastos como hechos", "PARTIAL", "Saldo obligado y fechas futuras"),
        ("Caja liquidada, comprometida y escenario", "Movimiento liquidado; sin saldo bancario inicial", "PARTIAL", "Proyección de ocho semanas con cobertura"),
        ("Calidad e incidencias", "Retornos físicos separados de créditos/reembolsos", "PARTIAL", "Casos de calidad vinculados"),
        ("Permisos financieros", "Autoridad de agentes prohíbe acciones externas", "PARTIAL", "Autorización operativa por rol/dato no demostrada"),
        ("Historia y conciliación", "Eventos y reconciliación fuente-mart sintéticos", "PARTIAL", "Versiones de costo y corrección trazable de partidas"),
    ]:
        matrix.append({"title": title, "status": status, "scope": pending, "current": current,
                       "evidence_refs": [evidence_ref(WORK / "lineage.json"), evidence_ref(process_path)]})
    state_map = {
        "IMPLEMENTED_LOCAL": "EXISTS",
        "SPECIFIED_NOT_IMPLEMENTED": "SPECIFIED",
        "PARTIAL": "PARTIAL",
        "PENDING_AUTHORIZED_DATA": "MISSING",
        "CONFLICT_OUT_OF_SCOPE": "CONFLICT",
    }
    status_mapping = {**{state: state for state in ("EXISTS", "SPECIFIED", "PARTIAL", "MISSING", "CONFLICT")}, **state_map}
    extension_matrix = []
    if extension is not None:
        for item in extension.get("extension_matrix", []):
            raw_status = item.get("status", "")
            assert raw_status in state_map, f"unknown extension state: {raw_status}"
            statement = item.get("evidence", "")
            refs = [evidence_ref(ROOT / ref["path"]) for ref in item.get("evidence_refs", [])]
            if not refs:
                refs = [evidence_ref(extension_path)]
            record = {
                "title": item.get("capability", ""), "status": state_map[raw_status],
                "source_status": raw_status, "scope": "extensión local sintética v" + str(extension.get("version", "")),
                "current": statement, "evidence_refs": refs,
            }
            extension_matrix.append(record)
            matrix.append(record)
    manifest = {
        "version": "1.0", "title": "Sistema analítico Alma de Lujo · v0.2",
        "scope": "Representación estática offline de contratos y evidencia sintética; ninguna acción externa",
        "as_of": workspace["metadata"]["as_of"],
        "synthetic": workspace["metadata"]["synthetic"],
        "warehouse_contract_version": workspace["version"],
        "source_content_hash": lineage["schema"]["manifest"]["source_content_hash"],
        "sections": sections,
        "base_sources": base_sources,
        "metrics": metric_records,
        "lineage": {"edges": lineage_edges, "evidence_refs": [evidence_ref(WORK / "lineage.json")]},
        "processes": process_records,
        "roles": role_records,
        "extension_matrix": matrix,
        "extension_status_mapping": state_map,
        "status_mapping": status_mapping,
        "ids": {"sources": source_names, "marts": mart_names, "processes": sorted(processes), "agents": sorted(agents)},
        "coverage": coverage,
        "source_to_marts": source_to_marts,
        "mart_to_marts_by_sql": {name: marts[name]["upstream_marts"] for name in mart_names},
        "mart_to_processes_by_packet_references": mart_to_processes,
        "process_to_agents_by_accepted_response": {pid: sorted(p["state"]["responses"]) for pid, p in processes.items()},
        "packet_status": {pid: p["packet"]["status"] for pid, p in processes.items()},
        "extension": {"present": extension is not None, "version": (extension or {}).get("version"),
                      "synthetic": (extension or {}).get("synthetic"),
                      "table_ids": [x.get("id", x.get("name")) for x in ext_tables],
                      "capability_ids": [x.get("id", x.get("name")) for x in ext_capabilities]},
        "source_sha256": {rel(path): sha(path) for path in sorted(used)},
        "links_are_relative": True,
    }

    # HTML intentionally embeds no data fetch or remote asset. All paths work
    # from a checked-out repo or an archive preserving its directory tree.
    source_cards = []
    for name in source_names:
        structure = lineage["schema"]["tables"][name]
        cols = structure["columns"]
        pk = [x["name"] for x in cols if x["pk"]]
        fk = structure["foreign_keys"]
        related = source_to_marts[name]
        decisions = sorted({pid for mart in related for pid in mart_to_processes[mart]})
        rows = "".join(f'<tr><td><code>{esc(c["name"])}</code></td><td>{esc(c["type"])}</td><td>{"PK" if c["pk"] else ""}{" · NULL permitido" if not c["notnull"] else ""}</td></tr>' for c in cols)
        fk_html = ", ".join(f'<code>{esc(x["from"])} → {esc(x["table"])}.{esc(x["to"])}</code>' for x in fk) or "Sin FK declarada"
        tags = "".join(f'<a class="chip" href="#mart-{esc(x)}">{esc(x)}</a>' for x in related)
        process_tags = "".join(f'<a class="chip secondary" href="#process-{esc(x)}">{esc(x)}</a>' for x in decisions)
        source_cards.append(f'''<details class="card searchable" id="source-{esc(name)}" data-search="{esc(name + ' ' + domains.get(name, '') + ' ' + ' '.join(related + decisions))}"><summary><span><code>{esc(name)}</code><small>{esc(domains.get(name, 'Fuente'))} · {esc(lineage["schema"]["catalog"][name]["grain"])}</small></span><strong>{counts[name]:,} filas</strong></summary><div class="detail-body"><p><b>Grano:</b> {esc(lineage["schema"]["catalog"][name]["grain"])}. <b>Clave primaria:</b> {esc(', '.join(pk))}. <b>Cobertura:</b> {"declarada" if coverage[name] else "UNKNOWN"}. <b>Origen:</b> snapshot sintético.</p><p><b>Claves relacionadas:</b> {fk_html}</p><p><b>Alimenta marts:</b> {tags or 'No aparece en un FROM/JOIN directo de estos SQL.'}</p><p><b>Decisiones vinculadas por referencias de paquetes:</b> {process_tags or 'Sin referencia de mart en paquetes actuales.'}</p><table><thead><tr><th>Campo</th><th>Tipo</th><th>Contrato</th></tr></thead><tbody>{rows}</tbody></table><p class="source-link">{a(WORK / 'tables' / (name + '.csv'), 'CSV sintético')} · {a(dictionary_path, 'Diccionario contractual')}</p></div></details>''')

    mart_cards = []
    for name in mart_names:
        m = marts[name]
        columns = []
        for col in m["columns"]:
            cname = col["name"]
            expr = m["expressions"].get(cname, "Expresión final no aislada; consultar SQL completo")
            window = "últimos 30 días" if "trailing_30d" in cname else ("mes calendario" if "month" in m["grain"] else m["grain"])
            semantics = "NULL = desconocido/no medido; no sustituir por cero" if not col["notnull"] else ("0 = indicador falso según SQL" if cname.endswith("_known") else "Valor según cobertura y SQL")
            columns.append(f'<tr><td><code>{esc(cname)}</code></td><td>{esc(unit(cname, name))}</td><td>{esc(window)}</td><td><code class="expression">{esc(expr)}</code></td><td>{esc(semantics)}</td></tr>')
        source_tags = "".join(f'<a class="chip" href="#source-{esc(x)}">{esc(x)}</a>' for x in m["dependencies"])
        upstream_tags = "".join(f'<a class="chip" href="#mart-{esc(x)}">{esc(x)}</a>' for x in m["upstream_marts"])
        process_tags = "".join(f'<a class="chip secondary" href="#process-{esc(x)}">{esc(x)}</a>' for x in mart_to_processes[name])
        gates = ", ".join(m["coverage_dependencies"]) or "revisar SQL y calidad"
        mart_cards.append(f'''<details class="card searchable" id="mart-{esc(name)}" data-search="{esc(name + ' ' + m['description'] + ' ' + ' '.join(x['name'] for x in m['columns']))}"><summary><span><code>{esc(name)}</code><small>{esc(m["grain"])}</small></span><strong>{m["rows"]:,} filas</strong></summary><div class="detail-body"><p>{esc(m["description"])}</p><p><b>Grano:</b> {esc(m["grain"])} · <b>Guardia de cobertura en SQL:</b> {esc(gates)} · <b>Estado:</b> cálculo determinista sobre simulación.</p><p><b>Fuentes directas:</b> {source_tags or 'Ninguna fuente en FROM/JOIN directo.'}</p><p><b>Marts anteriores:</b> {upstream_tags or 'Ninguno.'}</p><p><b>Decisión que informa:</b> {process_tags or 'Control de calidad para decisiones del warehouse.'}</p><p>{a(m["sql_path"], 'Definición SQL completa')} · {a(m["path"], 'Filas materializadas')} · {a(metrics_path, 'Contrato de métricas')}</p><div class="table-wrap"><table><thead><tr><th>Campo</th><th>Unidad</th><th>Ventana / grano</th><th>Definición en SELECT final</th><th>Desconocido</th></tr></thead><tbody>{''.join(columns)}</tbody></table></div></div></details>''')

    process_cards = []
    for pid, p in processes.items():
        definition, state, packet = p["definition"], p["state"], p["packet"]
        doc = p["docs"]
        transitions = "".join(f'<tr><td>{esc(", ".join(x["from"]))}</td><td><code>{esc(x["event"])}</code></td><td>{esc(x["to"])}</td><td>{esc(x["gate"])}</td></tr>' for x in definition["transitions"])
        analyst = [(agent, receipt) for agent, receipt in state["responses"].items() if agent != "evidence_reviewer"]
        roles = " · ".join(f'{esc(agent)} ({esc(receipt["model"])})' for agent, receipt in analyst)
        reviewer = state["responses"].get("evidence_reviewer", {})
        evidence = f'{a(p["state_path"], "Estado")} · {a(p["packet_path"], "Paquete")} · {a(p["definition_path"], "Definición")}'
        process_cards.append(f'''<details class="card searchable" id="process-{esc(pid)}" data-search="{esc(pid + ' ' + state['owner'] + ' ' + doc.get('purpose', ''))}"><summary><span><code>{esc(pid)}</code><small>{esc(doc.get("contract_id", definition["contract_id"]))} · {esc(state["owner"])}</small></span><strong class="status">{esc(state["status"])}</strong></summary><div class="detail-body"><p>{esc(doc.get("purpose", ""))}</p><p><b>Producto de decisión:</b> {esc(doc.get("decision_product", ""))}</p><p><b>Estado analítico persistido:</b> {esc(state["step"])} / {esc(state["status"])}. <b>Estados operativos terminales:</b> {esc(', '.join(definition["terminal_states"]))}.</p><p><b>Analista ejecutado:</b> {roles}. <b>Revisor independiente:</b> {esc(reviewer.get("model", "sin recibo"))}. <b>Veredicto:</b> {esc(packet["review"]["verdict"])}.</p><p><b>Marts citados:</b> {''.join(f'<a class="chip" href="#mart-{esc(x)}">{esc(x)}</a>' for x in p["marts"]) or 'Ninguno por puntero directo.'}</p><p><b>Excepciones documentadas:</b> {esc(', '.join(doc.get("exceptions", [])) or 'Ver catálogo contractual')}.</p><div class="table-wrap"><table><thead><tr><th>Desde</th><th>Evento</th><th>Hacia</th><th>Control</th></tr></thead><tbody>{transitions}</tbody></table></div><p class="source-link">{evidence} · {a(process_path, 'Catálogo y excepciones')}</p></div></details>''')

    agent_cards = []
    for aid, item in agents.items():
        c = item["contract"]
        executions = "".join(f'<li><a href="#process-{esc(x["process_id"])}">{esc(x["process_id"])}</a>: {esc(x["receipt"]["model"])} · recibo <code>{esc(x["receipt"]["sha256"][:12])}…</code></li>' for x in item["executions"])
        agent_cards.append(f'''<details class="card searchable" id="agent-{esc(aid)}" data-search="{esc(aid + ' ' + c['name'] + ' ' + c['objective'])}"><summary><span><code>{esc(aid)}</code><small>{esc(c["name"])}</small></span><strong>{len(item["executions"])} procesos</strong></summary><div class="detail-body"><p><b>Rol:</b> {esc(aid.replace('_', ' '))}. {esc(c["objective"])}</p><p><b>Entrada:</b> {esc(c["authority"]["read"])}. <b>Herramientas permitidas:</b> {esc(', '.join(c["tools"]))}.</p><p><b>Salida:</b> {esc(c["output"])} · {esc(c["authority"]["write"])}. <b>Autoridad externa:</b> {esc(c["authority"]["external_business_actions"])}. <b>Revisor independiente:</b> {"evidence_reviewer" if aid != "evidence_reviewer" else "este rol revisa respuestas de analistas distintos"}.</p><p><b>Runtime:</b> {esc(c["runtime"])}</p><p><b>Ejecución y evidencia:</b></p><ul>{executions}</ul><p><b>Cierre del contrato:</b> {esc('; '.join(c["completion"]))}</p><p><b>Falla cerrada:</b> {esc('; '.join(c["fail_closed"]))}</p><p class="source-link">{a(item["path"], 'Contrato del rol')} · {a(task_runs_path, 'Recibos de tareas')} · {a(model_provenance_path, 'Procedencia de modelos')}</p></div></details>''')

    packet_cards = []
    for pid, p in processes.items():
        packet = p["packet"]
        facts = "".join(f'<li><span class="fact-id">{esc(x["id"])}</span> {esc(x["statement"])} <b>{esc(x["value"] if x["value"] is not None else "UNKNOWN")}</b><small>Refs: {esc(", ".join(x["evidence_refs"]))}</small></li>' for x in packet["facts"])
        recs = "".join(f'<li><b>{esc(x["id"])}</b>: {esc(x["action"])}<div class="rec-meta">Métrica: {esc(x["primary_metric"])} · Guardia: {esc(x["guardrail"])} · Población: {esc(x["population"])} · Ventana: {esc(x["window"])} · Cierre: {esc(x["closure_rule"])}</div><small>Aprobación humana: {esc(x["approval_required"])} · Ejecución: {esc(x["execution"])}</small></li>' for x in packet["recommendations"])
        packet_cards.append(f'''<article class="packet searchable" id="packet-{esc(pid)}" data-search="{esc(pid + ' ' + ' '.join(x['statement'] for x in packet['facts']))}"><div class="packet-head"><div><span class="eyebrow">PAQUETE DE DECISIÓN · {esc(pid)}</span><h3>{esc(p["state"]["owner"])}</h3></div><span class="status">{esc(packet["status"])}</span></div><p class="notice">Datos de negocio sintéticos; fuentes públicas de mercado citadas aparte · corte {esc(workspace["metadata"]["as_of"])} · revisión {esc(packet["review"]["verdict"])} · ejecución externa {esc(packet["external_execution"])}</p><h4>Hechos citados</h4><ul class="facts">{facts}</ul><h4>Recomendaciones para decisión del responsable</h4><ol class="recs">{recs}</ol><h4>Desconocidos</h4>{render_list(packet["unknowns"])}<p class="source-link">{a(p["packet_path"], 'Paquete completo')} · {a(p["state_path"], 'Estado y recibos')}</p></article>''')

    gap_rows = [
        ("Costos visibles por producto", "El snapshot guarda costo unitario en variantes y líneas; finance_monthly conserva COGS desconocido cuando falta costo.", "PARCIAL", "Partidas/versiones documentadas, cobertura por componente, reparto y lectura autorizada. No se conoce costo ni precio real."),
        ("Compras y recepciones", "purchase_orders, purchase_receipts, supplier_payments y movements modelan compras, pagos y stock aceptado; PTS-01 tiene controles e idempotencia sintéticos.", "YA SOPORTADO EN BASE SINTÉTICA", "Inspección/preparación, discrepancias por línea y recorrido operativo sobre hechos reales siguen pendientes."),
        ("Obligaciones y caja", "cash_daily reúne eventos liquidados; finance_monthly separa gasto de caja y el paquete FCL-01 declara ausencia de saldo bancario.", "PARCIAL", "Obligaciones futuras, saldo inicial conciliado y proyección de ocho semanas; no llamar disponible al movimiento neto."),
        ("Inventario accionable", "inventory_position y inventory_aging calculan disponible, tránsito, conteos y cobertura con reglas de UNKNOWN/PRELAUNCH.", "PARCIAL", "Ubicación, preparación/no vendible, evidencia de última verificación y sugerencias con aprobación humana."),
        ("Resultados por drop/canal", "channel_performance vincula ventas entregadas y gasto descriptivo; no declara atribución causal.", "PARCIAL", "Presupuesto, compromisos y asignaciones sin duplicar venta/gasto; fuentes reales faltantes."),
        ("Calidad, contenido y préstamos", "Devoluciones y content_assets existen como hechos sintéticos separados.", "PENDIENTE", "Incidencias vinculadas, paquete comercial autorizado y custodia de préstamos antes de activarlos."),
    ]
    gap_evidence = [
        [WORK / "tables/variants.csv", ROOT / "models/marts/finance_monthly.sql"],
        [WORK / "tables/purchase_orders.csv", WORK / "tables/purchase_receipts.csv"],
        [ROOT / "models/marts/cash_daily.sql", processes["finance-close"]["packet_path"]],
        [ROOT / "models/marts/inventory_position.sql", ROOT / "models/marts/inventory_aging.sql"],
        [ROOT / "models/marts/channel_performance.sql"],
        [WORK / "tables/returns.csv", WORK / "tables/content_assets.csv"],
    ]
    gap_html = ""
    for (title, current, status, pending), paths in zip(gap_rows, gap_evidence):
        refs_html = " · ".join(f'{a(path, path.name)} <code>{sha(path)[:12]}…</code>' for path in paths)
        gap_html += f'<tr><td><b>{esc(title)}</b></td><td>{esc(current)}<small class="source-link">{refs_html}</small></td><td><span class="status">{esc(status)}</span></td><td>{esc(pending)}</td></tr>'
    if extension is None:
        extension_html = '<p class="notice">La ampliación local de costos y operaciones aún no tiene manifest de entrega en este árbol. La matriz describe la base v0.2 y necesidades de la adenda candidata; no certifica implementación nueva.</p>'
    else:
        bridge_html = ""
        if extension.get("catalog_bridge"):
            bridge_data = extension["catalog_bridge"]
            bridge_path = ROOT / bridge_data["source_path"]
            bridge_html = f'<p><b>Puente al catálogo del kit:</b> {a(bridge_path, bridge_data["source_path"])} · llave <code>{esc(bridge_data["source_key"])}</code> · SKU sin resolver: {len(bridge_data["unresolved_skus"])}. Este vínculo relaciona ejemplos sintéticos; no fusiona las 30 fuentes del warehouse con las 8 tablas de extensión.</p>'
        ext_rows = ""
        for x in ext_tables:
            label = x.get("id", x.get("name", "sin ID"))
            local_file = OUT / "operating-data" / x.get("file", "")
            table_link = a(local_file, label) if x.get("file") and local_file.is_file() else f"<code>{esc(label)}</code>"
            ext_rows += f'<tr><td>{table_link}</td><td>{esc(x.get("grain", "grano no declarado"))}</td><td>{esc(x.get("rows", x.get("count", "sin conteo")))}</td><td>{esc(x.get("purpose", x.get("status", "extensión sintética")))}</td></tr>'
        cap_rows = "".join(f'<li><b>{esc(x.get("title", x.get("id", "capacidad")))}</b>: {esc(x.get("status", "extensión sintética"))}{" — " + esc(x.get("description")) if x.get("description") else ""}</li>' for x in ext_capabilities)
        cap_html = "<ul>" + cap_rows + "</ul>" if cap_rows else "<p>El manifest no declara capacidades.</p>"
        ext_matrix_rows = ""
        for x in extension_matrix:
            refs_html = " · ".join(f'{a(ROOT / ref["path"], Path(ref["path"]).name)} <code>{ref["sha256"][:12]}…</code>' for ref in x["evidence_refs"])
            ext_matrix_rows += f'<tr><td>{esc(x["title"])}</td><td><span class="status">{esc(x["status"])}</span><small>{esc(x["source_status"])}</small></td><td>{esc(x["current"])}<small class="source-link">{refs_html}</small></td></tr>'
        ext_matrix_html = f'<h4>Estado declarado de cada capacidad</h4><div class="table-wrap"><table><thead><tr><th>Capacidad</th><th>Estado local</th><th>Evidencia o límite</th></tr></thead><tbody>{ext_matrix_rows}</tbody></table></div>' if ext_matrix_rows else ""
        ext_metric_rows = "".join(f'<tr><td><code>{esc(x.get("id", ""))}</code></td><td>{esc(x.get("formula", ""))}</td><td>{esc(x.get("unit", ""))}</td><td>{esc(x.get("unknown", ""))}</td></tr>' for x in extension.get("metric_definitions", []))
        metrics_html = f'<h4>Métricas adicionales declaradas</h4><div class="table-wrap"><table><thead><tr><th>Métrica</th><th>Fórmula</th><th>Unidad</th><th>Desconocido</th></tr></thead><tbody>{ext_metric_rows}</tbody></table></div>' if ext_metric_rows else ""
        value_groups = ""
        for group, values in extension.get("metrics", {}).items():
            if not isinstance(values, list) or not values:
                continue
            fields = [x for x in values[0] if x not in {"evidence_refs", "source_refs"}]
            rows_html = "".join("<tr>" + "".join(f'<td>{esc(row.get(field) if row.get(field) is not None else "UNKNOWN")}</td>' for field in fields) + "</tr>" for row in values[:20])
            value_groups += f'<details class="card"><summary><span><code>{esc(group)}</code><small>{len(values)} registros sintéticos; hasta 20 visibles</small></span></summary><div class="detail-body table-wrap"><table><thead><tr>{"".join(f"<th>{esc(field)}</th>" for field in fields)}</tr></thead><tbody>{rows_html}</tbody></table></div></details>'
        page_link = " · " + a(extension_page, "Vista de costos y operación") if extension_page.exists() else ""
        legend_html = '<p class="muted"><b>Estados canónicos:</b> EXISTS = verificable localmente · SPECIFIED = especificado sin código · PARTIAL = cobertura parcial · MISSING = evidencia/datos pendientes · CONFLICT = alcance incompatible.</p>'
        extension_html = f'<p class="notice">Extensión local sintética v{esc(extension.get("version", "sin versión"))}, separada de las {sections["sources"]} fuentes inmutables de v0.2. {a(extension_path, "Manifest de extensión")}{page_link}</p>{legend_html}{ext_matrix_html}{bridge_html}<div class="table-wrap"><table><thead><tr><th>Tabla adicional</th><th>Grano</th><th>Filas sintéticas</th><th>Propósito</th></tr></thead><tbody>{ext_rows}</tbody></table></div>{metrics_html}<h4>Medidas calculadas de ejemplo</h4>{value_groups}<h4>Capacidades declaradas por la extensión</h4>{cap_html}'

    quality_summary = " · ".join(f"{esc(k)}: {v}" for k, v in sorted({s: sum(x.get('status') == s for x in quality) for s in {x.get('status') for x in quality}}.items()))
    body = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Sistema analítico · Alma de Lujo</title><style>
    :root{{--ink:#153332;--muted:#526b69;--paper:#f5f3ec;--card:#fffefa;--line:#d9dfd6;--teal:#0d7167;--teal-soft:#e1f1ec;--gold:#b98236;--red:#9b4839;--shadow:0 12px 35px rgba(25,45,40,.07)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth;overflow-x:clip}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}a{{color:var(--teal)}}.shell{{max-width:1480px;margin:auto;padding:0 32px}}header{{background:#113f3b;color:#fff;padding:50px 0 42px}}header .eyebrow{{color:#b9dad1}}h1{{font-family:Georgia,serif;font-weight:400;font-size:clamp(38px,5vw,70px);line-height:1.04;margin:14px 0 18px;max-width:940px}}header p{{font-size:18px;max-width:900px;color:#d5e6e2;margin:0}}.eyebrow{{font-size:11px;font-weight:750;letter-spacing:.18em;text-transform:uppercase;color:var(--teal)}}.hero-metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:36px 0 0}}.hero-metrics div{{border:1px solid #5c7e79;border-radius:10px;padding:14px}}.hero-metrics strong{{display:block;font-size:26px;font-weight:600}}.hero-metrics span{{font-size:12px;color:#c9ddd8}}nav{{position:sticky;top:0;z-index:5;background:#fffefaee;backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}.nav-inner{{display:flex;gap:20px;align-items:center;overflow:auto;white-space:nowrap}}nav a{{padding:16px 0;color:var(--ink);font-weight:650;text-decoration:none;font-size:13px}}nav a:hover{{color:var(--teal)}}main{{padding:42px 0 90px}}section{{scroll-margin-top:85px;margin-bottom:70px}}h2{{font-family:Georgia,serif;font-weight:400;font-size:clamp(28px,3.2vw,42px);margin:0 0 8px}}.section-intro{{color:var(--muted);max-width:900px;margin:0 0 22px}}.toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:24px 0}}input[type=search]{{width:min(520px,100%);padding:13px 16px;border:1px solid #b5c8bf;border-radius:9px;font:inherit;background:#fff}}.search-count{{font-size:13px;color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.card,.packet,.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}}.card{{scroll-margin-top:88px}}.card summary{{list-style:none;cursor:pointer;padding:18px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px}}.card summary::-webkit-details-marker{{display:none}}.card summary::before{{content:'+';font-size:20px;color:var(--teal);order:3}}.card[open] summary::before{{content:'−'}}.card summary span{{min-width:0}}code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.92em;overflow-wrap:anywhere}}summary code{{font-weight:700;color:var(--teal);font-size:15px}}summary small{{display:block;color:var(--muted);font-size:12px;margin-top:3px}}summary strong{{font-size:12px;color:var(--gold);white-space:nowrap}}.detail-body{{border-top:1px solid var(--line);padding:8px 20px 20px;overflow:auto}}p{{margin:12px 0}}.chip{{display:inline-block;background:var(--teal-soft);color:var(--teal);border-radius:20px;text-decoration:none;padding:4px 9px;margin:2px;font-size:11px;font-weight:700}}.chip.secondary{{background:#f4ede1;color:#815a28}}table{{width:100%;border-collapse:collapse;font-size:12px;text-align:left}}th,td{{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-weight:750;background:#f7f8f4}}.table-wrap{{max-height:480px;overflow:auto;border:1px solid var(--line);border-radius:8px}}.expression{{white-space:normal;font-size:11px}}.source-link{{font-size:12px;color:var(--muted);margin-top:15px}}.status{{color:var(--red);background:#faede8;border-radius:20px;padding:5px 9px;font-size:11px;letter-spacing:.06em}}.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin:25px 0}}.flow>div{{background:#e7eee8;padding:17px;border-radius:10px;border-top:3px solid var(--teal);min-width:0}}.flow b{{display:block;font-size:22px}}.flow span{{display:block;color:var(--muted);font-size:12px}}.flow small{{display:block;margin-top:8px;color:var(--teal)}}.packet{{padding:22px;margin:16px 0;scroll-margin-top:88px;overflow-wrap:anywhere}}.packet-head{{display:flex;justify-content:space-between;gap:15px}}h3{{font-family:Georgia,serif;font-weight:400;font-size:25px;margin:3px 0 0}}h4{{margin:22px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.07em}}.notice{{background:#f6eee2;color:#745323;padding:9px 12px;border-radius:7px;font-size:12px}}.facts,.recs{{padding-left:23px}}.facts li,.recs li{{padding:9px 0;border-bottom:1px solid var(--line)}}.facts small,.recs small{{display:block;color:var(--muted);font-size:11px}}.fact-id{{color:var(--teal);font-family:ui-monospace,monospace;font-size:11px}}.rec-meta{{font-size:12px;color:var(--muted);margin:5px 0}}.panel{{padding:20px 24px}}.panel ul{{columns:2}}.muted{{color:var(--muted)}}.hidden{{display:none!important}}footer{{background:#133c39;color:#c5ded7;padding:30px 0;font-size:12px}}footer a{{color:#dcefe9}}@media(max-width:900px){{.hero-metrics{{grid-template-columns:repeat(3,1fr)}}.grid{{grid-template-columns:1fr}}.flow{{grid-template-columns:repeat(2,1fr)}}.panel ul{{columns:1}}}}@media(max-width:600px){{.shell{{padding:0 18px}}header{{padding:35px 0}}.hero-metrics{{grid-template-columns:repeat(2,1fr)}}.flow{{grid-template-columns:1fr}}}}
    </style></head><body><header><div class="shell"><div class="eyebrow">ATLAS DEL SISTEMA · V0.2 · {esc(workspace["metadata"]["as_of"])}</div><h1>Decisiones con trazabilidad, desde el dato hasta la revisión.</h1><p>Una vista navegable de la arquitectura analítica completa de Alma de Lujo. Datos comerciales simulados, cálculos SQL reproducibles y análisis de agentes nativos sujetos a revisión humana.</p><div class="hero-metrics"><div><strong>{sections["sources"]}</strong><span>fuentes tipadas</span></div><div><strong>{sections["source_rows"]:,}</strong><span>filas sintéticas</span></div><div><strong>{sections["marts"]}</strong><span>marts SQL</span></div><div><strong>{sections["processes"]}</strong><span>procesos</span></div><div><strong>{sections["agents"]}</strong><span>roles de agente</span></div><div><strong>{sections["decision_packets"]}</strong><span>paquetes revisados</span></div></div></div></header><nav><div class="shell nav-inner"><a href="#inicio">Mapa</a><a href="#decisiones">Decisiones</a><a href="#brechas">Brechas v0.3</a><a href="#fuentes">Fuentes</a><a href="#metricas">Métricas</a><a href="#procesos">Procesos</a><a href="#agentes">Agentes</a><a href="#controles">Controles</a></div></nav><main class="shell"><section id="inicio"><span class="eyebrow">01 · ORIENTACIÓN</span><h2>El sistema, de extremo a extremo</h2><p class="section-intro">Cada vínculo de fuente a mart se obtuvo del <code>FROM/JOIN</code> en SQL; los vínculos a procesos salen de referencias de evidencia de los paquetes. Abre cada tarjeta para inspeccionar sus contratos y archivos.</p><div class="flow"><div><b>{sections['sources']}</b><span>Fuentes relacionales</span><small>Snapshot sintético · PK/FK/coverage</small></div><div><b>{sections['marts']}</b><span>Marts y métricas</span><small>SQL determinista · NULL/UNKNOWN</small></div><div><b>{sections['processes']}</b><span>Procesos</span><small>Estados · transiciones · controles</small></div><div><b>{sections['agents']}</b><span>Agentes nativos</span><small>6 analistas · revisor independiente</small></div><div><b>{sections['decision_packets']}</b><span>Decision packets</span><small>REVIEW · aprobación humana</small></div></div><div class="panel"><b>Cómo leer los estados</b><p><b>Sintético</b> identifica datos simulados. <b>Determinista</b> identifica cálculos SQL y validadores. <b>Agéntico</b> identifica interpretación registrada de Codex. <b>UNKNOWN/NULL</b> indica cobertura o dato insuficiente; no equivale a cero. <b>REVIEW</b> solicita juicio del responsable; las recomendaciones no ejecutan compras, pagos ni cambios externos.</p><p class="muted">Grano y unidad se muestran en cada mart. Las cifras de reconciliación <code>purchase_receipts</code> son unidades físicas aunque las columnas genéricas se llamen <code>source_cents</code> y <code>mart_cents</code>.</p></div></section><section id="decisiones"><span class="eyebrow">02 · COCKPIT</span><h2>Paquetes listos para revisar</h2><p class="section-intro">Hechos y valores exactos del snapshot v0.2, con su puntero de evidencia. Las recomendaciones conservan métrica principal, guardia, población, ventana y regla de cierre. Todo permanece sujeto al responsable.</p>{''.join(packet_cards)}</section><section id="brechas"><span class="eyebrow">03 · ADENDA CANDIDATA</span><h2>Matriz de brechas: costos y operación</h2><p class="section-intro">La adenda v0.3 es una propuesta de ampliación, no evidencia de implementación ni autorización para operar con datos reales. El repositorio actual entrega un sistema analítico local con CLI y archivos; esta vista conserva su arquitectura. La extensión sintética local, cuando se entrega, aparece separada de las 30 fuentes base.</p><div class="table-wrap"><table><thead><tr><th>Necesidad</th><th>Confirmado actual en v0.2</th><th>Estado</th><th>Pendiente de la adenda</th></tr></thead><tbody>{gap_html}</tbody></table></div><h3>Extensión local de costos y operaciones</h3>{extension_html}</section><section id="fuentes"><span class="eyebrow">04 · DICCIONARIO</span><h2>{sections['sources']} fuentes y sus relaciones</h2><p class="section-intro">Cada conteo se coteja con el CSV distribuido. Los campos, claves y tipos vienen del esquema registrado en el linaje; la cobertura declarada viene del manifest del workspace.</p><div class="grid">{''.join(source_cards)}</div></section><section id="metricas"><span class="eyebrow">05 · MODELO SEMÁNTICO</span><h2>{sections['marts']} marts, campos y SQL</h2><p class="section-intro">La definición por campo reproduce la expresión de salida del SELECT final cuando se puede aislar; las CTE, filtros y joins completos se consultan en el SQL enlazado. El texto de negocio proviene del catálogo contractual de métricas.</p><div class="grid">{''.join(mart_cards)}</div></section><section id="procesos"><span class="eyebrow">06 · OPERACIÓN ANALÍTICA</span><h2>Estados y controles de {sections['processes']} procesos</h2><p class="section-intro">El catálogo define la finalidad y excepciones; las transiciones salen de los contratos JSON ejecutables. El estado mostrado es el estado analítico del ciclo de evidencia, independiente del estado operativo de cada instancia.</p><div class="grid">{''.join(process_cards)}</div></section><section id="agentes"><span class="eyebrow">07 · INTERPRETACIÓN NATIVA</span><h2>{sections['agents']} roles con límites claros</h2><p class="section-intro">Los contratos determinan entrada, salida, herramientas y autoridad. Los modelos y procesos ejecutados salen de recibos de respuesta aceptados; el revisor es un rol distinto del analista.</p><div class="grid">{''.join(agent_cards)}</div></section><section id="controles"><span class="eyebrow">08 · EVIDENCIA</span><h2>Calidad y procedencia</h2><div class="panel"><p><b>Controles registrados:</b> {len(quality)} · {quality_summary}. <b>Cobertura declarada:</b> {sum(bool(x) for x in coverage.values())}/{len(coverage)} fuentes.</p><p><b>Fuente de verdad:</b> {a(WORK / 'workspace.json', 'Manifest del workspace')} · {a(WORK / 'lineage.json', 'Linaje y hashes SQL')} · {a(WORK / 'quality.json', 'Calidad')} · {a(ROOT / 'client/system-manifest.json', 'Manifest de esta vista')}</p><p><b>Recibos cognitivos:</b> {len(task_runs['runs'])} ejecuciones registradas; identidad de modelos documentada en {a(model_provenance_path, 'model-provenance.json')}.</p><p class="muted">Esta vista se puede abrir sin servidor. No consulta APIs ni almacena datos del cliente. El manifest registra SHA-256 de cada contrato y archivo de evidencia consumido.</p></div></section></main><footer><div class="shell">Alma de Lujo · Sistema analítico local · Evidencia sintética v0.2 · {a(ROOT / 'README.md', 'README')} · {a(ROOT / 'specs/AGENT-SYSTEM.md', 'Contrato de agentes')}</div></footer><script>const search=document.createElement('div');search.className='toolbar';search.innerHTML='<input type="search" id="atlas-search" aria-label="Buscar en fuentes, métricas, procesos, agentes y decisiones" placeholder="Buscar fuente, campo, proceso o decisión…"><span class="search-count" id="search-count"></span>';document.querySelector('main').insertBefore(search,document.querySelector('#inicio'));const items=[...document.querySelectorAll('.searchable')];const input=document.querySelector('#atlas-search');function filter(){{const q=input.value.toLocaleLowerCase('es').trim();let visible=0;for(const el of items){{const text=(el.dataset.search+' '+el.textContent).toLocaleLowerCase('es');const hit=!q||text.includes(q);el.classList.toggle('hidden',!hit);if(hit)visible++}}document.querySelector('#search-count').textContent=q?visible+' resultados visibles':''}}input.addEventListener('input',filter);if(location.hash){{const target=document.querySelector(location.hash);if(target?.tagName==='DETAILS')target.open=true}}window.addEventListener('hashchange',()=>{{const target=document.querySelector(location.hash);if(target?.tagName==='DETAILS')target.open=true}});</script></body></html>'''
    # Ensure reported counts and IDs in the display derive from the manifest.
    for value in ["30", "11", "6", "7"]:
        assert value in body
    manifest["assets"] = [{"path": "client/SISTEMA_ANALITICO.html", "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}]
    return body, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed artifacts are current")
    args = parser.parse_args()
    body, manifest = build()
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    html_path = OUT / "SISTEMA_ANALITICO.html"
    manifest_path = OUT / "system-manifest.json"
    if args.check:
        assert html_path.read_text(encoding="utf-8") == body, "HTML is stale"
        assert manifest_path.read_text(encoding="utf-8") == manifest_text, "manifest is stale"
        print("PASS: HTML and manifest match all source evidence")
    else:
        OUT.mkdir(exist_ok=True)
        html_path.write_text(body, encoding="utf-8", newline="\n")
        manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")
        print(f"Wrote {rel(html_path)} and {rel(manifest_path)}")
    print(json.dumps(manifest["sections"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
