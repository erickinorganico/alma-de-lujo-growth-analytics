"""Exact hand oracles for Phase 2 finance marts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alma.operating_mart_contracts import bind_cut
from alma.operating_workspace import build_operating_workspace

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "client" / "source-packs" / "v1" / "synthetic"


class ObligationTests(unittest.TestCase):
    def test_recorded_unpaid_is_distinct_from_authoritative_outstanding(self) -> None:
        from alma.operating_finance_marts import reconcile_obligation

        obligation = {"obligation_id": "o1", "origin_type": "EXPENSE", "origin_id": "e1",
                      "original_cents": 180000, "due_date": None, "source_ref": "src:o1"}
        payment = {"payment_id": "p1", "obligation_id": "o1", "paid_date": "2026-09-20",
                   "amount_cents": 100000, "source_ref": "src:p1"}
        partial = reconcile_obligation(obligation, [payment], as_of="2026-09-21", application_coverage="PARTIAL")
        self.assertEqual(100000, partial["recorded_applied_cents"])
        self.assertEqual(80000, partial["recorded_unpaid_cents"])
        self.assertIsNone(partial["authoritative_outstanding_cents"])
        self.assertEqual("PARTIAL", partial["status"])
        self.assertEqual("UNDATED", partial["due_bucket"])
        measured = reconcile_obligation(obligation, [payment], as_of="2026-09-21", application_coverage="COMPLETE")
        self.assertEqual(80000, measured["authoritative_outstanding_cents"])
        with self.assertRaises(ValueError):
            reconcile_obligation(obligation, [payment, payment], as_of="2026-09-21", application_coverage="COMPLETE")
        with self.assertRaises(ValueError):
            reconcile_obligation(obligation, [dict(payment, amount_cents=180001)], as_of="2026-09-21", application_coverage="COMPLETE")

    def test_verified_cut_obligations_use_source_grain(self) -> None:
        from alma.operating_finance_marts import project_obligations, FINANCE_DEFINITIONS

        self.assertIn("recorded_unpaid_cents", FINANCE_DEFINITIONS)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                rows = project_obligations(cut, "2026-09-21")
                by_id = {row["obligation_id"]: row for row in rows}
                settled = by_id["synthetic:obligation-po-001"]
                self.assertEqual(900000, settled["recorded_applied_cents"])
                self.assertEqual(0, settled["recorded_unpaid_cents"])
                self.assertEqual("PARTIAL", settled["status"])
                self.assertEqual(result["cut_id"], settled["cut_id"])
                self.assertEqual(100000, by_id["synthetic:obligation-expense-001"]["recorded_unpaid_cents"])


if __name__ == "__main__":
    unittest.main()
