"""Acceptance contracts for the v1 weekly command and public client kit."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import alma.weekly as weekly_module
from alma.decision_register import create_register, verify_register
from alma.operating_contracts import SOURCE_NAMES, canonical_json
from alma.weekly import WeeklyContractError, continue_weekly_run, create_weekly_run
from alma.weekly_cycle import verify_cycle
from scripts.build_operating_workbooks import build_operating_workbooks
from scripts.package_client_v1 import PackageContractError, audit_client_zip, build_client_kit
from tests.test_decision_register import MODELS, closure_check
from tests.test_native_agents_v1 import receipt_for, response_for, trace_for


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "client" / "v1" / "policies" / "operating-metrics-synthetic-v1.json"


def generated_materials(home: Path) -> tuple[Path, Path]:
    generated = home / "generated"
    build_operating_workbooks(generated)
    return generated / "source-packs" / "synthetic", generated / "operating-v1-synthetic.xlsx"


def canonical_file(path: Path, value: object) -> Path:
    path.write_bytes(canonical_json(value))
    return path


@contextmanager
def weekly_home():
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        target = Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
        shutil.rmtree(target, ignore_errors=True)


def long_path(path: Path) -> Path:
    if sys.platform == "win32" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path.resolve()))
    return path


class WeeklyCommandTests(unittest.TestCase):
    def test_source_pack_and_workbook_create_derived_waiting_runs_without_overwrite(self) -> None:
        with weekly_home() as home:
            pack, workbook = generated_materials(home)
            for label, source in (("pack", pack), ("workbook", workbook)):
                with self.subTest(label=label):
                    output = home / label / ".local" / "client-runs"
                    result = create_weekly_run(source, POLICY, output)
                    run = Path(result["run"])
                    self.assertEqual(output.resolve(), run.parent)
                    self.assertEqual(result["cut_id"], run.name)
                    self.assertEqual("WAITING_ANALYSTS", result["status"])
                    self.assertEqual(label, result["input_route"])
                    self.assertEqual("WAITING_ANALYSTS", verify_cycle(result["cycle_path"])["status"])
                    index = json.loads((run / "run-index.json").read_text("utf-8"))
                    self.assertEqual(result["cut_id"], index["cut_id"])
                    self.assertEqual("SYNTHETIC_EXAMPLE", index["policy"]["status"])
                    self.assertTrue((run / "receipts" / "source.json").is_file())
                    self.assertTrue((run / "receipts" / "marts.json").is_file())
                    self.assertTrue((run / "receipts" / "native-waiting.json").is_file())
                    with self.assertRaises(WeeklyContractError):
                        create_weekly_run(source, POLICY, output)

    def test_prior_pair_policy_and_private_output_fail_closed(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            valid = home / ".local" / "client-runs"
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, POLICY, valid, prior_register=home / "register")
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, POLICY, home / "public-runs")
            stale = home / "stale-policy.json"
            content = json.loads(POLICY.read_text("utf-8"))
            content["effective_end"] = "2026-02-01"
            content["sha256"] = hashlib.sha256(canonical_json(
                {key: value for key, value in content.items() if key != "sha256"}
            )).hexdigest()
            canonical_file(stale, content)
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, stale, valid)
            self.assertFalse(valid.exists())

    def test_resume_actions_validate_evidence_and_preserve_initial_receipts(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            started = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            run = Path(started["run"])
            cycle = Path(started["cycle_path"])
            before = {path.name: path.read_bytes() for path in (run / "receipts").iterdir()}

            resumed = continue_weekly_run(run, "resume")
            self.assertEqual("WAITING_ANALYSTS", resumed["status"])
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "resume", role="growth_analyst")
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "record", role="growth_analyst")

            for role in sorted(MODELS):
                request = json.loads((cycle / "tasks" / f"{role}.request.json").read_text("utf-8"))
                response, trace = response_for(request), trace_for(request)
                response["recommendations"][0]["id"] = f"{role}-weekly-one"
                response_path = canonical_file(cycle / "tasks" / f"{role}.response.json", response)
                trace_path = canonical_file(cycle / "tasks" / f"{role}.query-trace.json", trace)
                receipt = receipt_for(request, response, trace, MODELS[role])
                receipt["agent_id"] = f"/root/weekly_{role}"
                external = canonical_file(home / f"{role}.dispatch-input.json", receipt)
                continue_weekly_run(run, "record", role=role, response=response_path,
                                    query_trace=trace_path, dispatch_receipt=external)
                continue_weekly_run(run, "submit", role=role, response=response_path,
                                    query_trace=trace_path,
                                    dispatch_receipt=cycle / "tasks" / f"{role}.dispatch.json")

            request = json.loads((cycle / "tasks" / "evidence_reviewer.request.json").read_text("utf-8"))
            response, trace = response_for(request), trace_for(request)
            response["verdict"] = "READY_FOR_OWNER"
            response_path = canonical_file(cycle / "tasks" / "evidence_reviewer.response.json", response)
            trace_path = canonical_file(cycle / "tasks" / "evidence_reviewer.query-trace.json", trace)
            receipt = receipt_for(request, response, trace, "gpt-6-astra")
            receipt["agent_id"] = "/root/weekly_reviewer"
            external = canonical_file(home / "reviewer.dispatch-input.json", receipt)
            continue_weekly_run(run, "record", role="evidence_reviewer", response=response_path,
                                query_trace=trace_path, dispatch_receipt=external)
            continue_weekly_run(run, "submit", role="evidence_reviewer", response=response_path,
                                query_trace=trace_path,
                                dispatch_receipt=cycle / "tasks" / "evidence_reviewer.dispatch.json")
            packet = continue_weekly_run(run, "packet")
            self.assertEqual("READY_FOR_OWNER", packet["status"])

            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            recommendation_id = packet["recommendations"][0]["item"]["id"]
            event = canonical_file(home / "owner-decision.json", {
                "recommendation_id": recommendation_id,
                "owner_role": "growth_owner",
                "due_date": "2026-10-15",
                "owner_choice": "ACCEPT",
                "closure_check": closure_check(),
            })
            registered = continue_weekly_run(run, "register", register=register,
                                             decision_event=event)
            self.assertEqual("OPEN", registered["status"])
            self.assertEqual(1, len(verify_register(register)["decisions"]))
            self.assertEqual(before, {path.name: path.read_bytes()
                                      for path in (run / "receipts").iterdir()})

    def test_launcher_help_and_second_process_resume_match_exact_interface(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            self.skipTest("PowerShell unavailable")
        for command in ("weekly", "weekly-resume"):
            process = subprocess.run([shell, "-NoProfile", "-File", str(ROOT / "run.ps1"),
                                      command, "--help"], cwd=ROOT, text=True,
                                     capture_output=True, check=False)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertIn("--help", process.stdout)
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            result = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            process = subprocess.run([sys.executable, "-m", "alma.weekly", "weekly-resume",
                                      "--run", result["run"], "--action", "resume"],
                                     cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual("WAITING_ANALYSTS", json.loads(process.stdout)["status"])

    def test_clean_git_archive_process_resumes_explicit_restored_private_run(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            result = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            run = Path(result["run"])
            immutable = {
                path.relative_to(run).as_posix(): path.read_bytes()
                for path in (run / "receipts").iterdir()
            }
            immutable["run-index.json"] = (run / "run-index.json").read_bytes()

            archive = home / "committed.zip"
            archived = subprocess.run(
                ["git", "archive", "--format=zip", "-o", str(archive), "HEAD"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, archived.returncode, archived.stderr)
            checkout = home / "clean-checkout"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(checkout)
            self.assertFalse((checkout / ".git").exists())

            backup = home / "explicit-private-run"
            shutil.copytree(long_path(run), long_path(backup))
            shutil.rmtree(long_path(run))
            run.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(long_path(backup), long_path(run))
            env = {**os.environ, "PYTHONPATH": str(checkout)}
            process = subprocess.run(
                [sys.executable, "-m", "alma.weekly", "weekly-resume",
                 "--run", str(run), "--action", "resume"],
                cwd=checkout, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual("WAITING_ANALYSTS", json.loads(process.stdout)["status"])
            self.assertEqual(immutable["run-index.json"], (run / "run-index.json").read_bytes())
            for relative, raw in immutable.items():
                if relative != "run-index.json":
                    self.assertEqual(raw, (run / relative).read_bytes())


class WeeklyPackageStageTests(unittest.TestCase):
    package_keys = {
        "version", "status", "path", "zip_sha256", "manifest_sha256",
        "member_count", "audit",
    }
    audit_keys = {"allowlist", "privacy", "links"}

    def test_success_binds_exact_safe_package_identity_and_public_inventory(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            output = home / ".local" / "client-runs"
            with mock.patch.object(weekly_module, "build_client_kit", wraps=build_client_kit,
                                   create=True) as builder, mock.patch.object(
                    weekly_module, "audit_client_zip", wraps=audit_client_zip,
                    create=True) as auditor:
                result = create_weekly_run(pack, POLICY, output)
            run = Path(result["run"])
            package = run / "public-kit" / "Alma_OS_Client_v1.zip"
            receipt_path = run / "receipts" / "public-package.json"
            index_path = run / "run-index.json"
            builder.assert_called_once_with(package)
            auditor.assert_called_once_with(package)
            receipt_raw = receipt_path.read_bytes()
            receipt = json.loads(receipt_raw)
            index = json.loads(index_path.read_text("utf-8"))
            self.assertEqual(self.package_keys, set(result["public_package"]))
            self.assertEqual(self.package_keys, set(receipt))
            self.assertEqual(self.audit_keys, set(receipt["audit"]))
            self.assertEqual({"allowlist": "PASS", "privacy": "PASS", "links": "PASS"},
                             receipt["audit"])
            self.assertEqual(receipt, index["public_package"])
            self.assertEqual(receipt, result["public_package"])
            self.assertEqual(canonical_json(receipt) + b"\n", receipt_raw)
            self.assertEqual(hashlib.sha256(receipt_raw).hexdigest(),
                             index["receipts"]["public-package.json"])
            self.assertEqual("public-kit/Alma_OS_Client_v1.zip", receipt["path"])
            self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(),
                             receipt["zip_sha256"])
            audited = audit_client_zip(package)
            self.assertEqual(audited["manifest_sha256"], receipt["manifest_sha256"])
            self.assertEqual(audited["member_count"], receipt["member_count"])
            self.assertEqual("WAITING_ANALYSTS", result["status"])
            self.assertFalse(result["native_execution_claimed"])
            self.assertEqual("PROHIBITED", result["external_execution"])
            with zipfile.ZipFile(package) as bundle:
                names = bundle.namelist()
            self.assertFalse(any(name.startswith(("input/", "tasks/", ".local/"))
                                 for name in names))
            self.assertFalse(any(token in name.lower() for name in names for token in
                                 ("response", "query-trace", "dispatch", "owner-decision")))
            self.assertTrue(all(".." not in Path(name).parts and ":" not in name and
                                "\\" not in name for name in names))

    def test_identical_public_inputs_are_reproducible_and_replay_changes_nothing(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            first = create_weekly_run(pack, POLICY, home / "first" / ".local" / "client-runs")
            second = create_weekly_run(pack, POLICY, home / "second" / ".local" / "client-runs")
            self.assertEqual(first["public_package"]["zip_sha256"],
                             second["public_package"]["zip_sha256"])
            self.assertEqual(first["public_package"]["manifest_sha256"],
                             second["public_package"]["manifest_sha256"])
            run = Path(first["run"])
            before = {path.relative_to(run).as_posix(): path.read_bytes()
                      for path in run.rglob("*") if path.is_file()}
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, POLICY, home / "first" / ".local" / "client-runs")
            after = {path.relative_to(run).as_posix(): path.read_bytes()
                     for path in run.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_builder_and_post_build_audit_failures_remove_the_new_cut(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)

            def fail_builder(output: str | Path) -> None:
                target = Path(output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"partial-public-package")
                raise PackageContractError("injected builder failure")

            builder_root = home / "builder" / ".local" / "client-runs"
            with mock.patch.object(weekly_module, "build_client_kit",
                                   side_effect=fail_builder, create=True):
                with self.assertRaises(WeeklyContractError):
                    create_weekly_run(pack, POLICY, builder_root)
            self.assertEqual([], list(builder_root.glob("*")))

            audit_root = home / "audit" / ".local" / "client-runs"
            with mock.patch.object(weekly_module, "build_client_kit", wraps=build_client_kit,
                                   create=True), mock.patch.object(
                    weekly_module, "audit_client_zip",
                    side_effect=PackageContractError("injected auditor failure"), create=True):
                with self.assertRaises(WeeklyContractError):
                    create_weekly_run(pack, POLICY, audit_root)
            self.assertEqual([], list(audit_root.glob("*")))

    def test_tamper_fails_closed_and_clean_archive_process_revalidates_package(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            result = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            run = Path(result["run"])
            package = run / result["public_package"]["path"]
            receipt = run / "receipts" / "public-package.json"
            index = run / "run-index.json"
            immutable = {"package": package.read_bytes(), "receipt": receipt.read_bytes(),
                         "index": index.read_bytes()}

            archive = home / "committed.zip"
            archived = subprocess.run(
                ["git", "archive", "--format=zip", "-o", str(archive), "HEAD"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, archived.returncode, archived.stderr)
            checkout = home / "clean-checkout"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(checkout)
            self.assertIn("audit_client_zip", (checkout / "alma" / "weekly.py").read_text("utf-8"))
            env = {**os.environ, "PYTHONPATH": str(checkout)}
            process = subprocess.run(
                [sys.executable, "-m", "alma.weekly", "weekly-resume",
                 "--run", str(run), "--action", "resume"],
                cwd=checkout, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual("WAITING_ANALYSTS", json.loads(process.stdout)["status"])
            self.assertEqual(immutable["package"], package.read_bytes())
            self.assertEqual(immutable["receipt"], receipt.read_bytes())
            self.assertEqual(immutable["index"], index.read_bytes())

            package.write_bytes(immutable["package"] + b"tamper")
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "resume")
            self.assertEqual(immutable["receipt"], receipt.read_bytes())
            self.assertEqual(immutable["index"], index.read_bytes())
            package.write_bytes(immutable["package"])
            changed = json.loads(receipt.read_text("utf-8"))
            changed["member_count"] += 1
            receipt.write_bytes(canonical_json(changed) + b"\n")
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "resume")
            self.assertEqual(immutable["package"], package.read_bytes())
            self.assertEqual(immutable["index"], index.read_bytes())


def safe_guides(root: Path) -> Path:
    guides = root / "guides"
    guides.mkdir()
    (guides / "EMPIEZA_AQUI.md").write_text(
        "# Empieza aquí\n\nKit informativo y sintético. "
        "[Guía](GUIA_SEMANAL.html) · [Portal](../PORTAL/index.html) · "
        "[Plantilla](../FUENTES/operating-v1-blank.xlsx)\n",
        encoding="utf-8",
    )
    (guides / "GUIA_SEMANAL.html").write_text(
        '<!doctype html><html lang="es"><body><h1>Guía semanal</h1>'
        '<p>Este ZIP no contiene el runtime de analistas y no ejecuta cortes privados.</p>'
        '<a href="../PORTAL/index.html">Abrir demo</a>'
        '<a href="../DICCIONARIO/DICCIONARIO-v1.json">Diccionario</a>'
        '</body></html>',
        encoding="utf-8",
    )
    return guides


class ClientKitTests(unittest.TestCase):
    def test_reproducible_zip_has_complete_hashes_links_policies_and_upstream_oracles(self) -> None:
        with weekly_home() as home:
            guides = safe_guides(home)
            first = build_client_kit(home / "kit-one.zip", guide_root=guides)
            second = build_client_kit(home / "kit-two.zip", guide_root=guides)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual("PASS", first["status"])
            audited = audit_client_zip(home / "kit-one.zip")
            self.assertEqual("PASS", audited["status"])
            extracted = home / "extracted"
            with zipfile.ZipFile(home / "kit-one.zip") as bundle:
                bundle.extractall(extracted)
                names = set(bundle.namelist())
            manifest = json.loads((extracted / "PACKAGE-MANIFEST.json").read_text("utf-8"))
            self.assertEqual(names - {"PACKAGE-MANIFEST.json"}, set(manifest["members"]))
            for relative, item in manifest["members"].items():
                self.assertEqual(item["sha256"], hashlib.sha256(
                    (extracted / relative).read_bytes()).hexdigest())
            self.assertEqual(hashlib.sha256((ROOT / "evidence" / "v1.0" / "workbooks" /
                "workbook-pack-parity.json").read_bytes()).hexdigest(),
                manifest["verification_inputs"]["workbook_pack_parity_sha256"])
            self.assertEqual(hashlib.sha256((ROOT / "evidence" / "v1.0" / "portal" /
                "portal-visual-inspection.json").read_bytes()).hexdigest(),
                manifest["verification_inputs"]["portal_visual_inspection_sha256"])
            self.assertIn("POLITICAS/operating-metrics-review-template-v1.json", names)
            self.assertIn("POLITICAS/operating-metrics-synthetic-v1.json", names)
            self.assertIn("PORTAL/index.html", names)
            self.assertNotIn("synthetic-current", "\n".join(names).lower())
            self.assertFalse(any(name.startswith(("alma/", "scripts/", "tasks/")) for name in names))

    def test_audit_rejects_private_native_runtime_credentials_traversal_and_policy_authority(self) -> None:
        with weekly_home() as home:
            source = home / "safe.zip"
            build_client_kit(source, guide_root=safe_guides(home))

            def mutate(name: str, member: str, content: bytes) -> Path:
                target = home / f"{name}.zip"
                with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, "w") as changed:
                    for info in original.infolist():
                        if info.filename != member:
                            changed.writestr(info, original.read(info.filename))
                    changed.writestr(member, content)
                return target

            cases = {
                "runtime": ("alma/weekly.py", b"este ZIP ejecuta un corte privado"),
                "native": ("tasks/growth_analyst.response.json", b"{}"),
                "private": ("private/current-cut.json", b"{}"),
                "credential": (".env", b"TOKEN=secret"),
                "traversal": ("../escape.txt", b"unsafe"),
                "broken_link": ("INICIO/GUIA_SEMANAL.html", b'<a href="missing.html">x</a>'),
            }
            for name, (member, content) in cases.items():
                with self.subTest(name=name), self.assertRaises(PackageContractError):
                    audit_client_zip(mutate(name, member, content))

            with zipfile.ZipFile(source) as bundle:
                policy = json.loads(bundle.read(
                    "POLITICAS/operating-metrics-review-template-v1.json"))
            policy["status"] = "APPROVED"
            policy["owner_approval_ref"] = "owner:private"
            policy["sha256"] = hashlib.sha256(canonical_json(
                {key: value for key, value in policy.items() if key != "sha256"}
            )).hexdigest()
            with self.assertRaises(PackageContractError):
                audit_client_zip(mutate("approved", "POLITICAS/operating-metrics-review-template-v1.json",
                                        canonical_json(policy)))


class GuideContractTests(unittest.TestCase):
    creation = (
        r".\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> "
        r"--output-root .local/client-runs [--prior-register <register-dir> "
        r"--prior-anchor <anchor.json>]"
    )
    resume_commands = (
        r".\run.ps1 weekly-resume --run <private-run-dir> --action record --role <role> "
        r"--response <response.json> --query-trace <trace.json> "
        r"--dispatch-receipt <receipt.json>",
        r".\run.ps1 weekly-resume --run <private-run-dir> --action submit --role <role> "
        r"--response <response.json> --query-trace <trace.json> "
        r"--dispatch-receipt <receipt.json>",
        r".\run.ps1 weekly-resume --run <private-run-dir> --action resume",
        r".\run.ps1 weekly-resume --run <private-run-dir> --action packet",
        r".\run.ps1 weekly-resume --run <private-run-dir> --action register --register "
        r"<register-dir> --decision-event <owner-decision.json>",
    )

    def test_analyst_runbook_has_exact_commands_and_operating_boundaries(self) -> None:
        text = (ROOT / "docs" / "ANALYST-WEEKLY-v1.md").read_text("utf-8")
        self.assertIn(self.creation, text)
        for command in self.resume_commands:
            self.assertIn(command, text)
        required = (
            "--help", "canonical source pack", "<output-root>/<cut_id>/",
            "both or neither", "git archive", "WAITING", "BLOCKED", "REVIEW",
            "agents/RUN-NATIVE-CYCLE.md", "Terra", "Luna", "Sol", "Astra",
            "stage receipts", "READY_FOR_OWNER", "decision-event",
            "carry-forward", "closure", ".local/", "no upload", "no sync",
            "no external business execution",
        )
        lowered = text.lower()
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), lowered)
        for phrase in (
            "public-kit/Alma_OS_Client_v1.zip", "receipts/public-package.json",
            "zip_sha256", "manifest_sha256", "member_count", "allowlist",
            "privacy", "links", "automáticamente", "independiente de waiting",
        ):
            with self.subTest(package_phrase=phrase):
                self.assertIn(phrase.lower(), lowered)
        self.assertNotIn(
            "python scripts/package_client_v1.py --output <alma-os-client-v1.zip>", text
        )

    def test_client_guides_start_with_sources_policies_and_public_only_journey(self) -> None:
        markdown = (ROOT / "client" / "v1" / "EMPIEZA_AQUI.md").read_text("utf-8")
        html = (ROOT / "client" / "v1" / "GUIA_SEMANAL.html").read_text("utf-8")
        joined = f"{markdown}\n{html}".lower()
        for phrase in (
            "22 tablas", "plantilla vacía", "review", "synthetic_example",
            "vacío no significa cero", "copia privada", "demo pública",
            "informativo y sintético", "no contiene el runtime de analistas",
            "no puede ejecutar un corte privado", "waiting", "blocked", "review",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, joined)
        self.assertIn("../portal/index.html", joined)
        self.assertIn("../fuentes/operating-v1-blank.xlsx", joined)
        self.assertNotIn(self.creation.lower(), joined)
        for relation in SOURCE_NAMES:
            with self.subTest(relation=relation):
                self.assertIn(f"`{relation}`", markdown)

    def test_real_guides_are_packaged_and_all_extracted_links_audit_cleanly(self) -> None:
        with weekly_home() as home:
            output = home / "alma-os-client-v1.zip"
            result = build_client_kit(output)
            self.assertEqual("PASS", result["status"])
            self.assertEqual("PASS", audit_client_zip(output)["status"])
            with zipfile.ZipFile(output) as bundle:
                self.assertEqual(
                    (ROOT / "client" / "v1" / "EMPIEZA_AQUI.md").read_bytes(),
                    bundle.read("INICIO/EMPIEZA_AQUI.md"),
                )
                self.assertEqual(
                    (ROOT / "client" / "v1" / "GUIA_SEMANAL.html").read_bytes(),
                    bundle.read("INICIO/GUIA_SEMANAL.html"),
                )


if __name__ == "__main__":
    unittest.main()
