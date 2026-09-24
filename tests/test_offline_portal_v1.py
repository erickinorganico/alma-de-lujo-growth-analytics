"""Contract tests for the v1 static offline portal."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from alma.decision_register import close_decision, create_register, register_decision, verify_register
from alma.operating_contracts import SOURCE_NAMES, canonical_json
from alma.weekly_cycle import read_terminal_packet, start_cycle
from scripts.build_offline_portal_v1 import (
    PORTAL_SECTIONS,
    PortalContractError,
    build_offline_portal,
    collect_portal_model,
    render_portal,
)
from tests.test_decision_register import closure_check, later_upstream, terminal_cycle
from tests.test_weekly_cycle import upstream


ROOT = Path(__file__).resolve().parents[1]


class _PortalTags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


class PortalExecutiveContractTests(unittest.TestCase):
    def test_canonical_domain_partition_and_unknown_source_fail_closed(self) -> None:
        from scripts.build_offline_portal_v1 import SOURCE_DOMAINS, _source_coverage

        grouped = [source for _, names in SOURCE_DOMAINS for source in names]
        self.assertEqual([5, 5, 5, 4, 3], [len(names) for _, names in SOURCE_DOMAINS])
        self.assertEqual(set(SOURCE_NAMES), set(grouped))
        self.assertEqual(len(SOURCE_NAMES), len(grouped))
        model = boundary_model()
        model["sources"].append({"source_id": "unmapped_v1", "status": "MISSING"})
        with self.assertRaises(PortalContractError):
            _source_coverage(model)

    def test_status_segments_reconcile_without_false_zero(self) -> None:
        from scripts.build_offline_portal_v1 import SOURCE_DOMAINS, _source_coverage

        model = boundary_model()
        names = list(SOURCE_NAMES)
        states = ("COMPLETE", "ZERO", "PARTIAL", "ESTIMATED", "MISSING", "ERROR", "NOT_APPLICABLE")
        model["sources"] = [{"source_id": name, "status": states[index % len(states)]}
                            for index, name in enumerate(names)]
        coverage = _source_coverage(model)
        self.assertEqual(22, sum(row["total"] for row in coverage))
        self.assertTrue(all(sum(source in group for _, group in SOURCE_DOMAINS) == 1
                            for source in names))
        self.assertEqual(22, sum(sum(row["counts"].values()) for row in coverage))
        model["sources"] = []
        self.assertNotIn("0/22", _source_coverage(model)[0]["label"])

    def test_first_screen_semantics_and_chart_table_parity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / ".local" / "portal"
            render_portal(boundary_model(), out)
            html_text = (out / "index.html").read_text("utf-8")
            tags = _PortalTags()
            tags.feed(html_text)
            self.assertIn('class="portal-rail"', html_text)
            self.assertIn('class="provenance-strip"', html_text)
            self.assertIn("Cobertura por dominio", html_text)
            self.assertIn("Detalles del corte y procedencia", html_text)
            self.assertLess(html_text.index("Cobertura por dominio"), html_text.index("Detalles del corte y procedencia"))
            self.assertTrue(any(tag == "svg" and attrs.get("role") == "img" and
                                "aria-labelledby" in attrs for tag, attrs in tags.tags))
            self.assertTrue(any(tag == "table" and attrs.get("id") == "coverage-table"
                                for tag, attrs in tags.tags))
            from scripts.build_offline_portal_v1 import _source_coverage
            for row in _source_coverage(boundary_model()):
                self.assertIn(f'>{row["domain"]} · {row["total"]}</text>', html_text)
                self.assertIn(f'<th scope="row">{row["domain"]}</th><td>COMPLETE ', html_text)
                self.assertEqual(row["total"], sum(row["counts"].values()))
            self.assertTrue(any(tag == "div" and attrs.get("tabindex") == "0" and
                                attrs.get("aria-label", "").startswith("Desplazar tabla de")
                                for tag, attrs in tags.tags))
            self.assertIn("No hay una serie comparable para este corte.", html_text)
            self.assertIn("&lt;script&gt;alert", html_text)

    def test_public_and_unselected_copy_never_borrows_current_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            private = Path(tmp) / ".local" / "unselected"
            render_portal(collect_portal_model(mode="public"), public)
            render_portal(collect_portal_model(mode="private"), private)
            public_html = (public / "index.html").read_text("utf-8")
            private_html = (private / "index.html").read_text("utf-8")
            self.assertIn("Inventario histórico sintético", public_html)
            self.assertIn("Sin métricas actuales en este ejemplo", public_html)
            self.assertIn("NO VERIFICADO", public_html)
            self.assertIn("DESCONOCIDO", public_html)
            self.assertIn("Alma de Lujo · Portal offline v1", public_html)
            self.assertIn("<h1>Corte semanal</h1>", public_html)
            self.assertIn("Todavía no hay un corte actual", private_html)
            self.assertIn("Abre un corte local verificado o consulta el ejemplo sintético.", private_html)
            self.assertNotIn("Inventario histórico sintético", private_html)

    def test_hash_mismatch_emits_bounded_blocked_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
            (cycle / "current-cut.json").write_bytes((cycle / "current-cut.json").read_bytes() + b"\n")
            out = home / ".local" / "blocked-view"
            result = build_offline_portal(mode="private", selected_cycle=cycle, output_dir=out)
            text = (out / "index.html").read_text("utf-8")
            self.assertEqual("blocked", result["mode"])
            self.assertIn("CORTE BLOQUEADO · NO USAR PARA DECISIONES", text)
            self.assertIn("Corrige la evidencia local", text)
            self.assertNotIn(str(cycle), text)
            self.assertNotIn("synthetic:sku", text)
            self.assertEqual([], json.loads((out / "metricas.json").read_text("utf-8"))["rows"])


class PortalEvidenceTests(unittest.TestCase):
    def test_public_and_unselected_views_do_not_accept_private_evidence(self) -> None:
        public = collect_portal_model(mode="public")
        self.assertEqual("EJEMPLO SINTÉTICO · HISTÓRICO v0.2", public["provenance"]["label"])
        self.assertEqual("historical_synthetic", public["provenance"]["role"])
        self.assertTrue(public["provenance"]["synthetic"])
        self.assertNotIn("private", canonical_json(public).decode("utf-8").lower())

        unselected = collect_portal_model(mode="private")
        self.assertEqual("SIN CORTE PRIVADO SELECCIONADO", unselected["provenance"]["label"])
        self.assertEqual([], unselected["metrics"])
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / ".local" / "weekly-cycles" / "candidate"
            private.mkdir(parents=True)
            with self.assertRaises(PortalContractError):
                collect_portal_model(mode="public", selected_cycle=private)

    def test_verified_synthetic_current_cut_preserves_waiting_state_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
            model = collect_portal_model(mode="private", selected_cycle=cycle)
            current = json.loads((cycle / "current-cut.json").read_text("utf-8"))
            self.assertIn("CORTE PRIVADO ACTUAL", model["provenance"]["label"])
            self.assertIn("SINTÉTICO", model["provenance"]["label"])
            self.assertEqual(current["cut_id"], model["cut"]["cut_id"])
            self.assertEqual(current["manifest_sha256"], model["cut"]["manifest_sha256"])
            self.assertEqual(current["mart_bundle_sha256"], model["cut"]["report_sha256"])
            self.assertEqual("ESPERANDO_RESPUESTA", model["native"]["status"])
            self.assertTrue(all(row["status"] == "ESPERANDO_RESPUESTA"
                                for row in model["native"]["roles"]))
            self.assertIsNone(model["packet"])

    def test_changed_current_report_or_path_escape_blocks_the_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            cycle = Path(start_cycle(cut, mart, home / ".local" / "weekly-cycles")["destination"])
            original = (cycle / "current-cut.json").read_bytes()
            (cycle / "current-cut.json").write_bytes(original + b"\n")
            with self.assertRaisesRegex(PortalContractError, "blocked|verify|hash"):
                collect_portal_model(mode="private", selected_cycle=cycle)
            with self.assertRaises(PortalContractError):
                collect_portal_model(mode="private", selected_cycle=cycle / ".." / cycle.name)

    def test_two_cut_register_keeps_exact_identity_closure_and_stale_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            first_cycle = terminal_cycle(home / "first")
            packet = read_terminal_packet(first_cycle)
            recommendation_ids = [row["item"]["id"] for row in packet["recommendations"][:2]]
            self.assertEqual(2, len(set(recommendation_ids)))
            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            first = register_decision(register, first_cycle, recommendation_ids[0],
                                      "growth_owner", "2026-10-02", "ACCEPT", closure_check())
            second = register_decision(register, first_cycle, recommendation_ids[1],
                                       "growth_owner", "2026-09-22", "ACCEPT", closure_check())
            cut, marts = later_upstream(home)
            later = start_cycle(cut, marts, home / ".local" / "weekly-cycles",
                                prior_register=register, prior_anchor=second["anchor"])
            later_cycle = Path(later["destination"])
            current = json.loads((later_cycle / "current-cut.json").read_text("utf-8"))
            evidence = {"cut_id": current["cut_id"],
                        "current_cut_sha256": later["current_cut_sha256"],
                        "pointer": "/metric_rows/0/value",
                        "observed_value": current["metric_rows"][0]["value"]}
            close_decision(register, first["decision_id"], later_cycle, evidence)
            expected = verify_register(register)
            model = collect_portal_model(mode="private", selected_cycle=later_cycle,
                                         decision_register=register)
            self.assertEqual(expected["anchor"], model["decision_register"]["current_anchor"])
            actual = {row["decision_id"]: row for row in model["decisions"]}
            self.assertEqual("CLOSED", actual[first["decision_id"]]["status"])
            self.assertEqual("STALE", actual[second["decision_id"]]["status"])
            for row in expected["decisions"]:
                rendered = actual[row["decision_id"]]
                for key in ("decision_id", "recommendation_id", "status", "source_hash",
                            "packet_hash", "due_date"):
                    self.assertEqual(row[key], rendered[key])
            self.assertTrue(actual[first["decision_id"]]["closure_evidence"])


def boundary_model() -> dict:
    digest = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    rows = [
        {"metric_id": "observed_zero_cents", "cut_id": "synthetic-boundary-cut",
         "as_of": "2026-09-22", "dimensions": {"case": "zero"}, "numerator": 0,
         "denominator": 1, "value": 0, "status": "MEASURED", "unit": "MXN_CENTS",
         "coverage_refs": ["sales_aggregates"], "source_refs": [digest("zero")],
         "source_hash": digest("zero"), "reconciliation_id": "rec-zero"},
        {"metric_id": "unknown_value", "cut_id": "synthetic-boundary-cut",
         "as_of": "2026-09-22", "dimensions": {"case": "unknown"}, "numerator": None,
         "denominator": None, "value": None, "status": "UNKNOWN", "unit": "UNITS",
         "coverage_refs": ["unmet_demand"], "source_refs": [digest("unknown")],
         "source_hash": digest("unknown"), "reconciliation_id": "rec-unknown"},
        {"metric_id": "partial_cents", "cut_id": "synthetic-boundary-cut",
         "as_of": "2026-09-22", "dimensions": {"case": "partial"}, "numerator": 123456789,
         "denominator": None, "value": 123456789, "status": "PARTIAL", "unit": "MXN_CENTS",
         "coverage_refs": ["cost_components"], "source_refs": [digest("partial")],
         "source_hash": digest("partial"), "reconciliation_id": "rec-partial"},
        {"metric_id": "policy_review", "cut_id": "synthetic-boundary-cut",
         "as_of": "2026-09-22", "dimensions": {"case": "review"}, "numerator": 1,
         "denominator": 2, "value": "0.5", "status": "REVIEW", "unit": "RATIO",
         "coverage_refs": ["budgets"], "source_refs": [digest("review")],
         "source_hash": digest("review"), "reconciliation_id": "rec-review"},
        {"metric_id": "blocked_metric", "cut_id": "synthetic-boundary-cut",
         "as_of": "2026-09-22", "dimensions": {"case": "blocked"}, "numerator": None,
         "denominator": None, "value": None, "status": "BLOCKED", "unit": "MXN_CENTS",
         "coverage_refs": ["cash_events"], "source_refs": [digest("blocked")],
         "source_hash": digest("blocked"), "reconciliation_id": "rec-blocked"},
    ]
    definitions = {row["metric_id"]: {
        "id": row["metric_id"], "version": "v1", "formula": "fixture_boundary",
        "unit": row["unit"], "grain": "cut", "window": "weekly",
        "sources": row["coverage_refs"], "unknown": "Missing stays unknown",
        "guardrail": "No external execution", "owner": "analytics_owner",
        "decision_use": "Boundary verification",
    } for row in rows}
    return {
        "version": "offline-portal-v1", "mode": "private_current",
        "provenance": {"label": "CORTE PRIVADO ACTUAL · 2026-09-22 · synthetic-boundary-cut · SINTÉTICO",
                       "role": "current", "synthetic": True, "status": "REVIEW",
                       "warning": "Fixture sintético; no usar para decisiones."},
        "cut": {"cut_id": "synthetic-boundary-cut", "cutoff": "2026-09-22T23:59:59-07:00",
                "timezone": "America/Tijuana", "input_class": "SYNTHETIC_EXAMPLE",
                "manifest_sha256": digest("manifest"), "report_sha256": digest("report"),
                "current_cut_sha256": digest("current"), "quality": {"workspace": "PASS"}},
        "sources": [{"source_id": "sales_aggregates", "source_hash": digest("source"),
                     "coverage": {"status": "COMPLETE"}, "status": "COMPLETE",
                     "synthetic": True, "contract": {"grain": "day,sku,channel",
                        "primary_key": ["sales_date", "sku_id", "channel_code"],
                        "fields": [{"name": "net_revenue_cents", "nullable": False,
                                    "unit": "MXN_CENTS"}]}}],
        "metrics": rows, "metric_definitions": definitions,
        "exceptions": [{"status": "BLOCKED", "metric_id": "blocked_metric",
                        "reason": "<script>alert('unsafe')</script>",
                        "next_action": "Aportar evidencia local"}],
        "lineage": {"source_sha256": {"sales_aggregates.csv": digest("source")}},
        "native": {"status": "ESPERANDO_RESPUESTA", "cycle_status": "WAITING_ANALYSTS",
                   "roles": [{"role": "growth_analyst", "status": "ESPERANDO_RESPUESTA",
                              "request_id": "req-synthetic", "request_sha256": digest("request"),
                              "response_sha256": None, "dispatch_sha256": None,
                              "agent_id": None, "model": None}]},
        "packet": None, "decisions": [], "decision_register": None,
        "stages": [{"name": name, "status": ("PASS" if index < 3 else "PENDIENTE"),
                    "evidence": "synthetic-evidence.json" if index < 3 else None}
                   for index, name in enumerate(("Fuentes", "Validación", "Marts y métricas",
                       "Análisis", "Revisión independiente", "Decisión del responsable",
                       "Próximo corte"))],
        "evidence": {"current_cut": {"name": "current-cut.json", "sha256": digest("current")}},
    }


class PortalAccessibilityTests(unittest.TestCase):
    def test_eight_semantic_sections_hostile_text_and_print_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / ".local" / "portal"
            receipt = render_portal(boundary_model(), out)
            html_text = (out / "index.html").read_text("utf-8")
            css = (out / "portal-v1.css").read_text("utf-8")
            positions = [html_text.index(f'id="{section_id}"') for section_id, _ in PORTAL_SECTIONS]
            self.assertEqual(sorted(positions), positions)
            for landmark in ("<header", 'aria-label="Secciones del portal"', "<main", "<section"):
                self.assertIn(landmark, html_text)
            self.assertIn("&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;", html_text)
            self.assertNotIn("<script>alert('unsafe')</script>", html_text)
            self.assertIn('aria-label="Buscar fuentes"', html_text)
            self.assertIn("Inventario completo", html_text)
            self.assertIn(":focus-visible", css)
            self.assertIn("@media print", css)
            self.assertIn("@top-center", html_text)
            self.assertRegex(css, r"overflow-wrap:\s*anywhere")
            self.assertRegex(css, r"flex-wrap:\s*wrap")
            self.assertNotIn("width: 390px", css)
            self.assertNotRegex(html_text, r'(?:href|src)="https?://')
            self.assertEqual("PASS", receipt["status"])
            for href in re.findall(r'href="([^"]+)"', html_text):
                if href.startswith("#"):
                    self.assertIn(f'id="{href[1:]}"', html_text)
                else:
                    self.assertTrue((out / href).resolve().is_relative_to(out.resolve()))
                    self.assertTrue((out / href).is_file(), href)

    def test_mart_portal_csv_json_oracle_preserves_boundary_values(self) -> None:
        model = boundary_model()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / ".local" / "portal"
            render_portal(model, out)
            exported_json = json.loads((out / "metricas.json").read_text("utf-8"))
            with (out / "metricas.csv").open(newline="", encoding="utf-8") as handle:
                exported_csv = list(csv.DictReader(handle))
            expected = {row["metric_id"]: row for row in model["metrics"]}
            actual_json = {row["metric_id"]: row for row in exported_json["rows"]}
            actual_csv = {row["metric_id"]: row for row in exported_csv}
            self.assertEqual(set(expected), set(actual_json), set(actual_csv))
            for metric_id, row in expected.items():
                self.assertEqual(row["value"], actual_json[metric_id]["value"])
                self.assertEqual(row["unit"], actual_json[metric_id]["unit"])
                self.assertEqual(row["status"], actual_json[metric_id]["status"])
                self.assertEqual(row["source_hash"], actual_json[metric_id]["source_hash"])
                self.assertEqual("" if row["value"] is None else str(row["value"]),
                                 actual_csv[metric_id]["value"])
                self.assertEqual(row["status"], actual_csv[metric_id]["status"])
            self.assertEqual(0, actual_json["observed_zero_cents"]["value"])
            self.assertIsNone(actual_json["unknown_value"]["value"])
            self.assertEqual(123456789, actual_json["partial_cents"]["value"])
            self.assertEqual({"MEASURED", "UNKNOWN", "PARTIAL", "REVIEW", "BLOCKED"},
                             {row["status"] for row in exported_json["rows"]})

    def test_public_and_private_destinations_are_separate_and_workbook_receipt_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            public_out = home / "public-portal"
            result = build_offline_portal(mode="public", output_dir=public_out)
            self.assertTrue((public_out / "index.html").is_file())
            self.assertEqual("public", result["mode"])
            with self.assertRaises(PortalContractError):
                build_offline_portal(mode="public", output_dir=home / ".local" / "public")
            with self.assertRaises(PortalContractError):
                render_portal(boundary_model(), home / ".local" / "tampered",
                              workbook_receipt=home / "missing-receipt.json")

    def test_visual_receipt_rehashes_the_bounded_browser_evidence(self) -> None:
        evidence = ROOT / "evidence" / "v1.0" / "portal"
        receipt_path = evidence / "portal-visual-inspection.json"
        receipt = json.loads(receipt_path.read_text("utf-8"))
        self.assertEqual("PASS", receipt["status"])
        self.assertTrue(receipt["inspection"]["all_pages_reviewed"])
        for key, surface in receipt["surfaces"].items():
            self.assertEqual(surface["print"]["page_count"],
                             receipt["inspection"][f"{key}_pages_reviewed"])
            pages = surface["print"]["rendered_pages"]
            self.assertEqual(list(range(1, len(pages) + 1)), [page["page"] for page in pages])
            self.assertTrue(all(page["disposition"] == "PASS" for page in pages))
        self.assertFalse(receipt["contains_absolute_paths"])
        self.assertFalse(receipt["contains_private_customer_data"])
        members = receipt["evidence_members"]
        self.assertEqual(len(members), receipt["evidence_member_count"])
        self.assertEqual(len(members), len({row["artifact"] for row in members}))
        expected = {receipt_path.name, *(row["artifact"] for row in members)}
        self.assertEqual(expected, {path.name for path in evidence.iterdir() if path.is_file()})
        for row in members:
            path = evidence / row["artifact"]
            self.assertEqual(row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        for surface in receipt["surfaces"].values():
            self.assertEqual("PASS", surface["disposition"])
            names = {row["path"] for row in surface["rendered_portal"]["files"]}
            self.assertIn("index.html", names)
            self.assertIn("portal-v1.css", names)
            self.assertEqual({"desktop", "tablet", "narrow", "small", "zoom"},
                             set(surface["captures"]))
            for capture in surface["captures"].values():
                self.assertEqual("PASS", capture["disposition"])
                self.assertEqual(capture["sha256"], hashlib.sha256(
                    (evidence / capture["artifact"]).read_bytes()).hexdigest())
            self.assertEqual("PASS", surface["print"]["disposition"])
        encoded = canonical_json(receipt).decode("utf-8")
        self.assertNotRegex(encoded, r"[A-Za-z]:\\")
        self.assertNotIn("/Users/", encoded)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
