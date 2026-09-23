"""Verified, read-only binding from immutable operating-v1 cuts to decision marts."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from alma.operating_contracts import (
    CONTRACT_VERSION, CUT_IDENTITY_FIELDS, SOURCE_NAMES, SOURCES,
    canonical_json, validate_metadata,
)
from alma.operating_workspace import relationship_summary

STATUSES = frozenset({"MEASURED", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE", "ESTIMATED", "ERROR"})
POLICY_STATUSES = frozenset({"REVIEW", "APPROVED", "SYNTHETIC_EXAMPLE"})
# Literal semantic floor: a changed Phase 1 registry cannot silently redefine a mart input.
REQUIRED_SEMANTIC_FIELDS = {
    "sku_catalog": ("sku_id", "effective_date", "lifecycle_status"),
    "sales_aggregates": ("sales_date", "sku_id", "channel_code", "delivery_cohort_id", "delivered_units", "net_revenue_cents", "variable_cost_cents", "coverage_status"),
    "availability_daily": ("availability_date", "sku_id", "observed_minutes", "sellable_minutes", "stockout_minutes", "coverage_status"),
    "unmet_demand": ("demand_event_id", "event_date", "sku_id", "channel_code", "requested_units"),
    "inventory_counts": ("count_id", "sku_id", "cutoff_date", "on_hand_units", "reserved_units", "non_sellable_units"),
    "inventory_movements": ("movement_id", "sku_id", "event_date", "movement_type", "units", "receipt_id", "quality_event_id", "loan_id"),
    "inventory_reservations": ("reservation_event_id", "reservation_id", "sku_id", "event_date", "event_type", "units"),
    "cost_versions": ("cost_version_id", "sku_id", "effective_date", "lifecycle_status", "quantity_basis", "public_price_cents"),
    "cost_components": ("component_id", "cost_version_id", "classification", "amount_cents", "required_flag", "quality_status", "included_in_component_id"),
    "cost_allocations": ("allocation_id", "component_id", "sku_id", "allocated_cents", "remainder_cents"),
    "purchase_orders": ("purchase_order_id", "sku_id", "ordered_units", "order_date", "status_code"),
    "purchase_receipts": ("receipt_id", "purchase_order_id", "received_date", "received_units", "inspection_units", "accepted_units", "rejected_units"),
    "obligations": ("obligation_id", "origin_type", "origin_id", "due_date", "original_cents"),
    "obligation_payments": ("payment_id", "obligation_id", "paid_date", "amount_cents"),
    "cash_events": ("event_id", "economic_event_id", "supersedes_event_id", "scenario_id", "event_date", "level", "amount_cents"),
    "cash_balance_evidence": ("balance_evidence_id", "scenario_id", "period_start", "period_end", "opening_balance_cents", "closing_balance_cents", "evidence_status"),
    "budgets": ("budget_id", "period_start", "period_end", "approved_cents"),
    "budget_allocations": ("budget_allocation_id", "budget_id", "origin_type", "origin_id", "allocated_cents"),
    "expenses": ("expense_id", "incurred_date", "amount_cents", "status_code"),
    "quality_events": ("quality_event_id", "sku_id", "receipt_id", "delivery_cohort_id", "event_date", "event_type", "units"),
    "sales_readiness": ("sku_id", "effective_date", "readiness_status"),
    "loans": ("loan_id", "sku_id", "quantity", "borrowed_date", "due_date", "returned_date", "status_code"),
}
SOURCE_BINDINGS = {
    name: {
        "table": name,
        "primary_key": tuple(contract["primary_key"]),
        "unique": tuple(tuple(fields) for fields in contract["unique"]),
        "fields": {field["name"]: {"type": field["type"], "unit": field["unit"], "nullable": field["nullable"]}
                   for field in contract["fields"]},
    }
    for name, contract in SOURCES.items()
}
if set(REQUIRED_SEMANTIC_FIELDS) != set(SOURCE_BINDINGS) or any(
    set(fields) - set(SOURCE_BINDINGS[name]["fields"])
    for name, fields in REQUIRED_SEMANTIC_FIELDS.items()
):
    raise RuntimeError("Phase 1 semantic fields are incomplete")


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    version: str
    formula: str
    unit: str
    grain: str
    window: str
    sources: tuple[str, ...]
    unknown: str
    guardrail: str
    owner: str
    decision_use: str

    def __post_init__(self) -> None:
        if not all((self.id, self.version, self.formula, self.unit, self.grain, self.window,
                    self.unknown, self.guardrail, self.owner, self.decision_use)):
            raise ValueError("metric definition requires all fields")
        if not self.sources or set(self.sources) - set(SOURCE_NAMES):
            raise ValueError("metric definition has invalid sources")


@dataclass(frozen=True)
class MetricRow:
    metric_id: str
    cut_id: str
    as_of: str
    dimensions: dict[str, str]
    numerator: int | None
    denominator: int | None
    value: int | str | None
    status: str
    coverage_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    reconciliation_id: str
    policy_version: str | None = None
    policy_sha256: str | None = None
    policy_status: str | None = None
    cost_quality: str | None = None

    def __post_init__(self) -> None:
        date.fromisoformat(self.as_of)
        if self.status not in STATUSES:
            raise ValueError("invalid metric status")
        if self.policy_status is not None and self.policy_status not in POLICY_STATUSES:
            raise ValueError("invalid policy status")
        if not self.metric_id or not self.cut_id or not self.reconciliation_id:
            raise ValueError("metric row identity missing")
        if self.status == "UNKNOWN" and self.value is not None:
            raise ValueError("unknown metric has a value")


@dataclass(frozen=True)
class Policy:
    content: dict[str, Any]
    sha256: str

    @property
    def status(self) -> str:
        return self.content["status"]

    @property
    def version(self) -> str:
        return self.content["policy_version"]

    @property
    def authorizes_real_cut(self) -> bool:
        return self.status == "APPROVED" and bool(self.content.get("owner_approval_ref"))


def load_policy(path: str | Path, *, as_of: str, real_cut: bool) -> Policy:
    """Load independently hashed policy; REVIEW is retained without approval."""
    try:
        content = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("policy unavailable or malformed") from exc
    required = {"policy_version", "effective_start", "effective_end", "status", "owner_approval_ref",
                "bases", "thresholds", "maturity_windows", "sha256"}
    if (not isinstance(content, dict) or set(content) != required
            or content["status"] not in POLICY_STATUSES
            or content["policy_version"] != "operating-metrics-policy-v1"):
        raise ValueError("invalid policy shape or status")
    digest = hashlib.sha256(canonical_json({k: v for k, v in content.items() if k != "sha256"})).hexdigest()
    if digest != content["sha256"]:
        raise ValueError("policy hash mismatch")
    measured = date.fromisoformat(as_of)
    if not date.fromisoformat(content["effective_start"]) <= measured < date.fromisoformat(content["effective_end"]):
        raise ValueError("policy stale")
    if content["status"] == "APPROVED" and not content["owner_approval_ref"]:
        raise ValueError("policy approval reference missing")
    if not isinstance(content["bases"], dict) or not isinstance(content["thresholds"], dict) or not isinstance(content["maturity_windows"], dict):
        raise ValueError("invalid policy bases")
    required_bases = {"landed_cost_inclusions", "revenue_basis", "cogs_basis", "variable_cost_basis",
                      "tax_basis", "shipping_basis", "discount_basis", "cash_projection_selection",
                      "cash_floor_basis", "budget_headroom_basis"}
    if (set(content["bases"]) != required_bases
            or not isinstance(content["bases"]["landed_cost_inclusions"], list)
            or not content["bases"]["landed_cost_inclusions"]
            or set(content["bases"]["landed_cost_inclusions"]) - {"DIRECT", "ALLOCATED"}
            or any(not isinstance(content["bases"][name], str) or not content["bases"][name]
                   for name in required_bases - {"landed_cost_inclusions"})
            or any(not isinstance(value, int) or value < 0 for value in content["thresholds"].values())
            or any(not isinstance(value, int) or value < 0 for value in content["maturity_windows"].values())):
        raise ValueError("invalid policy rule values")
    return Policy(content, digest)


class BoundCut:
    def __init__(self, connection: sqlite3.Connection, manifest: dict[str, Any]) -> None:
        self.connection = connection
        self.manifest = manifest
        self.cut_id = manifest["cut_id"]
        self.timezone = manifest["timezone"]
        self.cutoff_at = manifest["cutoff_at"]
        self.coverage = manifest["coverage"]
        self.source_hashes = manifest["source_sha256"]
        self.input_class = manifest["input_class"]

    def __enter__(self) -> "BoundCut":
        return self

    def __exit__(self, *args: object) -> None:
        self.connection.close()

    def coverage_status(self, source: str, as_of: str) -> str:
        entry = self.coverage[source]
        day = date.fromisoformat(as_of)
        if day > datetime.fromisoformat(self.cutoff_at).date():
            raise ValueError("as-of after cut")
        if not date.fromisoformat(entry["window_start"]) <= day <= date.fromisoformat(entry["window_end"]):
            return "MISSING"
        return entry["status"]


def bind_cut(path: str | Path) -> BoundCut:
    """Check all immutable cut bytes and semantic schema before exposing SQL."""
    if sys.version_info < (3, 11) or sqlite3.sqlite_version_info < (3, 37):
        raise RuntimeError("Python 3.11+ and STRICT SQLite required")
    root = Path(path).resolve(strict=True)
    manifest = json.loads((root / "workspace.json").read_text(encoding="utf-8"))
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    validate_metadata(metadata)
    if manifest["contract_version"] != CONTRACT_VERSION or manifest["quality_status"] != "PASS":
        raise ValueError("unsupported or failed cut")
    if any(manifest[key] != metadata[key] for key in ("contract_version", "input_class", "cutoff_at", "timezone", "currency", "coverage")):
        raise ValueError("cut metadata mismatch")
    if set(manifest["source_sha256"]) != {f"{name}.csv" for name in SOURCE_NAMES}:
        raise ValueError("source set mismatch")
    for filename, digest in manifest["source_sha256"].items():
        if hashlib.sha256((root / filename).read_bytes()).hexdigest() != digest:
            raise ValueError("source hash mismatch")
    if hashlib.sha256((root / "metadata.json").read_bytes()).hexdigest() != manifest["metadata_sha256"]:
        raise ValueError("metadata hash mismatch")
    identity = {field: manifest["source_sha256"] if field == "source_sha256" else metadata[field]
                for field in CUT_IDENTITY_FIELDS}
    if hashlib.sha256(canonical_json(identity)).hexdigest() != manifest["cut_id"]:
        raise ValueError("cut id mismatch")
    database = root / "operating.sqlite3"
    if hashlib.sha256(database.read_bytes()).hexdigest() != manifest["sqlite_sha256"]:
        raise ValueError("SQLite hash mismatch")
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        table_rows = {row["name"]: row for row in connection.execute("PRAGMA table_list") if row["type"] == "table" and not row["name"].startswith("sqlite_")}
        if set(table_rows) != set(SOURCE_BINDINGS) or any(row["strict"] != 1 for row in table_rows.values()):
            raise ValueError("missing or non-STRICT relation")
        for name, binding in SOURCE_BINDINGS.items():
            columns = {row["name"]: row for row in connection.execute(f'PRAGMA table_info("{name}")')}
            if set(columns) != set(binding["fields"]):
                raise ValueError(f"column mismatch: {name}")
            for field_name, spec in binding["fields"].items():
                expected_type = "INTEGER" if spec["type"] in {"integer", "nonnegative_integer", "signed_integer"} else "TEXT"
                if columns[field_name]["type"] != expected_type:
                    raise ValueError(f"column type mismatch: {name}.{field_name}")
            primary_key = tuple(row["name"] for row in sorted(columns.values(), key=lambda item: item["pk"]) if row["pk"])
            if primary_key != binding["primary_key"]:
                raise ValueError(f"primary key mismatch: {name}")
            foreign_keys = {(row["from"], row["table"], row["to"]) for row in connection.execute(f'PRAGMA foreign_key_list("{name}")')}
            for field in SOURCES[name]["fields"]:
                target = field["foreign_key"]
                if target is not None and (field["name"], target[0], target[1][0]) not in foreign_keys:
                    raise ValueError(f"foreign key mismatch: {name}.{field['name']}")
        relation = relationship_summary(connection)
        if relation["foreign_key_violations"] or relation["digest"] != manifest["relationship_check"]["digest"]:
            raise ValueError("relationship mismatch")
        if relation["row_counts"] != manifest["row_counts"] or relation["key_counts"] != manifest["key_counts"]:
            raise ValueError("row or key count mismatch")
        return BoundCut(connection, manifest)
    except Exception:
        connection.close()
        raise
