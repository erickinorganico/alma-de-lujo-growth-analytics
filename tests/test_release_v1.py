"""Adversarial tests for the non-recursive v1 release contract."""
from __future__ import annotations

import io
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import audit_release_v1 as audit
from scripts import package_release_v1 as package


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {
            "LICENSE": b"MIT License\n",
            "INICIO/index.html": b'<a href="../FUENTES/example.csv">Example</a>',
            "FUENTES/example.csv": b"kind,value\nSYNTHETIC,1\n",
            "acceptance-summary.json": b'{"version":"1.0.0","third_party_bundled":false,"execution":"PROHIBITED","external_gates":{"EXT-01":"UNKNOWN","EXT-02":"UNKNOWN","EXT-03":"REVIEW"}}\n',
        }

    def manifest(self):
        return package.make_manifest(self.files, version="1.0.0", license_sha256=package.sha(self.files["LICENSE"]))

    def write_zip(self, files=None, manifest=None):
        files = dict(self.files if files is None else files)
        manifest = self.manifest() if manifest is None else manifest
        files["release-manifest.json"] = package.canonical(manifest)
        output = self.root / "release.zip"
        package.write_zip(output, files)
        checksum = self.root / "release.zip.sha256"
        package.write_checksum(output, checksum)
        return output, checksum

    def raw_zip(self, extra, *, mode=0o100644):
        manifest = self.manifest()
        path = self.root / "raw.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in {**self.files, "release-manifest.json": package.canonical(manifest)}.items():
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
            for name, data in extra:
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED if name == "huge.txt" else zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, data)
        checksum = self.root / "raw.zip.sha256"
        package.write_checksum(path, checksum)
        return path, checksum, manifest

    def test_deterministic_and_exact_manifest(self):
        manifest = self.manifest()
        first, checksum = self.write_zip(manifest=manifest)
        second = self.root / "second.zip"
        package.write_zip(second, {**self.files, "release-manifest.json": package.canonical(manifest)})
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(audit.audit_preflight(first, checksum, manifest, "1.0.0", expected_license_sha256=package.sha(self.files["LICENSE"]))["status"], "PASS")

    def test_member_and_license_mutations_fail(self):
        for mutation in ("missing", "extra", "changed", "license_missing", "license_changed"):
            with self.subTest(mutation=mutation):
                files = dict(self.files)
                if mutation == "missing": files.pop("FUENTES/example.csv")
                if mutation == "extra": files["EXTRA.txt"] = b"surprise"
                if mutation == "changed": files["FUENTES/example.csv"] = b"changed"
                if mutation == "license_missing": files.pop("LICENSE")
                if mutation == "license_changed": files["LICENSE"] = b"changed"
                path, checksum = self.write_zip(files=files)
                with self.assertRaises(audit.ReleaseAuditError):
                    audit.audit_preflight(path, checksum, self.manifest(), "1.0.0", expected_license_sha256=package.sha(self.files["LICENSE"]))

    def test_self_entry_and_manifest_byte_change_fail(self):
        manifest = self.manifest()
        manifest["entries"]["release-manifest.json"] = manifest["entries"]["LICENSE"]
        path, checksum = self.write_zip(manifest=manifest)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")
        manifest = self.manifest()
        altered = dict(manifest)
        altered["extra"] = "different bytes"
        path, checksum = self.write_zip(manifest=altered)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")

    def test_third_party_requires_complete_notice(self):
        files = dict(self.files)
        files["assets/vendor.ttf"] = b"\x00\x01\x00\x00FONT"
        third_party = {"assets/vendor.ttf": {"name": "Vendor", "version": "1", "source": "https://example.org", "license": "OFL"}}
        with self.assertRaises(ValueError):
            package.make_manifest(files, version="1.0.0", license_sha256=package.sha(files["LICENSE"]), third_party=third_party)
        files["THIRD-PARTY-NOTICES-v1.md"] = b"Vendor 1 https://example.org\n"
        files["acceptance-summary.json"] = b'{"version":"1.0.0","third_party_bundled":true,"execution":"PROHIBITED","external_gates":{"EXT-01":"UNKNOWN","EXT-02":"UNKNOWN","EXT-03":"REVIEW"}}\n'
        manifest = package.make_manifest(files, version="1.0.0", license_sha256=package.sha(files["LICENSE"]), third_party=third_party)
        path, checksum = self.write_zip(files, manifest)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")
        files["THIRD-PARTY-NOTICES-v1.md"] += b"OFL\n"
        manifest = package.make_manifest(files, version="1.0.0", license_sha256=package.sha(files["LICENSE"]), third_party=third_party)
        path, checksum = self.write_zip(files, manifest)
        self.assertEqual(audit.audit_preflight(path, checksum, manifest, "1.0.0")["status"], "PASS")

    def test_traversal_duplicate_symlink_and_remote_link_fail(self):
        for bad in ("../escape", "C:/device", "CON.txt", "bad\\name"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    package.write_zip(self.root / "bad.zip", {bad: b"x"})
        files = dict(self.files)
        files["INICIO/index.html"] = b'<script src="https://example.org/a.js"></script>'
        manifest = package.make_manifest(files, version="1.0.0", license_sha256=package.sha(files["LICENSE"]))
        path, checksum = self.write_zip(files, manifest)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")
        for mutation in (("INICIO/INDEX.html", b"duplicate"), ("../escape.txt", b"x"),
                         ("NUL.txt", b"x"), ("huge.txt", b"\x00" * 2_000_000)):
            with self.subTest(name=mutation[0]):
                path, checksum, manifest = self.raw_zip([mutation])
                with self.assertRaises(audit.ReleaseAuditError):
                    audit.audit_preflight(path, checksum, manifest, "1.0.0")
        path, checksum, manifest = self.raw_zip([("symlink", b"LICENSE")], mode=0o120777)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")

    def test_version_and_broken_link_fail(self):
        path, checksum = self.write_zip()
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, self.manifest(), "2.0.0")
        files = dict(self.files)
        files["INICIO/index.html"] = b'<a href="../missing.txt">Missing</a>'
        manifest = package.make_manifest(files, license_sha256=package.sha(files["LICENSE"]))
        path, checksum = self.write_zip(files, manifest)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")

    def test_noncanonical_zip_metadata_fails(self):
        path = self.root / "metadata.zip"
        files = {**self.files, "release-manifest.json": package.canonical(self.manifest())}
        with zipfile.ZipFile(path, "w") as archive:
            for name, raw in files.items():
                info = zipfile.ZipInfo(name, (2026, 9, 28, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        checksum = self.root / "metadata.zip.sha256"
        package.write_checksum(path, checksum)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, self.manifest(), "1.0.0")

    def test_workbook_hidden_and_macro_surfaces_fail(self):
        for part, body in (("xl/vbaProject.bin", b"active"),
                           ("xl/workbook.xml", b'<workbook><definedName name="secret">x</definedName></workbook>')):
            with self.subTest(part=part):
                workbook = io.BytesIO()
                with zipfile.ZipFile(workbook, "w") as book:
                    book.writestr("[Content_Types].xml", b"<Types/>")
                    book.writestr(part, body)
                    if part != "xl/workbook.xml":
                        book.writestr("xl/workbook.xml", b"<workbook/>")
                with self.assertRaises(audit.ReleaseAuditError):
                    audit._audit_xlsx("book.xlsx", workbook.getvalue())

    def test_private_content_fails(self):
        files = dict(self.files)
        files["FUENTES/example.csv"] = b"customer_email\nana@example.com\n"
        manifest = package.make_manifest(files, version="1.0.0", license_sha256=package.sha(files["LICENSE"]))
        path, checksum = self.write_zip(files, manifest)
        with self.assertRaises(audit.ReleaseAuditError):
            audit.audit_preflight(path, checksum, manifest, "1.0.0")


class ReleaseDocumentationTests(unittest.TestCase):
    """Keep the published commands and private-root rollback contract executable."""

    def test_documented_cli_commands_match_current_help(self):
        root = Path(__file__).resolve().parents[1]
        runbook = (root / "docs/RUNBOOK-v1.md").read_text(encoding="utf-8")
        release = (root / "docs/RELEASE-v1.md").read_text(encoding="utf-8")
        package_help = subprocess.run(
            [sys.executable, "scripts/package_release_v1.py", "--help"], cwd=root,
            check=True, capture_output=True, text=True).stdout
        manifest_help = subprocess.run(
            [sys.executable, "scripts/package_release_v1.py", "generate-manifest", "--help"], cwd=root,
            check=True, capture_output=True, text=True).stdout
        audit_help = subprocess.run(
            [sys.executable, "scripts/audit_release_v1.py", "check-manifest", "--help"], cwd=root,
            check=True, capture_output=True, text=True).stdout
        self.assertIn("{generate-manifest,preflight,release}", package_help)
        for literal in ("--source-root", "--output"):
            self.assertIn(literal, manifest_help)
        for literal in ("--manifest", "--source-root", "--require-version"):
            self.assertIn(literal, audit_help)
        for command in package.RELEASE_COMMANDS:
            self.assertIn(command, release)
        self.assertIn(".\\run.ps1 weekly --help", runbook)
        self.assertIn(".\\run.ps1 weekly-resume --help", runbook)
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            for command, flags in (
                ("weekly", ("--source-pack", "--policy", "--output-root", "--prior-register", "--prior-anchor")),
                ("weekly-resume", ("--run", "--action", "--role", "--response", "--query-trace",
                                   "--dispatch-receipt", "--register", "--decision-event")),
            ):
                wrapper_help = subprocess.run(
                    [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "run.ps1",
                     command, "--help"], cwd=root, check=True, capture_output=True, text=True).stdout
                for flag in flags:
                    self.assertIn(flag, wrapper_help)
        weekly_help = subprocess.run(
            [sys.executable, "-m", "alma.weekly", "weekly", "--help"], cwd=root,
            check=True, capture_output=True, text=True).stdout
        resume_help = subprocess.run(
            [sys.executable, "-m", "alma.weekly", "weekly-resume", "--help"], cwd=root,
            check=True, capture_output=True, text=True).stdout
        for flag in ("--source-pack", "--policy", "--output-root", "--prior-register", "--prior-anchor"):
            self.assertIn(flag, weekly_help)
        for flag in ("--run", "--action", "--role", "--response", "--query-trace",
                     "--dispatch-receipt", "--register", "--decision-event"):
            self.assertIn(flag, resume_help)

    def test_sibling_update_rollback_and_uninstall_preserve_private_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installs = root / "installs"
            installs.mkdir()
            private = root / "private"
            private.mkdir()
            sentinel = private / "cut-receipt.json"
            sentinel.write_bytes(b'{"cut":"synthetic","immutable":true}\n')
            private_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()

            def archive(path: Path, version: str) -> Path:
                zip_path = root / f"Alma_OS_{version}.zip"
                package.write_zip(zip_path, {
                    "PORTAL/index.html": f"<title>Alma OS {version}</title>".encode(),
                    "VERSION.txt": (version + "\n").encode(),
                })
                checksum = root / f"Alma_OS_{version}.zip.sha256"
                package.write_checksum(zip_path, checksum)
                self.assertEqual(checksum.read_text(encoding="ascii").split()[0],
                                 hashlib.sha256(zip_path.read_bytes()).hexdigest())
                with zipfile.ZipFile(zip_path) as source:
                    source.extractall(path)
                self.assertTrue((path / "PORTAL/index.html").is_file())
                self.assertIn(b"<title>Alma OS", (path / "PORTAL/index.html").read_bytes())
                return zip_path

            prior = installs / "Alma_OS_v0.9.0"
            archive(prior, "0.9.0")
            with self.assertRaises(FileExistsError):
                if prior.exists():
                    raise FileExistsError("Never update in place")

            updated = installs / "Alma_OS_v1.0.0"
            self.assertFalse(updated.exists(), "Updates must use a fresh sibling directory")
            archive(updated, "1.0.0")
            shutil.rmtree(updated)  # rollback removes only the new package directory
            self.assertEqual((prior / "VERSION.txt").read_text(encoding="ascii"), "0.9.0\n")
            self.assertTrue((prior / "PORTAL/index.html").is_file())  # restored prior entrypoint smoke
            shutil.rmtree(prior)  # uninstall selected package only
            self.assertFalse(prior.exists())
            self.assertTrue(sentinel.is_file())
            self.assertEqual(hashlib.sha256(sentinel.read_bytes()).hexdigest(), private_hash)


class ReleaseWorkflowTests(unittest.TestCase):
    def test_preflight_cli_builds_and_audits_current_commit(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "Alma_OS_v1.0.0.zip"
            checksum = Path(temporary) / "Alma_OS_v1.0.0.zip.sha256"
            result = subprocess.run(
                [sys.executable, "scripts/package_release_v1.py", "preflight",
                 "--ref", "HEAD", "--output", str(archive), "--checksum", str(checksum)],
                cwd=root, check=True, capture_output=True, text=True)
            receipt = json.loads(result.stdout)
            self.assertEqual("PASS", receipt["status"])
            self.assertEqual(receipt["zip_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(
                "PASS",
                audit.audit_preflight(
                    archive, checksum, root / "client/v1/release-manifest.json", "1.0.0",
                    expected_license_sha256=receipt["license_sha256"],
                )["status"],
            )

    def test_both_matrix_jobs_share_four_exact_commands_and_receipt(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn("os: [windows-latest, ubuntu-latest]", workflow)
        self.assertIn("python-version: '3.12'", workflow)
        self.assertIn("name: release-v1-preflight-${{ matrix.os }}", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        for command in package.RELEASE_COMMANDS:
            self.assertEqual(workflow.count("          " + command + "\n"), 1, command)
        self.assertIn('"release_publication_executed":False', workflow)
