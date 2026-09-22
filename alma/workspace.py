"""Build a complete analytical workspace, source tables and executable processes."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from .storage import canonical
from .process_engine import atomic, start, definitions

ROOT=Path(__file__).resolve().parent.parent


def build_workspace(output, seed=42, scenario='normal', days=365, order_count=1200, input_path=None):
    from .simulation import generate, core_projection
    from .validation import validate
    from .warehouse import build_warehouse, query_mart, inspect_schema
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Workspace output must be empty; use process resume for existing runs')
    output.mkdir(parents=True,exist_ok=True)
    from .interchange import import_dataset
    from .warehouse import TABLE_COLUMNS
    data=import_dataset(input_path) if input_path else generate(seed=seed,scenario=scenario,days=days,order_count=order_count)
    atomic(output/'data.json',data)
    quality=validate(core_projection(data));atomic(output/'quality.json',quality)
    atomic(output/'research.json',json.loads((ROOT/'research/source-register.json').read_text(encoding='utf-8-sig')))
    (output/'tables').mkdir(exist_ok=True)
    atomic(output/'tables'/'metadata.json',data['metadata'])
    for name,rows in data['tables'].items():
        with (output/'tables'/(name+'.csv')).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=TABLE_COLUMNS[name]);writer.writeheader();writer.writerows(rows)
    if any(q['status']=='FAIL' for q in quality):
        atomic(output/'blocked.json',{'status':'BLOCKED','failed_checks':[q['id'] for q in quality if q['status']=='FAIL'],'synthetic':True})
        return {'status':'BLOCKED','output':str(output)}
    load=build_warehouse(data,output/'warehouse.sqlite3')
    atomic(output/'warehouse-load.json',load)
    # All SQL views are explicit files; request evidence and CSV share the same rows.
    names=sorted({m for d in definitions().values() for m in d['marts']})
    (output/'marts').mkdir(exist_ok=True)
    mart_rows={}
    for name in names:
        rows=query_mart(output/'warehouse.sqlite3',name);mart_rows[name]=rows
        atomic(output/'marts'/(name+'.json'),rows)
        if rows:
            with (output/'marts'/(name+'.csv')).open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lineage={'schema':inspect_schema(output/'warehouse.sqlite3'),'sql':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text(encoding='utf-8-sig')} for p in sorted((ROOT/'models').rglob('*.sql'))}}
    atomic(output/'lineage.json',lineage)
    from .experimentation import analyze_experiments
    atomic(output/'experiment-analysis.json',analyze_experiments(data))
    from .workspace_report import write_report
    write_report(data,mart_rows,quality,output)
    files=[p for p in output.rglob('*') if p.is_file() and p.suffix!='.sqlite3']
    manifest={'version':'2.0','status':'REVIEW' if any(q['status']!='PASS' for q in quality) else 'PASS',
              'metadata':data['metadata'],'counts':{t:len(r) for t,r in data['tables'].items()},
              'sha256':{str(p.relative_to(output)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              'database':'warehouse.sqlite3','database_rebuild':'python -m alma workspace --output NEW_EMPTY_DIRECTORY',
              'scope':'Synthetic analytical system; no external actions; native requests await actual Codex execution.'}
    atomic(output/'workspace.json',manifest)
    states=[start(output,pid) for pid in definitions()]
    return {'status':manifest['status'],'output':str(output),'tables':len(data['tables']),'orders':len(data['tables']['orders']),
            'marts':len(names),'processes':{s['process_id']:s['status'] for s in states}}
