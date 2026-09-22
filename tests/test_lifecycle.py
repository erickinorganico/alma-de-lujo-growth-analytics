import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from alma.lifecycle import apply_event, definitions, run_lifecycle_demo, verify_hash_chains


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="alma-lifecycle-")
        self.root = Path(self.temp.name)
        self.db = self.root / "lifecycle.sqlite3"
        self.sequence = 0

    def tearDown(self):
        self.temp.cleanup()

    def emit(self, process, instance, event, payload, key=None):
        self.sequence += 1
        return apply_event(
            self.db,
            process_id=process,
            instance_id=instance,
            event_id=f"event-{self.sequence}",
            event_type=event,
            payload=payload,
            idempotency_key=key or f"{process}:{instance}:{event}:{self.sequence}",
            occurred_at_utc=f"2026-03-{self.sequence:02d}T00:00:00Z",
            recorded_at_utc=f"2026-03-{self.sequence:02d}T00:00:00Z",
            source_refs=[f"synthetic://test/{process}/{instance}/{event}/{self.sequence}"],
        )

    @staticmethod
    def approval(instance, suffix="1"):
        return {
            "approval_id": "synthetic-approval-" + suffix,
            "approver_role": "synthetic_founder_fixture",
            "scope": instance,
            "decision": "APPROVE",
            "synthetic": True,
        }

    def state(self, process, instance):
        db = sqlite3.connect(self.db)
        try:
            row = db.execute(
                "SELECT current_state FROM lifecycle_instances WHERE process_id=? AND instance_id=?",
                (process, instance),
            ).fetchone()
            return row[0] if row else "NEW"
        finally:
            db.close()

    def event_count(self, process, instance):
        db = sqlite3.connect(self.db)
        try:
            return db.execute(
                "SELECT count(*) FROM lifecycle_events WHERE process_id=? AND instance_id=?",
                (process, instance),
            ).fetchone()[0]
        finally:
            db.close()

    def progress_po_to_approved(self, instance="po"):
        self.emit("procure-to-stock", instance, "po_drafted", {"quantity": 5, "unit_cost_cents": 100, "currency": "MXN"})
        self.emit("procure-to-stock", instance, "po_submitted", {"total_cents": 500})
        return self.emit("procure-to-stock", instance, "po_approved", {"approval": self.approval(instance, "po")})

    def progress_return_to_pending(self, instance="return"):
        self.emit("return-to-refund", instance, "return_requested", {"requested_qty": 1, "delivered_qty": 1})
        self.emit("return-to-refund", instance, "return_authorized", {"authorized_qty": 1, "authorized_amount_cents": 100, "approval": self.approval(instance, "return")})
        self.emit("return-to-refund", instance, "return_received", {"received_qty": 1})
        self.emit("return-to-refund", instance, "return_inspected", {"quantity": 1, "disposition": "RESTOCK"})
        return self.emit("return-to-refund", instance, "refund_requested", {"amount_cents": 100, "eligible_settled_cents": 100, "approval": self.approval(instance, "refund")})

    def progress_finance_to_reconciling(self, instance="close"):
        self.emit("finance-close", instance, "period_opened", {"period_start": "2026-02-01", "period_end": "2026-02-28", "currency": "MXN", "policy_version": "synthetic-v2"})
        self.emit("finance-close", instance, "cutoff_applied", {"as_of_date": "2026-02-28", "coverage_status": "COMPLETE"})
        self.emit("finance-close", instance, "controls_started", {"source_totals": {"revenue": 100}})
        return self.emit("finance-close", instance, "controls_passed", {"check_results": {"keys": "PASS", "lifecycle": "PASS", "coverage": "PASS"}})

    def progress_market_to_design(self, instance="market", observed="2026-02-20"):
        self.emit("market-to-experiment", instance, "question_opened", {"question": "Synthetic question", "decision_owner": "synthetic_owner"})
        self.emit("market-to-experiment", instance, "research_started", {"candidate_sources": ["s1"], "external_execution": "PROHIBITED"})
        source = {"id": "s1", "authority": "Synthetic fixture", "observed_date": observed, "scope": "context", "license": "link", "method": "synthetic", "limitation": "not demand"}
        self.emit("market-to-experiment", instance, "evidence_submitted", {"sources": [source]})
        return source

    def test_demo_runs_six_golden_paths_and_exports_evidence(self):
        output = self.root / "demo"
        summary = run_lifecycle_demo(output)
        self.assertEqual("PASS", summary["status"])
        self.assertEqual(6, summary["golden_instances"])
        self.assertEqual(6, summary["controlled_illegal_transitions"])
        self.assertTrue((output / "lifecycle.sqlite3").is_file())
        self.assertTrue((output / "exports" / "instances.json").is_file())
        self.assertGreater(verify_hash_chains(output / "lifecycle.sqlite3")["events_checked"], 30)
        instances = json.loads((output / "exports" / "instances.json").read_text(encoding="utf-8"))
        states = {(row["process_id"], row["instance_id"]): row["current_state"] for row in instances}
        self.assertEqual("CLOSED", states[("procure-to-stock", "po-golden")])
        self.assertEqual("DELIVERED", states[("lead-to-delivery", "order-golden")])
        self.assertEqual("CLOSED", states[("return-to-refund", "return-golden")])
        self.assertEqual("CLOSED", states[("finance-close", "close-golden")])
        self.assertEqual("REVIEW_READY", states[("weekly-growth-review", "growth-golden")])
        self.assertEqual("CLOSED", states[("market-to-experiment", "experiment-golden")])

    def test_each_process_rejects_an_illegal_first_transition_without_instance_effect(self):
        illegal = {
            "procure-to-stock": "goods_fully_received",
            "lead-to-delivery": "delivery_confirmed",
            "return-to-refund": "refund_settled",
            "finance-close": "close_approved",
            "weekly-growth-review": "review_packet_built",
            "market-to-experiment": "analysis_completed",
        }
        self.assertEqual(set(illegal), set(definitions()))
        for process, event in illegal.items():
            receipt = self.emit(process, "illegal-" + process, event, {"quantity": 1})
            self.assertEqual("REJECTED", receipt["status"])
            self.assertEqual("STATE_INVALID_TRANSITION", receipt["exception_code"])
            self.assertEqual("NEW", self.state(process, "illegal-" + process))
            self.assertEqual(0, self.event_count(process, "illegal-" + process))

    def test_same_event_is_noop_and_changed_duplicate_blocks_without_duplicate_business_event(self):
        process, instance, key = "lead-to-delivery", "lead-idempotent", "shared-key"
        first = self.emit(process, instance, "lead_captured", {"channel": "synthetic-social", "source_kind": "session"}, key=key)
        self.assertEqual("APPLIED", first["status"])
        request = dict(
            process_id=process, instance_id=instance, event_id="event-1", event_type="lead_captured",
            payload={"channel": "synthetic-social", "source_kind": "session"}, idempotency_key=key,
            occurred_at_utc="2026-03-01T00:00:00Z", recorded_at_utc="2026-03-01T00:00:00Z",
            source_refs=["synthetic://test/lead-to-delivery/lead-idempotent/lead_captured/1"],
        )
        replay = apply_event(self.db, **request)
        self.assertEqual("NO_OP_REPLAY", replay["status"])
        self.assertEqual(1, self.event_count(process, instance))
        request["payload"] = {"channel": "changed", "source_kind": "session"}
        conflict = apply_event(self.db, **request)
        self.assertEqual("CONFLICT", conflict["status"])
        self.assertEqual("CTR_DUPLICATE_EVENT_CONFLICT", conflict["exception_code"])
        self.assertEqual("BLOCKED", self.state(process, instance))
        self.assertEqual(1, self.event_count(process, instance))

    def test_missing_approval_waits_and_overreceipt_rolls_back(self):
        instance = "po-waiting"
        self.emit("procure-to-stock", instance, "po_drafted", {"quantity": 5, "unit_cost_cents": 100, "currency": "MXN"})
        self.emit("procure-to-stock", instance, "po_submitted", {"total_cents": 500})
        waiting = self.emit("procure-to-stock", instance, "po_approved", {})
        self.assertEqual("WAITING", waiting["status"])
        self.assertEqual("APPROVAL_MISSING", waiting["exception_code"])
        self.assertEqual("WAITING_APPROVAL", self.state("procure-to-stock", instance))
        self.progress_po_to_approved("po-over")
        before = self.event_count("procure-to-stock", "po-over")
        rejected = self.emit("procure-to-stock", "po-over", "goods_partially_received", {"accepted_qty": 6, "rejected_qty": 0})
        self.assertEqual("PROC_OVER_RECEIPT", rejected["exception_code"])
        self.assertEqual(before, self.event_count("procure-to-stock", "po-over"))
        self.assertEqual("APPROVED", self.state("procure-to-stock", "po-over"))

    def test_refund_overflow_and_finance_bridge_mismatch_have_no_transition_effect(self):
        self.progress_return_to_pending("refund-over")
        before = self.event_count("return-to-refund", "refund-over")
        result = self.emit("return-to-refund", "refund-over", "refund_settled", {"amount_cents": 101, "eligible_settled_cents": 100})
        self.assertEqual("FIN_REFUND_EXCEEDS_SETTLED", result["exception_code"])
        self.assertEqual(before, self.event_count("return-to-refund", "refund-over"))
        self.assertEqual("REFUND_PENDING", self.state("return-to-refund", "refund-over"))

        self.progress_finance_to_reconciling("bridge-fail")
        before = self.event_count("finance-close", "bridge-fail")
        result = self.emit("finance-close", "bridge-fail", "bridges_reconciled", {"source_components": {"revenue": 100}, "mart_components": {"revenue": 99}})
        self.assertEqual("FIN_BRIDGE_MISMATCH", result["exception_code"])
        self.assertEqual(before, self.event_count("finance-close", "bridge-fail"))
        self.assertEqual("RECONCILING", self.state("finance-close", "bridge-fail"))

    def test_stale_source_and_late_assignment_are_rejected_by_derived_gates(self):
        self.progress_market_to_design("stale", observed="2025-01-01")
        stale = self.emit("market-to-experiment", "stale", "evidence_accepted", {"as_of_date": "2026-03-01", "max_age_days": 60})
        self.assertEqual("SOURCE_STALE", stale["exception_code"])
        self.assertEqual("EVIDENCE_REVIEW", self.state("market-to-experiment", "stale"))

        instance = "late-assignment"
        self.progress_market_to_design(instance, observed="2026-02-20")
        self.emit("market-to-experiment", instance, "evidence_accepted", {"as_of_date": "2026-03-01", "max_age_days": 60})
        design = {"hypothesis": "Synthetic hypothesis", "primary_metric": "metric", "guardrail": "guardrail", "population": "synthetic population", "assignment": "random", "window": "28d", "sample_criterion": "100", "estimator": "difference", "close_rule": "fixed"}
        self.emit("market-to-experiment", instance, "experiment_designed", design)
        self.emit("market-to-experiment", instance, "experiment_approved", {"approval": self.approval(instance, "experiment")})
        before = self.event_count("market-to-experiment", instance)
        late = self.emit("market-to-experiment", instance, "assignment_started", {"assigned_at_utc": "2026-03-05T00:00:00Z", "first_outcome_at_utc": "2026-03-04T00:00:00Z"})
        self.assertEqual("EXP_ASSIGNMENT_INVALID", late["exception_code"])
        self.assertEqual(before, self.event_count("market-to-experiment", instance))
        self.assertEqual("APPROVED", self.state("market-to-experiment", instance))

    def test_non_synthetic_and_execution_payloads_are_never_accepted(self):
        base = dict(
            database=self.db, process_id="lead-to-delivery", instance_id="unsafe", event_id="unsafe-1",
            event_type="lead_captured", payload={"channel": "x", "source_kind": "session"},
            idempotency_key="unsafe-key", occurred_at_utc="2026-03-01T00:00:00Z",
            source_refs=["synthetic://test/unsafe"],
        )
        with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
            apply_event(**base, synthetic=False)
        base["payload"] = {"channel": "x", "source_kind": "session", "external_action": "SEND_MESSAGE"}
        with self.assertRaisesRegex(ValueError, "execution is prohibited"):
            apply_event(**base)


if __name__ == "__main__":
    unittest.main()
