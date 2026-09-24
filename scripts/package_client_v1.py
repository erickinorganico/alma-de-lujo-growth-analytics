#!/usr/bin/env python3
"""Build and exhaustively audit the reproducible public Alma OS v1 client kit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alma.operating_contracts import SOURCE_NAMES, SOURCES, canonical_json  # noqa: E402
from alma.operating_marts import _definitions  # noqa: E402
from scripts.build_offline_portal_v1 import build_offline_portal  # noqa: E402
from scripts.build_operating_workbooks import DOMAINS, build_operating_workbooks  # noqa: E402


VERSION = "alma-client-kit-v1"
MANIFEST = "PACKAGE-MANIFEST.json"
WORKBOOK_RECEIPT = ROOT / "evidence" / "v1.0" / "workbooks" / "workbook-pack-parity.json"
PORTAL_RECEIPT = ROOT / "evidence" / "v1.0" / "portal" / "portal-visual-inspection.json"
POLICIES = (
    "operating-metrics-review-template-v1.json",
    "operating-metrics-synthetic-v1.json",
)
PORTAL_FILES = (
    "index.html", "portal-v1.css", "metricas.csv", "metricas.json",
    "portal-model.json", "portal-manifest.json", "workbook-pack-parity.json",
)
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024


class PackageContractError(ValueError):
    """The public ZIP failed an allowlist, integrity, privacy or link check."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _expected_names() -> set[str]:
    names = {
        MANIFEST,
        "INICIO/EMPIEZA_AQUI.md",
        "INICIO/GUIA_SEMANAL.html",
        "FUENTES/operating-v1-blank.xlsx",
        "FUENTES/operating-v1-synthetic.xlsx",
        "FUENTES/workbook-manifest.json",
        "DICCIONARIO/DICCIONARIO-v1.json",
        "EJEMPLO/RECORRIDO-SINTETICO.md",
        *(f"POLITICAS/{name}" for name in POLICIES),
        *(f"PORTAL/{name}" for name in PORTAL_FILES),
    }
    for kind in ("blank", "synthetic"):
        names.add(f"FUENTES/source-packs/{kind}/metadata.json")
        names.update(f"FUENTES/source-packs/{kind}/{relation}.csv"
                     for relation in SOURCE_NAMES)
    return names


def _entry(data: bytes, category: str, *, relation: str | None = None,
           domain: str | None = None) -> dict[str, Any]:
    return {"sha256": _sha(data), "bytes": len(data), "category": category,
            "source_relation": relation, "domain": domain}


def _read_verified_receipt(path: Path, kind: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageContractError(f"{kind} receipt unavailable") from exc
    if value.get("status") != "PASS" or value.get("contains_absolute_paths") is not False:
        raise PackageContractError(f"{kind} receipt is not public-safe PASS")
    if kind == "portal" and (value.get("contains_private_customer_data") is not False or
                              value.get("unexpected_files") != []):
        raise PackageContractError("portal visual receipt is not bounded")
    return value, _sha(raw)


def _dictionary() -> bytes:
    definitions = _definitions()
    value = {
        "version": "operating-dictionary-v1",
        "money_boundary": "integer MXN cents",
        "null_boundary": "blank/null remains unknown; observed zero remains 0",
        "relations": {
            relation: {
                "domain": DOMAINS[relation],
                "grain": SOURCES[relation]["grain"],
                "primary_key": SOURCES[relation]["primary_key"],
                "fields": SOURCES[relation]["fields"],
            }
            for relation in SOURCE_NAMES
        },
        "metrics": {
            name: {
                "formula": item.formula, "unit": item.unit, "grain": item.grain,
                "window": item.window, "sources": list(item.sources),
                "unknown": item.unknown, "guardrail": item.guardrail,
                "owner": item.owner, "decision_use": item.decision_use,
            }
            for name, item in sorted(definitions.items())
        },
    }
    return canonical_json(value) + b"\n"


def _walkthrough() -> bytes:
    return (
        "# Recorrido sintético resuelto\n\n"
        "1. Abre `../FUENTES/operating-v1-synthetic.xlsx` y reconoce la etiqueta sintética.\n"
        "2. Abre `../PORTAL/index.html`; el primer corte es el ejemplo histórico v0.2.\n"
        "3. Revisa `../PORTAL/metricas.csv` y `../PORTAL/metricas.json`: cada valor conserva "
        "unidad, cobertura y hash de fuente.\n"
        "4. Usa las políticas de `../POLITICAS/` sólo en su contexto declarado. La plantilla REVIEW "
        "no es aprobación.\n"
        "5. El recorrido termina en revisión humana informativa. Este ZIP no contiene respuestas "
        "nativas, decisiones del responsable ni ejecución externa.\n"
    ).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _collect(guide_root: Path, work: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]],
                                                    dict[str, str]]:
    workbook_dir = work / "workbooks"
    build_operating_workbooks(workbook_dir)
    portal_dir = work / "portal"
    build_offline_portal(mode="public", output_dir=portal_dir)
    files: dict[str, bytes] = {}
    details: dict[str, dict[str, Any]] = {}

    def add(name: str, path: Path | None, category: str, *, data: bytes | None = None,
            relation: str | None = None, domain: str | None = None) -> None:
        if name in files or name not in _expected_names() or ".." in PurePosixPath(name).parts:
            raise PackageContractError("unexpected package member")
        if path is not None:
            if path.is_symlink() or not path.is_file():
                raise PackageContractError("missing or linked package input")
            body = path.read_bytes()
        elif data is not None:
            body = data
        else:
            raise PackageContractError("package member has no bytes")
        files[name] = body
        details[name] = _entry(body, category, relation=relation, domain=domain)

    add("INICIO/EMPIEZA_AQUI.md", guide_root / "EMPIEZA_AQUI.md", "guide")
    add("INICIO/GUIA_SEMANAL.html", guide_root / "GUIA_SEMANAL.html", "guide")
    for kind in ("blank", "synthetic"):
        add(f"FUENTES/operating-v1-{kind}.xlsx",
            workbook_dir / f"operating-v1-{kind}.xlsx", "workbook", domain="ALL")
        add(f"FUENTES/source-packs/{kind}/metadata.json",
            workbook_dir / "source-packs" / kind / "metadata.json", "source_metadata")
        for relation in SOURCE_NAMES:
            add(f"FUENTES/source-packs/{kind}/{relation}.csv",
                workbook_dir / "source-packs" / kind / f"{relation}.csv", "source_relation",
                relation=relation, domain=DOMAINS[relation])
    add("FUENTES/workbook-manifest.json", workbook_dir / "workbook-manifest.json",
        "source_manifest", domain="ALL")
    for policy in POLICIES:
        add(f"POLITICAS/{policy}", workbook_dir / "policies" / policy, "policy")
    for name in PORTAL_FILES:
        add(f"PORTAL/{name}", portal_dir / name, "public_demo")
    add("DICCIONARIO/DICCIONARIO-v1.json", None, "dictionary", data=_dictionary())
    add("EJEMPLO/RECORRIDO-SINTETICO.md", None, "walkthrough", data=_walkthrough())
    _, workbook_hash = _read_verified_receipt(WORKBOOK_RECEIPT, "workbook")
    _, portal_hash = _read_verified_receipt(PORTAL_RECEIPT, "portal")
    return files, details, {
        "workbook_pack_parity_sha256": workbook_hash,
        "portal_visual_inspection_sha256": portal_hash,
    }


def build_client_kit(output: str | Path, *, guide_root: str | Path | None = None) -> dict[str, Any]:
    """Generate fresh public materials, write deterministic ZIP bytes, then audit them."""
    target = Path(output)
    if target.exists() or target.is_symlink() or ".." in target.parts:
        raise PackageContractError("package output must be a new path")
    guides = Path(guide_root) if guide_root is not None else ROOT / "client" / "v1"
    if guides.is_symlink() or not guides.is_dir():
        raise PackageContractError("guide root unavailable")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alma-client-v1-") as tmp:
        files, details, verification = _collect(guides, Path(tmp))
    if set(files) != _expected_names() - {MANIFEST}:
        raise PackageContractError("package allowlist is incomplete")
    manifest = {
        "version": VERSION,
        "status": "PASS",
        "members": {name: details[name] for name in sorted(details)},
        "verification_inputs": verification,
        "public_boundaries": {
            "synthetic_or_blank_only": True,
            "contains_private_cut": False,
            "contains_native_response": False,
            "contains_analyst_runtime": False,
            "can_execute_private_cut": False,
            "external_business_execution": "PROHIBITED",
        },
        "manifest_self_hash_excluded": True,
    }
    files[MANIFEST] = canonical_json(manifest) + b"\n"
    try:
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9, strict_timestamps=True) as archive:
            for name in sorted(files):
                archive.writestr(_zip_info(name), files[name], compress_type=zipfile.ZIP_DEFLATED,
                                 compresslevel=9)
        audited = audit_client_zip(target)
        return {**audited, "path": str(target), "sha256": _sha(target.read_bytes())}
    except Exception:
        if target.exists():
            target.unlink()
        raise


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (name == path.as_posix() and not path.is_absolute() and ".." not in path.parts
            and not name.startswith(("/", "\\")) and "\\" not in name and ":" not in name)


def _links(name: str, body: str) -> list[str]:
    values = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', body, flags=re.I)
    if name.endswith(".md"):
        values.extend(re.findall(r'\[[^\]]+\]\(([^)]+)\)', body))
    return values


def _resolve_link(member: str, link: str) -> str | None:
    if link.startswith("#"):
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", link, flags=re.I) or link.startswith("//"):
        raise PackageContractError("external package link rejected")
    clean = link.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return None
    base = list(PurePosixPath(member).parent.parts)
    for part in PurePosixPath(clean).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not base:
                raise PackageContractError("package link escapes root")
            base.pop()
        else:
            base.append(part)
    return PurePosixPath(*base).as_posix()


def _audit_xlsx(raw: bytes) -> None:
    with zipfile.ZipFile(__import__("io").BytesIO(raw)) as workbook:
        names = {item.filename.lower() for item in workbook.infolist()}
        if any(token in name for name in names for token in
               ("vbaproject", "externallinks", "comments", "connections")):
            raise PackageContractError("unsafe embedded workbook surface")
        for name in names:
            if name.endswith(".rels") and b'targetmode="external"' in workbook.read(name).lower():
                raise PackageContractError("external workbook relationship")


def _audit_policy(raw: bytes, expected_status: str) -> None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PackageContractError("malformed public policy") from exc
    if (value.get("status") != expected_status or value.get("owner_approval_ref") is not None or
            value.get("sha256") != _sha(canonical_json(
                {key: item for key, item in value.items() if key != "sha256"}))):
        raise PackageContractError("public policy claims invalid authority")


def audit_client_zip(path: str | Path) -> dict[str, Any]:
    """Fail closed over member names, bytes, policies, embedded surfaces and links."""
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise PackageContractError("client ZIP unavailable")
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if (len(names) != len(set(names)) or set(names) != _expected_names() or
                any(not _safe_name(name) for name in names)):
            raise PackageContractError("ZIP member allowlist mismatch")
        if any(info.is_dir() or info.file_size > MAX_MEMBER or
               ((info.external_attr >> 16) & 0o170000) == 0o120000 for info in infos):
            raise PackageContractError("unsafe ZIP member metadata")
        if sum(info.file_size for info in infos) > MAX_TOTAL:
            raise PackageContractError("ZIP size cap exceeded")
        bodies = {name: archive.read(name) for name in names}
    try:
        manifest = json.loads(bodies[MANIFEST])
    except json.JSONDecodeError as exc:
        raise PackageContractError("package manifest malformed") from exc
    expected_members = _expected_names() - {MANIFEST}
    if (manifest.get("version") != VERSION or manifest.get("status") != "PASS" or
            set(manifest.get("members", {})) != expected_members or
            manifest.get("manifest_self_hash_excluded") is not True):
        raise PackageContractError("package manifest inventory mismatch")
    for name in expected_members:
        item = manifest["members"][name]
        if item.get("sha256") != _sha(bodies[name]) or item.get("bytes") != len(bodies[name]):
            raise PackageContractError("package member hash mismatch")
    _, workbook_hash = _read_verified_receipt(WORKBOOK_RECEIPT, "workbook")
    _, portal_hash = _read_verified_receipt(PORTAL_RECEIPT, "portal")
    if manifest.get("verification_inputs") != {
            "workbook_pack_parity_sha256": workbook_hash,
            "portal_visual_inspection_sha256": portal_hash}:
        raise PackageContractError("upstream verification receipt changed")
    boundaries = manifest.get("public_boundaries", {})
    if boundaries != {"synthetic_or_blank_only": True, "contains_private_cut": False,
            "contains_native_response": False, "contains_analyst_runtime": False,
            "can_execute_private_cut": False, "external_business_execution": "PROHIBITED"}:
        raise PackageContractError("public boundary claim changed")
    _audit_policy(bodies[f"POLITICAS/{POLICIES[0]}"], "REVIEW")
    _audit_policy(bodies[f"POLITICAS/{POLICIES[1]}"], "SYNTHETIC_EXAMPLE")
    for name in ("FUENTES/operating-v1-blank.xlsx", "FUENTES/operating-v1-synthetic.xlsx"):
        _audit_xlsx(bodies[name])
    lowered_names = "\n".join(names).lower()
    if any(token in lowered_names for token in (".local/", "current-cut", "decision-packet",
            ".response.json", "query-trace", "dispatch", "owner-decision", ".env", "id_rsa",
            "credential", "secret")):
        raise PackageContractError("private, native or credential-like member rejected")
    for name, raw in bodies.items():
        if not name.endswith((".md", ".html", ".json", ".csv", ".css")):
            continue
        text = raw.decode("utf-8")
        lower = text.lower()
        if any(claim in lower for claim in ("este zip ejecuta un corte privado",
                                             "este zip incluye el runtime",
                                             "este zip contiene el runtime de analistas")):
            raise PackageContractError("analyst runtime claim rejected")
        for link in _links(name, text):
            resolved = _resolve_link(name, link)
            if resolved is not None and resolved not in bodies:
                raise PackageContractError("broken local package link")
    return {"version": VERSION, "status": "PASS", "member_count": len(names),
            "manifest_sha256": _sha(bodies[MANIFEST]), "links": "PASS",
            "privacy": "PASS"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_client_kit(args.output)
    except (PackageContractError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "ERROR", "code": "client_kit_verification_failed",
                          "detail": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
