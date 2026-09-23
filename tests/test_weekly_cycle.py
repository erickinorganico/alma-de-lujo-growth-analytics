"""Disposable synthetic Phase 3 current-cut and native request contract tests."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from alma.operating_workspace import build_operating_workspace
from alma.operating_marts import build_operating_marts
from alma.weekly_cycle import (start_cycle, start_cycle_from_source_pack, verify_cycle,
                               cycle_status, resolve_pointer, record_dispatch,
                               submit_response, resume_cycle, read_terminal_packet)
from alma.native_agents_v1 import validate_request, validate_terminal_packet
from alma.operating_contracts import canonical_json

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


class WeeklyCycleTaskBundleTests(unittest.TestCase):
    def test_source_pack_rerun_reuses_verified_upstream_and_persists_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            operating = home / "operating"
            marts = home / ".local" / "operating-marts"
            cycles = home / ".local" / "weekly-cycles"
            first = start_cycle_from_source_pack(PACK, operating, marts, cycles)
            request = Path(first["destination"]) / "tasks" / "finance_analyst.request.json"
            original = request.read_bytes()
            second = start_cycle_from_source_pack(PACK, operating, marts, cycles)
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(original, request.read_bytes())
            self.assertEqual("source_pack", cycle_status(second["destination"])["input_route"])

    def test_missing_cash_blocks_only_dependent_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pack = home / "pack"
            shutil.copytree(PACK, pack)
            cash = pack / "cash_events.csv"
            cash.write_text(cash.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
            balance = pack / "cash_balance_evidence.csv"
            balance.write_text(balance.read_text(encoding="utf-8").replace(
                ",1100000,", ",2000000,"), encoding="utf-8")
            metadata_path = pack / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["coverage"]["cash_events"] = {"status": "MISSING",
                "window_start": None, "window_end": None}
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            cut = build_operating_workspace(pack, private_root=home / "operating")
            mart_root = home / ".local" / "operating-marts"
            mart = build_operating_marts(cut["destination"], mart_root,
                policy_path=POLICY, private_root=mart_root)
            state = start_cycle(cut["destination"], mart["destination"],
                home / ".local" / "weekly-cycles")
            tasks = Path(state["destination"]) / "tasks"
            finance = json.loads((tasks / "finance_analyst.request.json").read_text(encoding="utf-8"))
            commerce = json.loads((tasks / "commerce_analyst.request.json").read_text(encoding="utf-8"))
            self.assertEqual("BLOCKED_EVIDENCE", finance["evidence_status"])
            self.assertIn("cash_events", finance["blocked_sources"])
            self.assertNotEqual("BLOCKED_EVIDENCE", commerce["evidence_status"])
            self.assertEqual("MISSING", finance["evidence"]["coverage"]["cash_events"]["status"])

    def test_six_role_specific_hash_bound_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            state = start_cycle(cut, mart, home / ".local" / "weekly-cycles")
            directory = Path(state["destination"])
            bundle_raw = (directory / "task-bundle.json").read_bytes()
            bundle = json.loads(bundle_raw)
            self.assertEqual(hashlib.sha256(bundle_raw).hexdigest(), state["task_bundle_sha256"])
            self.assertEqual(6, len(bundle["requests"]))
            role_families = {}
            for role, item in bundle["requests"].items():
                raw = (directory / item["path"]).read_bytes()
                request = json.loads(raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
                self.assertEqual(state["cut_id"], request["cut_id"])
                self.assertEqual(state["current_cut_sha256"], request["current_cut_sha256"])
                self.assertEqual(state["manifest_sha256"], request["manifest_sha256"])
                self.assertEqual(request["evidence_hash"], hashlib.sha256(
                    json.dumps(request["evidence"], ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")).hexdigest())
                self.assertEqual("native-codex-task-bridge", request["execution_mode"])
                self.assertEqual([f"tasks/{role}.response.json", f"tasks/{role}.query-trace.json"],
                                 request["write_scope"])
                self.assertTrue(request["synthetic_business_data"])
                self.assertEqual("terra" if role in {"merchandiser", "finance_analyst"} else
                                 "luna" if role in {"commerce_analyst", "returns_analyst"} else "sol",
                                 request["expected_model_family"])
                self.assertTrue(request["evidence_refs"])
                for pointer in request["evidence_refs"]:
                    resolve_pointer(request["evidence"], pointer)
                role_families[role] = set(request["evidence"]["families"])
            self.assertNotEqual(role_families["merchandiser"], role_families["finance_analyst"])
            self.assertIn("cash", role_families["finance_analyst"])
            self.assertNotIn("cash", role_families["commerce_analyst"])
            self.assertEqual("WAITING_ANALYSTS", cycle_status(directory)["status"])

    def test_idempotent_bytes_and_strict_local_json_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            root = home / ".local" / "weekly-cycles"
            first = start_cycle(cut, mart, root)
            request = Path(first["destination"]) / "tasks" / "finance_analyst.request.json"
            original = request.read_bytes()
            second = start_cycle(cut, mart, root)
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(original, request.read_bytes())
            example = json.loads(original)["evidence"]
            self.assertEqual("ok", resolve_pointer({"a/b": {"~": ["ok"]}}, "/a~1b/~0/0"))
            for pointer in ("https://outside.example/fact", "../../private", "/a~2b", "/a~", "/0x", "/a/01"):
                with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                    resolve_pointer(example, pointer)
            request.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                verify_cycle(first["destination"])


class WeeklyCycleCLITests(unittest.TestCase):
    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "run_weekly_cycle.py"),
            *arguments], text=True, capture_output=True, check=False)

    def test_source_pack_start_status_verify_and_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            args = ("start", "--source-pack", str(PACK), "--operating-root",
                str(home / "operating"), "--mart-root", str(home / ".local" / "operating-marts"),
                "--output-root", str(home / ".local" / "weekly-cycles"))
            first = self._run(*args)
            self.assertEqual(0, first.returncode, first.stderr)
            receipt = json.loads(first.stdout)
            self.assertEqual("WAITING_ANALYSTS", receipt["status"])
            self.assertEqual("source_pack", receipt["input_route"])
            self.assertEqual(6, len(receipt["requests"]))
            self.assertNotIn("source_sha256", receipt)
            self.assertNotIn("metric_rows", receipt)
            for command in ("status", "verify"):
                checked = self._run(command, "--cycle", receipt["destination"])
                self.assertEqual(0, checked.returncode, checked.stderr)
                self.assertEqual(receipt, json.loads(checked.stdout))
            repeated = self._run(*args)
            self.assertEqual(0, repeated.returncode, repeated.stderr)
            self.assertEqual(receipt, json.loads(repeated.stdout))
            request = Path(receipt["requests"]["finance_analyst"])
            request.write_bytes(request.read_bytes() + b"\n")
            damaged = self._run("verify", "--cycle", receipt["destination"])
            self.assertEqual(2, damaged.returncode)
            self.assertEqual("cycle_verification_failed", json.loads(damaged.stderr)["code"])

    def test_prebuilt_route_and_argument_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cut, mart = upstream(home)
            output = home / ".local" / "weekly-cycles"
            started = self._run("start", "--workspace", str(cut), "--mart-bundle",
                str(mart), "--output-root", str(output))
            self.assertEqual(0, started.returncode, started.stderr)
            self.assertEqual("verified_boundary", json.loads(started.stdout)["input_route"])
            for arguments, code in (
                (("start", "--workspace", str(cut), "--output-root", str(output)),
                 "select exactly one route: --source-pack or --workspace with --mart-bundle"),
                (("start", "--source-pack", str(PACK), "--workspace", str(cut),
                  "--mart-bundle", str(mart), "--output-root", str(output)),
                 "select exactly one route: --source-pack or --workspace with --mart-bundle"),
                (("start", "--workbook", "example.xlsx", "--output-root", str(output)),
                 "direct workbook preparation belongs to Phase 4"),
            ):
                with self.subTest(arguments=arguments):
                    rejected = self._run(*arguments)
                    self.assertEqual(2, rejected.returncode)
                    self.assertEqual(code, json.loads(rejected.stderr)["code"])


class WeeklyCycleNativeStateTests(unittest.TestCase):
    def _cycle(self, home: Path) -> Path:
        cut, mart = upstream(home)
        started = start_cycle(cut, mart, home / ".local" / "weekly-cycles")
        return Path(started["destination"])

    def _submit(self, cycle: Path, role: str, agent_id: str, model: str,
                verdict: str = "REVIEW") -> dict:
        from tests.test_native_agents_v1 import response_for, trace_for, receipt_for

        request = json.loads((cycle / "tasks" / f"{role}.request.json").read_text(encoding="utf-8"))
        response, trace = response_for(request), trace_for(request)
        response["verdict"] = verdict
        receipt = receipt_for(request, response, trace, model)
        receipt["agent_id"] = agent_id
        response_path = cycle / "tasks" / f"{role}.response.json"
        trace_path = cycle / "tasks" / f"{role}.query-trace.json"
        response_path.write_bytes(canonical_json(response))
        trace_path.write_bytes(canonical_json(trace))
        recorded = record_dispatch(cycle, role, response_path, trace_path, receipt)
        self.assertEqual(receipt["response_sha256"], recorded["response_sha256"])
        return submit_response(cycle, role, response_path, trace_path,
                               cycle / "tasks" / f"{role}.dispatch.json")

    def test_any_order_analysts_reviewer_and_advisory_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cycle = self._cycle(Path(tmp))
            roles = list(reversed(sorted(verify_cycle(cycle)["expected_roles"])))
            models = {"merchandiser": "gpt-5.6-terra", "finance_analyst": "gpt-5.6-terra",
                "commerce_analyst": "gpt-6-luna", "returns_analyst": "gpt-6-luna",
                "growth_analyst": "gpt-6-sol", "market_researcher": "gpt-6-sol"}
            for index, role in enumerate(roles):
                state = self._submit(cycle, role, f"/root/fixture_{role}", models[role])
                self.assertEqual("WAITING_REVIEW" if index == len(roles) - 1 else
                                 "WAITING_ANALYSTS", state["status"])
            request = json.loads((cycle / "tasks" / "evidence_reviewer.request.json").read_text(
                encoding="utf-8"))
            self.assertTrue(validate_request(request))
            self.assertEqual("astra", request["expected_model_family"])
            self.assertEqual(set(roles), set(request["evidence"]["accepted_hashes"]))
            for role in roles:
                self.assertIn("response_sha256", request["evidence"]["accepted_hashes"][role])
                self.assertIn("query_trace_sha256", request["evidence"]["accepted_hashes"][role])
                self.assertIn("dispatch_sha256", request["evidence"]["accepted_hashes"][role])
            finished = self._submit(cycle, "evidence_reviewer", "/root/fixture_independent",
                                    "gpt-6-astra", "READY_FOR_OWNER")
            self.assertEqual("READY_FOR_OWNER", finished["status"])
            packet = read_terminal_packet(cycle)
            self.assertEqual("READY_FOR_OWNER", packet["status"])
            self.assertEqual("PROHIBITED", packet["external_execution"])
            self.assertEqual(6, len(packet["analyses"]))
            self.assertTrue(packet["facts"] and packet["unknowns"] and packet["hypotheses"])
            self.assertTrue(packet["recommendations"] and packet["challenges"])
            self.assertTrue(validate_terminal_packet({"cycle_dir": cycle}, packet))
            self.assertEqual("READY_FOR_OWNER", resume_cycle(cycle)["status"])

    def test_tamper_duplicate_and_same_reviewer_identity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cycle = self._cycle(Path(tmp))
            self._submit(cycle, "merchandiser", "/root/fixture_shared", "gpt-5.6-terra")
            changed = cycle / "tasks" / "merchandiser.response.json"
            changed.write_bytes(changed.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                verify_cycle(cycle)
        with tempfile.TemporaryDirectory() as tmp:
            cycle = self._cycle(Path(tmp))
            roles = sorted(verify_cycle(cycle)["expected_roles"])
            models = {"merchandiser": "gpt-5.6-terra", "finance_analyst": "gpt-5.6-terra",
                "commerce_analyst": "gpt-6-luna", "returns_analyst": "gpt-6-luna",
                "growth_analyst": "gpt-6-sol", "market_researcher": "gpt-6-sol"}
            for role in roles:
                self._submit(cycle, role, f"/root/fixture_{role}", models[role])
            with self.assertRaises(ValueError):
                self._submit(cycle, "evidence_reviewer", f"/root/fixture_{roles[0]}",
                             "gpt-6-astra", "READY_FOR_OWNER")
            self.assertEqual("WAITING_REVIEW", verify_cycle(cycle)["status"])
