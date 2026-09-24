"""Atomic private SQLite workspace builder for validated operating-v1 packs."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .operating_contracts import CUT_IDENTITY_FIELDS, SOURCE_NAMES, OperatingContractError, canonical_json, columns_for, source_contract
from .operating_interchange import parse_pack


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "models" / "operating_v1.sql"
DATABASE_FILENAME = "operating.sqlite3"
MANIFEST_FILENAME = "workspace.json"
INSERT_ORDER = (
    "sku_catalog",
    "sales_aggregates",
    "availability_daily",
    "unmet_demand",
    "inventory_counts",
    "inventory_reservations",
    "cost_versions",
    "cost_components",
    "cost_allocations",
    "budgets",
    "purchase_orders",
    "purchase_receipts",
    "expenses",
    "obligations",
    "obligation_payments",
    "quality_events",
    "sales_readiness",
    "loans",
    "inventory_movements",
    "cash_balance_evidence",
    "cash_events",
    "budget_allocations",
)


def _fail(code: str, location: str) -> None:
    raise OperatingContractError(code, location)


def _database_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _quote_identifier(value: str) -> str:
    if value not in SOURCE_NAMES:
        _fail("workspace.table", "database")
    return '"' + value + '"'


def _cut_id(parsed: dict[str, Any]) -> str:
    metadata = parsed["metadata"]
    identity = {
        field: (parsed["source_sha256"] if field == "source_sha256" else metadata[field])
        for field in CUT_IDENTITY_FIELDS
    }
    return hashlib.sha256(canonical_json(identity)).hexdigest()


def _key_count(connection: sqlite3.Connection, source: str) -> int:
    contract = source_contract(source)
    columns = contract["primary_key"]
    if len(columns) == 1:
        expression = f'COUNT(DISTINCT "{columns[0]}")'
    else:
        # Parser rejects duplicates, so the row count is the exact composite-key count.
        expression = "COUNT(*)"
    return int(connection.execute(f"SELECT {expression} FROM {_quote_identifier(source)}").fetchone()[0])


def relationship_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    """Return deterministic relationship evidence and its canonical digest."""

    connection.row_factory = sqlite3.Row
    row_counts = {
        source: int(connection.execute(f"SELECT COUNT(*) FROM {_quote_identifier(source)}").fetchone()[0])
        for source in SOURCE_NAMES
    }
    key_counts = {source: _key_count(connection, source) for source in SOURCE_NAMES}
    foreign_key_violations = [dict(row) for row in connection.execute("PRAGMA foreign_key_check")]
    cash_rows = [dict(row) for row in connection.execute(
        "SELECT event_id,economic_event_id,supersedes_event_id,scenario_id,level,direction,currency,obligation_id,payment_id "
        "FROM cash_events ORDER BY scenario_id,economic_event_id,event_id"
    )]
    predecessor_ids = {row["supersedes_event_id"] for row in cash_rows if row["supersedes_event_id"] is not None}
    cash = {
        "economic_identities": sorted({
            f'{row["scenario_id"]}:{row["economic_event_id"]}' for row in cash_rows
        }),
        "supersession_edges": sorted(
            [[row["supersedes_event_id"], row["event_id"]] for row in cash_rows if row["supersedes_event_id"] is not None]
        ),
        "active_leaf_ids": sorted(row["event_id"] for row in cash_rows if row["event_id"] not in predecessor_ids),
        "origin_bindings": [
            {
                "event_id": row["event_id"],
                "obligation_id": row["obligation_id"],
                "payment_id": row["payment_id"],
            }
            for row in cash_rows
        ],
    }
    cohort_rows = [dict(row) for row in connection.execute(
        "SELECT quality_event_id,event_type,delivery_cohort_id FROM quality_events ORDER BY quality_event_id"
    )]
    return_events = [row for row in cohort_rows if row["event_type"].startswith("RETURN_")]
    cohort_links = {
        "return_event_count": len(return_events),
        "linked_return_event_count": sum(row["delivery_cohort_id"] is not None for row in return_events),
        "linked_quality_event_ids": sorted(row["quality_event_id"] for row in return_events if row["delivery_cohort_id"] is not None),
    }
    origin_bindings = [dict(row) for row in connection.execute(
        "SELECT 'obligation' AS relation,obligation_id AS relation_id,origin_type,origin_id "
        "FROM obligations UNION ALL "
        "SELECT 'budget_allocation',budget_allocation_id,origin_type,origin_id FROM budget_allocations "
        "ORDER BY relation,relation_id"
    )]
    content = {
        "row_counts": row_counts,
        "key_counts": key_counts,
        "foreign_key_violations": foreign_key_violations,
        "cash": cash,
        "cohort_links": cohort_links,
        "origin_bindings": origin_bindings,
    }
    return {**content, "digest": hashlib.sha256(canonical_json(content)).hexdigest()}


def _create_database(parsed: dict[str, Any], path: Path) -> dict[str, Any]:
    if sqlite3.sqlite_version_info < (3, 37, 0):
        _fail("sqlite.version", "database")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.execute("BEGIN")
        connection.execute("PRAGMA defer_foreign_keys = ON")
        for source in INSERT_ORDER:
            columns = columns_for(source)
            quoted_columns = ",".join(f'"{column}"' for column in columns)
            marks = ",".join("?" for _ in columns)
            values = [
                tuple(_database_value(row[column]) for column in columns)
                for row in parsed["tables"][source]
            ]
            if values:
                connection.executemany(
                    f"INSERT INTO {_quote_identifier(source)} ({quoted_columns}) VALUES ({marks})",
                    values,
                )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            _fail("sqlite.integrity", "database")
        summary = relationship_summary(connection)
        if summary["foreign_key_violations"]:
            _fail("sqlite.foreign_key", "database")
        connection.execute("VACUUM")
        return summary
    except sqlite3.Error as exc:
        connection.rollback()
        raise OperatingContractError("sqlite.constraint", "database") from exc
    finally:
        connection.close()


def _copy_sources(pack: Path, stage: Path, parsed: dict[str, Any]) -> None:
    metadata_source = pack / "metadata.json"
    metadata_target = stage / "metadata.json"
    shutil.copyfile(metadata_source, metadata_target)
    if hashlib.sha256(metadata_target.read_bytes()).hexdigest() != parsed["metadata_sha256"]:
        _fail("workspace.source_changed", "metadata.json")
    for source in SOURCE_NAMES:
        filename = f"{source}.csv"
        target = stage / filename
        shutil.copyfile(pack / filename, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != parsed["source_sha256"][filename]:
            _fail("workspace.source_changed", filename)


def _cash_evidence_status(parsed: dict[str, Any]) -> str:
    statuses = {row["evidence_status"] for row in parsed["tables"]["cash_balance_evidence"]}
    if not statuses:
        return "MISSING"
    if len(statuses) == 1:
        return next(iter(statuses))
    return "MIXED"


def _cohort_link_status(summary: dict[str, Any]) -> str:
    cohorts = summary["cohort_links"]
    return "PASS" if cohorts["return_event_count"] == cohorts["linked_return_event_count"] else "PARTIAL"


def build_operating_workspace(
    pack_path: str | Path,
    *,
    private_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate, stage, and atomically publish one immutable private cut."""

    parsed = parse_pack(pack_path, private_root=private_root)
    pack = Path(pack_path).resolve(strict=True)
    cut_id = _cut_id(parsed)
    root = Path(private_root) if private_root is not None else ROOT / ".local"
    if root.exists() and root.is_symlink():
        _fail("path.symlink", "private_root")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OperatingContractError("workspace.private_root", "private_root") from exc
    root = root.resolve(strict=True)
    cuts = root / "operating-cuts"
    if cuts.exists() and (cuts.is_symlink() or not cuts.is_dir()):
        _fail("path.symlink", "operating-cuts")
    cuts_preexisting = cuts.exists()
    destination = cuts / cut_id
    if destination.exists():
        _fail("workspace.exists", "destination")

    stage = Path(tempfile.mkdtemp(prefix=f".staging-{cut_id[:12]}-", dir=root))
    published = False
    try:
        _copy_sources(pack, stage, parsed)
        database_path = stage / DATABASE_FILENAME
        relationships = _create_database(parsed, database_path)
        sqlite_sha256 = hashlib.sha256(database_path.read_bytes()).hexdigest()
        manifest = {
            "cut_id": cut_id,
            "contract_version": parsed["metadata"]["contract_version"],
            "input_class": parsed["metadata"]["input_class"],
            "cutoff_at": parsed["metadata"]["cutoff_at"],
            "timezone": parsed["metadata"]["timezone"],
            "currency": parsed["metadata"]["currency"],
            "coverage": parsed["metadata"]["coverage"],
            "quality_status": "PASS",
            "source_sha256": parsed["source_sha256"],
            "metadata_sha256": parsed["metadata_sha256"],
            "normalized_rows_digest": parsed["normalized_rows_digest"],
            "sqlite_sha256": sqlite_sha256,
            "row_counts": relationships["row_counts"],
            "key_counts": relationships["key_counts"],
            "cash_evidence_status": _cash_evidence_status(parsed),
            "cohort_link_status": _cohort_link_status(relationships),
            "relationship_check": {
                "status": "PASS",
                "digest": relationships["digest"],
                "foreign_key_violations": relationships["foreign_key_violations"],
            },
            "database": DATABASE_FILENAME,
        }
        (stage / MANIFEST_FILENAME).write_bytes(canonical_json(manifest) + b"\n")
        cuts.mkdir(exist_ok=True)
        try:
            os.replace(stage, destination)
        except OSError as exc:
            raise OperatingContractError("workspace.publish", "destination") from exc
        published = True
        return {
            "status": "PASS",
            "cut_id": cut_id,
            "destination": str(destination),
            "manifest": manifest,
        }
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage)
        if not published and not cuts_preexisting and cuts.exists() and not any(cuts.iterdir()):
            cuts.rmdir()


__all__ = [
    "DATABASE_FILENAME",
    "INSERT_ORDER",
    "MANIFEST_FILENAME",
    "build_operating_workspace",
    "relationship_summary",
]
