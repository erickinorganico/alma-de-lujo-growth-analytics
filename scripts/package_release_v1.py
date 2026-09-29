#!/usr/bin/env python3
"""Build the deterministic, tag-bound Alma OS v1.0.0 public client release."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VERSION = "1.0.0"
MANIFEST = "release-manifest.json"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
DIRECT_FILES = {
    "LICENSE": "LICENSE",
    "acceptance-summary.json": "client/v1/acceptance-summary.json",
    "RUNBOOK-v1.md": "docs/RUNBOOK-v1.md",
    "ACCEPTANCE-v1.md": "docs/ACCEPTANCE-v1.md",
    "RELEASE-v1.md": "docs/RELEASE-v1.md",
    "FUENTES/operating-v1-blank.xlsx": "client/v1/Alma_de_Lujo_OPERACION_PLANTILLA.xlsx",
    "FUENTES/operating-v1-synthetic.xlsx": "client/v1/Alma_de_Lujo_OPERACION_EJEMPLO.xlsx",
    "FUENTES/workbook-manifest.json": "client/v1/workbook-manifest.json",
}
OPTIONAL_NOTICE = "THIRD-PARTY-NOTICES-v1.md"
RELEASE_COMMANDS = (
    "python -m unittest tests.test_release_v1 -v",
    "python scripts/audit_release_v1.py check-manifest --manifest client/v1/release-manifest.json --source-root . --require-version 1.0.0",
    "python scripts/package_release_v1.py preflight --ref HEAD --output build/release-v1/Alma_OS_v1.0.0.zip --checksum build/release-v1/Alma_OS_v1.0.0.zip.sha256",
    "python scripts/audit_release_v1.py audit-preflight --zip build/release-v1/Alma_OS_v1.0.0.zip --checksum build/release-v1/Alma_OS_v1.0.0.zip.sha256 --manifest client/v1/release-manifest.json --require-version 1.0.0",
)
RELATIONS = (
    "sku_catalog", "sales_aggregates", "availability_daily", "unmet_demand",
    "inventory_counts", "inventory_movements", "inventory_reservations",
    "cost_versions", "cost_components", "cost_allocations", "purchase_orders",
    "purchase_receipts", "obligations", "obligation_payments", "cash_events",
    "cash_balance_evidence", "budgets", "budget_allocations", "expenses",
    "quality_events", "sales_readiness", "loans",
)
CLIENT_FILES = {
    "PACKAGE-MANIFEST.json", "INICIO/EMPIEZA_AQUI.md", "INICIO/GUIA_SEMANAL.html",
    "FUENTES/operating-v1-blank.xlsx", "FUENTES/operating-v1-synthetic.xlsx",
    "FUENTES/workbook-manifest.json", "DICCIONARIO/DICCIONARIO-v1.json",
    "EJEMPLO/RECORRIDO-SINTETICO.md",
    "POLITICAS/operating-metrics-review-template-v1.json",
    "POLITICAS/operating-metrics-synthetic-v1.json",
    *(f"PORTAL/{name}" for name in (
        "index.html", "portal-v1.css", "metricas.csv", "metricas.json",
        "portal-model.json", "portal-manifest.json", "workbook-pack-parity.json")),
    *(f"FUENTES/source-packs/{kind}/metadata.json" for kind in ("blank", "synthetic")),
    *(f"FUENTES/source-packs/{kind}/{relation}.csv"
      for kind in ("blank", "synthetic") for relation in RELATIONS),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def safe_name(name: str) -> bool:
    if (not name or "\\" in name or ":" in name or name.startswith("/") or
            name.endswith("/") or "//" in name):
        return False
    parts = name.split("/")
    if any(p in ("", ".", "..") or p.rstrip(" .") != p for p in parts):
        return False
    return not any(p.split(".")[0].casefold() in
                   {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                    *(f"lpt{i}" for i in range(1, 10))} for p in parts)


def _kind(name: str) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "SYNTHETIC" if "synthetic" in name.lower() else "BLANK"
    media = {".md": "text/markdown", ".html": "text/html", ".css": "text/css",
             ".json": "application/json", ".csv": "text/csv", ".txt": "text/plain",
             ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
             ".jpeg": "image/jpeg", ".gif": "image/gif", ".ttf": "font/ttf",
             ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2"}
    if suffix not in media and name != "LICENSE":
        raise ValueError(f"unclassified release member: {name}")
    lowered = name.lower()
    classification = ("BLANK" if "/blank/" in lowered else
                      "SYNTHETIC" if ("synthetic" in lowered or "ejemplo" in lowered or
                                      name.startswith("PORTAL/")) else "PUBLIC")
    return media.get(suffix, "text/plain"), classification


def make_manifest(files: dict[str, bytes], *, version: str = VERSION,
                  license_sha256: str | None = None,
                  third_party: dict[str, dict[str, str]] | None = None,
                  sources: dict[str, str] | None = None) -> dict[str, Any]:
    if MANIFEST in files or "LICENSE" not in files:
        raise ValueError("manifest is self-referential or LICENSE absent")
    if any(not safe_name(name) for name in files):
        raise ValueError("unsafe payload name")
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("case-insensitive duplicate payload")
    if license_sha256 is not None and sha(files["LICENSE"]) != license_sha256:
        raise ValueError("LICENSE differs from selected ref")
    third_party = third_party or {}
    if third_party and OPTIONAL_NOTICE not in files:
        raise ValueError("third-party bytes require notice")
    if OPTIONAL_NOTICE in files and not third_party:
        raise ValueError("unclassified third-party notice")
    for name, item in third_party.items():
        if name not in files or any(not item.get(key) for key in ("name", "version", "source", "license")):
            raise ValueError("incomplete third-party inventory")
    entries = {}
    for name, data in sorted(files.items()):
        media, classification = _kind(name)
        entries[name] = {"sha256": sha(data), "size": len(data), "media_type": media,
                         "source": (sources or {}).get(name, name),
                         "classification": classification,
                         "purpose": "offline client material" if name != "LICENSE" else "license and redistribution terms"}
        if name in third_party:
            entries[name]["third_party"] = third_party[name]
    return {"schema": "alma-release-manifest-v1", "version": version,
            "manifest_self_hash_excluded": True, "license_sha256": sha(files["LICENSE"]),
            "third_party_bundled": bool(third_party), "entries": entries}


def write_zip(output: Path, files: dict[str, bytes]) -> None:
    if any(not safe_name(name) for name in files) or len({n.casefold() for n in files}) != len(files):
        raise ValueError("unsafe or duplicate ZIP member")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stored entries avoid platform zlib differences; the two committed XLSX
    # files are already compressed. A fixed method is part of the format.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED,
                         strict_timestamps=True) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_STORED)


def write_checksum(output: Path, checksum: Path) -> None:
    checksum.parent.mkdir(parents=True, exist_ok=True)
    checksum.write_text(f"{sha(output.read_bytes())}  {output.name}\n", encoding="ascii", newline="\n")


def _source_bytes(root: Path, relative: str) -> bytes:
    path = root / relative
    if (not path.is_file() or not path.resolve().is_relative_to(root.resolve()) or
            any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent)):
        raise ValueError(f"missing or linked release source: {relative}")
    return path.read_bytes()


def collect_payload(root: Path, *, python: str = sys.executable) -> tuple[dict[str, bytes], dict[str, str]]:
    """Collect only explicit direct files plus the Phase 4 builder's fixed kit inventory."""
    files: dict[str, bytes] = {}
    sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="alma-v1-client-") as scratch:
        kit = Path(scratch) / "client.zip"
        subprocess.run([python, "scripts/package_client_v1.py", "--output", str(kit)],
                       cwd=root, check=True, stdout=subprocess.DEVNULL, timeout=600)
        with zipfile.ZipFile(kit) as archive:
            if set(archive.namelist()) != CLIENT_FILES:
                raise ValueError("Phase 4 client kit inventory changed")
            for name in sorted(CLIENT_FILES):
                if name in ("FUENTES/operating-v1-blank.xlsx", "FUENTES/operating-v1-synthetic.xlsx",
                            "FUENTES/workbook-manifest.json", "PACKAGE-MANIFEST.json"):
                    continue
                if not safe_name(name):
                    raise ValueError("unsafe Phase 4 member")
                files[name] = archive.read(name)
                sources[name] = f"generated:package_client_v1:{name}"
    for name, relative in DIRECT_FILES.items():
        files[name] = _source_bytes(root, relative)
        sources[name] = relative
    # The existing guide links point to the Phase 4 package manifest. Recompute
    # it over the reviewed workbook replacements so the guide remains navigable.
    phase4 = {"version": "alma-client-kit-v1", "status": "PASS",
              "members": {name: {"sha256": sha(data), "bytes": len(data)} for name, data in sorted(files.items())
                          if name not in ("LICENSE", "acceptance-summary.json", "RUNBOOK-v1.md",
                                          "ACCEPTANCE-v1.md", "RELEASE-v1.md")},
              "manifest_self_hash_excluded": True}
    files["PACKAGE-MANIFEST.json"] = canonical(phase4)
    sources["PACKAGE-MANIFEST.json"] = "generated:package_client_v1:normalized"
    notice_path = root / OPTIONAL_NOTICE
    if notice_path.is_file():
        files[OPTIONAL_NOTICE] = _source_bytes(root, OPTIONAL_NOTICE)
        sources[OPTIONAL_NOTICE] = OPTIONAL_NOTICE
    book = json.loads(files["FUENTES/workbook-manifest.json"])
    if (sha(files["FUENTES/operating-v1-blank.xlsx"]) != book["workbooks"]["blank"]["sha256"] or
            sha(files["FUENTES/operating-v1-synthetic.xlsx"]) != book["workbooks"]["synthetic"]["sha256"]):
        raise ValueError("delivered workbook differs from committed manifest")
    excel = json.loads(_source_bytes(root, "evidence/v1.0/excel/excel-recalculation.json"))
    actual = {item.get("sha256") for item in excel["workbooks"]}
    if not {book["workbooks"]["blank"]["sha256"], book["workbooks"]["synthetic"]["sha256"]} <= actual:
        raise ValueError("delivered workbook differs from Excel receipt")
    return files, sources


def archived_root(ref: str, destination: Path) -> str:
    commit = subprocess.check_output(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(["git", "archive", "--format=tar", commit], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for item in archive.getmembers():
            if item.issym() or item.islnk() or not safe_name(item.name.rstrip("/")):
                raise ValueError("unsafe tagged source")
        archive.extractall(destination, filter="data")
    return commit


def create_manifest(root: Path, destination: Path) -> dict[str, Any]:
    files, sources = collect_payload(root)
    acceptance = json.loads(files["acceptance-summary.json"])
    if acceptance.get("version") != VERSION or acceptance.get("third_party_bundled") is not False:
        raise ValueError("third-party disposition requires complete inventory")
    manifest = make_manifest(files, sources=sources, license_sha256=sha(files["LICENSE"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical(manifest))
    return manifest


def build(ref: str, output: Path, checksum: Path, *, acceptance: Path | None = None,
          ci_sidecar: Path | None = None) -> dict[str, Any]:
    if any(path.exists() or path.is_symlink() for path in (output, checksum, *([acceptance] if acceptance else []))):
        raise ValueError("release output already exists")
    with tempfile.TemporaryDirectory(prefix="alma-release-ref-") as scratch:
        root = Path(scratch)
        commit = archived_root(ref, root)
        files, sources = collect_payload(root)
        expected = _source_bytes(root, "client/v1/release-manifest.json")
        manifest = make_manifest(files, sources=sources, license_sha256=sha(files["LICENSE"]))
        if canonical(manifest) != expected:
            raise ValueError("committed release manifest differs from selected ref payload")
        files[MANIFEST] = expected
        write_zip(output, files)
        write_checksum(output, checksum)
        from scripts.audit_release_v1 import audit_preflight
        audit_preflight(output, checksum, manifest, VERSION,
                        expected_license_sha256=sha(files["LICENSE"]))
        result = {"status": "PASS", "commit": commit, "zip_sha256": sha(output.read_bytes()),
                  "manifest_sha256": sha(expected), "license_sha256": sha(files["LICENSE"])}
        if acceptance is not None:
            if ref != "v1.0.0" or ci_sidecar is None:
                raise ValueError("release requires exact tag and CI sidecar")
            ci = json.loads(ci_sidecar.read_bytes())
            if ci.get("proof_sha") != commit or ci.get("run", {}).get("head_sha") != commit:
                raise ValueError("same-SHA CI proof absent")
            final = ci.get("release_preflight", {})
            if final.get("commands") != list(RELEASE_COMMANDS):
                raise ValueError("four-command final CI proof absent")
            receipts = final.get("receipts", {})
            if set(receipts) != {"windows-latest", "ubuntu-latest"}:
                raise ValueError("both final CI preflight receipts required")
            for platform, row in receipts.items():
                stored = ci_sidecar.parent / "downloads" / commit / platform / "release-v1-preflight.json"
                if not stored.is_file() or row.get("sha256") != sha(stored.read_bytes()):
                    raise ValueError(f"downloaded final CI receipt changed or absent: {platform}")
                downloaded_receipt = json.loads(stored.read_bytes())
                if any(row.get(key) != downloaded_receipt.get(key) for key in (
                        "headSha", "commands", "zipSha256", "checksumSha256",
                        "manifestSha256", "licenseSha256", "privacy", "links",
                        "release_publication_executed")):
                    raise ValueError(f"downloaded final CI receipt fields changed: {platform}")
                if (row.get("headSha") != commit or row.get("commands") != list(RELEASE_COMMANDS) or
                        row.get("zipSha256") != result["zip_sha256"] or
                        row.get("checksumSha256") != sha(checksum.read_bytes()) or
                        row.get("manifestSha256") != result["manifest_sha256"] or
                        row.get("licenseSha256") != result["license_sha256"] or
                        row.get("privacy") != "PASS" or row.get("links") != "PASS" or
                        row.get("release_publication_executed") is not False or not row.get("sha256")):
                    raise ValueError(f"final CI preflight mismatch: {platform}")
            sidecar = {"schema": "alma-release-acceptance-v1", "tag": ref, "commit": commit,
                       "zip_sha256": result["zip_sha256"], "checksum_sha256": sha(checksum.read_bytes()),
                       "manifest_sha256": result["manifest_sha256"],
                       "license_sha256": result["license_sha256"],
                       "ci_sidecar_sha256": sha(ci_sidecar.read_bytes()),
                       "release_preflight": final,
                       "evidence_sha256": {
                           name: sha(_source_bytes(root, name)) for name in (
                               "evidence/v1.0/regression-acceptance.json",
                               "evidence/v1.0/two-week-native.json",
                               "evidence/v1.0/excel/excel-recalculation.json",
                               "evidence/v1.0/excel/visual-inspection.json")},
                       "release_publication_executed": False}
            acceptance.parent.mkdir(parents=True, exist_ok=True)
            acceptance.write_bytes(canonical(sidecar))
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    generated = sub.add_parser("generate-manifest")
    generated.add_argument("--source-root", type=Path, default=ROOT)
    generated.add_argument("--output", type=Path, required=True)
    for mode in ("preflight", "release"):
        part = sub.add_parser(mode)
        part.add_argument("--ref", required=True)
        part.add_argument("--output", required=True, type=Path)
        part.add_argument("--checksum", required=True, type=Path)
        if mode == "release":
            part.add_argument("--acceptance", required=True, type=Path)
            part.add_argument("--ci-sidecar", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "generate-manifest":
            manifest = create_manifest(args.source_root, args.output)
            result = {"status": "PASS", "manifest_sha256": sha(canonical(manifest)),
                      "member_count": len(manifest["entries"]) + 1}
        else:
            result = build(args.ref, args.output, args.checksum,
                           acceptance=getattr(args, "acceptance", None), ci_sidecar=getattr(args, "ci_sidecar", None))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
