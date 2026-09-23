"""Acceptance contracts for the v1 weekly command and public client kit."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path

from alma.decision_register import create_register, verify_register
from alma.operating_contracts import canonical_json
from alma.weekly import WeeklyContractError, continue_weekly_run, create_weekly_run
from alma.weekly_cycle import verify_cycle
from scripts.build_operating_workbooks import build_operating_workbooks
from tests.test_decision_register import MODELS, closure_check
from tests.test_native_agents_v1 import receipt_for, response_for, trace_for


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "client" / "v1" / "policies" / "operating-metrics-synthetic-v1.json"


def generated_materials(home: Path) -> tuple[Path, Path]:
    generated = home / "generated"
    build_operating_workbooks(generated)
    return generated / "source-packs" / "synthetic", generated / "operating-v1-synthetic.xlsx"


def canonical_file(path: Path, value: object) -> Path:
    path.write_bytes(canonical_json(value))
    return path


@contextmanager
def weekly_home():
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        target = Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
        shutil.rmtree(target, ignore_errors=True)


def long_path(path: Path) -> Path:
    if sys.platform == "win32" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path.resolve()))
    return path


class WeeklyCommandTests(unittest.TestCase):
    def test_source_pack_and_workbook_create_derived_waiting_runs_without_overwrite(self) -> None:
        with weekly_home() as home:
            pack, workbook = generated_materials(home)
            for label, source in (("pack", pack), ("workbook", workbook)):
                with self.subTest(label=label):
                    output = home / label / ".local" / "client-runs"
                    result = create_weekly_run(source, POLICY, output)
                    run = Path(result["run"])
                    self.assertEqual(output.resolve(), run.parent)
                    self.assertEqual(result["cut_id"], run.name)
                    self.assertEqual("WAITING_ANALYSTS", result["status"])
                    self.assertEqual(label, result["input_route"])
                    self.assertEqual("WAITING_ANALYSTS", verify_cycle(result["cycle_path"])["status"])
                    index = json.loads((run / "run-index.json").read_text("utf-8"))
                    self.assertEqual(result["cut_id"], index["cut_id"])
                    self.assertEqual("SYNTHETIC_EXAMPLE", index["policy"]["status"])
                    self.assertTrue((run / "receipts" / "source.json").is_file())
                    self.assertTrue((run / "receipts" / "marts.json").is_file())
                    self.assertTrue((run / "receipts" / "native-waiting.json").is_file())
                    with self.assertRaises(WeeklyContractError):
                        create_weekly_run(source, POLICY, output)

    def test_prior_pair_policy_and_private_output_fail_closed(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            valid = home / ".local" / "client-runs"
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, POLICY, valid, prior_register=home / "register")
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, POLICY, home / "public-runs")
            stale = home / "stale-policy.json"
            content = json.loads(POLICY.read_text("utf-8"))
            content["effective_end"] = "2026-02-01"
            content["sha256"] = hashlib.sha256(canonical_json(
                {key: value for key, value in content.items() if key != "sha256"}
            )).hexdigest()
            canonical_file(stale, content)
            with self.assertRaises(WeeklyContractError):
                create_weekly_run(pack, stale, valid)
            self.assertFalse(valid.exists())

    def test_resume_actions_validate_evidence_and_preserve_initial_receipts(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            started = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            run = Path(started["run"])
            cycle = Path(started["cycle_path"])
            before = {path.name: path.read_bytes() for path in (run / "receipts").iterdir()}

            resumed = continue_weekly_run(run, "resume")
            self.assertEqual("WAITING_ANALYSTS", resumed["status"])
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "resume", role="growth_analyst")
            with self.assertRaises(WeeklyContractError):
                continue_weekly_run(run, "record", role="growth_analyst")

            for role in sorted(MODELS):
                request = json.loads((cycle / "tasks" / f"{role}.request.json").read_text("utf-8"))
                response, trace = response_for(request), trace_for(request)
                response["recommendations"][0]["id"] = f"{role}-weekly-one"
                response_path = canonical_file(cycle / "tasks" / f"{role}.response.json", response)
                trace_path = canonical_file(cycle / "tasks" / f"{role}.query-trace.json", trace)
                receipt = receipt_for(request, response, trace, MODELS[role])
                receipt["agent_id"] = f"/root/weekly_{role}"
                external = canonical_file(home / f"{role}.dispatch-input.json", receipt)
                continue_weekly_run(run, "record", role=role, response=response_path,
                                    query_trace=trace_path, dispatch_receipt=external)
                continue_weekly_run(run, "submit", role=role, response=response_path,
                                    query_trace=trace_path,
                                    dispatch_receipt=cycle / "tasks" / f"{role}.dispatch.json")

            request = json.loads((cycle / "tasks" / "evidence_reviewer.request.json").read_text("utf-8"))
            response, trace = response_for(request), trace_for(request)
            response["verdict"] = "READY_FOR_OWNER"
            response_path = canonical_file(cycle / "tasks" / "evidence_reviewer.response.json", response)
            trace_path = canonical_file(cycle / "tasks" / "evidence_reviewer.query-trace.json", trace)
            receipt = receipt_for(request, response, trace, "gpt-6-astra")
            receipt["agent_id"] = "/root/weekly_reviewer"
            external = canonical_file(home / "reviewer.dispatch-input.json", receipt)
            continue_weekly_run(run, "record", role="evidence_reviewer", response=response_path,
                                query_trace=trace_path, dispatch_receipt=external)
            continue_weekly_run(run, "submit", role="evidence_reviewer", response=response_path,
                                query_trace=trace_path,
                                dispatch_receipt=cycle / "tasks" / "evidence_reviewer.dispatch.json")
            packet = continue_weekly_run(run, "packet")
            self.assertEqual("READY_FOR_OWNER", packet["status"])

            register = create_register(home / ".local" / "decision-register" / "weekly",
                                       "weekly", ["growth_owner"])
            recommendation_id = packet["recommendations"][0]["item"]["id"]
            event = canonical_file(home / "owner-decision.json", {
                "recommendation_id": recommendation_id,
                "owner_role": "growth_owner",
                "due_date": "2026-10-15",
                "owner_choice": "ACCEPT",
                "closure_check": closure_check(),
            })
            registered = continue_weekly_run(run, "register", register=register,
                                             decision_event=event)
            self.assertEqual("OPEN", registered["status"])
            self.assertEqual(1, len(verify_register(register)["decisions"]))
            self.assertEqual(before, {path.name: path.read_bytes()
                                      for path in (run / "receipts").iterdir()})

    def test_launcher_help_and_second_process_resume_match_exact_interface(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            self.skipTest("PowerShell unavailable")
        for command in ("weekly", "weekly-resume"):
            process = subprocess.run([shell, "-NoProfile", "-File", str(ROOT / "run.ps1"),
                                      command, "--help"], cwd=ROOT, text=True,
                                     capture_output=True, check=False)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertIn("--help", process.stdout)
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            result = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            process = subprocess.run([sys.executable, "-m", "alma.weekly", "weekly-resume",
                                      "--run", result["run"], "--action", "resume"],
                                     cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual("WAITING_ANALYSTS", json.loads(process.stdout)["status"])

    def test_clean_git_archive_process_resumes_explicit_restored_private_run(self) -> None:
        with weekly_home() as home:
            pack, _ = generated_materials(home)
            result = create_weekly_run(pack, POLICY, home / ".local" / "client-runs")
            run = Path(result["run"])
            immutable = {
                path.relative_to(run).as_posix(): path.read_bytes()
                for path in (run / "receipts").iterdir()
            }
            immutable["run-index.json"] = (run / "run-index.json").read_bytes()

            archive = home / "committed.zip"
            archived = subprocess.run(
                ["git", "archive", "--format=zip", "-o", str(archive), "HEAD"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, archived.returncode, archived.stderr)
            checkout = home / "clean-checkout"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(checkout)
            self.assertFalse((checkout / ".git").exists())

            backup = home / "explicit-private-run"
            shutil.copytree(long_path(run), long_path(backup))
            shutil.rmtree(long_path(run))
            run.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(long_path(backup), long_path(run))
            env = {**os.environ, "PYTHONPATH": str(checkout)}
            process = subprocess.run(
                [sys.executable, "-m", "alma.weekly", "weekly-resume",
                 "--run", str(run), "--action", "resume"],
                cwd=checkout, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual("WAITING_ANALYSTS", json.loads(process.stdout)["status"])
            self.assertEqual(immutable["run-index.json"], (run / "run-index.json").read_bytes())
            for relative, raw in immutable.items():
                if relative != "run-index.json":
                    self.assertEqual(raw, (run / relative).read_bytes())


if __name__ == "__main__":
    unittest.main()
