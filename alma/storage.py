"""Synthetic-only interchange and SQLite persistence; strict fixed table names."""
import csv
import json
import sqlite3
from pathlib import Path
from .validation import SCHEMA, INTEGER, NULLABLE, ContractError, check_structure


def canonical(data):
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')


def write_json(path, data):
    Path(path).write_bytes(canonical(data))


def export_csv(data, folder):
    check_structure(data)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'metadata.json',data['metadata'])
    for table,cols in SCHEMA.items():
        with (folder/(table+'.csv')).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=cols.split());writer.writeheader();writer.writerows(data['tables'][table])


def import_csv(folder):
    folder=Path(folder)
    metadata=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
    tables={}
    for table,cols in SCHEMA.items():
        file=folder/(table+'.csv')
        if file.stat().st_size>10_000_000:raise ContractError('CSV exceeds local safety limit')
        with file.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=cols.split():raise ContractError('CSV columns must match contract exactly: '+table)
            rows=[]
            for row in reader:
                if None in row or any(v is None for v in row.values()):raise ContractError('Ragged CSV row')
                for key,value in row.items():
                    if value=='' and (table,key) in NULLABLE:row[key]=None
                    elif key.endswith('_cents') or key in INTEGER:
                        try:row[key]=int(value)
                        except ValueError:raise ContractError('Expected integer: '+table+'.'+key)
                rows.append(row)
            tables[table]=rows
    return check_structure(dict(metadata=metadata,tables=tables))


def save_sqlite(data,path):
    check_structure(data)
    # New artifact only. Never overwrite a database passed by a user.
    path=Path(path)
    if path.exists():raise FileExistsError('Database exists; choose a fresh output directory')
    db=sqlite3.connect(path)
    try:
        with db:
            db.execute('CREATE TABLE metadata (document TEXT NOT NULL)')
            db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(data['metadata']),))
            for table,cols in SCHEMA.items():
                columns=cols.split()
                definition=','.join('"'+c+'" '+('INTEGER' if c.endswith('_cents') or c in INTEGER else 'TEXT') for c in columns)
                db.execute('CREATE TABLE "'+table+'" ('+definition+')')
                marks=','.join('?' for _ in columns)
                db.executemany('INSERT INTO "'+table+'" VALUES ('+marks+')',[tuple(r[c] for c in columns) for r in data['tables'][table]])
    finally:db.close()


def load_sqlite(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:
        metadata=json.loads(db.execute('SELECT document FROM metadata').fetchone()[0])
        tables={table:[dict(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')] for table in SCHEMA}
        return check_structure(dict(metadata=metadata,tables=tables))
    finally:db.close()
