"""Reconcile commercial lines against physical app units, without importing them."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
from uuid import UUID

from .app_cash_intake import digest
from .operating_contracts import canonical_json

SIZES = ('XS', 'S', 'M', 'L', 'XL')
TRANSITIONS = {
    ('draft', 'reserve'): 'reserved', ('draft', 'deliver'): 'delivered',
    ('draft', 'cancel'): 'cancelled', ('reserved', 'deliver'): 'delivered',
    ('reserved', 'cancel'): 'cancelled', ('delivered', 'return'): 'returned',
}


def fail(code):
    # Diagnostics never echo supplied notes, contacts, identifiers or paths.
    raise ValueError('app_inventory.' + code)


def integer(value, minimum=0, maximum=999_999_999):
    if type(value) is not int or not minimum <= value <= maximum:
        fail('integer')
    return value


def day(value):
    try:
        if date.fromisoformat(value).isoformat() != value:
            fail('date')
    except (TypeError, ValueError):
        fail('date')
    return value


def token(value, pattern=r'[A-Za-z0-9_-]{1,200}'):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        fail('identity')
    return value


def rows(value):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        fail('rows')
    return value


def index(value, key='id', pattern=r'[A-Za-z0-9_-]{1,200}'):
    result = {}
    for row in rows(value):
        identity = token(row.get(key), pattern)
        if identity in result:
            fail('duplicate_identity')
        result[identity] = row
    return result


def members(value, components):
    if not isinstance(value, list) or not value:
        fail('components')
    for item in value:
        token(item, r'[A-Za-z0-9_-]{1,40}')
        if item not in components:
            fail('unknown_component')
    if len(set(value)) != len(value):
        fail('duplicate_component')
    return value


def lifecycle(order):
    history = rows(order.get('history'))
    created = day(order.get('date'))
    if not history or history[0] != {'type': 'draft', 'date': created}:
        fail('history_origin')
    status, previous, events = 'draft', created, {}
    for row in history[1:]:
        if set(row) != {'type', 'date'}:
            fail('history_shape')
        current_day = day(row['date'])
        kind = token(row['type'])
        if current_day < previous or (status, kind) not in TRANSITIONS:
            fail('history_transition')
        status = TRANSITIONS[status, kind]
        previous = events[kind] = current_day
    if status != order.get('status'):
        fail('history_status')
    if status == 'returned':
        if type(order.get('restocked')) is not bool:
            fail('return_disposition')
    elif 'restocked' in order:
        fail('return_disposition')
    return events


def reconcile(handoff):
    """Check one revision; missing counts stay unknown and cash stays separate."""
    if not isinstance(handoff, dict) or handoff.get('schema') != 'alma.app-analytics-handoff.v1':
        fail('schema')
    claimed = handoff.get('handoff_sha256')
    if claimed != digest({k: v for k, v in handoff.items() if k != 'handoff_sha256'}):
        fail('handoff_hash')
    source = handoff.get('source')
    if not isinstance(source, dict):
        fail('source')
    try:
        instance = str(UUID(source['instance_id']))
    except (KeyError, TypeError, ValueError, AttributeError):
        fail('instance')
    revision = integer(source.get('revision'))
    state_hash = token(source.get('state_sha256'), r'[0-9a-f]{64}')
    if handoff.get('input_class') not in {'PRIVATE', 'SYNTHETIC_EXAMPLE'} or handoff.get('currency') != 'MXN':
        fail('classification')
    components = index(handoff.get('physical_components'), pattern=r'[A-Za-z0-9_-]{1,40}')
    products = index(handoff.get('commercial_products'))
    for component in components.values():
        integer(component.get('pieces_per_unit'), 1)
    for product in products.values():
        members(product.get('component_ids'), components)
    orders = index(handoff.get('orders'), pattern=r'[0-9a-f]{32}')
    movements = index(handoff.get('physical_movements'), pattern=r'[0-9a-f]{32}')
    counts = index(handoff.get('physical_counts'), key='sku')
    skus = {f'{component}-{size}': (component, size) for component in components for size in SIZES}
    if set(counts) - set(skus):
        fail('unknown_sku')
    expected, held, commercial, links = {}, Counter(), [], []
    for order_id, order in sorted(orders.items()):
        events = lifecycle(order)
        lines = rows(order.get('lines'))
        if not 1 <= len(lines) <= 50:
            fail('lines')
        required, total = Counter(), 0
        for ordinal, line in enumerate(lines):
            if type(line.get('line_index')) is not int or line['line_index'] != ordinal:
                fail('line_identity')
            product_id = token(line.get('product_id'))
            if product_id not in products or line.get('size') not in SIZES:
                fail('product_or_size')
            component_ids = members(line.get('component_ids'), components)
            units = integer(line.get('units'), 1, 1_000_000)
            price = integer(line.get('price_cents'), 1)
            total += units * price
            for component in sorted(component_ids):
                sku = f'{component}-{line["size"]}'
                required[sku] += units
                links.append(dict(order_id=order_id, line_index=ordinal, component_sku=sku,
                                  required_units=units))
            commercial.append(dict(
                order_id=order_id, line_index=ordinal, product_id=product_id, size=line['size'],
                ordered_units=units, unit_price_cents=price, ordered_amount_cents=units * price,
                delivered_units=units if 'deliver' in events else 0,
                returned_units=units if 'return' in events else 0,
                restocked_units=units if order.get('restocked') else 0,
                delivery_date=events.get('deliver'), return_date=events.get('return'),
                historical_components_differ=set(component_ids) != set(products[product_id]['component_ids'])))
        if integer(order.get('total_cents')) != total:
            fail('order_total')
        requirements = order.get('requirements')
        if not isinstance(requirements, dict):
            fail('requirements')
        for sku, quantity in requirements.items():
            token(sku)
            integer(quantity, 1)
        if requirements != dict(required):
            fail('requirements')
        if order['status'] == 'reserved':
            held.update(required)
        for kind, event in (('delivery', 'deliver'), ('return', 'return')):
            if event in events and (kind == 'delivery' or order['restocked']):
                for sku, quantity in required.items():
                    expected[order_id, kind, sku] = (events[event], -quantity if kind == 'delivery' else quantity)
    actual, posting_sequence, by_sku, sequences = {}, {}, defaultdict(list), []
    for movement_id, movement in movements.items():
        sequence = integer(movement.get('sequence'), 1)
        sku = token(movement.get('sku'))
        order_id = token(movement.get('order_id'), r'[0-9a-f]{32}')
        kind = token(movement.get('type'))
        if sku not in skus or order_id not in orders or kind not in {'delivery', 'return'}:
            fail('movement_relation')
        delta = integer(movement.get('delta'), -999_999_999)
        key = (order_id, kind, sku)
        if key in actual:
            fail('duplicate_post')
        actual[key] = (day(movement.get('date')), delta)
        posting_sequence[key] = sequence
        sequences.append(sequence)
        by_sku[sku].append((sequence, movement['date'], delta, movement_id))
    if sorted(sequences) != list(range(1, len(movements) + 1)):
        fail('movement_sequence')
    if actual != expected:
        fail('movement_reconciliation')
    for (order_id, kind, sku), sequence in posting_sequence.items():
        if kind == 'return' and sequence < posting_sequence[order_id, 'delivery', sku]:
            fail('movement_chronology')
    positions = []
    for sku, (component, size) in sorted(skus.items()):
        ledger = sorted(by_sku[sku])
        if [r[1] for r in ledger] != sorted(r[1] for r in ledger):
            fail('movement_chronology')
        count = counts.get(sku)
        on_hand = reserved = available = cursor = count_date = None
        applied = []
        if count:
            cursor = integer(count.get('cursor', 0), 0, len(movements))
            count_date = day(count.get('date'))
            on_hand = integer(count.get('on_hand'))
            reserved = count.get('reserved')
            if reserved is not None:
                reserved = integer(reserved, 0, on_hand) + held[sku]
            for sequence, movement_day, delta, movement_id in ledger:
                if sequence <= cursor:
                    if movement_day > count_date:
                        fail('count_chronology')
                    continue
                if movement_day < count_date:
                    fail('count_chronology')
                on_hand += delta
                if on_hand < 0:
                    fail('negative_stock')
                applied.append(movement_id)
            available = None if reserved is None else on_hand - reserved
            if on_hand < 0 or (available is not None and available < 0):
                fail('negative_stock')
        positions.append(dict(component_sku=sku, component_id=component, size=size,
                              pieces_per_unit=components[component]['pieces_per_unit'],
                              count_date=count_date, count_cursor=cursor, on_hand_units=on_hand,
                              reserved_units=reserved, available_units=available,
                              active_order_reserved_units=held[sku], applied_movement_ids=applied))
    result = dict(
        schema='alma.app-inventory-reconciliation.v1', input_class=handoff['input_class'],
        currency='MXN', source_instance_id=instance, source_revision=revision,
        source_state_sha256=state_hash, handoff_sha256=claimed,
        reconciliation_status='PASS', scope='app_revision_snapshot', import_ready=False,
        coverage='UNDECLARED', commercial_lines=commercial, component_links=links,
        physical_positions=positions,
        missing_count_skus=[r['component_sku'] for r in positions if r['on_hand_units'] is None],
        unknown_reservation_skus=[r['component_sku'] for r in positions if r['reserved_units'] is None],
        reconciled_movement_ids=sorted(movements),
        pending=['sellable_sku_and_component_bridge', 'channel_mapping', 'coverage_and_cutoff',
                 'revenue_and_return_recognition', 'historical_cost_policy', 'operating_v1_pack_validation'])
    result['report_sha256'] = digest(result)
    return result


def write_report(handoff, destination):
    result = reconcile(handoff)
    # Exclusive creation also rejects a destination equal to the input file.
    with Path(destination).open('xb') as stream:
        stream.write(canonical_json(result) + b'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private JSON path')
    args = parser.parse_args()
    write_report(json.loads(args.handoff.read_text(encoding='utf-8')), args.output)
    print('App quantities reconciled; private report saved; import_ready=false.')


if __name__ == '__main__':
    main()
