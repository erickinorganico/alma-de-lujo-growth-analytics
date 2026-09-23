"""Disposable synthetic Phase 3 current-cut and native request contract tests."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from alma.operating_workspace import build_operating_workspace
from alma.operating_marts import build_operating_marts
from alma.weekly_cycle import start_cycle, start_cycle_from_source_pack, verify_cycle, cycle_status

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


def upstream(home: Path) -> tuple[Path, Path]:
    cut = build_operating_workspace(PACK, private_root=home / "operating")
    mart_root = home / ".local" / "operating-marts"
    mart = build_operating_marts(cut["destination"], mart_root,
                                 policy_path=POLICY, private_root=mart_root)
    return Path(cut["destination"]), Path(mart["destination"])


class WeeklyCycleEvidenceTests(unittest.TestCase):
    def test_source_pack_and_verified_boundary_share_current_cut(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = start_cycle_from_source_pack(PACK, home / "operating-one",
                home / "first" / ".local" / "operating-marts",
                home / "first" / ".local" / "weekly-cycles")
            cut, mart = upstream(home / "second")
            boundary = start_cycle(cut, mart, home / "second" / ".local" / "weekly-cycles")
            self.assertEqual(source["cut_id"], boundary["cut_id"])
            self.assertEqual(source["current_cut_sha256"], boundary["current_cut_sha256"])
            self.assertEqual("source_pack", source["input_route"])
            self.assertEqual("verified_boundary", boundary["input_route"])
            report = json.loads((Path(source["destination"]) / "current-cut.json").read_text(encoding="utf-8"))
            self.assertEqual(source["cut_id"], report["cut_id"])
            self.assertEqual("SYNTHETIC_EXAMPLE", report["input_class"])
            self.assertTrue(report["synthetic_business_data"])
            self.assertEqual("PASS", report["quality"]["workspace"])
            self.assertIn("sales_aggregates.csv", report["source_sha256"])
            self.assertIn("realized_gross_margin", report["metric_definitions"])
            self.assertTrue(report["metric_rows"])
            self.assertEqual("WAITING_ANALYSTS", verify_cycle(source["destination"])["status"])
            schema = json.loads((ROOT / "contracts" / "weekly-cycle-v1.schema.json").read_text(encoding="utf-8"))
            self.assertTrue({"current_cut", "request", "response", "dispatch_receipt", "packet"}
                            <= set(schema["$defs"]))

    def test_tampered_upstream_bytes_fail_before_request_publication(self) -> None:
        for target in ("source", "manifest", "sqlite", "metric_registry", "mart_manifest"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                cut, mart = upstream(home)
                path = {"source": cut / "sales_aggregates.csv",
                    "manifest": cut / "workspace.json", "sqlite": cut / "operating.sqlite3",
                    "metric_registry": mart / "registry.json", "mart_manifest": mart / "manifest.json"}[target]
                path.write_bytes(path.read_bytes() + b"\n")
                output = home / ".local" / "weekly-cycles"
                with self.assertRaises((ValueError, OSError)):
                    start_cycle(cut, mart, output)
                self.assertFalse(list(output.rglob("*.request.json")) if output.exists() else [])

    def test_nonprivate_path_and_changed_report_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            with self.assertRaises(ValueError):
                start_cycle(cut, mart, home / "public")
            with self.assertRaises(ValueError):
                start_cycle(cut, mart, home / ".local" / ".." / "outside" / "weekly-cycles")
            link = home / "linked"
            try:
                link.symlink_to(home, target_is_directory=True)
            except OSError:
                pass  # Unprivileged Windows configurations may forbid symlinks.
            else:
                with self.assertRaises(ValueError):
                    start_cycle(cut, mart, link / ".local" / "weekly-cycles")
            result = start_cycle(cut, mart, home / ".local" / "weekly-cycles")
            current = Path(result["destination"]) / "current-cut.json"
            current.write_bytes(current.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                verify_cycle(result["destination"])
