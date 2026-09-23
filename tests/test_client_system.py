"""Evidence-based acceptance checks for the client-facing analytical system.

These tests intentionally compare the generated manifest with repository-owned
contracts and immutable v0.2 evidence. A declared count without matching rows,
hashes and local artifacts is not accepted as proof.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unittest
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
MANIFEST_PATH = CLIENT / "system-manifest.json"
HTML_PATH = CLIENT / "SISTEMA_ANALITICO.html"
WORKSPACE = ROOT / "evidence" / "v0.2" / "workspace"
WORKSPACE_INDEX = WORKSPACE / "workspace.json"
LINEAGE_EVIDENCE = WORKSPACE / "lineage.json"
ALLOWED_MATRIX_STATES = {"EXISTS", "SPECIFIED", "PARTIAL", "MISSING", "CONFLICT"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def state_values(value):
    """Flatten declared transition states while preserving every legal state."""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set)):
        return set().union(*(state_values(item) for item in value))
    if isinstance(value, dict):
        return {str(item) for item in value.keys()}
    raise AssertionError(f"Unsupported state declaration: {value!r}")


def pick(record: dict, *names: str):
    for name in names:
        if name in record:
            return record[name]
    raise AssertionError(f"Missing required field; expected one of {names}: {record}")


class LinksAndText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.text: list[str] = []
        self.remote_scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("href", "src", "action", "poster"):
            if attrs.get(key):
                self.links.append((key, attrs[key].strip()))
        if tag == "script" and attrs.get("src", "").strip().lower().startswith(("http:", "https:")):
            self.remote_scripts += 1

    def handle_data(self, data):
        self.text.append(data)


class ClientSystemAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST_PATH.exists():
            raise AssertionError(f"Client system manifest is missing: {MANIFEST_PATH}")
        if not HTML_PATH.exists():
            raise AssertionError(f"Client system cockpit is missing: {HTML_PATH}")
        cls.manifest = read_json(MANIFEST_PATH)
        cls.html = HTML_PATH.read_text(encoding="utf-8-sig")

    def _card(self, kind: str, item_id: str) -> str:
        card_id = f"{kind}-{item_id}"
        match = re.search(rf'<details\b[^>]*\bid="{re.escape(card_id)}"[^>]*>(.*?)</details>',
                          self.html, flags=re.IGNORECASE | re.DOTALL)
        self.assertIsNotNone(match, f"Cockpit is missing a detail card for {card_id}")
        return match.group(1)

    @staticmethod
    def _plain(html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).casefold()

    def _records(self, *keys):
        return pick(self.manifest, *keys)

    def _repo_path(self, raw: str, base: Path = CLIENT) -> Path:
        parsed = urlparse(raw)
        self.assertFalse(parsed.scheme or parsed.netloc, f"External resource is not offline-safe: {raw}")
        path = (base / parsed.path).resolve()
        self.assertTrue(path.is_relative_to(ROOT.resolve()), f"Path escapes repository: {raw}")
        return path

    def _verify_hashed_refs(self, refs, *, require_hash=True):
        if isinstance(refs, dict):
            refs = [refs]
        self.assertTrue(refs)
        found_hash = False
        for ref in refs:
            if isinstance(ref, str):
                path_value = ref.split("#", 1)[0]
                evidence_file = self._repo_path(path_value, ROOT)
                self.assertTrue(evidence_file.is_file(), f"Missing evidence file: {path_value}")
                expected = self.manifest.get("source_sha256", {}).get(path_value)
                if expected is None:
                    extension_path = CLIENT / "costs-operations-manifest.json"
                    if extension_path.exists():
                        extension = read_json(extension_path)
                        for source in extension.get("sources", []):
                            if source.get("source_path") == path_value or source.get("file") == Path(path_value).name:
                                expected = source.get("sha256")
                                break
                if require_hash:
                    self.assertTrue(expected, f"Evidence pointer has no content hash: {ref}")
                    self.assertEqual(expected, sha256(evidence_file), f"Stale evidence hash: {path_value}")
                    found_hash = True
                continue
            path_value = pick(ref, "path", "file", "artifact")
            evidence_file = self._repo_path(path_value, ROOT)
            self.assertTrue(evidence_file.is_file(), f"Missing evidence file: {path_value}")
            if require_hash or ("sha256" in ref or "hash" in ref):
                digest = pick(ref, "sha256", "hash")
                self.assertEqual(digest, sha256(evidence_file), f"Stale evidence hash: {path_value}")
                found_hash = True
        if require_hash:
            self.assertTrue(found_hash)

    def test_source_inventory_has_exactly_30_rows_and_evidence(self):
        ids = self.manifest["ids"]["sources"]
        self.assertEqual(len(ids), 30, "Base source inventory must contain exactly 30 records")
        self.assertEqual(len(set(ids)), 30)
        evidence_counts = read_json(WORKSPACE_INDEX)["counts"]
        self.assertEqual(set(evidence_counts), set(ids))
        declared_hashes = self.manifest["source_sha256"]
        for evidence_path, digest in declared_hashes.items():
            path = ROOT / evidence_path
            self.assertTrue(path.is_file(), f"Hashed source does not exist: {evidence_path}")
            self.assertEqual(digest, sha256(path), f"Stale source SHA-256: {evidence_path}")
        for table in ids:
            with self.subTest(source=table):
                table_file = WORKSPACE / "tables" / f"{table}.csv"
                self.assertTrue(table_file.is_file(), f"No row-level evidence for source {table}")
                relative = table_file.relative_to(ROOT).as_posix()
                self.assertIn(relative, declared_hashes, f"No per-source content hash: {table}")
                with table_file.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                    fields = list(rows[0].keys()) if rows else []
                self.assertEqual(len(rows), evidence_counts[table], "Source count must match actual evidence rows")
                self.assertEqual(declared_hashes[relative], sha256(table_file))
                card = self._card("source", table)
                content = self._plain(card)
                count_match = re.search(r"<strong>([\d,]+) filas</strong>", card, re.I)
                self.assertIsNotNone(count_match, f"No explicit source count displayed for {table}")
                self.assertEqual(int(count_match.group(1).replace(",", "")), len(rows))
                for label in ("grano:", "clave primaria:", "origen:", "alimenta marts:",
                              "decisiones vinculadas", "campo"):
                    self.assertIn(label, content, f"{table} is missing {label}")
                for field in fields:
                    self.assertIn(field.casefold(), content, f"Field {field} not documented for {table}")
                pk_match = re.search(r"clave primaria:</b>\s*([^<.]+)", card, re.I)
                self.assertIsNotNone(pk_match)
                pk_fields = {part.strip() for part in re.split(r"[,;+]", pk_match.group(1))}
                self.assertTrue(pk_fields)
                self.assertTrue(pk_fields.issubset(fields), f"Invalid primary key for {table}: {pk_fields}")
                self.assertEqual(len({tuple(row.get(field) for field in pk_fields) for row in rows}), len(rows),
                                 f"Primary key is not unique in {table}")

    def test_marts_have_formula_semantics_and_complete_source_lineage(self):
        expected = {p.stem for p in (ROOT / "models" / "marts").glob("*.sql")}
        ids = self.manifest["ids"]["marts"]
        self.assertEqual(len(ids), 11)
        self.assertEqual(set(ids), expected)
        sources = set(self.manifest["ids"]["sources"])
        edges = self.manifest["source_to_marts"]
        pairs = {(source, mart) for source, marts in edges.items() for mart in marts}
        hashes = self.manifest["source_sha256"]
        for name in ids:
            with self.subTest(mart=name):
                sql_path = ROOT / "models" / "marts" / f"{name}.sql"
                self.assertTrue(sql_path.is_file())
                sql_relative = sql_path.relative_to(ROOT).as_posix()
                self.assertIn(sql_relative, hashes)
                self.assertEqual(hashes[sql_relative], sha256(sql_path))
                sql_text = sql_path.read_text(encoding="utf-8").casefold()
                card = self._card("mart", name)
                content = self._plain(card)
                for label in ("grano:", "guardia de cobertura en sql:", "fuentes directas:", "definición sql completa"):
                    self.assertIn(label, content, f"{name} is missing {label}")
                upstream = set(re.findall(r'href="#source-([^"]+)"', card))
                self.assertTrue(upstream)
                self.assertTrue(upstream.issubset(sources), f"Unknown source listed for {name}: {upstream - sources}")
                executable_sources = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", sql_text)) & sources
                self.assertEqual(upstream, executable_sources,
                                 f"Displayed lineage does not cover every direct SQL source for {name}")
                for src in upstream:
                    self.assertIn((src, name), pairs, f"Missing lineage edge {src} -> {name}")
                # Every declared upstream relation must also occur in executable SQL.
                for src in upstream:
                    self.assertRegex(sql_text, rf"\b{re.escape(src.casefold())}\b",
                                     f"Declared source {src} absent from {name}.sql")
                self.assertRegex(content, r"mxn|centavos|unidades|ratio|porcentaje|%")
                self.assertRegex(content, r"ventana|30.d[ií]as|fecha|periodo|mes")
                self.assertRegex(content, r"unknown|null|desconoc|cobertura")
                self.assertRegex(content, r"decisi[oó]n que informa|decisi[oó]n vinculada|uso de decisi[oó]n|actionable decision",
                                 f"Mart {name} has no explicit decision-use statement")
                mart_csv = WORKSPACE / "marts" / f"{name}.csv"
                with mart_csv.open(encoding="utf-8-sig", newline="") as handle:
                    mart_fields = csv.DictReader(handle).fieldnames or []
                for field in mart_fields:
                    self.assertIn(field.casefold(), content, f"Metric field {field} lacks unit/formula/unknown handling in {name}")

    def test_processes_and_agent_roles_are_bound_to_local_contracts(self):
        expected_processes = {p.stem for p in (ROOT / "processes" / "business").glob("*.json")}
        process_ids = self.manifest["ids"]["processes"]
        self.assertEqual(len(process_ids), 6)
        self.assertEqual(set(process_ids), expected_processes)
        for pid in process_ids:
            contract_path = ROOT / "processes" / "business" / f"{pid}.json"
            contract = read_json(contract_path)
            card = self._card("process", pid)
            content = self._plain(card)
            for label in ("producto de decisión:", "estados operativos terminales:", "excepciones documentadas:",
                          "desde", "evento", "hacia", "control"):
                self.assertIn(label, content, f"Process {pid} is missing {label}")
            contract_states = state_values(contract.get("initial_state"))
            contract_states.update(state_values(contract.get("terminal_states", [])))
            for transition in contract.get("transitions", []):
                contract_states.update(state_values(transition.get("from")))
                contract_states.update(state_values(transition.get("to")))
            for state in contract_states:
                if state:
                    self.assertIn(state.casefold(), content)
            initial = state_values(contract.get("initial_state"))
            triggers = [transition.get("event", "") for transition in contract.get("transitions", [])
                        if initial & state_values(transition.get("from"))]
            self.assertTrue(triggers, f"No initial trigger declared for {pid}")
            for trigger in triggers:
                self.assertIn(trigger.casefold(), content, f"Trigger {trigger} missing from process {pid}")

        # The historical manifest lists single-role files; v1 multi-role catalogs
        # have their own contract gate and are not cards in this client manifest.
        agent_contracts = [path for path in (ROOT / "agents").glob("*.json")
                           if not path.name.endswith(".roles.json")]
        expected_roles = {p.stem for p in agent_contracts}
        role_ids = self.manifest["ids"]["agents"]
        self.assertEqual(len(role_ids), 7)
        self.assertEqual(set(role_ids), expected_roles)
        for name in role_ids:
            card = self._card("agent", name)
            content = self._plain(card)
            for label in ("entrada:", "salida:", "autoridad externa:", "revisor independiente:", "evidencia"):
                self.assertIn(label, content, f"Agent {name} is missing {label}")
            authority = content
            self.assertNotRegex(authority, r"\b(execute|place_order|issue_refund|publish|charge_card)\b")
            contract_path = ROOT / "agents" / f"{name}.json"
            self.assertIsInstance(read_json(contract_path), dict)
            contract = self._plain(contract_path.read_text(encoding="utf-8"))
            self.assertIn(name.replace("_", " ").casefold(), content)

    def test_html_is_offline_private_synthetic_and_local_links_resolve(self):
        html = self.html
        parser = LinksAndText()
        parser.feed(html)
        self.assertEqual(parser.remote_scripts, 0)
        self.assertNotRegex(html.casefold(), r"(fetch\s*\(|xmlhttprequest|websocket|https?://|@import\s+url)",
                            "Network-capable references must be removed for offline use")
        for key, value in parser.links:
            parsed = urlparse(value)
            self.assertFalse(parsed.scheme or parsed.netloc, f"External {key} is not offline-safe: {value}")
            if value.startswith("#") or not parsed.path:
                continue
            target = self._repo_path(value, CLIENT)
            self.assertTrue(target.is_file(), f"Broken local link/resource: {value}")

        visible = " ".join(parser.text).casefold()
        self.assertRegex(visible, r"sint[eé]tic|synthetic", "Synthetic data notice must be visible in rendered content")
        self.assertRegex(visible, r"offline|sin conexi[oó]n|local", "Offline/local use must be stated")
        self.assertNotRegex(html.casefold(), r"(react|supabase|authentication|autenticaci[oó]n).{0,80}(implemented|implementado|live|production)",
                            "Static HTML must not claim an unimplemented application backend")
        secret_patterns = [r"\bsk-[A-Za-z0-9_-]{16,}", r"AKIA[0-9A-Z]{16}", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"]
        for pattern in secret_patterns:
            self.assertNotRegex(html + MANIFEST_PATH.read_text(encoding="utf-8-sig"), pattern,
                                "Secret-like material found in client HTML/manifest")
        self.assertNotRegex(html + MANIFEST_PATH.read_text(encoding="utf-8-sig"),
                            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "Email/PII-like value found in client HTML/manifest")
        for path_value, digest in self.manifest["source_sha256"].items():
            target = self._repo_path(path_value, ROOT)
            self.assertTrue(target.is_file(), f"Manifest asset missing: {path_value}")
            self.assertEqual(digest, sha256(target))

    def test_costs_extension_is_registered_and_the_gap_matrix_uses_normalized_states(self):
        extension_path = CLIENT / "costs-operations-manifest.json"
        if not extension_path.exists():
            self.skipTest("Optional costs extension is not present")
        extension = read_json(extension_path)
        registration = self.manifest["extension"]
        self.assertIs(registration["present"], True)
        self.assertEqual(registration["version"], extension["version"])
        self.assertEqual(set(registration["table_ids"]), {source["name"] for source in extension["sources"]})
        self.assertIs(registration["synthetic"], True)
        extension_html_path = CLIENT / "COSTOS_Y_OPERACION.html"
        self.assertTrue(extension_html_path.is_file())
        extension_html = extension_html_path.read_text(encoding="utf-8-sig")
        extension_parser = LinksAndText()
        extension_parser.feed(extension_html)
        self.assertEqual(extension_parser.remote_scripts, 0)
        extension_text = " ".join(extension_parser.text).casefold()
        self.assertRegex(extension_text, r"sint[eé]tic|synthetic")
        self.assertRegex(extension_text, r"react|supabase")
        self.assertNotRegex(extension_html.casefold(), r"(fetch\s*\(|xmlhttprequest|websocket|https?://|@import\s+url)")
        for _, href in extension_parser.links:
            parsed = urlparse(href)
            self.assertFalse(parsed.scheme or parsed.netloc, f"Extension has an external dependency: {href}")
            if href.startswith("#") or not parsed.path:
                continue
            self.assertTrue(self._repo_path(href, CLIENT).is_file(), f"Extension has a broken link: {href}")
        section_match = re.search(r'<section\b[^>]*id="brechas"[^>]*>(.*?)</section>', self.html, re.I | re.S)
        self.assertIsNotNone(section_match, "Cockpit must present a cost/operations gap matrix")
        matrix_html = section_match.group(1)
        status_map = extension.get("status_mapping", self.manifest.get("status_mapping", {}))
        self.assertTrue(status_map, "The portal must map implementation statuses to canonical states")
        self.assertTrue(ALLOWED_MATRIX_STATES.issubset(set(status_map.values())))
        for status in ALLOWED_MATRIX_STATES:
            self.assertIn(status.casefold(), matrix_html.casefold(), f"Gap matrix legend omits {status}")
        matrix = extension.get("extension_matrix", [])
        self.assertTrue(matrix)
        for row in matrix:
            raw = row["status"].upper()
            mapped = row.get("canonical_status", status_map.get(raw, raw))
            if isinstance(mapped, dict):
                mapped = pick(mapped, "canonical", "state")
            self.assertIn(mapped, ALLOWED_MATRIX_STATES)
            self.assertIn(row["capability"].casefold(), matrix_html.casefold())
            self._verify_hashed_refs(row.get("evidence_refs", row.get("evidence", [])))

    def test_optional_v04_costs_manifest_never_inflates_base_sources(self):
        extension_path = CLIENT / "costs-operations-manifest.json"
        if not extension_path.exists():
            self.skipTest("Optional cost/operations extension is not present")
        extension = read_json(extension_path)
        extension_html = (CLIENT / "COSTOS_Y_OPERACION.html").read_text(encoding="utf-8-sig")
        extension_parser = LinksAndText()
        extension_parser.feed(extension_html)
        extension_text = " ".join(extension_parser.text).casefold()
        base = self._records("base_sources", "sources")
        self.assertEqual(len(base), 30, "The core manifest must retain exactly 30 base sources")
        sources = extension["sources"]
        expected_tables = {
            "cost_versions", "cost_components", "cost_allocations", "purchase_orders_ops",
            "purchase_receipts_ops", "obligations", "obligation_payments", "cash_scenario_events",
        }
        self.assertEqual({s["name"] for s in sources}, expected_tables,
                         "v0.4 operational tables are a separate eight-source extension")
        data_dir = CLIENT / "operating-data"
        loaded = {}
        for source in sources:
            name = source["name"]
            with self.subTest(extension_source=name):
                for field in ("file", "grain", "primary_key", "fields", "rows", "synthetic", "purpose", "sha256"):
                    self.assertIn(field, source)
                self.assertIs(source["synthetic"], True)
                self.assertTrue(source["grain"] and source["purpose"])
                file_path = (data_dir / source["file"]).resolve()
                self.assertTrue(file_path.is_relative_to(CLIENT.resolve()))
                self.assertTrue(file_path.is_file())
                self.assertEqual(source["sha256"], sha256(file_path), f"Stale CSV hash: {name}")
                with file_path.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    rows = list(reader)
                    fields = reader.fieldnames or []
                self.assertEqual(source["rows"], len(rows))
                self.assertEqual(set(source["fields"]), set(fields))
                keys = [key.strip() for key in source["primary_key"].split("+")]
                self.assertTrue(set(keys).issubset(fields))
                self.assertEqual(len({tuple(row[key] for key in keys) for row in rows}), len(rows),
                                 f"Duplicate extension primary key: {name}")
                loaded[name] = rows

        self.assertRegex(extension["version"], r"^0\.[34]\.\d+$")
        self.assertIs(extension["synthetic"], True)
        self.assertEqual(extension["external_execution"], "PROHIBITED")
        definitions = {item["id"]: item for item in extension["metric_definitions"]}
        required_metrics = {"known_cost_sum", "contribution_margin", "markup_on_cost", "purchase_receipt_bridge",
                            "obligation_balance", "cash_scenario_closing"}
        self.assertTrue(required_metrics.issubset(definitions))
        source_names = {source["name"] for source in sources}
        lineage_pairs = {(edge["from_table"], edge["to_metric"]) for edge in extension["lineage"]}
        for metric_id in required_metrics:
            definition = definitions[metric_id]
            for field in ("formula", "unit", "grain", "unknown", "decision", "window", "guardrail"):
                self.assertTrue(str(definition.get(field, "")).strip(), f"{metric_id} missing {field}")
            upstream = set(definition["sources"])
            self.assertTrue(upstream and upstream.issubset(source_names))
            for source_name in upstream:
                self.assertIn((source_name, metric_id), lineage_pairs,
                              f"Missing extension lineage {source_name} -> {metric_id}")
            self.assertTrue(str(definition["unknown"]).strip())
        self.assertNotEqual(definitions["contribution_margin"]["formula"], definitions["markup_on_cost"]["formula"])
        self.assertIn("/ price", definitions["contribution_margin"]["formula"])
        self.assertIn("/ complete unit management cost", definitions["markup_on_cost"]["formula"])

        # Recalculate the published operational measures from the declared CSV facts.
        components = {row["component_id"]: row for row in loaded["cost_components"]}
        versions = {row["cost_version_id"]: row for row in loaded["cost_versions"]}
        calculated = {row["cost_version_id"]: row for row in extension["metrics"]["cost_metrics"]}
        self.assertEqual(set(calculated), set(versions))
        for version_id, version in versions.items():
            relevant = [r for r in loaded["cost_components"] if r["cost_version_id"] == version_id]
            known = sum(int(r["amount_cents"]) for r in relevant if r["amount_cents"].isdigit() and not r["included_in_component_id"])
            missing = [r for r in relevant if r["required"] == "1" and r["quality"] == "missing"]
            result = calculated[version_id]
            self.assertEqual(result["known_total_cents"], known)
            self.assertEqual(result["status"] == "PARTIAL", bool(missing))
            if missing:
                self.assertIsNone(result["unit_management_cost_cents"])
                self.assertIsNone(result["contribution_margin"])
                self.assertIsNone(result["markup_on_cost"])
            else:
                unit_cost = known // int(version["quantity_basis"])
                price = int(version["public_price_cents"])
                fee = (price * int(version["selling_fee_bps"]) + 9999) // 10000
                self.assertEqual(result["unit_management_cost_cents"], unit_cost)
                self.assertEqual(Decimal(result["contribution_margin"]),
                                 Decimal(price - fee - unit_cost).__truediv__(Decimal(price)).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP))
                self.assertEqual(Decimal(result["markup_on_cost"]),
                                 Decimal(price - fee - unit_cost).__truediv__(Decimal(unit_cost)).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP))

        for allocation in extension["metrics"]["allocation_controls"]:
            self.assertTrue(allocation["reconciles"])
            self.assertEqual(allocation["allocated_cents"] + allocation["remainder_cents"], allocation["source_cents"])
        receipts = loaded["purchase_receipts_ops"]
        for purchase in extension["metrics"]["purchase_metrics"]:
            related = [r for r in receipts if r["purchase_order_id"] == purchase["purchase_order_id"]]
            self.assertEqual(purchase["received_qty"], sum(int(r["received_qty"]) for r in related))
            self.assertEqual(purchase["accepted_qty"], sum(int(r["accepted_qty"]) for r in related))
            self.assertEqual(purchase["still_to_receive_qty"], purchase["ordered_qty"] - purchase["received_qty"])
            self.assertEqual(purchase["received_qty"], purchase["accepted_qty"] + purchase["inspection_qty"] + purchase["rejected_qty"])
        payments = loaded["obligation_payments"]
        obligations_by_id = {row["obligation_id"]: row for row in loaded["obligations"]}
        orders_by_id = {row["purchase_order_id"]: row for row in loaded["purchase_orders_ops"]}
        for obligation in extension["metrics"]["obligation_metrics"]:
            paid = sum(int(r["amount_cents"]) for r in payments if r["obligation_id"] == obligation["obligation_id"])
            self.assertEqual(obligation["paid_cents"], paid)
            self.assertEqual(obligation["outstanding_cents"], obligation["original_cents"] - paid)
            self.assertLessEqual(paid, obligation["original_cents"], "Payments cannot exceed their obligation")
            source_obligation = obligations_by_id[obligation["obligation_id"]]
            if source_obligation["origin_type"] == "PURCHASE_ORDER":
                purchase_order = orders_by_id[source_obligation["origin_id"]]
                po_total = int(purchase_order["ordered_qty"]) * int(purchase_order["agreed_unit_cents"])
                if po_total != int(source_obligation["original_cents"]):
                    self.assertTrue(source_obligation.get("reconciliation_ref") or source_obligation.get("supporting_components"),
                                    "PO/obligation variance needs a source-backed breakdown")

        workbook_example_path = CLIENT / "example-input.json"
        self.assertIn(workbook_example_path.relative_to(ROOT).as_posix(), self.manifest["source_sha256"])
        catalog = {row["sku"]: row for row in read_json(workbook_example_path)["CATALOGO"]}
        for sku in {row["sku"] for row in loaded["cost_versions"]} | {row["sku"] for row in loaded["purchase_orders_ops"]}:
            self.assertIn(sku, catalog, f"Operational example SKU is not linked to the client catalog: {sku}")
            self.assertTrue(catalog[sku].get("color"), f"Missing color dimension for {sku}")
            self.assertTrue(catalog[sku].get("size"), f"Missing size dimension for {sku}")

        cash_events = loaded["cash_scenario_events"]
        as_of = date.fromisoformat(extension["as_of"])
        for scenario in extension["metrics"]["cash_scenarios"]:
            scenario_id = scenario["scenario_id"]
            self.assertEqual(len(scenario["weeks"]), 8)
            self.assertEqual(scenario["decision"], "COMPARE_ONLY_NO_EXECUTION")
            if scenario_id == "BASE":
                self.assertIn("opening_status", scenario, "An un-sourced opening balance needs an explicit status")
                opening_status = scenario["opening_status"].upper()
                if opening_status not in {"FACT", "OBSERVED"}:
                    self.assertRegex(opening_status, r"SCENARIO|ASSUMPTION|UNVERIFIED")
                self.assertNotRegex(scenario["level"].upper(), r"FACTS")
                opening_events = [r for r in cash_events if r["direction"] == "OPENING"]
                self.assertEqual(len(opening_events), 1)
                self.assertEqual(int(opening_events[0]["amount_cents"]), scenario["opening_cents"])
                self.assertEqual(opening_events[0]["source_ref"], scenario["opening_source_ref"])
            balance = scenario["opening_cents"]
            expected_minimum = balance
            relevant = [r for r in cash_events if r["scenario_id"] in ("BASE", scenario_id)]
            for index, week in enumerate(scenario["weeks"]):
                start = as_of + timedelta(days=1 + index * 7)
                end = start + timedelta(days=6)
                self.assertEqual(week["start"], start.isoformat())
                self.assertEqual(week["end"], end.isoformat())
                incoming = sum(int(r["amount_cents"]) for r in relevant
                               if r["direction"] == "IN" and start <= date.fromisoformat(r["event_date"]) <= end)
                outgoing = sum(int(r["amount_cents"]) for r in relevant
                               if r["direction"] == "OUT" and start <= date.fromisoformat(r["event_date"]) <= end)
                self.assertEqual(week["in_cents"], incoming)
                self.assertEqual(week["out_cents"], outgoing)
                balance += incoming - outgoing
                self.assertEqual(week["closing_cents"], balance)
                expected_minimum = min(expected_minimum, balance)
            self.assertEqual(scenario["closing_cents"], balance)
            self.assertEqual(scenario["minimum_weekly_closing_cents"], expected_minimum)



if __name__ == "__main__":
    unittest.main()
