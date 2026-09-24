from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from alma.decision_register import create_register, register_decision
from alma.operating_contracts import canonical_json
from alma.weekly_cycle import (
    export_acceptance_receipt,
    read_terminal_packet,
    start_cycle,
    verify_acceptance_receipt,
)
from tests.test_decision_register import closure_check, later_upstream, terminal_cycle


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "weekly-cycle-v1.schema.json"
VALIDATOR = ROOT / "scripts" / "validate_weekly_contract.ps1"


class WeeklyCycleJsonSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.home = Path(cls.temporary.name)
        cls.first_cycle = terminal_cycle(cls.home)
        cls.packet = read_terminal_packet(cls.first_cycle)
        cls.first_cut = json.loads(
            (cls.first_cycle / "current-cut.json").read_text(encoding="utf-8")
        )
        cls.register = create_register(
            cls.home / ".local" / "decision-register" / "weekly-schema",
            "weekly-schema",
            ["growth_owner"],
        )
        created = register_decision(
            cls.register,
            cls.first_cycle,
            cls.packet["recommendations"][0]["item"]["id"],
            "growth_owner",
            "2026-10-01",
            "ACCEPT",
            closure_check(),
        )
        later_cut, later_marts = later_upstream(cls.home)
        cls.second_cycle = Path(
            start_cycle(
                later_cut,
                later_marts,
                cls.home / ".local" / "weekly-cycles",
                prior_register=cls.register,
                prior_anchor=created["anchor"],
            )["destination"]
        )
        cls.second_cut = json.loads(
            (cls.second_cycle / "current-cut.json").read_text(encoding="utf-8")
        )
        cls.instances = cls.home / "schema-instances"
        cls.instances.mkdir()
        cls.counter = 0

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def _validate(cls, definition: str, value: object) -> subprocess.CompletedProcess[str]:
        cls.counter += 1
        instance = cls.instances / f"{definition}-{cls.counter}.json"
        instance.write_bytes(canonical_json(value))
        return subprocess.run(
            [
                "pwsh",
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(VALIDATOR),
                "-SchemaPath",
                str(SCHEMA),
                "-Definition",
                definition,
                "-InstancePath",
                str(instance),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def assertValid(self, definition: str, value: object) -> None:  # noqa: N802
        result = self._validate(definition, value)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(f"definition={definition} status=VALID", result.stdout.strip())

    def assertInvalid(self, definition: str, value: object) -> None:  # noqa: N802
        result = self._validate(definition, value)
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(f"definition={definition} status=INVALID", result.stdout.strip())
        diagnostic = result.stdout + result.stderr
        self.assertNotIn(str(self.home), diagnostic)
        self.assertNotIn(json.dumps(value, sort_keys=True), diagnostic)

    def test_real_packet_matches_exact_closed_schema(self) -> None:
        self.assertValid("packet", self.packet)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        packet_schema = schema["$defs"]["packet"]
        self.assertEqual(set(self.packet), set(packet_schema["required"]))
        self.assertEqual(set(self.packet), set(packet_schema["properties"]))
        self.assertFalse(packet_schema["additionalProperties"])
        self.assertNotIn("evidence_hashes", packet_schema["properties"])

    def test_first_and_governed_current_cuts_match_schema(self) -> None:
        self.assertValid("current_cut", self.first_cut)
        self.assertValid("current_cut", self.second_cut)
        self.assertValid("decision_binding", self.second_cut["decision_register"])
        self.assertValid("decision_anchor", self.second_cut["decision_register"]["anchor"])
        self.assertValid("carried_decision", self.second_cut["carried_decisions"][0])
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cut_schema = schema["$defs"]["current_cut"]
        self.assertEqual(set(self.first_cut), set(cut_schema["required"]))
        self.assertEqual(
            set(self.first_cut) | {"decision_register", "carried_decisions"},
            set(cut_schema["properties"]),
        )
        self.assertEqual(
            {"decision_register": ["carried_decisions"],
             "carried_decisions": ["decision_register"]},
            cut_schema["dependentRequired"],
        )

    def test_packet_missing_extra_hash_and_authority_mutations_fail(self) -> None:
        for field in self.packet:
            with self.subTest(missing=field):
                changed = copy.deepcopy(self.packet)
                del changed[field]
                self.assertInvalid("packet", changed)
        changes = {
            "top-level extra": lambda row: row.update(extra="forbidden"),
            "nested extra": lambda row: row["analyses"][0].update(extra="forbidden"),
            "short hash": lambda row: row.update(current_cut_sha256="0" * 63),
            "execution authority": lambda row: row.update(external_execution="EXECUTE"),
            "review verdict": lambda row: row["review"].update(verdict="APPROVED"),
            "wrapped role": lambda row: row["facts"][0].update(role="owner"),
        }
        for label, change in changes.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(self.packet)
                change(changed)
                self.assertInvalid("packet", changed)

    def test_current_cut_missing_extra_and_decision_mutations_fail(self) -> None:
        for field in self.first_cut:
            with self.subTest(missing=field):
                changed = copy.deepcopy(self.first_cut)
                del changed[field]
                self.assertInvalid("current_cut", changed)
        cases = {
            "top-level extra": lambda row: row.update(extra="forbidden"),
            "binding without carry": lambda row: row.pop("carried_decisions"),
            "carry without binding": lambda row: row.pop("decision_register"),
            "binding extra": lambda row: row["decision_register"].update(extra=True),
            "anchor extra": lambda row: row["decision_register"]["anchor"].update(extra=True),
            "anchor hash": lambda row: row["decision_register"]["anchor"].update(
                terminal_hash="0" * 63
            ),
            "anchor version": lambda row: row["decision_register"]["anchor"].update(
                version="decision-register-v2"
            ),
            "carried extra": lambda row: row["carried_decisions"][0].update(extra=True),
            "carried status": lambda row: row["carried_decisions"][0].update(status="DONE"),
            "carried count": lambda row: row["carried_decisions"][0].update(event_count="2"),
        }
        for label, change in cases.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(self.second_cut)
                change(changed)
                self.assertInvalid("current_cut", changed)

    def test_full_exchange_documents_validate_and_reject_structural_drift(self) -> None:
        tasks = self.first_cycle / "tasks"
        role = "merchandiser"
        documents = {
            "current_cut": self.first_cut,
            "request": json.loads(
                (tasks / f"{role}.request.json").read_text(encoding="utf-8")
            ),
            "response": json.loads(
                (tasks / f"{role}.response.json").read_text(encoding="utf-8")
            ),
            "query_trace": json.loads(
                (tasks / f"{role}.query-trace.json").read_text(encoding="utf-8")
            ),
            "dispatch_receipt": json.loads(
                (tasks / f"{role}.dispatch.json").read_text(encoding="utf-8")
            ),
            "packet": self.packet,
            "decision_binding": self.second_cut["decision_register"],
        }
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        for definition, document in documents.items():
            with self.subTest(definition=definition, case="valid"):
                self.assertValid(definition, document)
            required = schema["$defs"][definition]["required"]
            missing = copy.deepcopy(document)
            del missing[required[0]]
            with self.subTest(definition=definition, case="missing"):
                self.assertInvalid(definition, missing)
            extra = copy.deepcopy(document)
            extra["undeclared"] = "forbidden"
            with self.subTest(definition=definition, case="extra"):
                self.assertInvalid(definition, extra)

    def test_public_receipt_allowlists_and_validator_has_no_private_side_effect(self) -> None:
        public_path = self.home / "evidence" / "v1" / "native-cycle-acceptance.json"
        receipt = export_acceptance_receipt(self.first_cycle, public_path)
        self.assertEqual(
            {
                "version", "synthetic_business_data", "cut_id", "run_id",
                "current_cut_sha256", "manifest_sha256", "mart_bundle_sha256",
                "metric_contract_sha256", "task_bundle_sha256", "analysts", "reviewer",
                "terminal_status", "terminal_packet_sha256", "recorded_at_utc",
                "scope_limits",
            },
            set(receipt),
        )
        metadata_keys = {
            "agent_id", "model", "request_sha256", "response_sha256",
            "query_trace_sha256", "dispatch_sha256",
        }
        self.assertEqual(metadata_keys, set(receipt["reviewer"]))
        self.assertTrue(receipt["analysts"])
        for analyst in receipt["analysts"].values():
            self.assertEqual(metadata_keys, set(analyst))
        self.assertEqual(
            "PASS",
            verify_acceptance_receipt(
                public_path, self.home / ".local" / "weekly-cycles"
            )["status"],
        )
        tracked_receipt = ROOT / "evidence" / "v1" / "native-cycle-acceptance.json"
        tracked_before = tracked_receipt.read_bytes()
        files_before = {path.relative_to(self.home) for path in self.home.rglob("*") if path.is_file()}
        result = self._validate("packet", self.packet)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        files_after = {path.relative_to(self.home) for path in self.home.rglob("*") if path.is_file()}
        self.assertEqual(files_before | {Path("schema-instances") / f"packet-{self.counter}.json"},
                         files_after)
        self.assertEqual(tracked_before, tracked_receipt.read_bytes())
        self.assertNotIn("summary", result.stdout + result.stderr)
        self.assertNotIn("carried_decisions", result.stdout + result.stderr)

    def test_unrecognized_definition_fails_with_bounded_diagnostic(self) -> None:
        instance = self.instances / "unknown-definition.json"
        instance.write_bytes(canonical_json(self.packet))
        malicious = "not-allowlisted\nPRIVATE-CONTENT"
        result = subprocess.run(
            [
                "pwsh", "-NoLogo", "-NoProfile", "-File", str(VALIDATOR),
                "-SchemaPath", str(SCHEMA), "-Definition", malicious,
                "-InstancePath", str(instance),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("definition=UNRECOGNIZED status=INVALID", result.stdout.strip())
        self.assertNotIn("PRIVATE-CONTENT", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
