"""Exact hand oracles for Phase 2 finance marts."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
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


class CashTests(unittest.TestCase):
    def test_settled_event_supersedes_commitment_and_window_boundaries(self) -> None:
        from alma.operating_finance_marts import active_cash_events, cash_horizons

        as_of = "2026-09-21"
        base = {"scenario_id": "observed", "economic_event_id": "payment-1", "direction": "OUTFLOW",
                "amount_cents": 900000, "obligation_id": "o1", "source_ref": "src:cash"}
        forecast = dict(base, event_id="forecast", supersedes_event_id=None, event_date="2026-09-18",
                        level="COMMITTED", payment_id=None)
        actual = dict(base, event_id="actual", supersedes_event_id="forecast", event_date="2026-09-18",
                      level="RECONCILED", payment_id="p1")
        active = active_cash_events([forecast, actual], as_of)
        self.assertEqual(["actual"], [event["event_id"] for event in active])
        day55 = (date.fromisoformat(as_of) + timedelta(days=55)).isoformat()
        day56 = (date.fromisoformat(as_of) + timedelta(days=56)).isoformat()
        boundary = [dict(base, event_id="d55", economic_event_id="e55", supersedes_event_id=None,
                         event_date=day55, level="COMMITTED", payment_id=None, amount_cents=11),
                    dict(base, event_id="d56", economic_event_id="e56", supersedes_event_id=None,
                         event_date=day56, level="COMMITTED", payment_id=None, amount_cents=13),
                    dict(base, event_id="undated", economic_event_id="eu", supersedes_event_id=None,
                         event_date=None, level="UNDATED", payment_id=None, amount_cents=7),
                    dict(base, event_id="scenario", economic_event_id="es", supersedes_event_id=None,
                         event_date=day55, level="SCENARIO", payment_id=None, amount_cents=5)]
        horizons = cash_horizons(boundary, as_of)
        self.assertEqual(-11, horizons[56]["layers_cents"]["COMMITTED"])
        self.assertEqual(-24, horizons[91]["layers_cents"]["COMMITTED"])
        self.assertEqual(-7, horizons[56]["undated_cents"])
        self.assertEqual(-5, horizons[56]["scenario_cents"])

    def test_close_requires_independent_observed_opening_and_closing(self) -> None:
        from alma.operating_finance_marts import reconcile_cash_close, project_cash
        from alma.operating_mart_contracts import load_policy

        evidence = {"period_start": "2026-09-01", "period_end": "2026-09-21",
                    "opening_balance_cents": 2000000, "closing_balance_cents": 1100000,
                    "opening_observed_at": "2026-09-01T00:00:00-07:00",
                    "closing_observed_at": "2026-09-21T23:59:59-07:00", "evidence_status": "OBSERVED"}
        actual = {"event_id": "a", "level": "RECONCILED", "direction": "OUTFLOW",
                  "event_date": "2026-09-18", "amount_cents": 900000}
        self.assertEqual(1100000, reconcile_cash_close([actual], evidence, coverage="COMPLETE")["close_cents"])
        self.assertIsNone(reconcile_cash_close([actual], dict(evidence, opening_balance_cents=None), coverage="COMPLETE")["close_cents"])
        self.assertIsNone(reconcile_cash_close([actual], evidence, coverage="PARTIAL")["close_cents"])
        policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json", as_of="2026-09-21", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=tmp)
            with bind_cut(result["destination"]) as cut:
                cash = project_cash(cut, "2026-09-21", policy)
                self.assertEqual(("synthetic:cash-actual-001",), cash["active_event_ids"])
                self.assertEqual(-900000, cash["actual_movements_cents"])
                self.assertIsNone(cash["reconciled_close_cents"])


if __name__ == "__main__":
    unittest.main()
