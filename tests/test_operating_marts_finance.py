"""Exact hand oracles for Phase 2 finance marts."""
from __future__ import annotations

import tempfile
import unittest
import json
import shutil
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
        split = reconcile_obligation(dict(obligation, original_cents=101),
            [dict(payment, payment_id="p1", amount_cents=30),
             dict(payment, payment_id="p2", amount_cents=30)],
            as_of="2026-09-21", application_coverage="COMPLETE")
        self.assertEqual(60, split["recorded_applied_cents"])
        self.assertEqual(41, split["recorded_unpaid_cents"])
        void = reconcile_obligation(dict(obligation, status_code="VOID"), [],
            as_of="2026-09-21", application_coverage="COMPLETE")
        self.assertEqual(180000, void["documented_adjustments_cents"])
        self.assertEqual(0, void["authoritative_outstanding_cents"])
        with self.assertRaises(ValueError):
            reconcile_obligation(dict(obligation, status_code="VOID"), [payment],
                as_of="2026-09-21", application_coverage="COMPLETE")

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
    def test_observed_inflow_without_payable_is_valid(self) -> None:
        from alma.operating_finance_marts import active_cash_events

        observed = {"event_id": "observed-inflow", "economic_event_id": "sale-inflow",
                    "supersedes_event_id": None, "scenario_id": "observed",
                    "event_date": "2026-09-18", "level": "RECONCILED",
                    "direction": "INFLOW", "amount_cents": 100,
                    "obligation_id": None, "payment_id": None, "source_ref": "observed:bank:1"}
        self.assertEqual([observed], active_cash_events([observed], "2026-09-21"))
        observed_outflow = dict(observed, event_id="observed-outflow",
                                economic_event_id="expense-outflow", direction="OUTFLOW")
        self.assertEqual([observed_outflow], active_cash_events([observed_outflow], "2026-09-21"))
        with self.assertRaises(ValueError):
            active_cash_events([dict(observed_outflow, source_ref="")], "2026-09-21")
        with self.assertRaises(ValueError):
            active_cash_events([dict(observed, direction="OUTFLOW", obligation_id="payable-1")],
                               "2026-09-21")

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
        with self.assertRaises(ValueError):
            active_cash_events([forecast, dict(forecast, event_id="duplicate-root")], as_of)
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
            pack = Path(tmp) / "complete-cash-pack"
            shutil.copytree(PACK, pack)
            metadata_path = pack / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for source in ("cash_events", "cash_balance_evidence"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            complete = build_operating_workspace(pack, private_root=Path(tmp) / "complete-cash")
            with bind_cut(complete["destination"]) as cut:
                cash = project_cash(cut, "2026-09-21", policy)
                self.assertEqual(1100000, cash["reconciled_close_cents"])
                self.assertEqual(1100000, cash["horizons"][56]["daily_minimum_cents"])
                self.assertFalse(cash["horizons"][56]["cash_floor_breached"])


class BudgetTests(unittest.TestCase):
    def test_one_source_two_targets_and_two_payments_reconcile_once(self) -> None:
        from alma.operating_finance_marts import allocate_source_cents, distribute_state_cents

        allocations = [
            {"budget_allocation_id": "a1", "origin_type": "EXPENSE", "origin_id": "e1",
             "budget_id": "b1", "drop_code": "d1", "channel_code": "direct", "allocated_cents": 50},
            {"budget_allocation_id": "a2", "origin_type": "EXPENSE", "origin_id": "e1",
             "budget_id": "b2", "drop_code": "d2", "channel_code": "wholesale", "allocated_cents": 50},
        ]
        shares = allocate_source_cents(("EXPENSE", "e1"), 101, allocations)
        self.assertEqual(1, shares["unallocated_cents"])
        self.assertEqual(101, sum(shares["target_cents"].values()) + shares["unallocated_cents"])
        paid = distribute_state_cents(60, 101, shares)
        self.assertEqual(60, sum(paid["target_cents"].values()) + paid["unallocated_cents"])
        self.assertEqual([30, 30], sorted(paid["target_cents"].values()))
        incurred = distribute_state_cents(101, 101, shares)
        self.assertEqual(100, sum(incurred["target_cents"].values()))
        self.assertEqual(1, incurred["unallocated_cents"])
        with self.assertRaises(ValueError):
            allocate_source_cents(("EXPENSE", "e1"), 101, allocations + [allocations[0]])
        with self.assertRaises(ValueError):
            allocate_source_cents(("EXPENSE", "e1"), 99, allocations)

    def test_budget_states_and_policy_gated_headroom(self) -> None:
        from alma.operating_finance_marts import project_budgets
        from alma.operating_mart_contracts import load_policy

        policy = load_policy(ROOT / "policies" / "operating-metrics-synthetic-v1.json", as_of="2026-09-21", real_cut=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = build_operating_workspace(PACK, private_root=Path(tmp) / "partial")
            with bind_cut(result["destination"]) as cut:
                budget = project_budgets(cut, "2026-09-21", policy)
                target = budget["targets"][0]
                self.assertEqual(1200000, target["approved_ceiling_cents"])
                self.assertEqual(90000, target["open_commitment_cents"])
                self.assertEqual(910000, target["incurred_cents"])
                self.assertEqual(900000, target["paid_cents"])
                self.assertEqual(100000, target["outstanding_obligation_cents"])
                self.assertIsNone(target["headroom_cents"])
            pack = Path(tmp) / "pack"
            shutil.copytree(PACK, pack)
            metadata_path = pack / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for source in ("budgets", "budget_allocations", "expenses", "purchase_orders", "purchase_receipts",
                           "obligations", "obligation_payments"):
                metadata["coverage"][source]["status"] = "COMPLETE"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            result = build_operating_workspace(pack, private_root=Path(tmp) / "complete")
            with bind_cut(result["destination"]) as cut:
                target = project_budgets(cut, "2026-09-21", policy)["targets"][0]
                self.assertEqual(200000, target["headroom_cents"])


if __name__ == "__main__":
    unittest.main()
