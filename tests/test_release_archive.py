"""Fail-closed release archive, CI provenance and immutable readback tests."""
from __future__ import annotations

import io
import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts import verify_release_archive as proof


SHA = "a" * 40
OTHER = "b" * 40


def canonical_file(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(proof.encoded(value))


def job(label: str, *, conclusion: str = "success", sha: str = SHA) -> dict:
    return {"id": 1 if label == "windows-latest" else 2, "name": f"Release archive ({label})",
            "head_sha": sha, "status": "completed", "conclusion": conclusion}


class ArchiveSecurityTests(unittest.TestCase):
    def test_failed_command_reports_bounded_redacted_stdout_and_stderr(self) -> None:
        diagnostic = "v0.2-full-suite-and-scenarios:FAIL"
        secret = "ghp_" + "A" * 32
        stdout = "x" * 5000 + diagnostic + " " + secret
        stderr = "token=" + "B" * 32 + " gate failed"
        completed = CompletedProcess(["python", "scripts/verify_v1.py"], 1, stdout, stderr)
        with patch.object(proof.subprocess, "run", return_value=completed):
            with self.assertRaises(proof.ProofError) as caught:
                proof.command(["python", "scripts/verify_v1.py"])
        message = str(caught.exception)
        self.assertIn(diagnostic, message)
        self.assertIn("stdout_tail=", message)
        self.assertIn("stderr_tail=", message)
        self.assertIn("stdout_sha256=" + proof.digest(stdout.encode()), message)
        self.assertIn("stderr_sha256=" + proof.digest(stderr.encode()), message)
        self.assertNotIn(secret, message)
        self.assertNotIn("B" * 32, message)
        self.assertNotIn("x" * 3001, message)

    def test_relative_output_uses_absolute_venv_python_for_extracted_cwd(self) -> None:
        local = proof.ROOT / ".local"
        local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="archive-path-test-", dir=local) as temp:
            relative = Path(temp).relative_to(proof.ROOT)
            output = relative / "archive"
            receipt_path = relative / "archive.json"
            invoked: list[tuple[list[str], Path]] = []

            def fake_command(args: list[str], cwd: Path = proof.ROOT, **kwargs) -> CompletedProcess:
                invoked.append((args, cwd))
                if args[:2] == ["git", "rev-parse"]:
                    return CompletedProcess(args, 0, "tree\n", "")
                if args[1:3] == ["scripts/verify_v1.py", "deterministic"]:
                    artifacts = {
                        "evidence/v1.0/regression-acceptance.json": {"status": "PASS"},
                        ".local/v1-acceptance/deterministic/v2/verification.json": {},
                        ".local/v1-acceptance/deterministic/scope.json": {},
                        ".local/v1-acceptance/deterministic/workbooks.json": {},
                    }
                    for name, value in artifacts.items():
                        canonical_file(cwd / name, value)
                return CompletedProcess(args, 0, "", "")

            members = {name: "a" * 64 for name in proof.REQUIRED_SOURCE}
            with patch.object(proof, "archive_commit", return_value=members), \
                 patch.object(proof, "command", side_effect=fake_command), \
                 patch.object(proof, "_canonical_comparison", return_value={}), \
                 patch.object(proof, "tracked_tree_clean"):
                proof.run_archive(SHA, output, receipt_path)

            expected_python = (proof.ROOT / output / "venv" /
                               ("Scripts/python.exe" if proof.os.name == "nt" else "bin/python")).resolve()
            extracted = (proof.ROOT / output / "source").resolve()
            gate_calls = [(args, cwd) for args, cwd in invoked if cwd == extracted and args and
                          args[0] == str(expected_python)]
            self.assertEqual(1 + len(proof.GATES), len(gate_calls))  # pip plus four gates
            self.assertTrue(expected_python.is_absolute())
            self.assertTrue((proof.ROOT / receipt_path).is_file())

    def tar_bytes(self, extra: tuple[str, str] | None = None) -> bytes:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            for name in proof.REQUIRED_SOURCE:
                value = b"tracked"
                info = tarfile.TarInfo(name)
                info.size = len(value)
                tar.addfile(info, io.BytesIO(value))
            if extra:
                name, kind = extra
                info = tarfile.TarInfo(name)
                if kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../outside"
                else:
                    info.size = 6
                tar.addfile(info, io.BytesIO(b"secret") if kind == "file" else None)
        return stream.getvalue()

    def extract(self, tar_bytes: bytes, destination: Path) -> dict:
        def fake_command(args: list[str], cwd: Path = proof.ROOT, **kwargs) -> CompletedProcess:
            if args[:2] == ["git", "archive"]:
                return CompletedProcess(args, 0, tar_bytes, b"")
            if args[:2] == ["git", "ls-tree"]:
                oid = hashlib.sha1(b"blob 7\0tracked").hexdigest()
                rows = b"".join(f"100644 blob {oid}\t{name}".encode() + b"\0"
                                for name in proof.REQUIRED_SOURCE)
                return CompletedProcess(args, 0, rows, b"")
            return CompletedProcess(args, 0, "tree\n", "")
        with patch.object(proof, "command", side_effect=fake_command):
            return proof.archive_commit(SHA, destination)

    def test_archive_cannot_read_hidden_local_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "source"
            destination.mkdir()
            members = self.extract(self.tar_bytes(), destination)
            self.assertNotIn(".local/secret", members)
            self.assertFalse((destination / ".local").exists())
            self.assertEqual(set(members), set(proof.REQUIRED_SOURCE))

    def test_archive_rejects_symlink_and_path_escape(self) -> None:
        for extra in (("link", "symlink"), ("../outside", "file")):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / "source"
                destination.mkdir()
                with self.assertRaises(proof.ProofError):
                    self.extract(self.tar_bytes(extra), destination)


class RemoteProvenanceTests(unittest.TestCase):
    def test_run_rejects_different_head_sha(self) -> None:
        response = {"workflow_runs": [{"id": 4, "head_sha": OTHER, "path": ".github/workflows/verify.yml",
                                       "status": "completed", "conclusion": "success"}]}
        with patch.object(proof, "gh", return_value=json.dumps(response)):
            with self.assertRaisesRegex(proof.ProofError, "no workflow run"):
                proof._selected_run(SHA)

    def test_jobs_require_both_os_and_successful_same_sha(self) -> None:
        run = {"id": 4}
        cases = ([job("windows-latest")],
                 [job("windows-latest"), job("ubuntu-latest", conclusion="failure")],
                 [job("windows-latest"), job("ubuntu-latest", conclusion="skipped")],
                 [job("windows-latest"), job("ubuntu-latest", sha=OTHER)])
        for jobs in cases:
            with self.subTest(jobs=jobs), patch.object(proof, "gh", return_value=json.dumps({"jobs": jobs})):
                with self.assertRaises(proof.ProofError):
                    proof._selected_jobs(run, SHA)

    def test_waits_for_queued_run_and_both_jobs_without_real_sleep(self) -> None:
        pending = {"id": 4, "head_sha": SHA, "status": "queued"}
        complete = {"id": 4, "head_sha": SHA, "status": "completed", "conclusion": "success"}
        with patch.object(proof, "_selected_run", side_effect=[pending, complete]) as selected, \
             patch.object(proof, "_selected_jobs", return_value={"windows-latest": job("windows-latest"),
                                                                  "ubuntu-latest": job("ubuntu-latest")}), \
             patch.object(proof.time, "sleep") as sleep:
            self.assertEqual(complete, proof.wait_for_ci(SHA, timeout_seconds=5, interval_seconds=1))
            self.assertEqual(2, selected.call_count)
            sleep.assert_called_once_with(1)

    def test_ci_wait_has_finite_timeout(self) -> None:
        with patch.object(proof, "_selected_run", side_effect=proof.ProofError("no workflow run for proof SHA")), \
             patch.object(proof.time, "monotonic", side_effect=[0, 2]), \
             patch.object(proof.time, "sleep") as sleep:
            with self.assertRaisesRegex(proof.ProofError, "timed out"):
                proof.wait_for_ci(SHA, timeout_seconds=1, interval_seconds=1)
            sleep.assert_not_called()

    def fixtures(self, base: Path) -> tuple[Path, Path, dict]:
        receipt = base / "archive.json"
        sidecar = base / "sidecar.json"
        canonical_file(receipt, {"proof_sha": SHA, "status": "PASS", "source_hashes": {"source": SHA},
                                 "canonical_outputs": {"rows": OTHER}, "gates": [{"command": ["python", "gate"]}]})
        run = {"id": 4, "html_url": "https://github.com/example/actions/runs/4", "head_sha": SHA,
               "status": "completed", "conclusion": "success"}
        rows = {}
        for label in proof.OS_LABELS:
            saved = sidecar.parent / "downloads" / SHA / label / "ci-release-archive.json"
            canonical_file(saved, {"proof_sha": SHA, "os": proof.OS_LABELS[label],
                                   "source_hashes": {"source": SHA}, "canonical_outputs": {"rows": OTHER}})
            rows[label] = {"job_id": 1 if label == "windows-latest" else 2,
                           "job_name": f"Release archive ({label})", "conclusion": "success",
                           "head_sha": SHA, "artifact": f"release-receipt-{label}",
                           "sha256": proof.file_digest(saved)}
        canonical_file(sidecar, {"schema": "alma-release-remote-v1", "proof_sha": SHA,
                                "archive_receipt_sha256": proof.file_digest(receipt),
                                "commands": [["python", "gate"]],
                                "run": {"id": 4, "url": run["html_url"], "head_sha": SHA,
                                        "conclusion": "success"}, "receipts": rows})
        return receipt, sidecar, run

    def fake_download(self, _run: dict, sha: str, directory: Path) -> dict:
        self.assertEqual(sha, SHA)
        rows = {}
        for label in proof.OS_LABELS:
            target = directory / label / "ci-release-archive.json"
            canonical_file(target, {"proof_sha": SHA, "os": proof.OS_LABELS[label],
                                    "source_hashes": {"source": SHA}, "canonical_outputs": {"rows": OTHER}})
            rows[label] = {"job_id": 1 if label == "windows-latest" else 2,
                           "job_name": f"Release archive ({label})", "conclusion": "success",
                           "head_sha": SHA, "artifact": f"release-receipt-{label}",
                           "sha256": proof.file_digest(target), "file": target}
        return rows

    def test_sidecar_rejects_stale_sha_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, sidecar, _ = self.fixtures(Path(temp))
            data = proof.read_canonical(sidecar)
            data["proof_sha"] = OTHER
            canonical_file(sidecar, data)
            before = sidecar.read_bytes()
            with patch.object(proof, "validate_archive_receipt"):
                with self.assertRaisesRegex(proof.ProofError, "stale"):
                    proof.remote_proof(SHA, receipt, sidecar, existing=True)
            self.assertEqual(before, sidecar.read_bytes())

    def test_altered_stored_receipt_is_rejected_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, sidecar, _ = self.fixtures(Path(temp))
            stored = sidecar.parent / "downloads" / SHA / "ubuntu-latest" / "ci-release-archive.json"
            stored.write_bytes(b"altered")
            before = sidecar.read_bytes()
            with patch.object(proof, "validate_archive_receipt"):
                with self.assertRaisesRegex(proof.ProofError, "altered"):
                    proof.remote_proof(SHA, receipt, sidecar, existing=True)
            self.assertEqual(before, sidecar.read_bytes())

    def test_check_existing_is_byte_preserving(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, sidecar, run = self.fixtures(Path(temp))
            before = (receipt.read_bytes(), sidecar.read_bytes())
            with patch.object(proof, "validate_archive_receipt"), \
                 patch.object(proof, "_selected_run", return_value=run), \
                 patch.object(proof, "_download_receipts", side_effect=self.fake_download):
                proof.remote_proof(SHA, receipt, sidecar, existing=True)
            self.assertEqual(before, (receipt.read_bytes(), sidecar.read_bytes()))

    def test_altered_downloaded_receipt_is_rejected_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, sidecar, run = self.fixtures(Path(temp))
            before = (receipt.read_bytes(), sidecar.read_bytes())
            def altered_download(remote_run: dict, sha: str, directory: Path) -> dict:
                rows = self.fake_download(remote_run, sha, directory)
                target = rows["ubuntu-latest"]["file"]
                canonical_file(target, {"proof_sha": SHA, "os": "tampered",
                                        "source_hashes": {"source": SHA},
                                        "canonical_outputs": {"rows": OTHER}})
                rows["ubuntu-latest"]["sha256"] = proof.file_digest(target)
                return rows
            with patch.object(proof, "validate_archive_receipt"), \
                 patch.object(proof, "_selected_run", return_value=run), \
                 patch.object(proof, "_download_receipts", side_effect=altered_download):
                with self.assertRaisesRegex(proof.ProofError, "downloaded receipt changed"):
                    proof.remote_proof(SHA, receipt, sidecar, existing=True)
            self.assertEqual(before, (receipt.read_bytes(), sidecar.read_bytes()))


if __name__ == "__main__":
    unittest.main()
