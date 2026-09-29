"""Private, immutable inventory control over the canonical operating-v1 ledger."""
from __future__ import annotations

import csv
import hashlib
import html
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from alma.operating_contracts import canonical_json
from alma.operating_cost_inventory import project_inventory, project_purchases
from alma.operating_interchange import parse_pack
from alma.operating_mart_contracts import bind_cut
from alma.operating_workbook import export_workbook_to_pack
from alma.operating_workspace import _cut_id, build_operating_workspace


VERSION = "inventory-control-v1"
CSV_FIELDS = (
    "sku_id", "product_code", "variant_code", "category_code", "color_code",
    "size_code", "lifecycle_status", "as_of", "position_status",
    "on_hand_units", "sellable_on_hand_units", "reserved_units", "available_units",
    "recorded_in_transit_units", "open_purchase_units", "transit_variance_units",
    "inspection_units", "non_sellable_units", "loaned_units", "last_count_date",
    "count_age_days", "count_variance_units", "observed_net_outflow_30d",
    "sales_coverage", "priority", "action",
)


class InventoryControlError(ValueError):
    """The inventory control contract was rejected before publication."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _check_path(path: Path, *, recursive: bool = False) -> None:
    if ".." in path.parts:
        raise InventoryControlError("paths with '..' are not accepted")
    if _is_link(path) or any(_is_link(parent) for parent in path.parents if parent.exists()):
        raise InventoryControlError("linked paths are not accepted")
    if recursive and path.is_dir() and any(_is_link(item) for item in path.rglob("*")):
        raise InventoryControlError("linked source members are not accepted")


def _output_root(value: str | Path) -> Path:
    candidate = Path(value)
    if tuple(part.lower() for part in candidate.parts[-2:]) != (".local", "inventory-runs"):
        raise InventoryControlError("output root must end in .local/inventory-runs")
    _check_path(candidate)
    return candidate.resolve(strict=False)


def _copy_pack(source: Path, destination: Path) -> Path:
    _check_path(source, recursive=True)
    if not source.is_dir():
        raise InventoryControlError("source pack must be a directory or an .xlsx workbook")
    shutil.copytree(source, destination)
    return destination


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json(value) + b"\n")


def _window_coverage(cut: Any, source: str, start: str, end: str, has_rows: bool) -> str:
    declared = cut.coverage[source]
    if declared["status"] in {"MISSING", "NOT_APPLICABLE"}:
        return declared["status"]
    if (declared["window_start"] is not None and declared["window_end"] is not None
            and declared["window_start"] <= start and declared["window_end"] >= end):
        return declared["status"]
    return "PARTIAL" if has_rows else "MISSING"


def _action(stock: dict[str, Any], count: dict[str, Any] | None,
            open_purchase_units: int, count_max_age_days: int) -> tuple[str, str]:
    if count is None:
        return "BLOCKED", "COUNT_REQUIRED"
    if stock["count_variance_units"] not in {None, 0}:
        return "BLOCKED", "RECONCILE_COUNT"
    age = (date.fromisoformat(stock["as_of"]) - date.fromisoformat(count["cutoff_date"])).days
    if age > count_max_age_days:
        return "REVIEW", "COUNT_DUE"
    if stock["available_units"] is None:
        return "BLOCKED", "REVIEW_COVERAGE"
    if stock["available_units"] == 0:
        return "HIGH", "STOCKOUT_REVIEW"
    if count["in_transit_units"] != open_purchase_units:
        return "REVIEW", "RECONCILE_TRANSIT"
    if stock["status"] in {"PARTIAL", "UNKNOWN"}:
        return "REVIEW", "REVIEW_COVERAGE"
    return "OK", "MONITOR"


def _rows_for_cut(cut: Any, as_of: str, count_max_age_days: int) -> list[dict[str, Any]]:
    sku_rows = [dict(row) for row in cut.connection.execute(
        "SELECT * FROM sku_catalog WHERE effective_date<=? ORDER BY sku_id", (as_of,)
    )]
    latest_counts: dict[str, dict[str, Any]] = {}
    for raw in cut.connection.execute(
            "SELECT * FROM inventory_counts WHERE cutoff_date<=? "
            "ORDER BY sku_id,cutoff_date DESC,count_id", (as_of,)):
        row = dict(raw)
        latest_counts.setdefault(row["sku_id"], row)

    purchases: dict[str, int] = defaultdict(int)
    for purchase in project_purchases(cut, as_of):
        purchases[purchase["sku_id"]] += purchase["still_to_receive_units"]

    start = (date.fromisoformat(as_of) - timedelta(days=29)).isoformat()
    observed: dict[str, dict[str, int]] = {}
    for raw in cut.connection.execute(
            "SELECT sku_id,SUM(delivered_units) delivered,SUM(restocked_units) restocked "
            "FROM sales_aggregates WHERE sales_date>=? AND sales_date<=? GROUP BY sku_id",
            (start, as_of)):
        observed[raw["sku_id"]] = dict(raw)
    sales_coverage = _window_coverage(cut, "sales_aggregates", start, as_of, bool(observed))

    result = []
    for sku in sku_rows:
        stock = project_inventory(cut, sku["sku_id"], as_of)
        count = latest_counts.get(sku["sku_id"])
        open_purchase_units = purchases[sku["sku_id"]]
        priority, action = _action(stock, count, open_purchase_units, count_max_age_days)
        sales = observed.get(sku["sku_id"])
        count_age = None if count is None else (
            date.fromisoformat(as_of) - date.fromisoformat(count["cutoff_date"])
        ).days
        recorded_transit = None if count is None else count["in_transit_units"]
        result.append({
            "sku_id": sku["sku_id"],
            "product_code": sku["product_code"],
            "variant_code": sku["variant_code"],
            "category_code": sku["category_code"],
            "color_code": sku["color_code"],
            "size_code": sku["size_code"],
            "lifecycle_status": sku["lifecycle_status"],
            "as_of": as_of,
            "position_status": stock["status"],
            "on_hand_units": stock["on_hand_units"],
            "sellable_on_hand_units": stock["sellable_on_hand_units"],
            "reserved_units": stock["reserved_units"],
            "available_units": stock["available_units"],
            "recorded_in_transit_units": recorded_transit,
            "open_purchase_units": open_purchase_units,
            "transit_variance_units": None if recorded_transit is None else recorded_transit - open_purchase_units,
            "inspection_units": stock["inspection_units"],
            "non_sellable_units": stock["non_sellable_units"],
            "loaned_units": stock["loaned_units"],
            "last_count_date": None if count is None else count["cutoff_date"],
            "count_age_days": count_age,
            "count_variance_units": stock["count_variance_units"],
            "observed_net_outflow_30d": None if sales is None else sales["delivered"] - sales["restocked"],
            "sales_coverage": sales_coverage,
            "priority": priority,
            "action": action,
        })
    return result


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    priorities = Counter(row["priority"] for row in rows)
    actions = Counter(row["action"] for row in rows)
    if not rows or priorities["BLOCKED"]:
        status = "BLOCKED"
    elif sum(value for key, value in priorities.items() if key != "OK"):
        status = "REVIEW"
    else:
        status = "PASS"
    known_available = [row["available_units"] for row in rows if row["available_units"] is not None]
    return {
        "status": status,
        "sku_count": len(rows),
        "known_available_units": sum(known_available),
        "unknown_available_skus": len(rows) - len(known_available),
        "priority_counts": {key: priorities.get(key, 0) for key in ("BLOCKED", "HIGH", "REVIEW", "OK")},
        "action_counts": dict(sorted(actions.items())),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _display(value: Any) -> str:
    return "—" if value is None else html.escape(str(value))


def _write_html(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    body_rows = []
    for row in report["inventory"]:
        body_rows.append("<tr>" + "".join((
            f'<td><strong>{_display(row["variant_code"])}</strong><small>{_display(row["color_code"])} · {_display(row["size_code"])}</small></td>',
            f'<td class="num">{_display(row["on_hand_units"])}</td>',
            f'<td class="num">{_display(row["reserved_units"])}</td>',
            f'<td class="num emphasis">{_display(row["available_units"])}</td>',
            f'<td class="num">{_display(row["recorded_in_transit_units"])}</td>',
            f'<td class="num">{_display(row["inspection_units"])}</td>',
            f'<td>{_display(row["last_count_date"])}<small>{_display(row["count_age_days"])} días</small></td>',
            f'<td class="num">{_display(row["count_variance_units"])}</td>',
            f'<td><span class="pill {row["priority"].lower()}">{_display(row["priority"])}</span><small>{_display(row["action"])}</small></td>',
        )) + "</tr>")
    css = """
    :root{--ink:#18211b;--muted:#68746c;--paper:#f4f1e9;--card:#fffdf7;--line:#d9d5c9;--green:#1f6b4f;--gold:#a86f18;--red:#a13d32}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Inter,Segoe UI,sans-serif}.wrap{max-width:1380px;margin:auto;padding:42px 28px}header{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:28px}h1{font:700 42px/1.05 Georgia,serif;margin:0 0 8px}.eyebrow{color:var(--green);font-weight:800;letter-spacing:.12em;text-transform:uppercase;font-size:12px}.muted,small{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}.card b{display:block;font:700 30px/1 Georgia,serif;margin-top:8px}.tablebox{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:14px}table{border-collapse:collapse;width:100%;min-width:1050px}th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:left;color:var(--muted);background:#ebe7dc;position:sticky;top:0}th,td{padding:13px 12px;border-bottom:1px solid var(--line)}td small{display:block;font-size:11px}.num{text-align:right;font-variant-numeric:tabular-nums}.emphasis{font-weight:800}.pill{display:inline-block;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:800}.blocked{background:#f8deda;color:var(--red)}.high,.review{background:#f6e8c8;color:#744b0d}.ok{background:#dceee5;color:var(--green)}.note{margin-top:20px;border-left:4px solid var(--gold);padding:10px 14px;background:#fff7e7}@media(max-width:800px){.cards{grid-template-columns:1fr 1fr}header{display:block}h1{font-size:34px}}@media print{body{background:white}.wrap{padding:10px}.tablebox{overflow:visible}th{position:static}}
    """
    document = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Control de inventario · Alma de Lujo</title><style>{css}</style></head><body><main class="wrap"><header><div><div class="eyebrow">Alma OS · control operativo</div><h1>Inventario conciliado</h1><div class="muted">Corte {html.escape(report['as_of'])} · estado {html.escape(summary['status'])} · {summary['sku_count']} SKU</div></div><div class="muted">Cut ID<br><code>{html.escape(report['cut_id'][:16])}…</code></div></header><section class="cards"><div class="card">Unidades disponibles conocidas<b>{summary['known_available_units']}</b></div><div class="card">SKU bloqueados<b>{summary['priority_counts']['BLOCKED']}</b></div><div class="card">Atención alta<b>{summary['priority_counts']['HIGH']}</b></div><div class="card">SKU por revisar<b>{summary['priority_counts']['REVIEW']}</b></div></section><section class="tablebox"><table><thead><tr><th>Variante</th><th class="num">Físico</th><th class="num">Reservado</th><th class="num">Disponible</th><th class="num">Tránsito</th><th class="num">Inspección</th><th>Último conteo</th><th class="num">Variación</th><th>Acción</th></tr></thead><tbody>{''.join(body_rows)}</tbody></table></section><aside class="note"><strong>Límite de decisión:</strong> este control detecta diferencias y prioridades. No crea ajustes, órdenes de compra ni promesas de venta. La salida de 30 días es observada y conserva su cobertura; no se usa como regla automática de reabasto.</aside></main></body></html>"""
    path.write_text(document, encoding="utf-8")


def create_inventory_run(source: str | Path, output_root: str | Path,
                         *, count_max_age_days: int = 7) -> dict[str, Any]:
    """Create one immutable local control report from a workbook or source pack."""
    if not isinstance(count_max_age_days, int) or count_max_age_days < 0:
        raise InventoryControlError("count maximum age must be a nonnegative integer")
    root = _output_root(output_root)
    source_path = Path(source)
    _check_path(source_path, recursive=source_path.is_dir())
    source_path = source_path.resolve(strict=True)
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".inventory-prepare-", dir=root))
    published = False
    try:
        input_dir = stage / "input"
        input_dir.mkdir()
        if source_path.suffix.lower() == ".xlsx":
            copied = input_dir / "source.xlsx"
            shutil.copyfile(source_path, copied)
            exported = export_workbook_to_pack(
                copied, input_dir / "workbook-adapter", private_root=root.parent
            )
            pack = Path(exported["pack_path"])
            input_route = "workbook"
            source_receipt = {
                "workbook_sha256": exported["workbook_sha256"],
                "adapter_manifest_sha256": exported["manifest_sha256"],
            }
        else:
            pack = _copy_pack(source_path, input_dir / "source-pack")
            input_route = "source-pack"
            source_receipt = {}
        parsed = parse_pack(pack, private_root=root.parent)
        cut_id = _cut_id(parsed)
        destination = root / cut_id
        if destination.exists() or destination.is_symlink():
            raise InventoryControlError("inventory cut already exists; use a new source cut")
        built = build_operating_workspace(pack, private_root=stage)
        as_of = parsed["metadata"]["cutoff_at"][:10]
        with bind_cut(built["destination"]) as cut:
            rows = _rows_for_cut(cut, as_of, count_max_age_days)
        summary = _summary(rows)
        report = {
            "version": VERSION,
            "status": summary["status"],
            "cut_id": cut_id,
            "as_of": as_of,
            "timezone": parsed["metadata"]["timezone"],
            "input_class": parsed["metadata"]["input_class"],
            "input_route": input_route,
            "count_max_age_days": count_max_age_days,
            "summary": summary,
            "inventory": rows,
            "controls": {
                "source_of_truth": "operating-v1 canonical ledger",
                "replenishment_proposal": False,
                "automatic_adjustments": False,
                "external_execution": "PROHIBITED",
            },
        }
        _write_csv(stage / "inventory-control.csv", rows)
        _write_json(stage / "inventory-control.json", report)
        _write_html(stage / "inventory-control.html", report)
        receipt = {
            "version": VERSION,
            "status": report["status"],
            "cut_id": cut_id,
            "as_of": as_of,
            "input_class": report["input_class"],
            "input_route": input_route,
            "metadata_sha256": parsed["metadata_sha256"],
            "normalized_rows_digest": parsed["normalized_rows_digest"],
            "source_sha256": parsed["source_sha256"],
            "source_receipt": source_receipt,
            "files": {name: _sha(stage / name) for name in (
                "inventory-control.csv", "inventory-control.json", "inventory-control.html"
            )},
        }
        _write_json(stage / "receipt.json", receipt)
        os.replace(stage, destination)
        published = True
        return {
            "version": VERSION,
            "status": report["status"],
            "cut_id": cut_id,
            "as_of": as_of,
            "run": str(destination),
            "dashboard": str(destination / "inventory-control.html"),
            "csv": str(destination / "inventory-control.csv"),
            "receipt": str(destination / "receipt.json"),
            "summary": report["summary"],
            "external_execution": "PROHIBITED",
        }
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage)


__all__ = ["InventoryControlError", "create_inventory_run"]
