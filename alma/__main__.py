"""One-command analytical reports and offline verification."""
import argparse
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from . import __version__
from .analytics import analyze
from .fixtures import generate
from .storage import canonical, export_csv, import_csv, load_sqlite, save_sqlite, write_json
from .validation import ContractError, validate

ROOT=Path(__file__).resolve().parent.parent
SCENARIOS=('normal','missing_cost','negative_stock','missing_payment','duplicate_event')


def build(output, seed=42, scenario='normal', csv_input=None):
    output=Path(output).resolve()
    marker=output/'.alma-generated'
    if output.exists() and any(output.iterdir()) and (not marker.is_file() or marker.read_text(encoding='utf-8')!='alma-generated-v1'):
        raise ValueError('Output already exists and is not an Alma generated folder; choose a new folder')
    output.mkdir(parents=True,exist_ok=True)
    data=import_csv(csv_input) if csv_input else generate(seed,scenario)
    checks=validate(data)
    if any(q['id'].startswith('fk_') and q['status']=='FAIL' for q in checks):
        raise ContractError('Unresolved foreign keys; report withheld')
    report=analyze(data)
    marker.write_text('alma-generated-v1',encoding='utf-8')
    dbpath=output/'alma.sqlite3'
    if dbpath.is_symlink():raise ValueError('Refusing symlink database')
    if dbpath.exists():dbpath.unlink()
    save_sqlite(data,dbpath)
    if load_sqlite(dbpath)!=data:raise AssertionError('SQLite roundtrip mismatch')
    write_json(output/'data.json',data)
    write_json(output/'report.json',report)
    write_json(output/'decisions.json',report['decisions'])
    write_json(output/'quality.json',checks)
    export_csv(data,output/'csv')
    from .reporting import write_reports
    rendered=write_reports(report,output)
    files=['alma.sqlite3','data.json','report.json','decisions.json','quality.json',*rendered,'csv/metadata.json']
    files += ['csv/'+name+'.csv' for name in sorted(data['tables'])]
    receipt=dict(schema_version='1.0',software_version=__version__,policy_version='1.0-provisional',synthetic=True,seed=data['metadata']['seed'],scenario=data['metadata']['scenario'],as_of=data['metadata']['as_of'],status=report['meta']['status'],counts={k:len(v) for k,v in data['tables'].items()},sha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in files})
    write_json(output/'receipt.json',receipt)
    return report


def verify(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    outcomes=[]
    expected={'normal':set(),'missing_cost':{'cost_coverage'},'negative_stock':{'stock_nonnegative'},'missing_payment':{'payment_reconciliation'},'duplicate_event':{'unique_movements'}}
    with tempfile.TemporaryDirectory(prefix='alma-verify-') as temp:
        for scenario in SCENARIOS:
            folder=Path(temp)/scenario
            report=build(folder,scenario=scenario)
            problems={q['id'] for q in report['quality'] if q['status']!='PASS'}
            ok=(report['meta']['status']=='PASS' and not problems) if scenario=='normal' else report['meta']['status']=='BLOCKED' and expected[scenario]<=problems
            roundtrip=import_csv(folder/'csv')==generate(42,scenario)
            outcomes.append(dict(scenario=scenario,passed=ok and roundtrip,status=report['meta']['status'],problems=sorted(problems),csv_roundtrip=roundtrip))
        r1=build(Path(temp)/'replay-a');r2=build(Path(temp)/'replay-b')
        deterministic=canonical(r1)==canonical(r2)
    from .evaluation import evaluate_agents
    agent_evals=evaluate_agents()
    write_json(output/'agent-evals.json',agent_evals)
    evidence=dict(agent_evals_passed=agent_evals['passed'],schema_version='1.0',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),scenario_results=outcomes,reproducible=deterministic,passed=agent_evals['passed'] and result.wasSuccessful() and result.testsRun>0 and deterministic and all(x['passed'] for x in outcomes))
    write_json(output/'verification.json',evidence)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return 0 if evidence['passed'] else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description='Alma de Lujo reproducible synthetic growth analytics')
    sub=parser.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo');demo.add_argument('--output',default='build/demo');demo.add_argument('--seed',type=int,default=42);demo.add_argument('--scenario',choices=SCENARIOS,default='normal');demo.add_argument('--csv-input')
    check=sub.add_parser('verify');check.add_argument('--output',default='build/verification')
    args=parser.parse_args(argv)
    try:
        if args.command=='verify':return verify(args.output)
        report=build(args.output,args.seed,args.scenario,args.csv_input)
        print(json.dumps(dict(output=str(Path(args.output).resolve()),status=report['meta']['status'],scenario=report['meta']['scenario'],synthetic=True),ensure_ascii=False))
        return 0 if report['meta']['status']=='PASS' else 2
    except (OSError,ValueError,AssertionError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
