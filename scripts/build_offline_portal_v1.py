"""Build the provenance-safe v1 static offline portal.

The portal is a read-only projection.  Private views are accepted only from a
Phase 3 cycle that replays successfully against its Phase 1 cut, Phase 2 mart
bundle and native-task journal.  Public views use only the checked-in v0.2
synthetic evidence and never receive a private path.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alma.decision_register import verify_register
from alma.operating_contracts import SOURCE_NAMES, canonical_json, source_contract
from alma.weekly_cycle import verify_cycle


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_WORKSPACE = ROOT / "evidence" / "v0.2" / "workspace"
WORKBOOK_RECEIPT = ROOT / "evidence" / "v1.0" / "workbooks" / "workbook-pack-parity.json"
HASH_LEN = 64
PORTAL_SECTIONS = (
    ("inicio", "Inicio / corte seleccionado"),
    ("recorrido", "Recorrido semanal"),
    ("decisiones", "Decisiones"),
    ("excepciones", "Excepciones y calidad"),
    ("fuentes", "Fuentes"),
    ("metricas", "Métricas"),
    ("procesos", "Procesos y roles"),
    ("linaje", "Linaje y exportación"),
)
EXPORT_COLUMNS = ("metric_id", "value", "unit", "status", "source_hash", "cut_id",
                  "as_of", "reconciliation_id")


class PortalContractError(ValueError):
    """A portal input cannot be represented without weakening provenance."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
            raise PortalContractError("missing, linked or oversized portal evidence")
        return json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise PortalContractError("portal evidence could not be verified") from exc


def _portable_name(path: Path) -> str:
    """Return a non-sensitive evidence name, never an absolute path."""
    return path.name


def _historical_model() -> dict[str, Any]:
    workspace_path = PUBLIC_WORKSPACE / "workspace.json"
    quality_path = PUBLIC_WORKSPACE / "quality.json"
    if not workspace_path.is_file() or not quality_path.is_file():
        raise PortalContractError("historical synthetic evidence is missing")
    workspace = _json(workspace_path)
    quality = _json(quality_path)
    counts = workspace.get("counts", {}) if isinstance(workspace, dict) else {}
    coverage = workspace.get("metadata", {}).get("coverage", {}) if isinstance(workspace, dict) else {}
    sources = [
        {"source_id": name, "row_count": counts[name], "coverage": coverage.get(name),
         "status": (coverage.get(name, {}).get("status", "UNKNOWN")
                    if isinstance(coverage.get(name), dict)
                    else ("MEASURED" if coverage.get(name) is True else "UNKNOWN")),
         "source_hash": None, "synthetic": True}
        for name in sorted(counts)
    ]
    return {
        "version": "offline-portal-v1",
        "mode": "public",
        "provenance": {
            "label": "EJEMPLO SINTÉTICO · HISTÓRICO v0.2",
            "role": "historical_synthetic",
            "synthetic": True,
            "status": "PASS",
            "warning": "Ejemplo informativo. No representa un corte actual ni una aprobación.",
        },
        "cut": None,
        "sources": sources,
        "metrics": [],
        "metric_definitions": {},
        "exceptions": quality.get("exceptions", []) if isinstance(quality, dict) else [],
        "lineage": {},
        "native": {"status": "HISTÓRICO", "roles": []},
        "packet": None,
        "decisions": [],
        "decision_register": None,
        "stages": [
            {"name": name, "status": "HISTÓRICO", "evidence": _portable_name(workspace_path)}
            for name in ("Fuentes", "Validación", "Marts y métricas", "Análisis",
                         "Revisión independiente", "Decisión del responsable", "Próximo corte")
        ],
        "evidence": {
            "workspace": {"name": _portable_name(workspace_path), "sha256": _sha(workspace_path)},
            "quality": {"name": _portable_name(quality_path), "sha256": _sha(quality_path)},
        },
    }


def _unselected_model() -> dict[str, Any]:
    return {
        "version": "offline-portal-v1",
        "mode": "unselected",
        "provenance": {
            "label": "SIN CORTE PRIVADO SELECCIONADO",
            "role": "unselected",
            "synthetic": None,
            "status": "REVIEW",
            "warning": "Selecciona un corte verificado para consultar evidencia actual.",
        },
        "cut": None, "sources": [], "metrics": [], "metric_definitions": {},
        "exceptions": [], "lineage": {},
        "native": {"status": "NO_INICIADO", "roles": []},
        "packet": None, "decisions": [], "decision_register": None,
        "stages": [], "evidence": {},
    }


def _private_cycle_path(value: str | Path) -> Path:
    raw = Path(value)
    if ".." in raw.parts:
        raise PortalContractError("private cycle path escape blocked")
    try:
        path = raw.resolve(strict=True)
    except OSError as exc:
        raise PortalContractError("selected cycle is missing") from exc
    if ".local" not in path.parts:
        raise PortalContractError("selected cycle must remain under an ignored .local root")
    return path


def _native_projection(cycle: Path, state: dict[str, Any]) -> dict[str, Any]:
    accepted = state.get("accepted_roles", {})
    roles = []
    for role in sorted(state.get("expected_roles", {})):
        entry = accepted.get(role)
        request = _json(cycle / "tasks" / f"{role}.request.json")
        roles.append({
            "role": role,
            "status": "RESPUESTA_VERIFICADA" if entry else "ESPERANDO_RESPUESTA",
            "request_id": request["request_id"],
            "request_sha256": state["expected_roles"][role]["request_sha256"],
            "response_sha256": entry.get("response_sha256") if entry else None,
            "dispatch_sha256": entry.get("dispatch_sha256") if entry else None,
            "agent_id": entry.get("agent_id") if entry else None,
            "model": entry.get("model") if entry else None,
        })
    reviewer = state.get("reviewer")
    if state.get("reviewer_request_sha256") is not None or reviewer is not None:
        roles.append({
            "role": "evidence_reviewer",
            "status": "RESPUESTA_VERIFICADA" if reviewer else "ESPERANDO_RESPUESTA",
            "request_id": reviewer.get("request_id") if reviewer else None,
            "request_sha256": state.get("reviewer_request_sha256"),
            "response_sha256": reviewer.get("response_sha256") if reviewer else None,
            "dispatch_sha256": reviewer.get("dispatch_sha256") if reviewer else None,
            "agent_id": reviewer.get("agent_id") if reviewer else None,
            "model": reviewer.get("model") if reviewer else None,
        })
    if any(row["status"] == "ESPERANDO_RESPUESTA" for row in roles):
        status = "ESPERANDO_RESPUESTA"
    elif reviewer is not None:
        status = state["status"]
    else:
        status = "ESPERANDO_RESPUESTA"
    return {"status": status, "cycle_status": state["status"], "roles": roles}


def _decision_projection(register: str | Path | None, report: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if register is None:
        return list(report.get("carried_decisions", [])), report.get("decision_register")
    try:
        verified = verify_register(register)
    except (ValueError, OSError, KeyError) as exc:
        raise PortalContractError("decision register verification blocked") from exc
    events = verified["events"]
    decisions = []
    for row in verified["decisions"]:
        latest = next(event for event in reversed(events) if event["decision_id"] == row["decision_id"])
        decisions.append({**row, "closure_evidence": latest.get("closure_evidence"),
                          "terminal_hash": row["terminal_hash"]})
    binding = report.get("decision_register") or {}
    return decisions, {
        "register_id": verified["register_id"],
        "original_anchor": binding.get("prior_anchor"),
        "cut_anchor": binding.get("anchor"),
        "current_anchor": verified["anchor"],
    }


def _current_model(cycle: Path, decision_register: str | Path | None) -> dict[str, Any]:
    try:
        verified = verify_cycle(cycle)
        report_path, state_path = cycle / "current-cut.json", cycle / "state.json"
        report, state = _json(report_path), _json(state_path)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise PortalContractError("selected cut verification blocked by hash or contract mismatch") from exc
    if verified.get("cut_id") != report.get("cut_id") or verified.get("status") != state.get("status"):
        raise PortalContractError("selected cut verification blocked by identity mismatch")
    synthetic = report.get("synthetic_business_data") is True
    label = f"CORTE PRIVADO ACTUAL · {report['cutoff_at']} · {report['cut_id']}"
    if synthetic:
        label += " · SINTÉTICO"
    sources = []
    for filename, digest in sorted(report["source_sha256"].items()):
        source_id = filename.removesuffix(".csv")
        sources.append({
            "source_id": source_id,
            "source_hash": digest,
            "coverage": report["coverage"].get(source_id, {}),
            "status": report["coverage"].get(source_id, {}).get("status", "UNKNOWN"),
            "synthetic": synthetic,
            "contract": source_contract(source_id) if source_id in SOURCE_NAMES else {},
        })
    packet_path = cycle / "decision-packet.json"
    packet = _json(packet_path) if packet_path.exists() else None
    decisions, register_projection = _decision_projection(decision_register, report)
    stages = [
        {"name": "Fuentes", "status": report["quality"]["workspace"], "evidence": "workspace.json"},
        {"name": "Validación", "status": report["quality"]["workspace"], "evidence": "current-cut.json"},
        {"name": "Marts y métricas", "status": "PASS", "evidence": "mart manifest"},
        {"name": "Análisis", "status": "PASS" if state.get("accepted_roles") else "ESPERANDO_RESPUESTA", "evidence": "tasks"},
        {"name": "Revisión independiente", "status": state["status"] if state.get("reviewer") else "ESPERANDO_RESPUESTA", "evidence": "evidence_reviewer"},
        {"name": "Decisión del responsable", "status": "ADVISORY" if packet else "PENDIENTE", "evidence": "decision-packet.json" if packet else None},
        {"name": "Próximo corte", "status": "PENDIENTE", "evidence": None},
    ]
    metrics = []
    for original in report["metric_rows"]:
        row = dict(original)
        definition = report["metric_definitions"][row["metric_id"]]
        source_hashes = {
            name: report["source_sha256"][f"{name}.csv"]
            for name in row.get("source_refs", [])
            if f"{name}.csv" in report["source_sha256"]
        }
        row["unit"] = definition["unit"]
        row["source_hashes"] = source_hashes
        row["source_hash"] = hashlib.sha256(canonical_json(source_hashes)).hexdigest()
        metrics.append(row)
    return {
        "version": "offline-portal-v1", "mode": "private_current",
        "provenance": {"label": label, "role": "current", "synthetic": synthetic,
                       "status": state["status"],
                       "warning": "Evidencia local verificada; las recomendaciones siguen siendo asesoría."},
        "cut": {"cut_id": report["cut_id"], "cutoff": report["cutoff_at"],
                "timezone": report["timezone"], "input_class": report["input_class"],
                "manifest_sha256": report["manifest_sha256"],
                "report_sha256": report["mart_bundle_sha256"],
                "current_cut_sha256": verified["current_cut_sha256"],
                "quality": report["quality"]},
        "sources": sources, "metrics": metrics,
        "metric_definitions": report["metric_definitions"],
        "exceptions": report.get("exceptions", []), "lineage": report.get("lineage", {}),
        "native": _native_projection(cycle, state), "packet": packet,
        "decisions": decisions, "decision_register": register_projection, "stages": stages,
        "evidence": {
            "current_cut": {"name": report_path.name, "sha256": _sha(report_path)},
            "state": {"name": state_path.name, "sha256": _sha(state_path)},
            "packet": ({"name": packet_path.name, "sha256": _sha(packet_path)}
                       if packet_path.exists() else None),
        },
    }


def collect_portal_model(*, mode: str, selected_cycle: str | Path | None = None,
                         decision_register: str | Path | None = None) -> dict[str, Any]:
    """Collect one verified portal model without writing or copying evidence."""
    if mode not in {"public", "private"}:
        raise PortalContractError("portal mode must be public or private")
    if mode == "public":
        if selected_cycle is not None or decision_register is not None:
            raise PortalContractError("public portal refuses selected cut or decision register")
        return _historical_model()
    if selected_cycle is None:
        if decision_register is not None:
            raise PortalContractError("decision register requires a selected cut")
        return _unselected_model()
    cycle = _private_cycle_path(selected_cycle)
    if decision_register is not None:
        _private_cycle_path(decision_register)
    return _current_model(cycle, decision_register)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _value(value: Any, status: str | None = None) -> str:
    if value is None:
        return "DESCONOCIDO" if status in {"UNKNOWN", "PARTIAL", "REVIEW", "BLOCKED"} else "Sin datos"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _short(value: Any) -> str:
    text = str(value or "")
    return text[:12] + ("…" if len(text) > 12 else "")


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _verify_workbook_receipt(path: str | Path) -> tuple[dict[str, Any], str]:
    receipt_path = Path(path)
    receipt = _json(receipt_path)
    relations = receipt.get("relations", {}) if isinstance(receipt, dict) else {}
    if (receipt.get("status") != "PASS" or receipt.get("contract_version") != "operating-v1" or
            receipt.get("relation_count") != 22 or len(relations) != 22 or
            any(row.get("disposition") != "PASS" for row in relations.values()) or
            receipt.get("contains_absolute_paths") is not False or receipt.get("contains_cell_values") is not False):
        raise PortalContractError("workbook parity receipt is missing or blocked")
    return receipt, _sha(receipt_path)


def _metric_export(model: dict[str, Any]) -> dict[str, Any]:
    cut = model.get("cut") or {}
    rows = []
    for original in model.get("metrics", []):
        row = dict(original)
        if not isinstance(row.get("source_hash"), str) or len(row["source_hash"]) != HASH_LEN:
            raise PortalContractError("metric source hash is missing")
        rows.append({key: row.get(key) for key in EXPORT_COLUMNS})
    return {
        "version": "offline-portal-metrics-v1",
        "provenance_label": model["provenance"]["label"],
        "cut_id": cut.get("cut_id"), "cutoff": cut.get("cutoff"),
        "timezone": cut.get("timezone"), "synthetic": model["provenance"].get("synthetic"),
        "warning": model["provenance"].get("warning"), "rows": rows,
    }


def _metric_csv(export: dict[str, Any]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in export["rows"]:
        writer.writerow({key: "" if row[key] is None else row[key] for key in EXPORT_COLUMNS})
    return buffer.getvalue().encode("utf-8")


def verify_metric_exports(model: dict[str, Any], portal_dir: str | Path) -> dict[str, Any]:
    """Independently parse JSON/CSV exports and compare exact boundary values."""
    folder = Path(portal_dir)
    exported = _json(folder / "metricas.json")
    with (folder / "metricas.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    expected = _metric_export(model)["rows"]
    json_rows = exported.get("rows") if isinstance(exported, dict) else None
    if not isinstance(json_rows, list) or len(expected) != len(json_rows) or len(expected) != len(csv_rows):
        raise PortalContractError("metric export row count differs")
    for wanted, json_row, csv_row in zip(expected, json_rows, csv_rows, strict=True):
        if json_row != wanted:
            raise PortalContractError("JSON metric export differs from verified model")
        for key in EXPORT_COLUMNS:
            actual = csv_row.get(key)
            target = "" if wanted[key] is None else str(wanted[key])
            if actual != target:
                raise PortalContractError(f"CSV metric export differs at {wanted['metric_id']}/{key}")
    return {"status": "PASS", "rows": len(expected),
            "json_sha256": _sha(folder / "metricas.json"),
            "csv_sha256": _sha(folder / "metricas.csv")}


def _packet_groups(packet: dict[str, Any] | None) -> str:
    if packet is None:
        return '<p class="empty-state"><strong>Paquete pendiente.</strong> La solicitud no equivale a una respuesta nativa. Estado: ESPERANDO_RESPUESTA.</p>'
    groups = (("Hechos", "facts"), ("Desconocidos", "unknowns"),
              ("Hipótesis", "hypotheses"), ("Recomendaciones", "recommendations"))
    rendered = []
    for title, key in groups:
        items = packet.get(key, [])
        body = "".join(f"<li><pre>{_esc(_json_text(item))}</pre></li>" for item in items)
        rendered.append(f'<article class="packet-group"><h3>{title}</h3><ul>{body or "<li>Sin elementos verificados</li>"}</ul></article>')
    return '<div class="evidence-grid">' + "".join(rendered) + "</div>"


def _render_html(model: dict[str, Any], workbook_hash: str) -> str:
    provenance = model["provenance"]
    cut = model.get("cut") or {}
    label = provenance["label"]
    nav = "".join(f'<a href="#{section_id}">{_esc(title)}</a>' for section_id, title in PORTAL_SECTIONS)
    fact_rows = [
        ("Rol", provenance.get("role")), ("Estado", provenance.get("status")),
        ("Corte", cut.get("cut_id")), ("Fecha de corte", cut.get("cutoff")),
        ("Zona horaria", cut.get("timezone")), ("Calidad", (cut.get("quality") or {}).get("workspace")),
    ]
    facts = "".join(f'<div><dt>{_esc(name)}</dt><dd>{_esc(_value(value))}</dd></div>' for name, value in fact_rows)
    hash_rows = "".join(
        f'<tr><th scope="row">{_esc(name)}</th><td><code title="{_esc(value)}">{_esc(value)}</code></td></tr>'
        for name, value in (("Manifest", cut.get("manifest_sha256")),
                            ("Reporte/mart", cut.get("report_sha256")),
                            ("Vista", cut.get("current_cut_sha256")),
                            ("Workbook oracle", workbook_hash))
        if value
    )
    stages = "".join(
        f'<tr><th scope="row">{index}. {_esc(row["name"])}</th><td><span class="status status-{_esc(str(row["status"]).lower())}">{_esc(row["status"])}</span></td><td>{_esc(_value(row.get("evidence")))}</td></tr>'
        for index, row in enumerate(model.get("stages", []), 1)
    )
    decisions = "".join(
        f'<tr><th scope="row"><code>{_esc(row["decision_id"])}</code></th><td>{_esc(row["status"])}</td><td>{_esc(row["due_date"])}</td><td><code>{_esc(_short(row["source_hash"]))}</code></td><td><code>{_esc(_short(row["packet_hash"]))}</code></td><td>{_esc(_value(row.get("closure_evidence"), row["status"]))}</td></tr>'
        for row in model.get("decisions", [])
    )
    priority = {"BLOCKED": 0, "ERROR": 0, "REVIEW": 1, "UNKNOWN": 2, "PARTIAL": 2}
    exceptions = sorted(model.get("exceptions", []), key=lambda row: priority.get(str(row.get("status", row.get("severity", "PASS"))), 3))
    exception_rows = "".join(
        f'<tr><th scope="row">{_esc(row.get("metric_id", row.get("source_id", "General")))}</th><td>{_esc(row.get("status", row.get("severity", "REVIEW")))}</td><td>{_esc(row.get("reason", row.get("message", "Evidencia incompleta")))}</td><td>{_esc(row.get("next_action", "Revisar evidencia local"))}</td></tr>'
        for row in exceptions
    )
    source_cards = []
    for source in model.get("sources", []):
        contract = source.get("contract") or {}
        fields = contract.get("fields", [])
        field_rows = "".join(
            f'<tr><th scope="row"><code>{_esc(field.get("name"))}</code></th><td>{_esc(field.get("unit"))}</td><td>{"Sí" if field.get("nullable") else "No"}</td></tr>'
            for field in fields
        )
        search = " ".join((source.get("source_id", ""), _json_text(contract), source.get("status", "")))
        source_cards.append(
            f'<details class="source-card" data-search="{_esc(search)}" id="fuente-{_esc(source["source_id"])}"><summary><span><code>{_esc(source["source_id"])}</code><small>{_esc(source.get("status"))}</small></span><span class="hash">{_esc(_short(source.get("source_hash")))}</span></summary><div class="detail"><p><b>Grano:</b> {_esc(contract.get("grain", "Histórico v0.2"))} · <b>Clave:</b> {_esc(", ".join(contract.get("primary_key", [])) or "Ver contrato histórico")}</p><p><b>Cobertura:</b> {_esc(_value(source.get("coverage"), source.get("status")))} · <b>Sintético:</b> {_esc(source.get("synthetic"))}</p><div class="table-wrap"><table><caption>Campos declarados</caption><thead><tr><th scope="col">Campo</th><th scope="col">Unidad</th><th scope="col">Nullable</th></tr></thead><tbody>{field_rows or "<tr><td colspan=\"3\">Consultar el contrato histórico hash-bound.</td></tr>"}</tbody></table></div></div></details>'
        )
    metric_rows = []
    for row in model.get("metrics", []):
        definition = model.get("metric_definitions", {}).get(row["metric_id"], {})
        metric_rows.append(
            f'<tr><th scope="row"><code>{_esc(row["metric_id"])}</code></th><td class="metric-value">{_esc(_value(row.get("value"), row.get("status")))}</td><td>{_esc(row.get("unit", definition.get("unit")))}</td><td><span class="status status-{_esc(str(row.get("status", "unknown")).lower())}">{_esc(row.get("status"))}</span></td><td>{_esc(definition.get("formula", "Ver catálogo"))}</td><td>{_esc(definition.get("window", row.get("as_of")))}</td><td>{_esc(definition.get("unknown", "Ausencia permanece desconocida"))}</td><td>{_esc(definition.get("guardrail", "Sin ejecución externa"))}</td><td>{_esc(definition.get("owner", "analytics_owner"))}</td><td><code>{_esc(_short(row.get("source_hash")))}</code></td></tr>'
        )
    roles = "".join(
        f'<article class="role-card"><p class="eyebrow">{_esc(row["status"])}</p><h3>{_esc(row["role"])}</h3><p>Solicitud <code>{_esc(_short(row.get("request_id")))}</code></p><p>Agente: {_esc(_value(row.get("agent_id")))} · Modelo: {_esc(_value(row.get("model")))}</p><p><b>Autoridad externa:</b> PROHIBITED</p></article>'
        for row in model.get("native", {}).get("roles", [])
    )
    evidence_rows = "".join(
        f'<tr><th scope="row">{_esc(name)}</th><td>{_esc(_value(item.get("name") if item else None))}</td><td><code>{_esc(_value(item.get("sha256") if item else None))}</code></td></tr>'
        for name, item in model.get("evidence", {}).items()
    )
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Alma OS · Portal offline v1</title><link rel="stylesheet" href="portal-v1.css"></head>
<body><a class="skip-link" href="#contenido">Saltar al contenido</a>
<header><div class="shell"><p class="eyebrow">ALMA OS · PORTAL OFFLINE v1</p><h1>Evidencia semanal para decidir con trazabilidad</h1><p class="provenance-label">{_esc(label)}</p><p class="warning" role="status">{_esc(provenance.get("warning"))}</p><p class="print-provenance">{_esc(label)} · Corte {_esc(_value(cut.get("cut_id")))} · Estado {_esc(provenance.get("status"))}</p></div></header>
<nav aria-label="Secciones del portal"><div class="shell nav-inner">{nav}</div></nav>
<main id="contenido" class="shell">
<section id="inicio" aria-labelledby="titulo-inicio"><p class="eyebrow">01 · CONTEXTO</p><h2 id="titulo-inicio">Inicio / corte seleccionado</h2><p>Esta página es local: no sube, sincroniza ni ejecuta datos o decisiones.</p><dl class="fact-grid">{facts}</dl><div class="table-wrap"><table><caption>Proveniencia verificada</caption><tbody>{hash_rows or '<tr><td>Sin hashes de un corte seleccionado.</td></tr>'}</tbody></table></div><div class="actions"><a href="metricas.csv" download>Descargar CSV</a><a href="metricas.json" download>Descargar JSON</a><a href="portal-model.json" download>Descargar modelo JSON</a><button type="button" onclick="window.print()">Imprimir / Guardar PDF</button></div></section>
<section id="recorrido" aria-labelledby="titulo-recorrido"><p class="eyebrow">02 · FLUJO</p><h2 id="titulo-recorrido">Recorrido semanal</h2><div class="table-wrap"><table><caption>Estados del corte; pendiente y espera siguen visibles</caption><thead><tr><th scope="col">Etapa</th><th scope="col">Estado</th><th scope="col">Evidencia</th></tr></thead><tbody>{stages or '<tr><td colspan="3">Sin corte actual seleccionado.</td></tr>'}</tbody></table></div></section>
<section id="decisiones" aria-labelledby="titulo-decisiones"><p class="eyebrow">03 · DECISIÓN HUMANA</p><h2 id="titulo-decisiones">Decisiones</h2><p>Los paquetes son asesoría. La revisión, el registro del responsable y el cierre son eventos distintos.</p>{_packet_groups(model.get("packet"))}<div class="table-wrap"><table><caption>Registro de decisiones del corte</caption><thead><tr><th scope="col">ID</th><th scope="col">Estado</th><th scope="col">Vence</th><th scope="col">Fuente</th><th scope="col">Paquete</th><th scope="col">Cierre</th></tr></thead><tbody>{decisions or '<tr><td colspan="6">Sin decisión del responsable registrada.</td></tr>'}</tbody></table></div></section>
<section id="excepciones" aria-labelledby="titulo-excepciones"><p class="eyebrow">04 · ANTES DE LOS PASS</p><h2 id="titulo-excepciones">Excepciones y calidad</h2><div class="table-wrap"><table><caption>Bloqueos, revisiones y desconocidos primero</caption><thead><tr><th scope="col">Fuente o métrica</th><th scope="col">Estado</th><th scope="col">Razón</th><th scope="col">Siguiente evidencia</th></tr></thead><tbody>{exception_rows or '<tr><td colspan="4">Sin excepciones declaradas en este contexto.</td></tr>'}</tbody></table></div></section>
<section id="fuentes" aria-labelledby="titulo-fuentes"><p class="eyebrow">05 · CONTRATO DE ENTRADA</p><h2 id="titulo-fuentes">Fuentes</h2><div class="search-tools"><label for="source-search">Buscar fuentes</label><input id="source-search" type="search" aria-label="Buscar fuentes" placeholder="Fuente, campo, proceso o decisión"><output id="source-count">Inventario completo: {len(source_cards)} fuentes</output></div><div id="source-empty" class="empty-state" hidden><h3>Sin coincidencias para “<span id="source-query"></span>”</h3><p>Borra el filtro o busca por fuente, campo, proceso o decisión. El inventario completo sigue disponible.</p></div><div class="source-grid">{''.join(source_cards) or '<p>Sin fuentes en este contexto.</p>'}</div></section>
<section id="metricas" aria-labelledby="titulo-metricas"><p class="eyebrow">06 · DEFINICIONES</p><h2 id="titulo-metricas">Métricas</h2><p>Un cero observado permanece 0; la ausencia se muestra como DESCONOCIDO.</p><div class="table-wrap"><table><caption>{_esc(label)} · Diccionario y valores verificados</caption><thead><tr><th scope="col">Métrica</th><th scope="col">Valor</th><th scope="col">Unidad</th><th scope="col">Estado</th><th scope="col">Fórmula</th><th scope="col">Ventana</th><th scope="col">Regla unknown</th><th scope="col">Guardrail</th><th scope="col">Owner</th><th scope="col">Fuente hash</th></tr></thead><tbody>{''.join(metric_rows) or '<tr><td colspan="10">Sin valores de métrica para este contexto.</td></tr>'}</tbody></table></div></section>
<section id="procesos" aria-labelledby="titulo-procesos"><p class="eyebrow">07 · RESPONSABILIDAD</p><h2 id="titulo-procesos">Procesos y roles</h2><p>Estado nativo: <strong>{_esc(model.get("native", {}).get("status", "NO_INICIADO"))}</strong>. Una solicitud preparada no es una ejecución.</p><div class="evidence-grid">{roles or '<p>Sin ejecución nativa para este contexto.</p>'}</div></section>
<section id="linaje" aria-labelledby="titulo-linaje"><p class="eyebrow">08 · EXPORTACIÓN</p><h2 id="titulo-linaje">Linaje y exportación</h2><p>Fuente → mart/métrica → proceso/rol → paquete. Los hashes enlazan cada capa y no ejecutan acciones externas.</p><div class="table-wrap"><table><caption>Inventario portable de evidencia</caption><thead><tr><th scope="col">Capa</th><th scope="col">Archivo</th><th scope="col">SHA-256</th></tr></thead><tbody>{evidence_rows or '<tr><td colspan="3">Evidencia histórica embebida y verificada.</td></tr>'}</tbody></table></div><p><a href="workbook-pack-parity.json">Ver oracle workbook → pack → manifest</a> · <a href="metricas.csv" download>Descargar CSV</a> · <a href="metricas.json" download>Descargar JSON</a></p></section>
</main><footer><div class="shell"><p>{_esc(label)} · Portal local sin servidor · Ejecución externa PROHIBITED</p></div></footer>
<script>(function(){{const input=document.getElementById('source-search');const cards=[...document.querySelectorAll('.source-card')];const out=document.getElementById('source-count');const empty=document.getElementById('source-empty');const query=document.getElementById('source-query');if(!input)return;input.addEventListener('input',()=>{{const q=input.value.trim().toLocaleLowerCase('es');let visible=0;cards.forEach(card=>{{const hit=!q||card.dataset.search.toLocaleLowerCase('es').includes(q);card.hidden=!hit;if(hit)visible++;}});out.textContent=q?`${{visible}} de ${{cards.length}} fuentes visibles`:`Inventario completo: ${{cards.length}} fuentes`;query.textContent=input.value;empty.hidden=visible!==0;}});}})();</script>
</body></html>'''


def render_portal(model: dict[str, Any], output_dir: str | Path, *,
                  workbook_receipt: str | Path = WORKBOOK_RECEIPT) -> dict[str, Any]:
    """Atomically render one portable portal and exact CSV/JSON exports."""
    receipt, workbook_hash = _verify_workbook_receipt(workbook_receipt)
    destination = Path(output_dir)
    if ".." in destination.parts or destination.exists():
        raise PortalContractError("portal destination must be new and cannot escape")
    mode = model.get("mode")
    if mode == "public" and ".local" in destination.parts:
        raise PortalContractError("public portal cannot be written under a private root")
    if mode == "private_current" and ".local" not in destination.parts:
        raise PortalContractError("current portal must remain under an ignored .local root")
    parent = destination.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    css_source = ROOT / "client" / "portal-v1.css"
    if not css_source.is_file():
        raise PortalContractError("portal stylesheet is missing")
    stage = Path(tempfile.mkdtemp(prefix=".portal-stage-", dir=parent))
    published = False
    try:
        export = _metric_export(model)
        (stage / "metricas.json").write_bytes(canonical_json(export))
        (stage / "metricas.csv").write_bytes(_metric_csv(export))
        (stage / "portal-model.json").write_bytes(canonical_json(model))
        shutil.copyfile(css_source, stage / "portal-v1.css")
        shutil.copyfile(Path(workbook_receipt), stage / "workbook-pack-parity.json")
        html_text = _render_html(model, workbook_hash)
        if any(token in html_text.lower() for token in ('href="http:', 'href="https:', 'src="http:', 'src="https:')):
            raise PortalContractError("remote portal asset or link blocked")
        (stage / "index.html").write_text(html_text, encoding="utf-8", newline="\n")
        parity = verify_metric_exports(model, stage)
        names = sorted(path.name for path in stage.iterdir())
        hashes = {name: _sha(stage / name) for name in names}
        manifest = {"version": "offline-portal-build-v1", "mode": mode,
                    "status": "PASS", "workbook_receipt_sha256": workbook_hash,
                    "metric_parity": parity, "artifacts": names,
                    "artifact_sha256": hashes}
        (stage / "portal-manifest.json").write_bytes(canonical_json(manifest))
        os.replace(stage, destination)
        published = True
        return {**manifest, "destination": str(destination),
                "html_sha256": _sha(destination / "index.html")}
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage)


def build_offline_portal(*, mode: str, output_dir: str | Path,
                         selected_cycle: str | Path | None = None,
                         decision_register: str | Path | None = None,
                         workbook_receipt: str | Path = WORKBOOK_RECEIPT) -> dict[str, Any]:
    model = collect_portal_model(mode=mode, selected_cycle=selected_cycle,
                                 decision_register=decision_register)
    return {**render_portal(model, output_dir, workbook_receipt=workbook_receipt),
            "mode": mode}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Alma OS v1 offline portal")
    parser.add_argument("--mode", choices=("public", "private"), required=True)
    parser.add_argument("--selected-cycle")
    parser.add_argument("--decision-register")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    if args.output_dir:
        result = build_offline_portal(mode=args.mode, output_dir=args.output_dir,
                                      selected_cycle=args.selected_cycle,
                                      decision_register=args.decision_register)
    else:
        result = collect_portal_model(mode=args.mode, selected_cycle=args.selected_cycle,
                                      decision_register=args.decision_register)
    print(canonical_json(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
