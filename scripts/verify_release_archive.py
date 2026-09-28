#!/usr/bin/env python3
"""Prove a committed Alma release from a clean archive and two matching CI jobs.

The CI form is ``prove --local-only``. It runs the same archive gates and uploads
its archive receipt. The ordinary form also reads the completed GitHub jobs.
Neither form executes Excel; committed Excel and visual evidence is checked.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OWNER = "erickinorganico"
REPOSITORY = "alma-de-lujo-growth-analytics"
WORKFLOW = "verify.yml"
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
SENSITIVE_OUTPUT = re.compile(
    r"(?i)(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/-]{12,}|Authorization:\s*[^\r\n]+|"
    r"\b(?:password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+)"
)
OS_LABELS = {"windows-latest": "Windows", "ubuntu-latest": "Linux"}
REQUIRED_SOURCE = (
    "requirements-client.txt",
    "scripts/verify_release_archive.py",
    "tests/test_release_archive.py",
    ".github/workflows/verify.yml",
    "scripts/github-personal.ps1",
    "client/v1/workbook-manifest.json",
    "evidence/v1.0/excel/excel-recalculation.json",
    "evidence/v1.0/excel/visual-inspection.json",
)
GATES = (
    ("v1-deterministic", ("scripts/verify_v1.py", "deterministic", "--output",
                           "evidence/v1.0/regression-acceptance.json"), 2400),
    ("client-package-privacy-links", ("-m", "unittest", "tests.test_weekly_kit.ClientKitTests",
                                      "tests.test_client_system", "tests.test_security", "-v"), 900),
    ("final-workbooks-and-receipts", ("scripts/verify_operating_workbooks.py", "check", "--manifest",
                                      "client/v1/workbook-manifest.json", "--excel-receipt",
                                      "evidence/v1.0/excel/excel-recalculation.json", "--visual-receipt",
                                      "evidence/v1.0/excel/visual-inspection.json"), 600),
    ("publishable-source-audit", ("scripts/audit_release.py",), 300),
)


class ProofError(ValueError):
    """A proof gate or immutable evidence check failed."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def read_canonical(path: Path) -> dict:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or raw != encoded(value):
        raise ProofError(f"noncanonical receipt: {path}")
    return value


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded(value))


def rooted(path: Path) -> Path:
    """Resolve CLI paths against the repository before gates change cwd."""
    return (path if path.is_absolute() else ROOT / path).resolve(strict=False)


def failure_stream(value: str | bytes | None, *, limit: int = 3000) -> tuple[str, str]:
    """Return a full digest and a bounded, redacted diagnostic tail."""
    raw = value.encode("utf-8", "replace") if isinstance(value, str) else value or b""
    safe = SENSITIVE_OUTPUT.sub("[REDACTED]", raw.decode("utf-8", "replace"))
    return digest(raw), json.dumps(safe[-limit:], ensure_ascii=True)


def command(args: list[str], cwd: Path = ROOT, *, timeout: int = 120, text: bool = True) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=text, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        out_hash, out_tail = failure_stream(exc.stdout)
        err_hash, err_tail = failure_stream(exc.stderr)
        raise ProofError(f"command timed out after {timeout}s: {Path(args[0]).name}; "
                         f"stdout_sha256={out_hash} stdout_tail={out_tail}; "
                         f"stderr_sha256={err_hash} stderr_tail={err_tail}") from exc
    if result.returncode:
        out_hash, out_tail = failure_stream(result.stdout)
        err_hash, err_tail = failure_stream(result.stderr)
        raise ProofError(f"command failed ({result.returncode}): {Path(args[0]).name}; "
                         f"stdout_sha256={out_hash} stdout_tail={out_tail}; "
                         f"stderr_sha256={err_hash} stderr_tail={err_tail}")
    return result


def resolve_ref(ref: str) -> str:
    value = command(["git", "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"] ).stdout.strip().lower()
    if not SHA.fullmatch(value):
        raise ProofError("ref did not resolve to one full commit SHA")
    return value


def tracked_tree_clean(sha: str) -> None:
    head = resolve_ref("HEAD")
    if head != sha:
        raise ProofError("head SHA differs from frozen proof SHA")
    if command(["git", "status", "--porcelain=v1", "--untracked-files=no"]).stdout.strip():
        raise ProofError("tracked working tree is dirty")


def archive_commit(sha: str, destination: Path) -> dict[str, str]:
    """Extract only ordinary files/directories from git archive, then attest its tree."""
    tar = command(["git", "archive", "--format=tar", sha], text=False, timeout=300).stdout
    members: dict[str, str] = {}
    blobs: dict[str, tuple[str, str]] = {}
    names: set[str] = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(tar), mode="r:") as archive:
        for entry in archive:
            relative = PurePosixPath(entry.name)
            pieces = relative.parts
            if (not pieces or relative.is_absolute() or any(piece in ("", ".", "..") for piece in pieces)
                    or ":" in pieces[0] or "\\" in entry.name or entry.name.casefold() in names):
                raise ProofError(f"unsafe or duplicate archive path: {entry.name}")
            names.add(entry.name.casefold())
            if entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()):
                raise ProofError(f"archive symlink or special member: {entry.name}")
            target = destination.joinpath(*pieces)
            if not target.resolve(strict=False).is_relative_to(destination.resolve()):
                raise ProofError(f"archive path escapes destination: {entry.name}")
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            total += entry.size
            if entry.size > 100_000_000 or total > 500_000_000 or len(names) > 20_000:
                raise ProofError("archive size or member limit exceeded")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(entry)
            if source is None:
                raise ProofError(f"unreadable archive member: {entry.name}")
            with target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            raw = target.read_bytes()
            members[entry.name] = digest(raw)
            mode = "100755" if entry.mode & 0o111 else "100644"
            blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            blobs[entry.name] = (mode, blob)
    for name in REQUIRED_SOURCE:
        if name not in members:
            raise ProofError(f"missing tracked input: {name}")
    tree_raw = command(["git", "ls-tree", "-r", "-z", "--full-tree", sha], text=False).stdout
    expected_blobs = {}
    for record in tree_raw.split(b"\0"):
        if not record:
            continue
        metadata, filename = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split(" ")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ProofError(f"unsupported committed member: {filename!r}")
        expected_blobs[filename.decode("utf-8")] = (mode, oid)
    if blobs != expected_blobs:
        raise ProofError("extracted archive files, modes or blobs differ from committed tree")
    # The archive lacks .git. A disposable index lets existing audit commands
    # inspect the extracted tracked tree without seeing the developer checkout.
    command(["git", "init", "-q"], destination)
    command(["git", "add", "--all"], destination)
    command(["git", "-c", "user.name=Archive Proof", "-c", "user.email=archive-proof@invalid.example",
             "commit", "-q", "-m", "Disposable archive index"], destination)
    return members


def _canonical_comparison(root: Path) -> dict[str, str]:
    """Compare stable scenario/source/mart facts, excluding SQLite bytes and timing."""
    generated = json.loads((root / ".local/v1-acceptance/deterministic/v2/verification.json").read_bytes())
    committed = json.loads((root / "evidence/v0.2/verification.json").read_bytes())
    fields = ("source_hashes", "scenarios", "mechanism_checks", "replay_and_integrity")
    # Scenario summaries and mart hashes represent canonical rows; elapsed time,
    # interpreter metadata, and binary database serialization are not evidence.
    output: dict[str, str] = {}
    for field in fields:
        actual = generated.get(field)
        expected = committed.get(field)
        if field == "scenarios":
            def stable(rows: list[dict]) -> list[dict]:
                return [{key: row.get(key) for key in ("scenario", "status", "passed", "summary", "counts", "mart_hashes", "quality_issues")}
                        for row in rows]
            actual, expected = stable(actual), stable(expected)
        if actual != expected:
            raise ProofError(f"canonical output drift: {field}")
        output[field] = digest(encoded(actual))
    return output


def v1_failed_gate_summary(receipt_path: Path) -> str:
    """Surface failed inner gates without dumping the complete acceptance log."""
    if not receipt_path.is_file():
        return "receipt missing"
    if receipt_path.stat().st_size > 500_000:
        return "receipt oversized"
    try:
        receipt = json.loads(receipt_path.read_bytes())
        if not isinstance(receipt, dict) or receipt.get("version") != "v1.0-release-acceptance" or \
                not isinstance(receipt.get("gates"), list) or len(receipt["gates"]) > 16:
            return "receipt schema invalid"
        failed = []
        for gate in receipt["gates"]:
            if not isinstance(gate, dict) or gate.get("status") not in {"FAIL", "BLOCKED"}:
                continue
            name = gate.get("gate")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", name):
                name = "invalid-gate-name"
            row = {"gate": name, "status": gate["status"]}
            for key in ("stdout_tail", "stderr_tail"):
                value = gate.get(key, "")
                if isinstance(value, str):
                    row[key] = json.loads(failure_stream(value, limit=600)[1])
            failed.append(row)
        status = receipt.get("status") if receipt.get("status") in {"FAIL", "BLOCKED"} else "INVALID"
        return json.dumps({"status": status, "failed_gates": failed},
                          sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    except (OSError, ValueError, TypeError):
        return "receipt unreadable"


def run_archive(sha: str, output: Path, receipt_path: Path) -> dict:
    output = rooted(output)
    receipt_path = rooted(receipt_path)
    if output.exists() or receipt_path.exists():
        raise ProofError("archive output or receipt already exists")
    if output.resolve(strict=False).is_relative_to(ROOT / "client"):
        raise ProofError("archive output cannot be inside delivered client files")
    start = time.monotonic()
    output.mkdir(parents=True)
    extracted = output / "source"
    extracted.mkdir()
    members = archive_commit(sha, extracted)
    venv = output / "venv"
    command([sys.executable, "-m", "venv", str(venv)], timeout=300)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Only the committed optional client requirements are installed.
    command([str(python), "-m", "pip", "install", "-r", "requirements-client.txt"], extracted, timeout=900)
    gates: list[dict] = []
    for name, suffix, timeout in GATES:
        began = time.monotonic()
        args = [str(python), *suffix]
        try:
            result = command(args, extracted, timeout=timeout)
        except (ProofError, subprocess.TimeoutExpired) as exc:
            detail = ""
            if name == "v1-deterministic":
                inner = extracted / "evidence/v1.0/regression-acceptance.json"
                if inner.exists():
                    detail = f"; inner_receipt={v1_failed_gate_summary(inner)}"
            raise ProofError(f"gate {name}: {exc}{detail}") from exc
        gates.append({"name": name, "command": ["python", *suffix], "exit_code": result.returncode,
                      "duration_seconds": round(time.monotonic() - began, 3),
                      "stdout_sha256": digest(result.stdout.encode()), "stderr_sha256": digest(result.stderr.encode())})
    regression = json.loads((extracted / "evidence/v1.0/regression-acceptance.json").read_bytes())
    if regression.get("status") != "PASS":
        raise ProofError("v1 deterministic acceptance did not PASS")
    canonical = _canonical_comparison(extracted)
    artifacts = {
        "evidence/v1.0/regression-acceptance.json": file_digest(extracted / "evidence/v1.0/regression-acceptance.json"),
        ".local/v1-acceptance/deterministic/v2/verification.json": file_digest(
            extracted / ".local/v1-acceptance/deterministic/v2/verification.json"),
        ".local/v1-acceptance/deterministic/scope.json": file_digest(
            extracted / ".local/v1-acceptance/deterministic/scope.json"),
        ".local/v1-acceptance/deterministic/workbooks.json": file_digest(
            extracted / ".local/v1-acceptance/deterministic/workbooks.json"),
    }
    tracked_tree_clean(sha)
    receipt = {"schema": "alma-release-archive-v1", "status": "PASS", "proof_sha": sha,
               "os": platform.system(), "python": platform.python_version(), "excel_executed": False,
               "requirements_sha256": members["requirements-client.txt"],
               "source_tree": command(["git", "rev-parse", f"{sha}^{{tree}}"] ).stdout.strip(),
               "source_hashes": {name: members[name] for name in REQUIRED_SOURCE},
               "canonical_outputs": canonical, "artifact_sha256": artifacts, "gates": gates,
               "duration_seconds": round(time.monotonic() - start, 3)}
    write_new(receipt_path, receipt)
    return receipt


def validate_archive_receipt(receipt: dict, sha: str) -> None:
    if (receipt.get("schema") != "alma-release-archive-v1" or receipt.get("status") != "PASS" or
            receipt.get("proof_sha") != sha or receipt.get("excel_executed") is not False or
            receipt.get("source_tree") != command(["git", "rev-parse", f"{sha}^{{tree}}"] ).stdout.strip()):
        raise ProofError("archive receipt schema, SHA, tree or status mismatch")
    if not isinstance(receipt.get("canonical_outputs"), dict) or set(receipt["canonical_outputs"]) != {
            "source_hashes", "scenarios", "mechanism_checks", "replay_and_integrity"}:
        raise ProofError("archive canonical output inventory mismatch")
    expected_artifacts = {"evidence/v1.0/regression-acceptance.json",
                          ".local/v1-acceptance/deterministic/v2/verification.json",
                          ".local/v1-acceptance/deterministic/scope.json",
                          ".local/v1-acceptance/deterministic/workbooks.json"}
    if set(receipt.get("artifact_sha256", {})) != expected_artifacts or any(
            not re.fullmatch(r"[0-9a-f]{64}", value) for value in receipt["artifact_sha256"].values()):
        raise ProofError("archive generated artifact digest inventory mismatch")
    for name in REQUIRED_SOURCE:
        expected = digest(command(["git", "show", f"{sha}:{name}"], text=False).stdout)
        if receipt.get("source_hashes", {}).get(name) != expected:
            raise ProofError(f"archive source hash mismatch: {name}")
    if receipt.get("requirements_sha256") != receipt["source_hashes"]["requirements-client.txt"]:
        raise ProofError("archive requirements hash mismatch")
    gates = receipt.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise ProofError("archive gate count mismatch")
    for actual, (name, suffix, _) in zip(gates, GATES):
        if actual.get("name") != name or actual.get("command") != ["python", *suffix] or actual.get("exit_code") != 0:
            raise ProofError(f"archive gate command or result mismatch: {name}")


def gh(*args: str) -> str:
    wrapper = ROOT / "scripts/github-personal.ps1"
    if not wrapper.is_file():
        raise ProofError("personal GitHub wrapper missing")
    shell = "powershell.exe" if os.name == "nt" else "pwsh"
    return command([shell, "-NoProfile", "-File", str(wrapper), *args], timeout=180).stdout


def _selected_run(sha: str) -> dict:
    data = json.loads(gh("api", f"repos/{OWNER}/{REPOSITORY}/actions/runs", "--method", "GET",
                         "-f", f"head_sha={sha}", "-f", "per_page=100"))
    runs = [run for run in data.get("workflow_runs", []) if run.get("head_sha") == sha and
            str(run.get("path", "")).split("@", 1)[0].endswith("/" + WORKFLOW)]
    if not runs:
        raise ProofError("no workflow run for proof SHA")
    run = max(runs, key=lambda value: int(value["id"]))
    if run.get("status") == "completed" and run.get("conclusion") != "success":
        raise ProofError("same-SHA workflow run failed or was skipped")
    return run


def _selected_jobs(run: dict, sha: str) -> dict[str, dict]:
    data = json.loads(gh("api", f"repos/{OWNER}/{REPOSITORY}/actions/runs/{run['id']}/jobs",
                         "--method", "GET", "-f", "per_page=100"))
    result: dict[str, dict] = {}
    for label in OS_LABELS:
        matches = [job for job in data.get("jobs", []) if label in job.get("name", "").lower()]
        if not matches:
            raise ProofError(f"missing {label} job")
        if len(matches) != 1:
            raise ProofError(f"ambiguous {label} job")
        job = matches[0]
        if job.get("head_sha") != sha:
            raise ProofError(f"{label} job head SHA mismatch")
        if job.get("status") != "completed":
            raise ProofError(f"pending {label} job")
        if job.get("conclusion") != "success":
            raise ProofError(f"{label} job failed or was skipped")
        result[label] = job
    return result


def wait_for_ci(sha: str, *, timeout_seconds: int = 3600, interval_seconds: int = 30) -> dict:
    """Wait for the exact commit's workflow, with a finite deadline."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        run = None
        try:
            run = _selected_run(sha)
        except ProofError as exc:
            if str(exc) != "no workflow run for proof SHA":
                raise
        if run is not None and run.get("status") == "completed":
            if run.get("conclusion") != "success":
                raise ProofError("same-SHA workflow run failed or was skipped")
            try:
                _selected_jobs(run, sha)
                return run
            except ProofError as exc:
                # A completed run can precede propagation of its jobs endpoint.
                if not str(exc).startswith(("missing ", "pending ")):
                    raise
        if time.monotonic() >= deadline:
            raise ProofError("timed out waiting for same-SHA Windows and Ubuntu CI jobs")
        time.sleep(interval_seconds)


def _download_receipts(run: dict, sha: str, directory: Path) -> dict[str, dict]:
    jobs = _selected_jobs(run, sha)
    downloaded: dict[str, dict] = {}
    for label, job in jobs.items():
        folder = directory / label
        folder.mkdir(parents=True)
        name = f"release-receipt-{label}"
        gh("run", "download", str(run["id"]), "--repo", f"{OWNER}/{REPOSITORY}",
           "--name", name, "--dir", str(folder))
        files = [file for file in folder.rglob("*") if file.is_file()]
        if any(file.is_symlink() or not file.resolve().is_relative_to(folder.resolve()) for file in files):
            raise ProofError(f"{label} artifact has an unsafe file path")
        if len(files) != 1 or files[0].name != "ci-release-archive.json":
            raise ProofError(f"{label} receipt artifact is missing or ambiguous")
        receipt = read_canonical(files[0])
        if (receipt.get("schema") != "alma-release-archive-v1" or receipt.get("status") != "PASS" or
                receipt.get("proof_sha") != sha or receipt.get("os") != OS_LABELS[label] or
                not str(receipt.get("python", "")).startswith("3.12.") or
                receipt.get("excel_executed") is not False):
            raise ProofError(f"{label} receipt content mismatch")
        validate_archive_receipt(receipt, sha)
        downloaded[label] = {"job_id": job["id"], "job_name": job["name"],
                             "conclusion": job["conclusion"], "head_sha": job["head_sha"],
                             "artifact": name, "sha256": file_digest(files[0]), "file": files[0]}
    return downloaded


def remote_proof(sha: str, archive_receipt: Path, sidecar: Path, *, existing: bool) -> None:
    sidecar_absolute = sidecar.absolute()
    if sidecar_absolute.is_relative_to(ROOT) and not sidecar_absolute.is_relative_to(ROOT / ".local"):
        raise ProofError("remote sidecar must be ignored under .local or outside the repository")
    local = read_canonical(archive_receipt)
    validate_archive_receipt(local, sha)
    if existing:
        saved = read_canonical(sidecar)
        if (saved.get("schema") != "alma-release-remote-v1" or saved.get("proof_sha") != sha or
                saved.get("archive_receipt_sha256") != file_digest(archive_receipt) or
                saved.get("run", {}).get("head_sha") != sha or
                saved.get("run", {}).get("conclusion") != "success" or
                saved.get("commands") != [gate["command"] for gate in local["gates"]] or
                set(saved.get("receipts", {})) != set(OS_LABELS)):
            raise ProofError("stale or noncanonical remote sidecar")
        for label in OS_LABELS:
            row = saved.get("receipts", {}).get(label, {})
            stored = sidecar.parent / "downloads" / sha / label / "ci-release-archive.json"
            if not stored.is_file() or row.get("sha256") != file_digest(stored):
                raise ProofError(f"stored {label} receipt altered or absent")
    elif sidecar.exists():
        raise ProofError("remote sidecar already exists")
    run = _selected_run(sha) if existing else wait_for_ci(sha)
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ProofError("same-SHA workflow run is not successful")
    if existing and (saved["run"].get("id") != run["id"] or saved["run"].get("url") != run.get("html_url")):
        raise ProofError("remote run changed since sidecar")
    with tempfile.TemporaryDirectory(prefix="alma-gh-receipts-") as temp:
        received = _download_receipts(run, sha, Path(temp))
        for label, row in received.items():
            downloaded = read_canonical(row["file"])
            if downloaded["source_hashes"] != local["source_hashes"] or downloaded["canonical_outputs"] != local["canonical_outputs"]:
                raise ProofError(f"{label} canonical output or source mismatch")
        if existing:
            for label, row in received.items():
                old = saved["receipts"][label]
                if any(old.get(field) != row[field] for field in ("job_id", "job_name", "conclusion", "head_sha", "artifact", "sha256")):
                    raise ProofError(f"{label} downloaded receipt changed")
            return
        folder = sidecar.parent / "downloads" / sha
        if folder.exists():
            raise ProofError("downloaded receipt destination already exists")
        for label, row in received.items():
            target = folder / label / "ci-release-archive.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(row["file"].read_bytes())
            del row["file"]
        sidecar_data = {"schema": "alma-release-remote-v1", "proof_sha": sha,
                        "archive_receipt_sha256": file_digest(archive_receipt),
                        "commands": [gate["command"] for gate in local["gates"]],
                        "run": {"id": run["id"], "url": run.get("html_url"), "head_sha": run["head_sha"],
                                "conclusion": run["conclusion"]}, "receipts": received}
        write_new(sidecar, sidecar_data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prove",))
    parser.add_argument("--ref", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive-receipt", type=Path, required=True)
    parser.add_argument("--remote-sidecar", type=Path)
    parser.add_argument("--check-existing", action="store_true")
    parser.add_argument("--local-only", action="store_true", help="CI: execute archive gates and emit the local receipt")
    args = parser.parse_args(argv)
    try:
        if args.check_existing and args.local_only:
            raise ProofError("check-existing cannot be local-only")
        if not args.local_only and args.remote_sidecar is None:
            raise ProofError("remote sidecar is required")
        if not args.check_existing and args.output is None:
            raise ProofError("output is required when creating proof")
        args.archive_receipt = rooted(args.archive_receipt)
        if args.output is not None:
            args.output = rooted(args.output)
        if args.remote_sidecar is not None:
            args.remote_sidecar = rooted(args.remote_sidecar)
        sha = resolve_ref(args.ref)
        tracked_tree_clean(sha)
        if args.check_existing:
            remote_proof(sha, args.archive_receipt, args.remote_sidecar, existing=True)
        else:
            run_archive(sha, args.output, args.archive_receipt)
            if not args.local_only:
                remote_proof(sha, args.archive_receipt, args.remote_sidecar, existing=False)
        tracked_tree_clean(sha)
        print(json.dumps({"status": "PASS", "proof_sha": sha, "excel_executed": False}, sort_keys=True))
        return 0
    except (ProofError, OSError, subprocess.TimeoutExpired, tarfile.TarError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
