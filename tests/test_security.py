"""Fail-closed input and action-boundary tests."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))

from alma.decisions import build_decisions, execute_action, validate_packet
from alma.analytics import analyze
from alma.fixtures import generate
from alma.__main__ import build
from alma.validation import ContractError, check_structure, validate


class InputSecurityTests(unittest.TestCase):
    def test_only_exact_top_level_contract_is_accepted(self) -> None:
        data = generate()
        data["unexpected"] = "not authorized"
        with self.assertRaisesRegex(ContractError, "metadata and tables only"):
            check_structure(data)

    def test_non_synthetic_or_missing_synthetic_marker_is_rejected(self) -> None:
        for marker in (False, None):
            with self.subTest(marker=marker):
                data = generate()
                if marker is None:
                    del data["metadata"]["synthetic"]
                else:
                    data["metadata"]["synthetic"] = marker
                with self.assertRaisesRegex(ContractError, "explicitly synthetic"):
                    check_structure(data)

    def test_extra_pii_columns_are_rejected(self) -> None:
        for column, value in (("email", "synthetic@example.invalid"), ("phone", "+520000000000"), ("address", "synthetic address")):
            with self.subTest(column=column):
                data = generate()
                data["tables"]["customers"][0][column] = value
                with self.assertRaisesRegex(ContractError, "customers: unexpected columns"):
                    check_structure(data)

    def test_extra_columns_are_rejected_on_every_table(self) -> None:
        source = generate()
        for table in source["tables"]:
            with self.subTest(table=table):
                data = copy.deepcopy(source)
                data["tables"][table][0]["unexpected"] = "x"
                with self.assertRaisesRegex(ContractError, f"{table}: unexpected columns"):
                    check_structure(data)

    def test_malformed_table_shapes_and_missing_tables_are_rejected(self) -> None:
        cases = []
        missing = generate()
        del missing["tables"]["payments"]
        cases.append(missing)
        non_list = generate()
        non_list["tables"]["payments"] = {"not": "rows"}
        cases.append(non_list)
        non_dict_row = generate()
        non_dict_row["tables"]["payments"][0] = "not-a-row"
        cases.append(non_dict_row)
        for data in cases:
            with self.subTest(shape=type(data["tables"].get("payments")).__name__):
                with self.assertRaises(ContractError):
                    check_structure(data)

    def test_foreign_key_failure_is_visible_and_build_is_withheld(self) -> None:
        data = generate()
        data["tables"]["order_items"][0]["order_id"] = "missing-order"
        quality = {row["id"]: row for row in validate(data)}
        self.assertEqual("FAIL", quality["fk_order_items_order_id"]["status"])

        from unittest.mock import patch
        import tempfile

        with self.assertRaisesRegex(ContractError, "invalid relationships"):
            analyze(data)

        with tempfile.TemporaryDirectory() as tmp, patch("alma.__main__.generate", return_value=data):
            with self.assertRaises(ContractError):
                build(Path(tmp) / "blocked")

    def test_invalid_delivery_date_is_visible_and_analysis_is_withheld(self) -> None:
        data = generate()
        delivered = next(order for order in data["tables"]["orders"] if order["status"] == "delivered")
        delivered["delivered_date"] = "2026-01-01"
        quality = {row["id"]: row for row in validate(data)}
        self.assertEqual("FAIL", quality["delivery_dates"]["status"])
        with self.assertRaisesRegex(ContractError, "delivery dates"):
            analyze(data)


class DecisionBoundaryTests(unittest.TestCase):
    def test_generated_packets_validate_and_keep_actions_blocked(self) -> None:
        report = analyze(generate())
        packets = build_decisions(report)
        self.assertTrue(packets)
        for packet in packets:
            with self.subTest(packet=packet.get("id")):
                self.assertTrue(validate_packet(packet, report))
                self.assertTrue(packet["facts"])
                for fact in packet["facts"]:
                    self.assertTrue(fact["evidence_refs"])
                for action in packet["actions"]:
                    self.assertIs(action["approval_required"], True)
                    self.assertEqual("BLOCKED", action["execution"])
                    with self.assertRaises(PermissionError):
                        execute_action(action)

    def test_tampered_packet_without_evidence_or_gate_is_rejected(self) -> None:
        report = analyze(generate())
        packet = copy.deepcopy(build_decisions(report)[0])
        packet["facts"][0]["evidence_refs"] = []
        with self.assertRaises((ValueError, PermissionError)):
            validate_packet(packet, report)

        packet = copy.deepcopy(build_decisions(report)[0])
        packet["actions"][0]["approval_required"] = False
        packet["actions"][0]["execution"] = "APPROVED"
        with self.assertRaises((ValueError, PermissionError)):
            validate_packet(packet, report)

    def test_execute_action_always_denies_even_adversarial_payloads(self) -> None:
        payloads = [
            {},
            {"approval_required": False, "execution": "APPROVED"},
            {"description": "refund", "approved_by": "synthetic-owner"},
            "publish externally",
            None,
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(PermissionError):
                    execute_action(payload)


if __name__ == "__main__":
    unittest.main()
