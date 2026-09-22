"""End-to-end v2 acceptance: scenarios, SQL bridges, interchange and replay."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from alma.storage import canonical
from alma.simulation import generate, core_projection
from alma.validation import validate
from alma.warehouse import build_warehouse, query_mart, ingest_batch, inspect_schema, MARTS, TABLE_COLUMNS
from alma.process_engine import atomic


def run(output,skip_tests=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    if not skip_tests:
        log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
        (output/'tests.log').write_text(log.getvalue(),encoding='utf-8')
        tests={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}
    else:tests={'passed':None,'mode':'scenario-only; not full acceptance'}
    records=[];snapshots={};source_hashes={};controls={}
    for scenario in ('normal','stock_pressure','promotion_illusion','cash_squeeze','missing_cost','broken_link'):
        data=generate(seed=42,scenario=scenario);source_hashes[scenario]=hashlib.sha256(canonical(data)).hexdigest()
        checks=validate(core_projection(data));issues=[r['id'] for r in checks if r['status']!='PASS']
        with tempfile.TemporaryDirectory(prefix='alma-v2-'+scenario+'-') as tmp:
            db=Path(tmp)/'warehouse.sqlite3'
            try:
                receipt=build_warehouse(data,db)
                marts={name:query_mart(db,name) for name in MARTS}
                controls[scenario]=receipt['control_results']
                finance=marts['finance_monthly'];inventory=marts['inventory_position'];cash=marts['cash_daily']
                def total(key):
                    vals=[r.get(key) for r in finance]
                    return sum(vals) if vals and all(v is not None for v in vals) else None
                summary={'units_ordered':sum(r['quantity'] for r in data['tables']['order_items']),
                    'net_revenue_cents':total('net_revenue_cents'),'cogs_cents':total('cogs_cents'),
                    'contribution_after_variable_cents':total('contribution_after_variable_cents'),
                    'operating_after_all_expenses_cents':total('operating_after_all_expenses_cents'),
                    'cash_movement_cents':sum(r['net_cash_change_cents'] for r in cash),
                    'minimum_cumulative_cash_cents':min((r['cumulative_cash_movement_cents'] for r in cash),default=None),
                    'supplier_payments_cents':sum(r['amount_cents'] for r in data['tables']['supplier_payments']),
                    'low_cover_variants':sum(r.get('cover_days') is not None and r['cover_days']<14 for r in inventory),
                    'count_discrepancies':sum(r.get('count_discrepancy_qty') not in (0,None) for r in inventory),
                    'unknown_cogs_months':sum(r.get('cogs_cents') is None for r in finance)}
                snapshots[scenario]=summary
                passed=all(r['passed']==1 for r in receipt['control_results']) and scenario!='broken_link'
                if scenario=='missing_cost':passed &= summary['unknown_cogs_months']>0 and summary['cogs_cents'] is None and summary['net_revenue_cents'] is not None
                records.append({'scenario':scenario,'status':'REVIEW' if scenario=='missing_cost' else 'PASS','passed':passed,'quality_issues':issues,'summary':summary,
                    'counts':{t:len(rows) for t,rows in data['tables'].items()},'mart_hashes':{m:hashlib.sha256(canonical(rows)).hexdigest() for m,rows in marts.items()}})
                if scenario=='normal':
                    idempotent=ingest_batch(db,data)['idempotent']
                    schema=inspect_schema(db)
                    replay_sources=canonical(data)==canonical(generate(seed=42,scenario=scenario))
                    second=generate(seed=43,scenario='normal');second_valid=not any(r['status']=='FAIL' for r in validate(core_projection(second)))
                    second_diff=canonical(second)!=canonical(data)
                    bad=generate(scenario='broken_link')
                    baseline={m:canonical(query_mart(db,m)) for m in MARTS}
                    rejected=False
                    try:ingest_batch(db,bad)
                    except ValueError:rejected=True
                    preserved=all(canonical(query_mart(db,m))==baseline[m] for m in MARTS)
                    checks_meta={'same_seed_source_replay':replay_sources,'second_seed_valid_and_different':second_valid and second_diff,'same_batch_noop':idempotent,'bad_batch_rejected_prior_marts_preserved':rejected and preserved,'source_tables':len(TABLE_COLUMNS),'sql_marts':len(MARTS)}
            except (ValueError,sqlite3.Error) as exc:
                records.append({'scenario':scenario,'status':'BLOCKED','passed':scenario=='broken_link','error':str(exc),'quality_issues':issues,'database_published':db.exists()})
    base=snapshots['normal'];stock=snapshots['stock_pressure'];promo=snapshots['promotion_illusion'];cash=snapshots['cash_squeeze']
    mechanisms={
      'stock_pressure_changes_inventory':stock['low_cover_variants']>base['low_cover_variants'] and stock['count_discrepancies']>base['count_discrepancies'],
      'promotion_volume_rises_contribution_falls':promo['units_ordered']>base['units_ordered'] and promo['contribution_after_variable_cents']<base['contribution_after_variable_cents'],
      'cash_squeeze_increases_supplier_cash_out':cash['supplier_payments_cents']>base['supplier_payments_cents'] and cash['minimum_cumulative_cash_cents']<base['minimum_cumulative_cash_cents']}
    artifact={'version':'2.0','synthetic':True,'tests':tests,'scenarios':records,'mechanism_checks':mechanisms,'replay_and_integrity':checks_meta,
              'source_hashes':source_hashes,'elapsed_seconds':round(time.perf_counter()-start,2),
              'passed':tests['passed'] is True and all(r['passed'] for r in records) and all(mechanisms.values()) and all(v for k,v in checks_meta.items() if isinstance(v,bool)),
              'limits':'Deterministic acceptance only; actual native execution is evaluated from dispatch/response/reviewer artifacts separately.'}
    atomic(output/'verification.json',artifact);atomic(output/'sql-controls.json',controls)
    cols=['scenario','units_ordered','net_revenue_cents','contribution_after_variable_cents','cash_movement_cents','low_cover_variants','unknown_cogs_months']
    lines=['# Scenario comparison','', '**All commercial values are synthetic; cents MXN. Fixed-seed what-if mechanisms are assumptions, not causal estimates.**','','| '+' | '.join(cols)+' |','| '+' | '.join('---' for _ in cols)+' |']
    for row in records:
        vals={'scenario':row['scenario'],**row.get('summary',{})};lines.append('| '+' | '.join(str(vals.get(k,'BLOCKED')) for k in cols)+' |')
    lines+=['','Mechanism checks: '+json.dumps(mechanisms), '','Same seed, changed seed, duplicate delivery and broken-batch preservation: '+json.dumps(checks_meta)]
    (output/'SCENARIO-COMPARISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'passed':artifact['passed'],'tests':tests,'scenario_results':[{k:r[k] for k in ('scenario','passed','status')} for r in records],'mechanism_checks':mechanisms,'output':str(output)},indent=2))
    return artifact

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/v2-verification');parser.add_argument('--skip-tests',action='store_true');args=parser.parse_args()
    result=run(args.output,args.skip_tests);raise SystemExit(0 if result['passed'] or args.skip_tests and all(r['passed'] for r in result['scenarios']) and all(result['mechanism_checks'].values()) else 1)
