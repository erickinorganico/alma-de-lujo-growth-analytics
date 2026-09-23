"""Learning, exception, and private publication oracles for operating marts."""
from __future__ import annotations

import tempfile
import unittest
import json
import shutil
import hashlib
import csv
from pathlib import Path
from unittest.mock import patch

from alma.operating_mart_contracts import bind_cut, load_policy
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


def _csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


class LearningTests(unittest.TestCase):
    def test_project_learning_mixed_cohort_maturity(self) -> None:
        from alma.operating_learning_exceptions import project_learning

        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            shutil.copytree(PACK, pack)
            metadata_file = pack / "metadata.json"
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            metadata["cutoff_at"] = "2026-10-21T23:59:59-07:00"
            for source in metadata["coverage"]:
                metadata["coverage"][source]["window_end"] = "2026-10-21"
            for source in ("sales_aggregates", "quality_events"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            sales_file = pack / "sales_aggregates.csv"
            fields, sales = _csv_rows(sales_file)
            first = sales[0]
            first.update(delivered_units="10", returned_units="1", restocked_units="1",
                         coverage_status="COMPLETE")
            sales.append(dict(first, sales_date="2026-10-20", delivery_cohort_id="synthetic:cohort-002",
                              delivered_units="90", returned_units="0", restocked_units="0",
                              source_ref="synthetic:source:sales-002"))
            sales.append(dict(first, sales_date="2026-09-02", delivery_cohort_id="synthetic:cohort-foreign",
                              delivered_units="1", returned_units="0", restocked_units="0",
                              source_ref="synthetic:source:sales-foreign"))
            _write_csv(sales_file, fields, sales)
            movement_file = pack / "inventory_movements.csv"
            fields, movements = _csv_rows(movement_file)
            opening = next(row for row in movements if row["movement_type"] == "OPENING")
            opening["units"] = "200"
            old_sale = next(row for row in movements if row["movement_type"] == "SALE_OUT")
            old_sale["units"] = "10"
            for day, units, tag in (("2026-10-20", "90", "recent"),
                                   ("2026-09-02", "1", "foreign")):
                movements.append(dict(old_sale, movement_id=f"synthetic:movement-sale-{tag}",
                    event_date=day, sales_date=day, units=units,
                    source_ref=f"synthetic:source:movement-sale-{tag}"))
            _write_csv(movement_file, fields, movements)
            counts = pack / "inventory_counts.csv"
            counts.write_text(counts.read_text(encoding="utf-8").replace(",24,2,", ",115,2,"), encoding="utf-8")
            quality_file = pack / "quality_events.csv"
            fields, quality = _csv_rows(quality_file)
            quality[0].update(event_type="RETURN_RECEIVED", units="1", event_date="2026-10-01")
            quality.append(dict(quality[0], quality_event_id="synthetic:quality-inspected-cohort",
                                event_type="INSPECTED", units="10", event_date="2026-10-01",
                                source_ref="synthetic:source:quality-inspected-cohort"))
            quality.append(dict(quality[0], quality_event_id="synthetic:quality-rejected-cohort",
                                event_type="REJECTED", units="2", event_date="2026-10-01",
                                source_ref="synthetic:source:quality-rejected-cohort"))
            for kind, units in (("RETURN_RECEIVED", "5"), ("INSPECTED", "100"), ("REJECTED", "100")):
                tag = kind.lower()
                quality.append(dict(quality[0], quality_event_id=f"synthetic:quality-foreign-{tag}",
                    delivery_cohort_id="synthetic:cohort-foreign", event_type=kind, units=units,
                    source_ref=f"synthetic:source:quality-foreign-{tag}"))
            _write_csv(quality_file, fields, quality)
            cut_result = build_operating_workspace(pack, private_root=Path(tmp) / "cuts")
            policy = load_policy(POLICY, as_of="2026-10-21", real_cut=False)
            with bind_cut(cut_result["destination"]) as cut:
                result = project_learning(cut, "synthetic:sku-001", "2026-09-15", "2026-10-22", policy)
                self.assertEqual({"numerator": 1, "denominator": 10, "value": "0.1", "status": "MEASURED"},
                                 result["mature_returns"])
                self.assertEqual("0.2", result["quality_defects"]["value"])
                self.assertEqual("UNKNOWN", next(row for row in result["cohort_rows"]
                    if row["delivery_cohort_id"] == "synthetic:cohort-002")["mature_returns"]["status"])
                self.assertFalse(any(row["delivery_cohort_id"] == "synthetic:cohort-foreign"
                                     for row in result["cohort_rows"]))
                self.assertEqual(4, len(result["excluded_quality_evidence"]))
                self.assertEqual({"UNLINKED", "OUTSIDE_SELECTED_COHORT"},
                    {row["reason"] for row in result["excluded_quality_evidence"]})

    def test_eligible_sell_through_and_mature_cohort_controls(self) -> None:
        from alma.operating_learning_exceptions import sell_through, mature_return_rate, variant_mix

        sold = sell_through(12, 1, 20, 16, coverage="COMPLETE")
        self.assertEqual(11, sold["numerator"])
        self.assertEqual(36, sold["denominator"])
        self.assertEqual("0.3055555556", sold["value"])
        self.assertEqual("NOT_APPLICABLE", sell_through(0, 0, 0, 0, coverage="COMPLETE")["status"])
        early = mature_return_rate(12, 2, cohort_date="2026-09-15", as_of="2026-09-21",
                                   maturity_days=30, linked=True, coverage="COMPLETE")
        self.assertEqual("UNKNOWN", early["status"])
        mature = mature_return_rate(12, 2, cohort_date="2026-09-15", as_of="2026-10-20",
                                    maturity_days=30, linked=True, coverage="COMPLETE")
        self.assertEqual("0.1666666667", mature["value"])
        self.assertEqual("UNKNOWN", mature_return_rate(12, 2, cohort_date="2026-09-15",
            as_of="2026-10-20", maturity_days=30, linked=False, coverage="COMPLETE")["status"])
        self.assertEqual("0.4", variant_mix(4, 10, exposure_comparable=True,
            price_comparable=True, coverage="COMPLETE")["value"])
        self.assertEqual("UNKNOWN", variant_mix(4, 10, exposure_comparable=False,
            price_comparable=True, coverage="COMPLETE")["status"])

    def test_stockout_and_unmet_are_observations_not_preference_or_channel_zero(self) -> None:
        from alma.operating_learning_exceptions import project_learning

        policy = load_policy(POLICY, as_of="2026-09-21", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                learning = project_learning(cut, "synthetic:sku-001", "2026-09-01", "2026-09-22", policy)
                self.assertEqual(12, learning["gross_delivered_units"])
                self.assertEqual(11, learning["net_depleted_units"])
                self.assertEqual(480, learning["exposure"]["stockout_minutes"])
                self.assertEqual("UNKNOWN", learning["preference_status"])
                self.assertEqual("UNKNOWN", learning["sell_through"]["status"])
                self.assertEqual("UNKNOWN", learning["mature_returns"]["status"])
                self.assertEqual(3, learning["recorded_unmet"][0]["requested_units_lower_bound"])
                self.assertFalse(any(row["channel_code"] == "synthetic:wholesale" for row in learning["recorded_unmet"]))


class ExceptionTests(unittest.TestCase):
    def test_actionable_exceptions_and_public_projection(self) -> None:
        from alma.operating_learning_exceptions import project_exceptions, sales_readiness_projection

        policy = load_policy(POLICY, as_of="2026-09-21", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                exceptions = project_exceptions(cut, "2026-09-21", policy)
                categories = {row["category"] for row in exceptions}
                self.assertIn("COST_INCOMPLETE", categories)
                self.assertIn("RECEIPT_UNINSPECTED", categories)
                self.assertIn("QUALITY_HOLD", categories)
                self.assertEqual(len(exceptions), len({row["exception_id"] for row in exceptions}))
                for row in exceptions:
                    self.assertTrue(row["owner_role"])
                    self.assertTrue(row["next_action_code"])
                    self.assertEqual("UNRESOLVED", row["closure_status"])
                public = sales_readiness_projection(cut, exceptions, policy)
                self.assertTrue(all(row["category"] in {"SALES_READINESS", "QUALITY_HOLD", "LOAN_RETURN_DUE"} for row in public))
                self.assertFalse(any("cost" in key.lower() or "recipient" in key.lower()
                                     for row in public for key in row))

    def test_overdue_and_missing_custody_are_distinct(self) -> None:
        from alma.operating_learning_exceptions import loan_issue

        overdue = {"loan_id": "loan-1", "sku_id": "sku-1", "due_date": "2026-09-10",
                   "returned_date": None, "status_code": "OPEN", "borrowed_date": "2026-09-01"}
        self.assertEqual("LOAN_RETURN_DUE", loan_issue(overdue, has_return_movement=False,
            as_of="2026-09-21", grace_days=0))
        self.assertEqual("CUSTODY_EVIDENCE_MISSING", loan_issue(dict(overdue, returned_date="2026-09-20",
            status_code="RETURNED"), has_return_movement=False, as_of="2026-09-21", grace_days=0))

    def test_sales_fields_categories_and_values_are_allowlisted(self) -> None:
        from alma.operating_learning_exceptions import validate_sales_row

        safe = {"category": "SALES_READINESS", "sku_id": "synthetic:sku-001",
                "public_variant": "synthetic:variant-001", "issue_code": "BLOCKED",
                "owner_role": "COMMERCIAL_OWNER", "next_action_code": "RESOLVE_READINESS_BLOCK",
                "due_date": None, "closure_state": "OPEN"}
        validate_sales_row(safe)
        for bad in (dict(safe, cost_cents=100), dict(safe, category="COST_INCOMPLETE"),
                    dict(safe, public_variant="supplier_account_123"),
                    dict(safe, next_action_code="BANK_TRANSFER"),
                    dict(safe, owner_role="person@example.com")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_sales_row(bad)


class BundleTests(unittest.TestCase):
    def test_complete_bundle_registry_lineage_and_two_cut_history(self) -> None:
        from alma.operating_marts import build_operating_marts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / ".local" / "operating-marts"
            cut1 = build_operating_workspace(PACK, private_root=root / "cuts")
            first = build_operating_marts(cut1["destination"], private, policy_path=POLICY,
                                          private_root=private)
            dest1 = Path(first["destination"])
            self.assertTrue(dest1.is_dir())
            manifest = json.loads((dest1 / "manifest.json").read_text(encoding="utf-8"))
            registry = json.loads((dest1 / "registry.json").read_text(encoding="utf-8"))
            metric_rows = json.loads((dest1 / "metric_rows.json").read_text(encoding="utf-8"))
            controls = json.loads((dest1 / "controls.json").read_text(encoding="utf-8"))
            self.assertEqual(set(manifest["artifact_sha256"]), set(manifest["artifacts"]))
            for artifact, digest in manifest["artifact_sha256"].items():
                self.assertEqual(digest, hashlib.sha256((dest1 / artifact).read_bytes()).hexdigest())
            self.assertEqual({row["metric_id"] for row in metric_rows}, set(registry))
            self.assertEqual(len(metric_rows), sum(controls[name]["metric_count"] for name in
                ("cost_inventory", "finance", "learning")))
            self.assertTrue({"recorded_unpaid_cents", "budget_headroom_cents", "sell_through",
                             "stockout_exposure", "available_units"}.issubset(registry))
            self.assertEqual(manifest["policy_sha256"], first["policy_sha256"])
            self.assertEqual(manifest["source_sha256"], json.loads(
                (Path(cut1["destination"]) / "workspace.json").read_text(encoding="utf-8"))["source_sha256"])
            with self.assertRaises(ValueError):
                build_operating_marts(cut1["destination"], private, policy_path=POLICY,
                                      private_root=private)
            pack2 = root / "pack2"
            shutil.copytree(PACK, pack2)
            sku = pack2 / "sku_catalog.csv"
            sku.write_text(sku.read_text(encoding="utf-8").replace(
                "synthetic:source:sku-001", "synthetic:source:sku-002"), encoding="utf-8")
            cut2 = build_operating_workspace(pack2, private_root=root / "cuts")
            second = build_operating_marts(cut2["destination"], private, policy_path=POLICY,
                                           private_root=private)
            self.assertNotEqual(first["cut_id"], second["cut_id"])
            self.assertTrue(dest1.is_dir())
            self.assertTrue(Path(second["destination"]).is_dir())

    def test_bad_policy_tamper_and_unsafe_paths_publish_nothing(self) -> None:
        from alma.operating_marts import build_operating_marts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / ".local" / "operating-marts"
            cut = build_operating_workspace(PACK, private_root=root / "cuts")
            bad_policy = root / "missing.json"
            with self.assertRaises(ValueError):
                build_operating_marts(cut["destination"], private, policy_path=bad_policy,
                                      private_root=private)
            self.assertFalse(private.exists())
            stale = root / "stale.json"
            stale_policy = json.loads(POLICY.read_text(encoding="utf-8"))
            stale_policy["effective_end"] = "2026-09-21"
            from alma.operating_contracts import canonical_json
            stale_policy["sha256"] = hashlib.sha256(canonical_json({
                key: value for key, value in stale_policy.items() if key != "sha256"
            })).hexdigest()
            stale.write_text(json.dumps(stale_policy), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_operating_marts(cut["destination"], private, policy_path=stale,
                                      private_root=private)
            self.assertFalse(private.exists())
            with self.assertRaises(ValueError):
                build_operating_marts(cut["destination"], root / "outside", policy_path=POLICY,
                                      private_root=private)
            self.assertFalse(private.exists())
            with self.assertRaises(ValueError):
                build_operating_marts(cut["destination"], private / ".." / "operating-marts",
                                      policy_path=POLICY, private_root=private)
            self.assertFalse(private.exists())

    def test_registry_and_reconciliation_failure_publish_nothing(self) -> None:
        from alma import operating_marts
        build_operating_marts = operating_marts.build_operating_marts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / ".local" / "operating-marts"
            cut = build_operating_workspace(PACK, private_root=root / "cuts")
            original = operating_marts._definitions
            with patch.object(operating_marts, "_definitions", side_effect=lambda: {
                key: value for key, value in original().items() if key != "sell_through"
            }):
                with self.assertRaises(ValueError):
                    operating_marts.build_operating_marts(cut["destination"], private,
                                                          policy_path=POLICY, private_root=private)
            self.assertFalse(private.exists())
            with patch.object(operating_marts, "project_inventory", side_effect=ValueError("variance")):
                with self.assertRaises(ValueError):
                    operating_marts.build_operating_marts(cut["destination"], private,
                                                          policy_path=POLICY, private_root=private)
            self.assertFalse(private.exists())
            inventory = operating_marts.project_inventory
            with patch.object(operating_marts, "project_inventory", side_effect=lambda *args: {
                **inventory(*args), "status": "INVALID"
            }):
                with self.assertRaises(ValueError):
                    build_operating_marts(cut["destination"], private,
                                          policy_path=POLICY, private_root=private)
            self.assertFalse(private.exists())
            link = root / "link"
            try:
                link.symlink_to(root, target_is_directory=True)
            except OSError:
                pass  # Windows may deny unprivileged symlink creation.
            else:
                with self.assertRaises(ValueError):
                    build_operating_marts(cut["destination"], link / ".local" / "operating-marts",
                                          policy_path=POLICY, private_root=private)
            self.assertFalse(private.exists())
            source = Path(cut["destination"]) / "sku_catalog.csv"
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                build_operating_marts(cut["destination"], private, policy_path=POLICY,
                                      private_root=private)
            self.assertFalse(private.exists())


if __name__ == "__main__":
    unittest.main()
