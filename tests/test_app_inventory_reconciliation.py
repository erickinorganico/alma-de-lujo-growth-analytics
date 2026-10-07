"""Synthetic app-shaped facts; no customer database or network is used."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from alma.app_cash_intake import digest
from alma.app_inventory_reconciliation import reconcile, write_report


def bind(handoff):
    handoff['handoff_sha256'] = digest({k: v for k, v in handoff.items() if k != 'handoff_sha256'})
    return handoff


def order(number, product, components, units=1, status='delivered'):
    history = [dict(type='draft', date='2026-09-29')]
    if status == 'reserved':
        history.append(dict(type='reserve', date='2026-09-30'))
    elif status in {'delivered', 'returned'}:
        history.append(dict(type='deliver', date='2026-09-30'))
    elif status == 'cancelled':
        history.append(dict(type='cancel', date='2026-09-30'))
    result = dict(id=f'{number:032x}', date='2026-09-29', status=status,
                  lines=[dict(line_index=0, product_id=product, component_ids=components,
                              size='S', units=units, price_cents=10000)],
                  requirements={f'{component}-S': units for component in components},
                  total_cents=units*10000, history=history)
    if status == 'returned':
        history.append(dict(type='return', date='2026-10-01'))
        result['restocked'] = True
    return result


def movement(number, order_number, sku, delta, kind='delivery', day='2026-09-30'):
    return dict(id=f'{number+100:032x}', sequence=number, order_id=f'{order_number:032x}',
                sku=sku, delta=delta, type=kind, date=day)


def fixture():
    return bind(dict(
        schema='alma.app-analytics-handoff.v1', input_class='SYNTHETIC_EXAMPLE', currency='MXN',
        source=dict(instance_id='ed18d89a-32a0-4b85-b345-404867ab8ea1', revision=12, state_sha256='a'*64),
        physical_components=[dict(id='A', pieces_per_unit=1), dict(id='B', pieces_per_unit=2)],
        commercial_products=[dict(id='COM-SET', component_ids=['A','B']), dict(id='COM-SINGLE', component_ids=['A'])],
        physical_counts=[dict(sku=f'{c}-S', on_hand=10, reserved=0, cursor=0, date='2026-09-29') for c in ('A','B')],
        orders=[order(1, 'COM-SET', ['A','B']), order(2, 'COM-SINGLE', ['A'], units=2)],
        physical_movements=[movement(1,1,'A-S',-1), movement(2,1,'B-S',-1), movement(3,2,'A-S',-2)],
        cash_entries=[], cost_versions=[]))


def position(result, sku):
    return next(r for r in result['physical_positions'] if r['component_sku'] == sku)


class AppInventoryReconciliationTests(unittest.TestCase):
    def check_bad(self, change, code):
        data = fixture()
        change(data)
        with self.assertRaisesRegex(ValueError, code):
            reconcile(bind(data))

    def test_shared_component_is_deducted_once_per_physical_unit(self):
        result = reconcile(fixture())
        self.assertEqual(sum(r['delivered_units'] for r in result['commercial_lines']), 3)
        self.assertEqual(len(result['component_links']), 3)
        self.assertEqual(position(result, 'A-S')['on_hand_units'], 7)
        self.assertEqual(position(result, 'B-S')['on_hand_units'], 9)
        self.assertEqual(position(result, 'B-S')['pieces_per_unit'], 2)
        self.assertEqual(len(result['physical_positions']), 10)
        self.assertFalse(result['import_ready'])
        self.assertEqual(result['coverage'], 'UNDECLARED')
        self.assertNotIn('net_revenue_cents', result['commercial_lines'][0])

    def test_same_day_recount_uses_cursor_not_date_and_does_not_double_deduct(self):
        data = fixture()
        data['physical_counts'][0].update(on_hand=9, cursor=2, date='2026-09-30')
        result = reconcile(bind(data))
        actual = position(result, 'A-S')
        self.assertEqual(actual['on_hand_units'], 7)
        self.assertEqual(actual['applied_movement_ids'], [data['physical_movements'][2]['id']])

    def test_absent_counts_and_unknown_reservations_do_not_become_zero(self):
        data = fixture()
        data['physical_counts'][0]['reserved'] = None
        result = reconcile(bind(data))
        self.assertEqual(position(result, 'A-S')['on_hand_units'], 7)
        self.assertIsNone(position(result, 'A-S')['available_units'])
        self.assertIsNone(position(result, 'A-M')['on_hand_units'])
        self.assertIn('A-M', result['missing_count_skus'])
        self.assertIn('A-S', result['unknown_reservation_skus'])

    def test_active_reservations_are_added_but_cancelled_and_draft_orders_are_not(self):
        data = fixture()
        data['orders'].extend([order(3,'COM-SET',['A','B'],status='reserved'),
                               order(4,'COM-SET',['A','B'],status='draft'),
                               order(5,'COM-SET',['A','B'],status='cancelled')])
        data['physical_counts'][0]['reserved'] = 2
        result = reconcile(bind(data))
        self.assertEqual(position(result, 'A-S')['reserved_units'], 3)
        self.assertEqual(position(result, 'A-S')['available_units'], 4)
        self.assertEqual(sum(r['delivered_units'] for r in result['commercial_lines']), 3)

    def test_full_return_restock_requires_each_component_but_no_cash_refund(self):
        data = fixture()
        data['orders'][0] = order(1,'COM-SET',['A','B'],status='returned')
        data['physical_movements'].extend([movement(4,1,'A-S',1,'return','2026-10-01'),
                                           movement(5,1,'B-S',1,'return','2026-10-01')])
        result = reconcile(bind(data))
        self.assertEqual(position(result,'A-S')['on_hand_units'], 8)
        self.assertEqual(position(result,'B-S')['on_hand_units'], 10)
        self.assertEqual(result['commercial_lines'][0]['return_date'], '2026-10-01')
        self.assertEqual(result['commercial_lines'][0]['restocked_units'], 1)

    def test_non_restocked_return_never_invents_physical_receipt(self):
        data = fixture()
        data['orders'][0] = order(1,'COM-SET',['A','B'],status='returned')
        data['orders'][0]['restocked'] = False
        result = reconcile(bind(data))
        self.assertEqual(position(result,'A-S')['on_hand_units'], 7)
        self.assertEqual(result['commercial_lines'][0]['returned_units'], 1)
        self.assertEqual(result['commercial_lines'][0]['restocked_units'], 0)
        data['physical_movements'].append(movement(4,1,'A-S',1,'return','2026-10-01'))
        with self.assertRaisesRegex(ValueError, 'movement_reconciliation'):
            reconcile(bind(data))

    def test_historical_line_composition_is_not_replaced_by_current_catalog(self):
        data = fixture()
        data['commercial_products'][0]['component_ids'] = ['B']
        result = reconcile(bind(data))
        self.assertTrue(result['commercial_lines'][0]['historical_components_differ'])
        self.assertEqual(position(result,'A-S')['on_hand_units'], 7)

    def test_multiple_lines_sharing_component_reconcile_one_aggregate_movement(self):
        data = fixture()
        first, second = data['orders']
        first['lines'].append(dict(second['lines'][0], line_index=1))
        first['requirements']['A-S'] = 3
        first['total_cents'] = 30000
        data['orders'] = [first]
        data['physical_movements'] = [movement(1,1,'A-S',-3),movement(2,1,'B-S',-1)]
        result = reconcile(bind(data))
        self.assertEqual(position(result,'A-S')['on_hand_units'], 7)
        self.assertEqual(len(result['component_links']), 3)
        self.assertEqual(len(result['reconciled_movement_ids']), 2)

    def test_duplicate_post_cannot_hide_behind_matching_total(self):
        def change(data):
            data['physical_movements'][2]['delta'] = -1
            data['physical_movements'].append(movement(4,2,'A-S',-1))
        self.check_bad(change, 'duplicate_post')

    def test_missing_wrong_and_orphan_movements_reject(self):
        self.check_bad(lambda d: d['physical_movements'].pop(), 'movement_reconciliation')
        self.check_bad(lambda d: d['physical_movements'][0].update(delta=-2), 'movement_reconciliation')
        self.check_bad(lambda d: d['physical_movements'][0].update(order_id='f'*32), 'movement_relation')
        self.check_bad(lambda d: d['physical_movements'][0].update(date='2026-09-29'), 'movement_reconciliation')

    def test_bad_requirements_totals_and_boolean_quantities_reject(self):
        self.check_bad(lambda d: d['orders'][0]['requirements'].update({'A-S':2}), 'requirements')
        self.check_bad(lambda d: d['orders'][0].update(total_cents=9999), 'order_total')
        for field in ('units','price_cents'):
            self.check_bad(lambda d: d['orders'][0]['lines'][0].update({field:True}), 'integer')
        self.check_bad(lambda d: d['orders'][0]['lines'][0].update(line_index=True), 'line_identity')
        self.check_bad(lambda d: d['orders'][0]['requirements'].update({'A-S':True}), 'integer')

    def test_duplicate_components_and_source_identities_reject(self):
        self.check_bad(lambda d: d['orders'][0]['lines'][0].update(component_ids=['A','A']), 'duplicate_component')
        self.check_bad(lambda d: d['orders'].append(copy.deepcopy(d['orders'][0])), 'duplicate_identity')
        self.check_bad(lambda d: d['physical_counts'].append(copy.deepcopy(d['physical_counts'][0])), 'duplicate_identity')
        self.check_bad(lambda d: d['physical_movements'].append(copy.deepcopy(d['physical_movements'][0])), 'duplicate_identity')

    def test_sequence_and_count_cursor_integrity_reject(self):
        self.check_bad(lambda d: d['physical_movements'][0].update(sequence=2), 'movement_sequence')
        self.check_bad(lambda d: d['physical_counts'][0].update(cursor=4), 'integer')
        self.check_bad(lambda d: d['physical_counts'][0].update(cursor=True), 'integer')
        self.check_bad(lambda d: d['physical_counts'][0].update(date='2026-10-01'), 'count_chronology')
        self.check_bad(lambda d: d['physical_counts'][0].update(cursor=3), 'count_chronology')

    def test_inconsistent_lifecycle_rejects_before_reconstructing_stock(self):
        self.check_bad(lambda d: d['orders'][0].update(status='draft'), 'history_status')
        self.check_bad(lambda d: d['orders'][0]['history'].append(dict(type='deliver',date='2026-09-30')), 'history_transition')
        self.check_bad(lambda d: d['orders'][0]['history'][1].update(date='2026-09-28'), 'history_transition')
        self.check_bad(lambda d: d['orders'][0].update(restocked=True), 'return_disposition')

    def test_negative_reconstructed_stock_or_availability_rejects(self):
        self.check_bad(lambda d: d['physical_counts'][0].update(on_hand=2), 'negative_stock')
        self.check_bad(lambda d: d['physical_counts'][0].update(reserved=8), 'negative_stock')

    def test_same_day_return_cannot_precede_its_delivery_sequence(self):
        data = fixture()
        data['orders'][0] = order(1,'COM-SET',['A','B'],status='returned')
        data['orders'][0]['history'][-1]['date'] = '2026-09-30'
        data['physical_movements'].extend([movement(4,1,'A-S',1,'return'), movement(5,1,'B-S',1,'return')])
        data['physical_movements'][0]['sequence'] = 4
        data['physical_movements'][3]['sequence'] = 1
        with self.assertRaisesRegex(ValueError, 'movement_chronology'):
            reconcile(bind(data))

    def test_later_return_cannot_hide_negative_stock_after_anchor(self):
        data = fixture()
        data['orders'][0] = order(1,'COM-SET',['A','B'],status='returned')
        data['physical_movements'].extend([movement(4,1,'A-S',1,'return','2026-10-01'),
                                           movement(5,1,'B-S',1,'return','2026-10-01')])
        data['physical_counts'][0]['on_hand'] = 2
        with self.assertRaisesRegex(ValueError, 'negative_stock'):
            reconcile(bind(data))

    def test_input_class_binding_determinism_and_private_fields(self):
        data = fixture()
        data['input_class'] = 'PRIVATE'
        data['orders'][0]['contact'] = 'PRIVATE_SENTINEL'
        data['orders'][0]['cost_snapshots'] = [{'note':'PRIVATE_SENTINEL'}]
        data['commercial_products'][0]['label'] = 'PRIVATE_SENTINEL'
        bind(data)
        before = copy.deepcopy(data)
        result = reconcile(data)
        self.assertEqual(result, reconcile(data))
        self.assertEqual(data, before)
        self.assertEqual(result['input_class'], 'PRIVATE')
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
        self.assertEqual(result['report_sha256'], digest({k:v for k,v in result.items() if k!='report_sha256'}))
        data['source']['revision'] += 1
        with self.assertRaisesRegex(ValueError, 'handoff_hash'):
            reconcile(data)
        self.assertNotEqual(reconcile(bind(data))['report_sha256'], result['report_sha256'])

    def test_empty_ledger_has_unknown_counts_and_never_claims_native_readiness(self):
        data = fixture()
        for key in ('orders','physical_counts','physical_movements'):
            data[key] = []
        result = reconcile(bind(data))
        self.assertEqual(len(result['missing_count_skus']), 10)
        self.assertFalse(result['import_ready'])
        self.assertEqual(result['coverage'], 'UNDECLARED')

    def test_malformed_shape_reports_code_without_private_values(self):
        self.check_bad(lambda d: d.update(orders='PRIVATE_SENTINEL'), 'app_inventory.rows')
        self.check_bad(lambda d: d['physical_counts'][0].update(sku='PRIVATE SENTINEL'), 'app_inventory.identity')
        self.check_bad(lambda d: d['source'].update(instance_id='PRIVATE_SENTINEL'), 'app_inventory.instance')

    def test_exclusive_output_and_invalid_input_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'private.json'
            result = write_report(fixture(), path)
            before = path.read_bytes()
            self.assertEqual(json.loads(before), result)
            with self.assertRaises(FileExistsError):
                write_report(fixture(), path)
            self.assertEqual(before, path.read_bytes())
            invalid = fixture()
            invalid['physical_movements'].pop()
            with self.assertRaises(ValueError):
                write_report(bind(invalid), Path(folder)/'invalid.json')
            self.assertEqual([p.name for p in Path(folder).iterdir()], ['private.json'])


if __name__ == '__main__':
    unittest.main()
