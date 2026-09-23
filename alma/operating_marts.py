"""Verify and atomically publish one private, read-only Phase 2 mart bundle."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from alma.operating_contracts import SOURCE_NAMES, canonical_json
from alma.operating_cost_inventory import (
    project_cost, project_inventory, project_purchases, realized_economics,
)
from alma.operating_finance_marts import (
    FINANCE_DEFINITIONS, project_budgets, project_cash, project_obligations,
)
from alma.operating_learning_exceptions import (
    LEARNING_DEFINITIONS, project_exceptions, project_learning,
    sales_readiness_projection, validate_sales_row,
)
from alma.operating_mart_contracts import (
    MetricDefinition, MetricRow, Policy, bind_cut, load_policy,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / ".local" / "operating-marts"
_MAX = (1 << 63) - 1

COST_DEFINITIONS = {
    "complete_landed_cost_cents": MetricDefinition(
        "complete_landed_cost_cents", "v1", "sum eligible distinct cost components and allocations",
        "MXN_CENTS", "sku_id x cost_version_id", "as_of",
        ("cost_versions", "cost_components", "cost_allocations"),
        "UNKNOWN unless all required components and allocation evidence are complete",
        "component and allocation cents reconcile exactly", "finance", "price_review"),
    "available_units": MetricDefinition(
        "available_units", "v1", "on hand - non-sellable - active reserved",
        "UNITS", "sku_id", "as_of",
        ("inventory_movements", "inventory_counts", "inventory_reservations", "loans", "purchase_receipts"),
        "UNKNOWN on count or custody variance", "physical movements and accepted receipts reconcile",
        "inventory", "replenishment_review"),
    "purchase_remaining_units": MetricDefinition(
        "purchase_remaining_units", "v1", "ordered - received for noncancelled purchase",
        "UNITS", "purchase_order_id", "as_of", ("purchase_orders", "purchase_receipts"),
        "PARTIAL when purchase or receipt coverage incomplete", "distinct receipts <= ordered",
        "purchasing", "delivery_review"),
    "realized_contribution_cents": MetricDefinition(
        "realized_contribution_cents", "v1", "net revenue - unit COGS - variable cost",
        "MXN_CENTS", "sku_id x channel_code", "[start,end)",
        ("sales_aggregates", "cost_versions", "cost_components", "cost_allocations"),
        "UNKNOWN without complete dated cost and sales coverage", "same grain and policy basis",
        "finance", "unit_economics_review"),
}


def _private_root(output_root: str | Path, configured: str | Path | None) -> Path:
    """Reject redirection before making any output directory."""
    root = Path(configured) if configured is not None else PRIVATE_ROOT
    target = Path(output_root)
    if root.name != "operating-marts" or root.parent.name != ".local":
        raise ValueError("private root must be .local/operating-marts")
    for path in (root, target):
        if ".." in path.parts:
            raise ValueError("output path traversal")
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
                raise ValueError("symlink or junction output path")
    resolved_root = root.resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    if resolved_target != resolved_root:
        raise ValueError("output outside configured private root")
    return resolved_root


def _definitions() -> dict[str, MetricDefinition]:
    definitions: dict[str, MetricDefinition] = {}
    for family in (COST_DEFINITIONS, FINANCE_DEFINITIONS, LEARNING_DEFINITIONS):
        for metric_id, definition in family.items():
            if metric_id in definitions or metric_id != definition.id:
                raise ValueError("duplicate or mismatched metric definition")
            definitions[metric_id] = definition
    return definitions


def _metric(
    metric_id: str, cut_id: str, as_of: str, dimensions: dict[str, str], value: int | None,
    status: str, sources: tuple[str, ...], source_refs: tuple[str, ...], reconciliation_id: str,
    policy: Policy | None = None,
) -> MetricRow:
    return MetricRow(metric_id, cut_id, as_of, dimensions, value if value is not None else None,
                     1 if value is not None else None, value, status, sources, source_refs,
                     reconciliation_id, policy.version if policy else None,
                     policy.sha256 if policy else None, policy.status if policy else None)


def _collect(cut: Any, as_of: str, policy: Policy) -> tuple[dict[str, Any], list[MetricRow]]:
    start = cut.coverage["sales_aggregates"]["window_start"]
    end = (date.fromisoformat(as_of) + timedelta(days=1)).isoformat()
    skus = [row[0] for row in cut.connection.execute("SELECT sku_id FROM sku_catalog ORDER BY sku_id")]
    channels = [row[0] for row in cut.connection.execute(
        "SELECT DISTINCT channel_code FROM sales_aggregates ORDER BY channel_code")]
    cost_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    economic_rows: list[dict[str, Any]] = []
    learning_rows: list[dict[str, Any]] = []
    metrics: list[MetricRow] = []
    for sku in skus:
        cost = project_cost(cut, sku, as_of, policy)
        cost_rows.append({"sku_id": sku, **cost})
        metrics.append(_metric("complete_landed_cost_cents", cut.cut_id, as_of,
            {"sku_id": sku, "cost_version_id": cost.get("cost_version_id") or "UNKNOWN"},
            cost.get("complete_cost_cents"), cost["status"],
            COST_DEFINITIONS["complete_landed_cost_cents"].sources,
            tuple(cost.get("source_refs", ())), f"cost:{cut.cut_id}:{sku}:{as_of}", policy))
        inventory = project_inventory(cut, sku, as_of)
        inventory_rows.append(inventory)
        metrics.append(_metric("available_units", cut.cut_id, as_of, {"sku_id": sku},
            inventory["available_units"], inventory["status"],
            COST_DEFINITIONS["available_units"].sources,
            tuple(inventory["source_refs"]), inventory["reconciliation_id"]))
        learning = project_learning(cut, sku, start, end, policy)
        learning_rows.append(learning)
        metrics.extend(learning["metric_rows"])
        for channel in channels:
            economics = realized_economics(cut, sku, channel, start, end, policy)
            economic_rows.append({"sku_id": sku, "channel_code": channel, **economics})
            metrics.append(_metric("realized_contribution_cents", cut.cut_id, as_of,
                {"sku_id": sku, "channel_code": channel, "window_start": start, "window_end": end},
                economics["contribution_cents"], economics["status"],
                COST_DEFINITIONS["realized_contribution_cents"].sources,
                tuple(economics["source_refs"]), economics["reconciliation_id"], policy))
    purchases = project_purchases(cut, as_of)
    for purchase in purchases:
        metrics.append(_metric("purchase_remaining_units", cut.cut_id, as_of,
            {"purchase_order_id": purchase["purchase_order_id"]},
            purchase["still_to_receive_units"], purchase["status"],
            COST_DEFINITIONS["purchase_remaining_units"].sources,
            tuple(purchase["source_refs"]), purchase["reconciliation_id"]))
    obligations = project_obligations(cut, as_of)
    for obligation in obligations:
        metrics.append(obligation["metric_row"])
        value = obligation["authoritative_outstanding_cents"]
        metrics.append(_metric("authoritative_outstanding_cents", cut.cut_id, as_of,
            {"obligation_id": obligation["obligation_id"]}, value,
            "UNKNOWN" if value is None else obligation["status"],
            FINANCE_DEFINITIONS["authoritative_outstanding_cents"].sources,
            tuple(obligation["source_refs"]), obligation["reconciliation_id"] + ":authoritative"))
    cash = project_cash(cut, as_of, policy)
    metrics.append(cash["metric_row"])
    for horizon, details in cash["horizons"].items():
        for layer, value in details.items():
            if layer not in {"committed_cents", "planned_cents", "scenario_cents", "undated_cents"}:
                continue
            metrics.append(_metric("cash_layer_cents", cut.cut_id, as_of,
                {"scenario_id": cash["scenario_id"], "horizon": str(horizon), "layer": layer},
                value, "ESTIMATED" if value is not None else "UNKNOWN",
                FINANCE_DEFINITIONS["cash_layer_cents"].sources,
                tuple(cash["source_refs"]), f"cash-layer:{cut.cut_id}:{horizon}:{layer}:{as_of}", policy))
    budgets = project_budgets(cut, as_of, policy)
    metrics.extend(row["metric_row"] for row in budgets["targets"])
    exceptions = project_exceptions(cut, as_of, policy)
    sales = sales_readiness_projection(cut, exceptions, policy)
    for row in sales:
        validate_sales_row(row)
    families = {"cost": cost_rows, "inventory": inventory_rows, "purchases": purchases,
                "economics": economic_rows, "obligations": obligations, "cash": cash,
                "budgets": budgets, "learning": learning_rows, "exceptions": exceptions,
                "sales_readiness": sales}
    return families, metrics


def _validate(cut: Any, policy: Policy, definitions: dict[str, MetricDefinition],
              metrics: list[MetricRow]) -> None:
    if not metrics or set(definitions) != {row.metric_id for row in metrics}:
        raise ValueError("metric registry and emitted rows differ")
    reconciliations: set[str] = set()
    for row in metrics:
        definition = definitions[row.metric_id]
        if row.cut_id != cut.cut_id or row.reconciliation_id in reconciliations:
            raise ValueError("metric cut or reconciliation identity mismatch")
        reconciliations.add(row.reconciliation_id)
        if not row.coverage_refs or set(row.coverage_refs) - set(definition.sources):
            raise ValueError("metric coverage sources mismatch definition")
        if set(row.coverage_refs) - set(cut.coverage):
            raise ValueError("metric coverage missing from cut")
        if row.policy_sha256 is not None and (row.policy_sha256 != policy.sha256 or
              row.policy_version != policy.version or row.policy_status != policy.status):
            raise ValueError("metric policy binding mismatch")
        for amount in (row.numerator, row.denominator, row.value):
            if isinstance(amount, int) and (amount < -_MAX - 1 or amount > _MAX):
                raise ValueError("metric integer overflow")
        if row.status == "MEASURED" and row.value is None:
            raise ValueError("measured metric without value")


def _controls(metrics: list[MetricRow], exceptions: list[dict[str, Any]]) -> dict[str, Any]:
    families = {"cost_inventory": COST_DEFINITIONS, "finance": FINANCE_DEFINITIONS,
                "learning": LEARNING_DEFINITIONS}
    result: dict[str, Any] = {}
    for family, definitions in families.items():
        selected = [row for row in metrics if row.metric_id in definitions]
        if not selected:
            raise ValueError("empty metric family")
        counts: dict[str, int] = {}
        for row in selected:
            counts[row.status] = counts.get(row.status, 0) + 1
        result[family] = {"metric_count": len(selected), "status_counts": counts,
                          "reconciliation_ids": sorted(row.reconciliation_id for row in selected)}
    result["exceptions"] = {"exception_count": len(exceptions),
                            "reconciliation_ids": sorted(row["reconciliation_id"] for row in exceptions)}
    return result


def _csv_metric_rows(rows: list[MetricRow]) -> bytes:
    stream = io.StringIO(newline="")
    fields = ("metric_id", "cut_id", "as_of", "dimensions", "numerator", "denominator",
              "value", "status", "reconciliation_id")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        record = asdict(row)
        writer.writerow({field: json.dumps(record[field], sort_keys=True, ensure_ascii=False)
                         if field == "dimensions" else record[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def build_operating_marts(
    cut_path: str | Path, output_root: str | Path, *, policy_path: str | Path,
    private_root: str | Path | None = None,
) -> dict[str, Any]:
    """Verify inputs and all families, then publish a complete immutable private bundle."""
    root = _private_root(output_root, private_root)
    with bind_cut(cut_path) as cut:
        as_of = cut.cutoff_at[:10]
        policy = load_policy(policy_path, as_of=as_of,
                             real_cut=cut.input_class != "SYNTHETIC_EXAMPLE")
        definitions = _definitions()
        families, metrics = _collect(cut, as_of, policy)
        _validate(cut, policy, definitions, metrics)
        controls = _controls(metrics, families["exceptions"])
        registry = {name: asdict(definition) for name, definition in sorted(definitions.items())}
        contract_hash = hashlib.sha256(canonical_json(registry)).hexdigest()
        cut_id = cut.cut_id
        lineage = {"cut_id": cut_id, "cutoff_at": cut.cutoff_at,
                   "input_class": cut.input_class, "source_sha256": cut.source_hashes,
                   "coverage": cut.coverage, "policy_version": policy.version,
                   "policy_sha256": policy.sha256, "policy_status": policy.status,
                   "metric_contract_sha256": contract_hash,
                   "decision_status": "REVIEW" if cut.input_class != "SYNTHETIC_EXAMPLE" and
                      not policy.authorizes_real_cut else "SYNTHETIC_EXAMPLE" if
                      cut.input_class == "SYNTHETIC_EXAMPLE" else "APPROVED"}
        artifacts = {"registry.json": canonical_json(registry),
                     "metric_rows.json": canonical_json([asdict(row) for row in metrics]),
                     "metric_rows.csv": _csv_metric_rows(metrics),
                     "controls.json": canonical_json(controls),
                     "families.json": canonical_json(_plain(families)),
                     "exceptions.json": canonical_json(families["exceptions"]),
                     "sales_readiness.json": canonical_json(families["sales_readiness"]),
                     "lineage.json": canonical_json(lineage)}
        destination = root / cut_id / contract_hash
        if destination.exists() or destination.is_symlink():
            raise ValueError("operating mart bundle already exists")
        artifact_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}
        manifest = {"cut_id": cut_id, "policy_version": policy.version,
                    "policy_sha256": policy.sha256, "policy_status": policy.status,
                    "metric_contract_sha256": contract_hash,
                    "source_sha256": cut.source_hashes, "coverage": cut.coverage,
                    "artifacts": sorted(artifacts), "artifact_sha256": artifact_hashes,
                    "decision_status": lineage["decision_status"]}
        # Recheck the path immediately before staging, including newly introduced links.
        if _private_root(output_root, private_root) != root:
            raise ValueError("private output root changed")
        root.mkdir(parents=True, exist_ok=True)
        cut_root = root / cut_id
        if cut_root.exists() and (cut_root.is_symlink() or
                                  (hasattr(cut_root, "is_junction") and cut_root.is_junction())):
            raise ValueError("cut output redirected")
        cut_root.mkdir(exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=cut_root))
        try:
            for name, data in artifacts.items():
                (stage / name).write_bytes(data)
                if hashlib.sha256((stage / name).read_bytes()).hexdigest() != artifact_hashes[name]:
                    raise ValueError("staged artifact hash mismatch")
            (stage / "manifest.json").write_bytes(canonical_json(manifest))
            if destination.exists() or destination.is_symlink():
                raise ValueError("operating mart bundle already exists")
            os.replace(stage, destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    return {"destination": str(destination), "cut_id": cut_id,
            "metric_contract_sha256": contract_hash,
            "policy_sha256": policy.sha256, "metric_count": len(metrics)}
