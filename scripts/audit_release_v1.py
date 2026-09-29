#!/usr/bin/env python3
"""Fail-closed audit of the Alma OS v1 release ZIP and committed manifest."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.package_release_v1 import (CLIENT_FILES, DIRECT_FILES, FIXED_TIME, MANIFEST, OPTIONAL_NOTICE,
                                         RELEASE_COMMANDS, _kind, canonical, collect_payload, make_manifest,
                                         safe_name, sha)


MAX_MEMBERS = 300
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_RATIO = 1000
TEXT_SUFFIXES = {".txt", ".md", ".html", ".css", ".json", ".csv", ".xml", ".rels", ".py", ".ps1"}
BINARY_SUFFIXES = {".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ttf", ".otf", ".woff", ".woff2"}
SECRET = re.compile(r"(?i)(?:AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|(?:password|api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_+/-]{12,})")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?52[- .]?)?(?:\(\d{2,3}\)|\d{2,3})[- .]\d{3}[- .]\d{4}(?!\w)")
PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:\\Users\\|/Users/[^/\s]+/|/home/[^/\s]+/|file://|\\\\[^\\\s]+\\)")
FORBIDDEN_NAME = re.compile(r"(?i)(?:^|/)(?:\.local|\.env|private|native-drafts|responses?|query-traces?|register-events?|credentials?|id_rsa)(?:/|\.|$)")
FORBIDDEN_FIELD = re.compile(r"(?i)^(?:native_)?(?:request|response|query_trace|dispatch)(?:_body|_content|_text)?$|^(?:customer_)?(?:email|phone|full_name|street_address)$|^register_events?$|^private_cut$")
ACTIVE_XLSX = re.compile(r"(?i)(?:vbaProject|externalLinks|embeddings|connections|customXml|activeX|oleObjects|queryTables|pivotCache|powerPivot|comments|threadedComments|person)")
LINK = re.compile(r"(?i)(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]|\[[^\]]+\]\(([^)]+)\)")


class ReleaseAuditError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseAuditError(message)


def _load_manifest(value: dict | Path) -> tuple[dict, bytes]:
    if isinstance(value, dict):
        return value, canonical(value)
    raw = Path(value).read_bytes()
    parsed = json.loads(raw)
    require(raw == canonical(parsed), "manifest is not canonical JSON")
    return parsed, raw


def _validate_infos(infos: list[zipfile.ZipInfo]) -> list[str]:
    names = [item.filename for item in infos]
    require(0 < len(names) <= MAX_MEMBERS, "ZIP member count limit")
    require(len({name.casefold() for name in names}) == len(names), "case-insensitive duplicate ZIP member")
    require(all(safe_name(name) and not FORBIDDEN_NAME.search(name) for name in names), "unsafe or private ZIP path")
    total = 0
    for item in infos:
        require(not item.is_dir() and not (item.flag_bits & 1), "directory or encrypted ZIP member")
        require(item.compress_type == zipfile.ZIP_STORED, "unexpected ZIP compression")
        require(item.file_size <= MAX_MEMBER, "ZIP member too large")
        require(item.compress_size > 0 or item.file_size == 0, "invalid compression size")
        require(item.file_size <= max(1, item.compress_size) * MAX_RATIO, "excessive ZIP compression ratio")
        mode = (item.external_attr >> 16) & 0o170000
        require(mode == 0o100000, "ZIP member is not a regular file")
        require(item.date_time == FIXED_TIME and item.create_system == 3 and
                (item.external_attr >> 16) == 0o100644,
                "ZIP metadata differs from canonical build")
        total += item.file_size
    require(total <= MAX_TOTAL, "ZIP expanded size limit")
    return names


def _text(name: str, raw: bytes) -> str:
    try:
        value = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReleaseAuditError(f"invalid UTF-8 text: {name}") from exc
    require("\x00" not in value, f"NUL in text: {name}")
    return value


def _privacy(name: str, value: str) -> None:
    require(not SECRET.search(value), f"credential-like content: {name}")
    # JSON escapes backslashes. Collapse one layer before checking UNC paths;
    # otherwise a relative `.venv\\Scripts\\python.exe` appears to be a UNC host.
    path_text = value.replace("\\\\", "\\") if name.endswith(".json") else value
    require(not PRIVATE_PATH.search(path_text), f"private absolute path: {name}")
    # Only two literal example domains are tolerated in source-code templates;
    # CSV/HTML/Markdown/JSON business content never gets this exception.
    emails = EMAIL.findall(value)
    allowed = {"archive-proof@invalid.example"} if name.endswith(".py") else set()
    require(all(email.lower() in allowed for email in emails), f"email-like content: {name}")
    if name.endswith(".csv"):
        require(not PHONE.search(value), f"phone-like content: {name}")
        header = value.splitlines()[0].split(",") if value else []
        require(not any(FORBIDDEN_FIELD.fullmatch(field.strip('"')) for field in header),
                f"PII-like CSV field: {name}")
    if name.endswith(".json"):
        try:
            document = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ReleaseAuditError(f"invalid JSON: {name}") from exc
        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, child in node.items():
                    require(not FORBIDDEN_FIELD.fullmatch(str(key)), f"private JSON field: {name}")
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)
        walk(document)


def _links(name: str, body: str, members: set[str]) -> None:
    if not name.endswith((".md", ".html", ".css")):
        return
    links = [(match.group(1) or match.group(2)) for match in LINK.finditer(body)]
    if name.endswith((".css", ".html")):
        links += re.findall(r"(?i)url\(\s*['\"]?([^)'\"]+)", body)
        links += re.findall(r"(?i)@import\s+['\"]([^'\"]+)", body)
    for value in links:
        link = value.strip().strip("<>")
        require(not re.search(r"\s", link), f"malformed link: {name}")
        require(not link.startswith("//"), f"remote link: {name}")
        parsed = urlsplit(link)
        require(not parsed.scheme and not parsed.netloc, f"external link: {name}")
        local = unquote(parsed.path)
        if not local:
            continue
        require("\\" not in local and not local.startswith("/"), f"absolute or backslash link: {name}")
        target = posixpath.normpath(posixpath.join(posixpath.dirname(name), local))
        require(target != ".." and not target.startswith("../") and target in members,
                f"broken or escaping link: {name} -> {link}")


def _audit_xlsx(name: str, raw: bytes) -> dict:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ReleaseAuditError(f"invalid XLSX: {name}") from exc
    with archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        require(0 < len(names) < 400 and len({n.casefold() for n in names}) == len(names),
                f"XLSX member count or duplicate: {name}")
        require(sum(item.file_size for item in infos) < 50_000_000, f"oversized XLSX: {name}")
        for item in infos:
            require(safe_name(item.filename) and item.file_size < 20_000_000 and
                    not (item.flag_bits & 1) and
                    ((item.external_attr >> 16) & 0o170000) != 0o120000,
                    f"unsafe XLSX part: {name}!{item.filename}")
        require("[Content_Types].xml" in names and "xl/workbook.xml" in names,
                f"missing XLSX core: {name}")
        require(not any(ACTIVE_XLSX.search(part) for part in names), f"active or hidden XLSX part: {name}")
        inventory = {}
        for part in names:
            content = archive.read(part)
            inventory[part] = sha(content)
            if part.endswith((".xml", ".rels")):
                xml = _text(f"{name}!{part}", content)
                _privacy(f"{name}!{part}", xml)
                root = ET.fromstring(content)
                if part.endswith(".rels"):
                    for relation in root:
                        require(relation.attrib.get("TargetMode", "").lower() != "external" and
                                not re.match(r"(?i)(?:[a-z][\w+.-]*:|//)", relation.attrib.get("Target", "")),
                                f"external XLSX relationship: {name}!{part}")
                for definition in re.findall(r"(?i)<(?:\w+:)?definedName\b[^>]*>", xml):
                    require(re.search(r'''(?i)name=['"]_xlnm\.(?:Print_Area|Print_Titles|_FilterDatabase)['"]''', definition)
                            is not None, f"unexpected defined name: {name}!{part}")
                require(not re.search(r"(?i)state=['\"](?:hidden|veryHidden)['\"]", xml),
                        f"hidden sheet: {name}!{part}")
                require(not re.search(r'''(?i)<(?:\w+:)?(?:row|col)\b[^>]*hidden=['"](?:1|true)['"]''', xml),
                        f"hidden row or column: {name}!{part}")
                require(not re.search(r"(?i)<(?:\w+:)?f(?:\s|>)", xml),
                        f"formula cell: {name}!{part}")
                require(not re.search(r"(?i)(?:macroEnabled|vbaProject|file://)", xml),
                        f"active or external XLSX content: {name}!{part}")
            elif part not in ("[Content_Types].xml",):
                require(False, f"uninspected XLSX binary part: {name}!{part}")
        return inventory


def _audit_binary(name: str, raw: bytes) -> None:
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        _audit_xlsx(name, raw)
    elif suffix == ".pdf":
        require(raw.startswith(b"%PDF-") and b"%%EOF" in raw[-1024:], f"invalid PDF: {name}")
        require(not any(token in raw for token in (b"/JavaScript", b"/EmbeddedFile", b"/Launch", b"/AA")),
                f"active PDF content: {name}")
        _privacy(name, raw.decode("latin-1", errors="ignore"))
    elif suffix in (".png", ".jpg", ".jpeg", ".gif"):
        magic = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8", ".jpeg": b"\xff\xd8", ".gif": b"GIF8"}[suffix]
        require(raw.startswith(magic), f"invalid image: {name}")
        _privacy(name, raw.decode("latin-1", errors="ignore"))
    elif suffix in (".ttf", ".otf", ".woff", ".woff2"):
        magic = {".ttf": b"\x00\x01\x00\x00", ".otf": b"OTTO", ".woff": b"wOFF", ".woff2": b"wOF2"}[suffix]
        require(raw.startswith(magic), f"invalid font: {name}")
        _privacy(name, raw.decode("latin-1", errors="ignore"))
    else:
        raise ReleaseAuditError(f"unclassified binary: {name}")


def _notice(files: dict[str, bytes], manifest: dict) -> None:
    bundled = manifest.get("third_party_bundled")
    require(type(bundled) is bool, "third-party disposition missing")
    acceptance = json.loads(files["acceptance-summary.json"])
    require(acceptance.get("third_party_bundled") is bundled, "acceptance third-party disposition mismatch")
    assets = {name: row["third_party"] for name, row in manifest["entries"].items() if "third_party" in row}
    require(bool(assets) is bundled, "third-party inventory mismatch")
    require((OPTIONAL_NOTICE in files) is bundled, "third-party notice missing or unclassified")
    if bundled:
        notice = _text(OPTIONAL_NOTICE, files[OPTIONAL_NOTICE])
        for row in assets.values():
            for key in ("name", "version", "source", "license"):
                require(row.get(key) and row[key] in notice, f"third-party notice lacks {key}")


def check_manifest(manifest_path: Path, source_root: Path, require_version: str) -> dict:
    manifest, raw = _load_manifest(manifest_path)
    files, sources = collect_payload(source_root)
    acceptance = json.loads(files["acceptance-summary.json"])
    require(acceptance.get("version") == require_version, "acceptance version mismatch")
    require(acceptance.get("third_party_bundled") is False, "unsupported third-party disposition")
    expected = make_manifest(files, version=require_version, sources=sources,
                             license_sha256=sha(files["LICENSE"]))
    require(raw == canonical(expected), "stale or incomplete staged-source release manifest")
    return {"status": "PASS", "manifest_sha256": sha(raw), "license_sha256": sha(files["LICENSE"]),
            "members": len(files) + 1}


def audit_preflight(zip_path: Path, checksum_path: Path, manifest_value: dict | Path,
                    require_version: str, *, expected_license_sha256: str | None = None) -> dict:
    manifest, manifest_bytes = _load_manifest(manifest_value)
    require(manifest.get("schema") == "alma-release-manifest-v1" and
            manifest.get("version") == require_version and
            manifest.get("manifest_self_hash_excluded") is True, "manifest schema/version mismatch")
    entries = manifest.get("entries")
    require(isinstance(entries, dict) and MANIFEST not in entries, "manifest self-entry")
    require("LICENSE" in entries and "acceptance-summary.json" in entries, "required release entry absent")
    checksum = checksum_path.read_text(encoding="ascii").strip()
    require(re.fullmatch(r"[0-9a-f]{64}  " + re.escape(zip_path.name), checksum) is not None,
            "malformed checksum sidecar")
    require(checksum[:64] == sha(zip_path.read_bytes()), "ZIP checksum mismatch")
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        names = _validate_infos(infos)
        require(set(names) == set(entries) | {MANIFEST}, "ZIP member set differs from manifest")
        files = {name: archive.read(name) for name in names}
    if "FUENTES/workbook-manifest.json" in files:
        expected_payload = CLIENT_FILES | set(DIRECT_FILES) | ({OPTIONAL_NOTICE} if OPTIONAL_NOTICE in files else set())
        require(set(files) == expected_payload | {MANIFEST}, "literal public release payload allowlist mismatch")
    require(files[MANIFEST] == manifest_bytes, "ZIP manifest differs from supplied committed manifest")
    require(sha(files["LICENSE"]) == manifest.get("license_sha256"), "LICENSE hash mismatch")
    if expected_license_sha256 is not None:
        require(sha(files["LICENSE"]) == expected_license_sha256, "LICENSE differs from tagged tree")
    for name, row in entries.items():
        require(safe_name(name) and isinstance(row, dict), "invalid manifest entry")
        require(row.get("sha256") == sha(files[name]) and row.get("size") == len(files[name]),
                f"payload hash/size mismatch: {name}")
        require(row.get("media_type") and row.get("source") and row.get("purpose") and
                row.get("classification") in ("BLANK", "SYNTHETIC", "PUBLIC"),
                f"incomplete payload classification: {name}")
        require((row["media_type"], row["classification"]) == _kind(name),
                f"incorrect payload type or classification: {name}")
        suffix = Path(name).suffix.lower()
        if suffix in TEXT_SUFFIXES or name == "LICENSE":
            body = _text(name, files[name])
            _privacy(name, body)
            _links(name, body, set(files))
            if suffix in (".html", ".css"):
                require(not re.search(r"(?i)(?:fetch\s*\(|XMLHttpRequest|importScripts\s*\(|<script[^>]+src\s*=\s*['\"]?https?://)", body),
                        f"remote runtime dependency: {name}")
        elif suffix in BINARY_SUFFIXES:
            _audit_binary(name, files[name])
        else:
            raise ReleaseAuditError(f"uninspected payload type: {name}")
    _notice(files, manifest)
    if "PACKAGE-MANIFEST.json" in files:
        phase4 = json.loads(files["PACKAGE-MANIFEST.json"])
        require(phase4.get("version") == "alma-client-kit-v1" and phase4.get("status") == "PASS",
                "Phase 4 nested manifest invalid")
        phase4_names = CLIENT_FILES - {"PACKAGE-MANIFEST.json"}
        require(set(phase4.get("members", {})) == phase4_names, "Phase 4 nested manifest incomplete")
        for name in phase4_names:
            row = phase4["members"][name]
            require(row.get("sha256") == sha(files[name]) and row.get("bytes") == len(files[name]),
                    f"Phase 4 nested manifest drift: {name}")
    acceptance = json.loads(files["acceptance-summary.json"])
    require(acceptance.get("version") == require_version, "acceptance version mismatch")
    require(acceptance.get("execution") == "PROHIBITED", "business execution boundary missing")
    require(acceptance.get("external_gates") == {"EXT-01": "UNKNOWN", "EXT-02": "UNKNOWN",
                                                  "EXT-03": "REVIEW"},
            "external acceptance state changed")
    for name in ("FUENTES/operating-v1-blank.xlsx", "FUENTES/operating-v1-synthetic.xlsx"):
        if name in files:
            book = json.loads(files["FUENTES/workbook-manifest.json"])
            kind = "blank" if "blank" in name else "synthetic"
            require(book["workbooks"][kind]["sha256"] == sha(files[name]),
                    f"workbook manifest mismatch: {name}")
            require(entries[name]["classification"] == ("BLANK" if kind == "blank" else "SYNTHETIC"),
                    f"workbook classification mismatch: {name}")
    with tempfile.TemporaryDirectory(prefix="alma-release-extracted-") as temp:
        root = Path(temp)
        for name, raw in files.items():
            target = root.joinpath(*name.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        require(all((root.joinpath(*name.split("/"))).read_bytes() == files[name] for name in names),
                "extracted member differs")
    return {"status": "PASS", "version": require_version, "member_count": len(names),
            "manifest_sha256": sha(manifest_bytes), "license_sha256": sha(files["LICENSE"]),
            "zip_sha256": sha(zip_path.read_bytes()), "privacy": "PASS", "links": "PASS"}


def verify_published(tag: str, wrapper: Path, ci_sidecar: Path, download_dir: Path,
                     require_version: str) -> dict:
    """Read the public GitHub release through the isolated account wrapper."""
    require(tag == "v1.0.0" and require_version == "1.0.0", "unexpected release version")
    require(not download_dir.exists(), "readback directory must be fresh")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    require(bool(shell) and wrapper.is_file(), "GitHub wrapper or PowerShell unavailable")
    repo = "erickinorganico/alma-de-lujo-growth-analytics"

    def gh(*args: str) -> str:
        result = subprocess.run([shell, "-NoProfile", "-File", str(wrapper.resolve()), *args],
                                cwd=ROOT, capture_output=True, text=True, timeout=180)
        require(result.returncode == 0, f"GitHub wrapper failed: {' '.join(args[:2])}")
        return result.stdout

    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=ROOT)

    commit = git("rev-parse", f"{tag}^{{commit}}").decode("ascii").strip()
    remote_ref = json.loads(gh("api", f"repos/{repo}/git/ref/tags/{tag}"))
    remote_object = remote_ref["object"]
    for _ in range(3):
        if remote_object["type"] == "commit":
            break
        require(remote_object["type"] == "tag", "unexpected remote tag object")
        remote_object = json.loads(gh("api", f"repos/{repo}/git/tags/{remote_object['sha']}"))["object"]
    require(remote_object["type"] == "commit" and remote_object["sha"] == commit,
            "remote tag target differs from local reviewed commit")
    release = json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))
    require(release.get("tag_name") == tag and not release.get("draft") and
            not release.get("prerelease"), "release tag or status mismatch")
    names = {"Alma_OS_v1.0.0.zip", "Alma_OS_v1.0.0.zip.sha256", "Alma_OS_v1.0.0.acceptance.json"}
    assets = release.get("assets", [])
    require(len(assets) == 3 and {asset.get("name") for asset in assets} == names,
            "published asset inventory mismatch")
    download_dir.mkdir(parents=True)
    gh("release", "download", tag, "--repo", repo, "--dir", str(download_dir.resolve()))
    require({path.name for path in download_dir.iterdir()} == names,
            "downloaded asset inventory mismatch")
    for asset in assets:
        path = download_dir / asset["name"]
        require(path.is_file() and path.stat().st_size == asset["size"],
                f"downloaded asset size mismatch: {asset['name']}")
    archive = download_dir / "Alma_OS_v1.0.0.zip"
    checksum = download_dir / "Alma_OS_v1.0.0.zip.sha256"
    acceptance_path = download_dir / "Alma_OS_v1.0.0.acceptance.json"
    acceptance_raw = acceptance_path.read_bytes()
    accepted = json.loads(acceptance_raw)
    require(acceptance_raw == canonical(accepted), "noncanonical acceptance sidecar")
    ci_raw = ci_sidecar.read_bytes()
    ci = json.loads(ci_raw)
    require(accepted.get("tag") == tag and accepted.get("commit") == commit and
            accepted.get("zip_sha256") == sha(archive.read_bytes()) and
            accepted.get("checksum_sha256") == sha(checksum.read_bytes()) and
            accepted.get("ci_sidecar_sha256") == sha(ci_raw) and
            ci.get("proof_sha") == commit, "downloaded release identity mismatch")
    proof = ci.get("release_preflight", {})
    require(accepted.get("release_preflight") == proof and
            proof.get("commands") == list(RELEASE_COMMANDS) and
            set(proof.get("receipts", {})) == {"windows-latest", "ubuntu-latest"},
            "final CI commands/receipts absent")
    for platform, row in proof["receipts"].items():
        stored = ci_sidecar.parent / "downloads" / commit / platform / "release-v1-preflight.json"
        require(stored.is_file() and row.get("sha256") == sha(stored.read_bytes()),
                f"stored CI receipt missing or changed: {platform}")
        downloaded_receipt = json.loads(stored.read_bytes())
        require(all(row.get(key) == downloaded_receipt.get(key) for key in (
                    "headSha", "commands", "zipSha256", "checksumSha256", "manifestSha256",
                    "licenseSha256", "privacy", "links", "release_publication_executed")),
                f"CI receipt content mismatch: {platform}")
        require(row.get("headSha") == commit and row.get("commands") == list(RELEASE_COMMANDS) and
                row.get("zipSha256") == accepted["zip_sha256"] and
                row.get("checksumSha256") == accepted["checksum_sha256"] and
                row.get("manifestSha256") == accepted["manifest_sha256"] and
                row.get("licenseSha256") == accepted["license_sha256"] and
                row.get("privacy") == "PASS" and row.get("links") == "PASS" and
                row.get("release_publication_executed") is False,
                f"CI receipt release mismatch: {platform}")
    raw_manifest = git("show", f"{tag}:client/v1/release-manifest.json")
    manifest = json.loads(raw_manifest)
    require(raw_manifest == canonical(manifest), "tagged manifest noncanonical")
    result = audit_preflight(archive, checksum, manifest, require_version,
                             expected_license_sha256=sha(git("show", f"{tag}:LICENSE")))
    require(result["manifest_sha256"] == accepted.get("manifest_sha256") and
            result["license_sha256"] == accepted.get("license_sha256"),
            "downloaded manifest or LICENSE mismatch")
    return {"status": "PASS", "tag": tag, "commit": commit,
            "zip_sha256": result["zip_sha256"], "asset_count": 3,
            "privacy": result["privacy"], "links": result["links"]}


def audit_release(zip_path: Path, checksum_path: Path, acceptance_path: Path,
                  ci_sidecar: Path, require_version: str) -> dict:
    acceptance_raw = acceptance_path.read_bytes()
    accepted = json.loads(acceptance_raw)
    require(acceptance_raw == canonical(accepted) and
            accepted.get("schema") == "alma-release-acceptance-v1", "release sidecar invalid")
    tag = accepted.get("tag")
    require(tag == f"v{require_version}", "release tag/version mismatch")
    commit = subprocess.check_output(["git", "rev-parse", f"{tag}^{{commit}}"], cwd=ROOT,
                                     text=True).strip()
    require(accepted.get("commit") == commit and
            accepted.get("zip_sha256") == sha(zip_path.read_bytes()) and
            accepted.get("checksum_sha256") == sha(checksum_path.read_bytes()) and
            accepted.get("ci_sidecar_sha256") == sha(ci_sidecar.read_bytes()),
            "release sidecar identity/hash mismatch")
    ci = json.loads(ci_sidecar.read_bytes())
    proof = ci.get("release_preflight", {})
    require(ci.get("proof_sha") == commit and accepted.get("release_preflight") == proof and
            proof.get("commands") == list(RELEASE_COMMANDS) and
            set(proof.get("receipts", {})) == {"windows-latest", "ubuntu-latest"},
            "release CI proof missing")
    for platform, row in proof["receipts"].items():
        require(row.get("headSha") == commit and row.get("commands") == list(RELEASE_COMMANDS) and
                row.get("zipSha256") == accepted["zip_sha256"] and
                row.get("checksumSha256") == accepted["checksum_sha256"] and
                row.get("manifestSha256") == accepted["manifest_sha256"] and
                row.get("licenseSha256") == accepted["license_sha256"] and
                row.get("privacy") == "PASS" and row.get("links") == "PASS" and
                row.get("release_publication_executed") is False,
                f"CI receipt mismatch: {platform}")
    tagged_manifest = subprocess.check_output(["git", "show", f"{tag}:client/v1/release-manifest.json"],
                                              cwd=ROOT)
    manifest = json.loads(tagged_manifest)
    require(tagged_manifest == canonical(manifest), "tagged release manifest noncanonical")
    tagged_license = subprocess.check_output(["git", "show", f"{tag}:LICENSE"], cwd=ROOT)
    result = audit_preflight(zip_path, checksum_path, manifest, require_version,
                             expected_license_sha256=sha(tagged_license))
    require(result["manifest_sha256"] == accepted["manifest_sha256"] and
            result["license_sha256"] == accepted["license_sha256"],
            "release manifest/LICENSE differs from acceptance sidecar")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode")
    check = sub.add_parser("check-manifest")
    check.add_argument("--manifest", required=True, type=Path)
    check.add_argument("--source-root", required=True, type=Path)
    check.add_argument("--require-version", required=True)
    preflight = sub.add_parser("audit-preflight")
    preflight.add_argument("--zip", required=True, type=Path)
    preflight.add_argument("--checksum", required=True, type=Path)
    preflight.add_argument("--manifest", required=True, type=Path)
    preflight.add_argument("--require-version", required=True)
    preflight.add_argument("--ref", default="HEAD", help="Git ref whose exact LICENSE must be present")
    published = sub.add_parser("verify-published")
    published.add_argument("--tag", required=True)
    published.add_argument("--github-wrapper", required=True, type=Path)
    published.add_argument("--ci-sidecar", required=True, type=Path)
    published.add_argument("--download-dir", required=True, type=Path)
    published.add_argument("--require-version", required=True)
    release = sub.add_parser("audit-release")
    release.add_argument("--zip", required=True, type=Path)
    release.add_argument("--checksum", required=True, type=Path)
    release.add_argument("--acceptance", required=True, type=Path)
    release.add_argument("--ci-sidecar", required=True, type=Path)
    release.add_argument("--require-version", required=True)
    command_line = sys.argv[1:]
    if command_line and command_line[0].startswith("--"):
        command_line.insert(0, "audit-release")
    args = parser.parse_args(command_line)
    try:
        if args.mode == "check-manifest":
            result = check_manifest(args.manifest, args.source_root, args.require_version)
        elif args.mode == "audit-preflight":
            tagged_license = subprocess.check_output(["git", "show", f"{args.ref}:LICENSE"], cwd=ROOT)
            result = audit_preflight(args.zip, args.checksum, args.manifest, args.require_version,
                                     expected_license_sha256=sha(tagged_license))
        elif args.mode == "verify-published":
            result = verify_published(args.tag, args.github_wrapper, args.ci_sidecar,
                                      args.download_dir, args.require_version)
        elif args.mode == "audit-release":
            result = audit_release(args.zip, args.checksum, args.acceptance,
                                   args.ci_sidecar, args.require_version)
        else:
            parser.error("choose check-manifest or audit-preflight")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ReleaseAuditError, ValueError, OSError, KeyError, TypeError, AttributeError,
            json.JSONDecodeError, zipfile.BadZipFile, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
