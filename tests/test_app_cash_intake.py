"""Synthetic contract and filesystem tests, using the real operating-v1 parser."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from alma.app_cash_intake import digest, intake, prepare
from alma.operating_interchange import parse_pack
from alma.operating_workspace import build_operating_workspace


INSTANCE = 'ed18d89a-32a0-4b85-b345-404867ab8ea1'


def inputs():
    handoff = dict(schema='alma.app-analytics-handoff.v1', input_class='SYNTHETIC_EXAMPLE', currency='MXN',
                   source=dict(instance_id=INSTANCE, revision=12, state_sha256='a'*64),
                   cash_entries=[
                       dict(id='1'*32, type='payment', date='2026-09-30', amount_cents=10000, order_id='8'*32),
                       dict(id='2'*32, type='payment', date='2026-09-30', amount_cents=5000, order_id='8'*32),
                       dict(id='3'*32, type='refund', date='2026-09-30', amount_cents=2000, order_id='8'*32),
                       dict(id='4'*32, type='expense', date='2026-09-30', amount_cents=3000),
                   ])
    handoff['handoff_sha256'] = digest(handoff)
    review = dict(schema='alma.app-cash-review.v1', handoff_sha256=handoff['handoff_sha256'],
                  source_instance_id=INSTANCE, window_start='2026-09-30', window_end='2026-09-30',
                  cutoff_at='2026-09-30T23:59:59-07:00', timezone='America/Tijuana',
                  opening_balance_cents=20000, closing_balance_cents=30000,
                  opening_observed_at='2026-09-30T00:00:00-07:00', closing_observed_at='2026-09-30T23:59:59-07:00',
                  evidence_ref='synthetic-balances', reviewed_cash_ids=[row['id'] for row in handoff['cash_entries']])
    return handoff, review


def rebind(handoff, review):
    handoff['handoff_sha256'] = digest({k: v for k, v in handoff.items() if k != 'handoff_sha256'})
    review['handoff_sha256'] = handoff['handoff_sha256']


class AppCashIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.handoff, self.review = inputs()

    def test_native_pack_reconciles_partial_payments_refund_and_expense(self):
        path = intake(self.handoff, self.review, self.root)
        parsed = parse_pack(path/'pack', private_root=self.root)
        self.assertEqual(parsed['diagnostics'], [])
        rows = parsed['tables']['cash_events']
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row['economic_event_id'] for row in rows}), 4)
        self.assertEqual([row['direction'] for row in rows], ['INFLOW','INFLOW','OUTFLOW','OUTFLOW'])
        self.assertEqual(sum(r['amount_cents']*(1 if r['direction']=='INFLOW' else -1) for r in rows), 10000)
        self.assertEqual(len(parsed['tables']['cash_balance_evidence']), 1)
        for source, coverage in parsed['metadata']['coverage'].items():
            self.assertEqual(coverage['status'], 'PARTIAL' if source.startswith('cash_') else 'MISSING')
        self.assertEqual(parsed['tables']['sales_aggregates'], [])
        self.assertEqual(parsed['tables']['inventory_movements'], [])

    def test_deterministic_replay_preserves_inputs_and_existing_bytes(self):
        before = copy.deepcopy((self.handoff, self.review))
        path = intake(self.handoff, self.review, self.root)
        files = {p.relative_to(path): p.read_bytes() for p in path.rglob('*') if p.is_file()}
        self.assertEqual(intake(self.handoff, self.review, self.root), path)
        self.assertEqual(before, (self.handoff, self.review))
        self.assertEqual(files, {p.relative_to(path): p.read_bytes() for p in path.rglob('*') if p.is_file()})

    def test_native_workspace_accepts_pack_with_relations_and_missing_sales(self):
        path = intake(self.handoff, self.review, self.root)
        result = build_operating_workspace(path/'pack', private_root=self.root)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['manifest']['row_counts']['cash_events'], 4)
        self.assertEqual(result['manifest']['row_counts']['sales_aggregates'], 0)
        self.assertEqual(result['manifest']['coverage']['sales_aggregates']['status'], 'MISSING')
        self.assertEqual(result['manifest']['relationship_check']['foreign_key_violations'], [])

    def test_replay_refuses_unexpected_directories(self):
        path = intake(self.handoff, self.review, self.root)
        (path/'pack/extra').mkdir()
        with self.assertRaisesRegex(ValueError, 'existing_bundle'):
            intake(self.handoff, self.review, self.root)

    def test_replay_rejects_tampered_existing_bundle_without_overwriting(self):
        path = intake(self.handoff, self.review, self.root)
        target = path/'pack/cash_events.csv'
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'existing_bundle'):
            intake(self.handoff, self.review, self.root)
        self.assertEqual(target.read_bytes(), b'changed')

    def test_hash_and_review_bindings_fail_before_output(self):
        self.handoff['cash_entries'][0]['amount_cents'] += 1
        with self.assertRaisesRegex(ValueError, 'handoff_hash'):
            intake(self.handoff, self.review, self.root)
        rebind(self.handoff, self.review)
        self.review['source_instance_id'] = 'f'*32
        with self.assertRaisesRegex(ValueError, 'policy_binding'):
            intake(self.handoff, self.review, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_every_selected_cash_row_requires_explicit_review(self):
        for ids in ([], ['1'*32]*4, self.review['reviewed_cash_ids']+['f'*32]):
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'review_coverage'):
                prepare(self.handoff, dict(self.review, reviewed_cash_ids=ids))

    def test_balance_mismatch_rejects_without_publishing(self):
        self.review['closing_balance_cents'] += 1
        with self.assertRaisesRegex(ValueError, 'balance_reconciliation'):
            intake(self.handoff, self.review, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_money_and_duplicate_identities_are_strict(self):
        for value in (True, 1.5, '10000', None, -1):
            handoff, review = inputs()
            handoff['cash_entries'][0]['amount_cents'] = value
            rebind(handoff, review)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'cash_amount'):
                prepare(handoff, review)
        self.handoff['cash_entries'].append(dict(self.handoff['cash_entries'][0]))
        rebind(self.handoff, self.review)
        with self.assertRaisesRegex(ValueError, 'cash_identity'):
            prepare(self.handoff, self.review)

    def test_corrections_are_not_fictitious_cash_inflows(self):
        self.handoff['cash_entries'].append(dict(id='5'*32, type='expense_reverse', date='2026-09-30',
                                                amount_cents=3000, reverses='4'*32))
        self.review['reviewed_cash_ids'].append('5'*32)
        self.review['closing_balance_cents'] = 33000
        rebind(self.handoff, self.review)
        path = intake(self.handoff, self.review, self.root)
        parsed = parse_pack(path/'pack', private_root=self.root)
        self.assertEqual(len(parsed['tables']['cash_events']), 3)
        receipt = json.loads((path/'receipt.json').read_text())
        self.assertEqual(receipt['excluded_correction_ids'], ['4'*32, '5'*32])

    def test_cross_window_and_orphan_corrections_reject(self):
        self.handoff['cash_entries'].append(dict(id='5'*32, type='expense_reverse', date='2026-10-01',
                                                amount_cents=3000, reverses='4'*32))
        rebind(self.handoff, self.review)
        with self.assertRaisesRegex(ValueError, 'reversal_cross_window'):
            prepare(self.handoff, self.review)
        self.handoff['cash_entries'][-1]['reverses'] = 'f'*32
        rebind(self.handoff, self.review)
        with self.assertRaisesRegex(ValueError, 'reversal_pair'):
            prepare(self.handoff, self.review)

    def test_whole_day_boundaries_and_real_timezone_are_required(self):
        for key, value in [('opening_observed_at','2026-09-30T10:00:00-07:00'),
                           ('closing_observed_at','2026-09-30T23:59:59'),
                           ('timezone','Unknown/Zone'), ('cutoff_at','2026-09-30T23:59:59-08:00')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake(self.handoff, dict(self.review, **{key:value}), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_zero_rows_do_not_claim_zero_coverage_and_balances_remain_explicit(self):
        self.handoff['cash_entries'] = []
        self.review['reviewed_cash_ids'] = []
        self.review['closing_balance_cents'] = self.review['opening_balance_cents']
        rebind(self.handoff, self.review)
        parsed = parse_pack(intake(self.handoff, self.review, self.root)/'pack', private_root=self.root)
        self.assertEqual(parsed['metadata']['coverage']['cash_events']['status'], 'PARTIAL')
        self.assertEqual(parsed['tables']['cash_events'], [])

    def test_identifiers_survive_revision_but_not_another_installation(self):
        first = prepare(self.handoff, self.review)[1]['cash_events'][0]['event_id']
        self.handoff['source']['revision'] += 1
        rebind(self.handoff, self.review)
        self.assertEqual(prepare(self.handoff, self.review)[1]['cash_events'][0]['event_id'], first)
        self.handoff['source']['instance_id'] = self.review['source_instance_id'] = 'ed18d89a-32a0-4b85-b345-404867ab8ea2'
        rebind(self.handoff, self.review)
        self.assertNotEqual(prepare(self.handoff, self.review)[1]['cash_events'][0]['event_id'], first)

    def test_private_class_and_no_free_text_in_output(self):
        self.handoff['input_class'] = 'PRIVATE'
        self.handoff['orders'] = [{'contact':'DO_NOT_EXPORT', 'note':'DO_NOT_EXPORT'}]
        rebind(self.handoff, self.review)
        path = intake(self.handoff, self.review, self.root)
        parsed = parse_pack(path/'pack', private_root=self.root)
        self.assertEqual(parsed['metadata']['input_class'], 'PRIVATE')
        self.assertTrue(all(b'DO_NOT_EXPORT' not in p.read_bytes() for p in path.rglob('*') if p.is_file()))
        self.handoff['cash_entries'][0]['note'] = 'DO_NOT_EXPORT'
        rebind(self.handoff, self.review)
        with self.assertRaisesRegex(ValueError, 'cash_shape'):
            prepare(self.handoff, self.review)
