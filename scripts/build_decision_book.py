"""Compile accepted native outputs; this renderer performs no model inference."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from alma.process_engine import definitions, read, status

LABELS = {
    "procure-to-stock": "Compras e inventario",
    "lead-to-delivery": "Conversión, pedidos y entrega",
    "return-to-refund": "Devolución, crédito y reembolso",
    "finance-close": "Cierre financiero",
    "weekly-growth-review": "Prioridades de crecimiento",
    "market-to-experiment": "Mercado y experimentación",
}


def build(workspace: Path, output: Path) -> None:
    states = status(workspace)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Link relative to the evidence release directory, not a machine-specific path.
    prefix = Path(os.path.relpath(workspace, output.parent)).as_posix()
    release_prefix = Path(os.path.relpath(workspace.parent, output.parent)).as_posix()
    lines = [
        "# Alma de Lujo · Libro de decisiones v0.2", "",
        "Seis análisis ejecutados por agentes nativos de Codex y revisados por un agente diferente. "
        "Este documento compila las respuestas aceptadas; no genera análisis nuevos.", "",
        "**Caso comercial completamente sintético.** REVIEW significa que la propuesta necesita resolver "
        "las objeciones del revisor antes de considerarse una decisión del negocio. Ningún paquete autoriza "
        "compras, pagos, campañas o reembolsos.", "",
        f"[Tablas y dossier]({prefix}/DOSSIER.md) · [Ejecuciones y trazas]({release_prefix}/agents/task-runs.json) · "
        f"[Aceptación del alcance]({release_prefix}/acceptance.json) · [Comparación de escenarios]({release_prefix}/SCENARIO-COMPARISON.md)", "",
        "| Proceso | Estado analítico | Modelo analista | Modelo revisor | Evidencia |",
        "| --- | --- | --- | --- | --- |",
    ]
    packets = []
    for definition in definitions().values():
        pid = definition['id']
        folder = workspace / 'processes' / pid
        packet = read(folder / 'decision-packet.json')
        current = next(item for item in states if item['process_id'] == pid)
        if current['status'] not in {'REVIEW', 'READY_FOR_OWNER'}:
            raise ValueError('Process has not completed native review: ' + pid)
        analyst_role = definition['agent']
        analyst = read(folder / 'tasks' / (analyst_role + '.response.json'))
        analyst_dispatch = read(folder / 'tasks' / (analyst_role + '.dispatch.json'))
        reviewer_dispatch = read(folder / 'tasks' / 'evidence_reviewer.dispatch.json')
        link = f'{prefix}/processes/{pid}'
        lines.append(f"| {LABELS[pid]} | {packet['status']} | {analyst_dispatch['model']} | "
                     f"{reviewer_dispatch['model']} | [Paquete]({link}/decision-packet.json) |")
        packets.append((pid, packet, analyst, analyst_role, link))
    for pid, packet, analyst, role, link in packets:
        lines.extend(['', '## ' + LABELS[pid], '', analyst['summary'], '',
                      f"[Solicitud y evidencia]({link}/tasks/{role}.request.json) · "
                      f"[Traza de consultas]({link}/tasks/{role}.trace.json) · "
                      f"[Historial de estados]({link}/events.json)", '', '### Hechos e inferencias', ''])
        for fact in analyst['facts']:
            kind = 'Observación' if fact['kind'] == 'observation' else 'Inferencia'
            refs = ', '.join('`' + ref + '`' for ref in fact['evidence_refs'])
            lines.append(f"- **{kind}:** {fact['statement']} Evidencia: {refs}.")
        lines.extend(['', '### Propuestas para revisión', ''])
        for rec in analyst['recommendations']:
            lines.extend([f"**{rec['id']} — {rec['action']}**", '',
                          f"- Métrica: {rec['primary_metric']}", f"- Límite: {rec['guardrail']}",
                          f"- Población: {rec['population']}", f"- Ventana: {rec['window']}",
                          f"- Cierre: {rec['closure_rule']}", ''])
        lines.extend(['### Revisión independiente', '', packet['review']['summary'], ''])
        lines.extend('- ' + item for item in packet['review']['challenges'])
        lines.extend(['', '### Incertidumbres explícitas', ''])
        lines.extend('- ' + item for item in analyst['unknowns'])
    lines.extend(['', '## Cómo interpretar esta entrega', '',
                  'Las citas numéricas exactas se validan automáticamente contra el snapshot. '
                  'La revisión nativa cuestiona el significado y la prioridad de las propuestas. '
                  'Los recibos son constancias del runtime padre con modelo, tarea y tiempos; '
                  'no son firmas criptográficas del proveedor. Un nuevo snapshot emite nuevas solicitudes '
                  'y requiere un nuevo ciclo cognitivo dentro de Codex.', ''])
    output.write_text('\n'.join(lines), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    build(Path(args.workspace), Path(args.output))
    print(json.dumps({'output': args.output, 'status': 'PASS'}))
