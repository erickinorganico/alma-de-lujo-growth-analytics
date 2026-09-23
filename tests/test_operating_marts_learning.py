"""Learning, exception, and private publication oracles for operating marts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alma.operating_mart_contracts import bind_cut, load_policy
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"
POLICY = ROOT / "policies" / "operating-metrics-synthetic-v1.json"


class LearningTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
