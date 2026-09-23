"""Verify, export, and restore immutable private operating-v1 cuts."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .operating_contracts import (
    CONTRACT_VERSION,
    CUT_IDENTITY_FIELDS,
    SOURCE_NAMES,
    OperatingContractError,
    canonical_json,
    columns_for,
    source_contract,
)
from .operating_interchange import MAX_CSV_BYTES, MAX_METADATA_BYTES, parse_pack
from .operating_workspace import DATABASE_FILENAME, MANIFEST_FILENAME, relationship_summary


ROOT = Path(__file__).resolve().parents[1]
MAX_MANIFEST_BYTES = 2_000_000
MAX_DATABASE_BYTES = 512_000_000
MAX_ARCHIVE_BYTES = 512_000_000
MAX_ARCHIVE_TOTAL_BYTES = (len(SOURCE_NAMES) * MAX_CSV_BYTES) + MAX_METADATA_BYTES + MAX_MANIFEST_BYTES + MAX_DATABASE_BYTES
MAX_COMPRESSION_RATIO = 200
EXPECTED_FILES = frozenset(
    {"metadata.json", MANIFEST_FILENAME, DATABASE_FILENAME, *(f"{name}.csv" for name in SOURCE_NAMES)}
)
_MANIFEST_KEYS = frozenset({
    "cut_id",
    "contract_version",
    "input_class",
    "cutoff_at",
    "timezone",
    "currency",
    "coverage",
    "quality_status",
    "source_sha256",
    "metadata_sha256",
    "normalized_rows_digest",
    "sqlite_sha256",
    "row_counts",
    "key_counts",
    "cash_evidence_status",
    "cohort_link_status",
    "relationship_check",
    "database",
})


def _fail(code: str, location: str) -> None:
    raise OperatingContractError(code, location)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _private_root(private_root: str | Path | None, *, create: bool = False) -> Path:
    root = Path(private_root) if private_root is not None else ROOT / ".local"
    if root.is_symlink():
        _fail("path.symlink", "private_root")
    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OperatingContractError("path.private_root", "private_root") from exc
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise OperatingContractError("path.private_root", "private_root") from exc
    if not resolved.is_dir():
        _fail("path.private_root", "private_root")
    return resolved


def _private_existing(path: str | Path, root: Path, location: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        _fail("path.symlink", location)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise OperatingContractError("path.missing", location) from exc
    if not _inside(resolved, root):
        _fail("path.private_root", location)
    return resolved


def _read_canonical_json(path: Path, *, maximum: int, code: str) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size > maximum:
            _fail(f"{code}_size", path.name)
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatingContractError(code, path.name) from exc
    if not isinstance(value, dict):
        _fail(code, path.name)
    if raw != canonical_json(value) + b"\n":
        _fail(f"{code}_canonical", path.name)
    return value


def _cut_id(parsed: dict[str, Any]) -> str:
    metadata = parsed["metadata"]
    identity = {
        field: (parsed["source_sha256"] if field == "source_sha256" else metadata[field])
        for field in CUT_IDENTITY_FIELDS
    }
    return hashlib.sha256(canonical_json(identity)).hexdigest()


def _database_rows(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    connection.row_factory = sqlite3.Row
    for source in SOURCE_NAMES:
        columns = columns_for(source)
        projection = ",".join(f'"{column}"' for column in columns)
        order = ",".join(f'"{column}"' for column in source_contract(source)["primary_key"])
        rows[source] = [dict(row) for row in connection.execute(
            f'SELECT {projection} FROM "{source}" ORDER BY {order}'
        )]
    return rows


def _parsed_database_rows(parsed: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for source in SOURCE_NAMES:
        columns = columns_for(source)
        primary_key = source_contract(source)["primary_key"]
        rows = [
            {
                column: value.isoformat() if hasattr(value, "isoformat") else value
                for column, value in ((column, row[column]) for column in columns)
            }
            for row in parsed["tables"][source]
        ]
        normalized[source] = sorted(rows, key=lambda row: tuple(row[column] for column in primary_key))
    return normalized


def _schema_check(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    tables = {
        row["name"]: row
        for row in connection.execute("PRAGMA table_list")
        if row["type"] == "table" and not row["name"].startswith("sqlite_")
    }
    if set(tables) != set(SOURCE_NAMES) or any(row["strict"] != 1 for row in tables.values()):
        _fail("verify.schema", "operating.sqlite3")
    for source in SOURCE_NAMES:
        columns = tuple(row["name"] for row in connection.execute(f'PRAGMA table_info("{source}")'))
        if columns != columns_for(source):
            _fail("verify.schema", f"operating.sqlite3:{source}")


def _copy_pack_for_parse(cut: Path, root: Path) -> tuple[Path, dict[str, Any]]:
    stage = Path(tempfile.mkdtemp(prefix=".verify-pack-", dir=root))
    try:
        for name in ["metadata.json", *(f"{source}.csv" for source in SOURCE_NAMES)]:
            shutil.copyfile(cut / name, stage / name)
        return stage, parse_pack(stage, private_root=root)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _cash_evidence_status(parsed: dict[str, Any]) -> str:
    statuses = {row["evidence_status"] for row in parsed["tables"]["cash_balance_evidence"]}
    if not statuses:
        return "MISSING"
    return next(iter(statuses)) if len(statuses) == 1 else "MIXED"


def verify_cut(path: str | Path, *, private_root: str | Path | None = None) -> dict[str, Any]:
    """Verify one accepted cut against its raw sources, database, and manifest."""

    root = _private_root(private_root)
    cut = _private_existing(path, root, "cut")
    if not cut.is_dir():
        _fail("path.directory", "cut")
    children = list(cut.iterdir())
    if {child.name for child in children} != EXPECTED_FILES or any(not child.is_file() for child in children):
        _fail("verify.files", "cut")
    if any(child.is_symlink() for child in children):
        _fail("path.symlink", "cut")

    manifest = _read_canonical_json(cut / MANIFEST_FILENAME, maximum=MAX_MANIFEST_BYTES, code="verify.manifest")
    if frozenset(manifest) != _MANIFEST_KEYS:
        _fail("verify.manifest_keys", MANIFEST_FILENAME)
    metadata_digest = hashlib.sha256((cut / "metadata.json").read_bytes()).hexdigest()
    if manifest.get("metadata_sha256") != metadata_digest:
        _fail("verify.metadata_hash", "metadata.json")
    source_digests = {
        f"{source}.csv": hashlib.sha256((cut / f"{source}.csv").read_bytes()).hexdigest()
        for source in SOURCE_NAMES
    }
    if manifest.get("source_sha256") != source_digests:
        _fail("verify.source_hash", "sources")
    stage, parsed = _copy_pack_for_parse(cut, root)
    try:
        if manifest.get("metadata_sha256") != parsed["metadata_sha256"]:
            _fail("verify.metadata_hash", "metadata.json")
        if manifest.get("source_sha256") != parsed["source_sha256"]:
            _fail("verify.source_hash", "sources")
        if manifest.get("normalized_rows_digest") != parsed["normalized_rows_digest"]:
            _fail("verify.normalized_rows", "sources")
        cut_id = _cut_id(parsed)
        if manifest.get("cut_id") != cut_id:
            _fail("verify.cut_id", MANIFEST_FILENAME)
        metadata = parsed["metadata"]
        for field in ("contract_version", "input_class", "cutoff_at", "timezone", "currency", "coverage"):
            if manifest.get(field) != metadata[field]:
                _fail("verify.manifest_metadata", field)
        if manifest.get("contract_version") != CONTRACT_VERSION or manifest.get("quality_status") != "PASS":
            _fail("verify.manifest_status", MANIFEST_FILENAME)
        if manifest.get("database") != DATABASE_FILENAME:
            _fail("verify.database_name", MANIFEST_FILENAME)

        database = cut / DATABASE_FILENAME
        if database.stat().st_size > MAX_DATABASE_BYTES:
            _fail("verify.sqlite_size", DATABASE_FILENAME)
        sqlite_digest = hashlib.sha256(database.read_bytes()).hexdigest()
        if manifest.get("sqlite_sha256") != sqlite_digest:
            _fail("verify.sqlite_hash", DATABASE_FILENAME)
        try:
            connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise OperatingContractError("verify.sqlite_open", DATABASE_FILENAME) from exc
        try:
            connection.execute("PRAGMA query_only=ON")
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                _fail("verify.sqlite_integrity", DATABASE_FILENAME)
            _schema_check(connection)
            foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
            if foreign_keys:
                _fail("verify.foreign_key", DATABASE_FILENAME)
            if canonical_json(_database_rows(connection)) != canonical_json(_parsed_database_rows(parsed)):
                _fail("verify.database_rows", DATABASE_FILENAME)
            relationships = relationship_summary(connection)
        except sqlite3.Error as exc:
            raise OperatingContractError("verify.sqlite", DATABASE_FILENAME) from exc
        finally:
            connection.close()

        if manifest.get("row_counts") != relationships["row_counts"]:
            _fail("verify.row_counts", MANIFEST_FILENAME)
        if manifest.get("key_counts") != relationships["key_counts"]:
            _fail("verify.key_counts", MANIFEST_FILENAME)
        relationship_check = manifest.get("relationship_check")
        if not isinstance(relationship_check, dict) or set(relationship_check) != {"status", "digest", "foreign_key_violations"}:
            _fail("verify.relationship", MANIFEST_FILENAME)
        if relationship_check != {
            "status": "PASS",
            "digest": relationships["digest"],
            "foreign_key_violations": [],
        }:
            _fail("verify.relationship", MANIFEST_FILENAME)
        cohorts = relationships["cohort_links"]
        cohort_status = "PASS" if cohorts["return_event_count"] == cohorts["linked_return_event_count"] else "PARTIAL"
        if manifest.get("cohort_link_status") != cohort_status:
            _fail("verify.cohort", MANIFEST_FILENAME)
        if manifest.get("cash_evidence_status") != _cash_evidence_status(parsed):
            _fail("verify.cash_evidence", MANIFEST_FILENAME)
        return {
            "status": "PASS",
            "cut_id": cut_id,
            "checked_files": len(EXPECTED_FILES),
            "issues": [],
        }
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _archive_member(name: str, data: bytes) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def export_cut(
    path: str | Path,
    output: str | Path,
    *,
    private_root: str | Path | None = None,
) -> dict[str, Any]:
    """Verify and write a deterministic ZIP below the private export root."""

    root = _private_root(private_root, create=True)
    cut = _private_existing(path, root, "cut")
    verification = verify_cut(cut, private_root=root)
    exports = root / "operating-exports"
    if exports.exists() and (exports.is_symlink() or not exports.is_dir()):
        _fail("path.symlink", "operating-exports")
    output_path = Path(output)
    try:
        proposed_parent = output_path.parent.resolve(strict=True)
    except OSError:
        proposed_parent = output_path.parent
    if proposed_parent != exports or output_path.name in {"", ".", ".."} or output_path.suffix.lower() != ".zip":
        _fail("path.private_root", "output")
    if output_path.exists() or output_path.is_symlink():
        _fail("archive.exists", "output")
    exports_preexisting = exports.exists()
    try:
        exports.mkdir(exist_ok=True)
    except OSError as exc:
        raise OperatingContractError("archive.output", "output") from exc

    fd, temporary_name = tempfile.mkstemp(prefix=".export-", suffix=".zip", dir=exports)
    os.close(fd)
    temporary = Path(temporary_name)
    published = False
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=False) as archive:
            for name in sorted(EXPECTED_FILES):
                data = (cut / name).read_bytes()
                archive.writestr(_archive_member(name, data), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            _fail("archive.size", "output")
        os.replace(temporary, output_path)
        published = True
        return {
            "status": "PASS",
            "cut_id": verification["cut_id"],
            "archive": str(output_path.resolve(strict=True)),
            "members": len(EXPECTED_FILES),
            "archive_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        }
    except OSError as exc:
        raise OperatingContractError("archive.output", "output") from exc
    finally:
        if not published and temporary.exists():
            temporary.unlink()
        if not published and not exports_preexisting and exports.exists() and not any(exports.iterdir()):
            exports.rmdir()


__all__ = [
    "EXPECTED_FILES",
    "MAX_ARCHIVE_BYTES",
    "MAX_ARCHIVE_TOTAL_BYTES",
    "MAX_COMPRESSION_RATIO",
    "export_cut",
    "verify_cut",
]
