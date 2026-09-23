"""Build the provenance-safe v1 static offline portal.

The portal is a read-only projection.  Private views are accepted only from a
Phase 3 cycle that replays successfully against its Phase 1 cut, Phase 2 mart
bundle and native-task journal.  Public views use only the checked-in v0.2
synthetic evidence and never receive a private path.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from alma.decision_register import verify_register
from alma.operating_contracts import SOURCE_NAMES, canonical_json, source_contract
from alma.weekly_cycle import verify_cycle


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_WORKSPACE = ROOT / "evidence" / "v0.2" / "workspace"
WORKBOOK_RECEIPT = ROOT / "evidence" / "v1.0" / "workbooks" / "workbook-pack-parity.json"
HASH_LEN = 64


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
        "sources": sources, "metrics": report["metric_rows"],
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Alma OS v1 offline portal")
    parser.add_argument("--mode", choices=("public", "private"), required=True)
    parser.add_argument("--selected-cycle")
    parser.add_argument("--decision-register")
    args = parser.parse_args(argv)
    model = collect_portal_model(mode=args.mode, selected_cycle=args.selected_cycle,
                                 decision_register=args.decision_register)
    print(canonical_json(model).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
