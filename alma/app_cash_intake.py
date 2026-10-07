"""Convert an app handoff and explicit balance evidence into a cash-only pack."""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
from uuid import UUID

from .operating_contracts import SOURCE_NAMES, canonical_json, columns_for
from .operating_interchange import parse_pack

POLICY_KEYS = {
    'schema', 'handoff_sha256', 'source_instance_id', 'window_start', 'window_end',
    'cutoff_at', 'timezone', 'opening_balance_cents', 'closing_balance_cents',
    'opening_observed_at', 'closing_observed_at', 'evidence_ref', 'reviewed_cash_ids',
}


def fail(code):
    # Never echo supplied values, paths, contacts, or notes in diagnostics.
    raise ValueError('app_cash.' + code)


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def identifier(kind, instance, value):
    return kind + '-' + digest([instance, value])[:40]


def day(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            fail('date')
        return parsed
    except (TypeError, ValueError):
        fail('date')


def prepare(handoff, policy):
    """Return source rows and provenance; never infer evidence from a ledger."""
    if not isinstance(handoff, dict) or handoff.get('schema') != 'alma.app-analytics-handoff.v1':
        fail('handoff_schema')
    claimed = handoff.get('handoff_sha256')
    if claimed != digest({k: v for k, v in handoff.items() if k != 'handoff_sha256'}):
        fail('handoff_hash')
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS or policy['schema'] != 'alma.app-cash-review.v1':
        fail('policy_schema')
    source = handoff.get('source', {})
    try:
        instance = str(UUID(source['instance_id']))
    except (KeyError, TypeError, ValueError, AttributeError):
        fail('instance')
    if policy['source_instance_id'] != instance or policy['handoff_sha256'] != claimed:
        fail('policy_binding')
    if type(source.get('revision')) is not int or source['revision'] < 0:
        fail('revision')
    if handoff.get('currency') != 'MXN' or handoff.get('input_class') not in {'PRIVATE', 'SYNTHETIC_EXAMPLE'}:
        fail('classification')
    start, end = day(policy['window_start']), day(policy['window_end'])
    if start > end:
        fail('window')
    try:
        opening = datetime.fromisoformat(policy['opening_observed_at'])
        closing = datetime.fromisoformat(policy['closing_observed_at'])
        cutoff = datetime.fromisoformat(policy['cutoff_at'])
        if any(t.tzinfo is None or t.utcoffset() is None for t in (opening, closing, cutoff)):
            fail('timestamps')
        # App cash has dates, not intraday timestamps: require whole-day evidence.
        if opening.date() != start or opening.time() != time.min or closing.date() != end or closing.time() != time(23, 59, 59):
            fail('whole_days_required')
        if opening > closing or closing > cutoff or cutoff.date() != end:
            fail('timestamps')
    except (TypeError, ValueError):
        fail('timestamps')
    if any(type(policy[k]) is not int for k in ('opening_balance_cents', 'closing_balance_cents')):
        fail('balance_integer')
    evidence = policy['evidence_ref']
    if not isinstance(evidence, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9._:-]{0,63}', evidence):
        fail('evidence_ref')
    cash = handoff.get('cash_entries')
    if not isinstance(cash, list):
        fail('cash_shape')
    by_id = {}
    for row in cash:
        if not isinstance(row, dict) or set(row) - {'id', 'type', 'date', 'amount_cents', 'order_id', 'reverses'}:
            fail('cash_shape')
        key = row.get('id')
        if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{32}', key) or key in by_id:
            fail('cash_identity')
        if row.get('type') not in {'payment', 'refund', 'expense', 'expense_reverse'}:
            fail('cash_kind')
        if type(row.get('amount_cents')) is not int or not 0 < row['amount_cents'] <= 999_999_999:
            fail('cash_amount')
        day(row.get('date'))
        by_id[key] = row
    selected = {key: row for key, row in by_id.items() if start <= day(row['date']) <= end}
    reviewed = policy['reviewed_cash_ids']
    if not isinstance(reviewed, list) or any(not isinstance(k, str) for k in reviewed):
        fail('reviewed_ids')
    if len(set(reviewed)) != len(reviewed) or set(reviewed) != set(selected):
        fail('review_coverage')
    excluded = set()
    reversed_ids = set()
    for key, row in by_id.items():
        if row['type'] != 'expense_reverse':
            if 'reverses' in row:
                fail('reversal_kind')
            continue
        original_id = row.get('reverses')
        original = by_id.get(original_id)
        if not original or original['type'] != 'expense' or original['amount_cents'] != row['amount_cents'] or original['date'] > row['date'] or original_id in reversed_ids:
            fail('reversal_pair')
        reversed_ids.add(original_id)
        if (key in selected) != (original_id in selected):
            fail('reversal_cross_window')
        if key in selected:
            # App reversal corrects a recorded expense; it is not an observed inflow.
            excluded.update((key, original_id))
    tables = {name: [] for name in SOURCE_NAMES}
    scenario = identifier('app', instance, 'observed-cash')
    links = []
    for key, row in sorted(selected.items()):
        if key in excluded:
            continue
        event = identifier('event', instance, key)
        tables['cash_events'].append(dict(
            event_id=event, economic_event_id=identifier('cash', instance, key),
            supersedes_event_id=None, scenario_id=scenario, event_date=row['date'],
            level='RECONCILED', direction='INFLOW' if row['type'] == 'payment' else 'OUTFLOW',
            amount_cents=row['amount_cents'], currency='MXN', obligation_id=None,
            payment_id=None, source_ref=identifier('source', instance, key)))
        links.append(dict(app_cash_id=key, event_id=event))
    net = sum(r['amount_cents'] * (1 if r['direction'] == 'INFLOW' else -1) for r in tables['cash_events'])
    if policy['closing_balance_cents'] - policy['opening_balance_cents'] != net:
        fail('balance_reconciliation')
    tables['cash_balance_evidence'].append(dict(
        balance_evidence_id=identifier('balance', instance, [str(start), str(end)]),
        scenario_id=scenario, period_start=str(start), period_end=str(end),
        opening_balance_cents=policy['opening_balance_cents'], closing_balance_cents=policy['closing_balance_cents'],
        opening_observed_at=policy['opening_observed_at'], closing_observed_at=policy['closing_observed_at'],
        evidence_status='OBSERVED', source_ref=evidence))
    coverage = {name: dict(status='MISSING', window_start=None, window_end=None) for name in SOURCE_NAMES}
    for name in ('cash_events', 'cash_balance_evidence'):
        coverage[name] = dict(status='PARTIAL', window_start=str(start), window_end=str(end))
    metadata = dict(contract_version='operating-v1', input_class=handoff['input_class'],
                    cutoff_at=policy['cutoff_at'], timezone=policy['timezone'], currency='MXN', coverage=coverage)
    # Validate all three instants against the engine's IANA timezone policy.
    from .operating_contracts import validate_metadata
    validate_metadata(metadata)
    for stamp in ('opening_observed_at', 'closing_observed_at'):
        probe = dict(metadata, cutoff_at=policy[stamp], coverage={name: dict(status='MISSING', window_start=None, window_end=None) for name in SOURCE_NAMES})
        validate_metadata(probe)
    receipt = dict(schema='alma.app-cash-receipt.v1', handoff_sha256=claimed,
                   source_instance_id=instance, source_revision=source['revision'],
                   policy_sha256=digest(policy), event_links=links,
                   excluded_correction_ids=sorted(excluded), outside_window_ids=sorted(set(by_id) - set(selected)),
                   net_cash_cents=net, scope='cash_only', sales_and_inventory_imported=False)
    return metadata, tables, receipt


def pack_files(metadata, tables):
    files = {'metadata.json': canonical_json(metadata) + b'\n'}
    for name in SOURCE_NAMES:
        text = io.StringIO(newline='')
        writer = csv.DictWriter(text, fieldnames=columns_for(name), lineterminator='\n')
        writer.writeheader()
        writer.writerows(tables[name])
        files[name + '.csv'] = text.getvalue().encode('utf-8')
    return files


def intake(handoff, policy, output_root):
    """Validate the native pack before exclusive publication; exact replay is safe."""
    metadata, tables, receipt = prepare(handoff, policy)
    files = pack_files(metadata, tables)
    root = Path(output_root).resolve(strict=True)
    if not root.is_dir():
        fail('output_root')
    bundle_id = digest([receipt['handoff_sha256'], receipt['policy_sha256']])
    destination = root / bundle_id
    with tempfile.TemporaryDirectory(prefix='.app-cash-', dir=root) as folder:
        staging = Path(folder)
        for name, content in files.items():
            (staging/name).write_bytes(content)
        parsed = parse_pack(staging, private_root=root)
        receipt['normalized_rows_digest'] = parsed['normalized_rows_digest']
        receipt['pack_sha256'] = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        expected = {'pack/' + name: content for name, content in files.items()}
        expected['receipt.json'] = canonical_json(receipt) + b'\n'
        if destination.exists() or destination.is_symlink():
            pack = destination/'pack'
            if destination.is_symlink() or destination.is_junction() or not destination.is_dir() or pack.is_symlink() or pack.is_junction() or not pack.is_dir():
                fail('existing_bundle')
            if {p.name for p in destination.iterdir()} != {'receipt.json', 'pack'} or {p.name for p in pack.iterdir()} != set(files):
                fail('existing_bundle')
            if any((destination/name).is_symlink() or not (destination/name).is_file() or (destination/name).read_bytes() != value for name, value in expected.items()):
                fail('existing_bundle')
            return destination
        destination.mkdir()  # Exclusive: a concurrent creator is never replaced.
        (destination/'pack').mkdir()
        for name, content in expected.items():
            with (destination/name).open('xb') as stream:
                stream.write(content)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True, help='Existing private directory, never committed')
    args = parser.parse_args()
    handoff = json.loads(args.handoff.read_text(encoding='utf-8'))
    policy = json.loads(args.review.read_text(encoding='utf-8'))
    intake(handoff, policy, args.output_root)
    print('Validated cash-only operating-v1 pack saved; no analytical cycle executed.')


if __name__ == '__main__':
    main()
