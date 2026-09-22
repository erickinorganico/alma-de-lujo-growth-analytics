"""Audit publishable files without printing secret values. Run from repository root."""
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PATTERNS={
    'github_token':re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
    'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'aws_access_key':re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'secret_assignment':re.compile(r'(?im)^\s*(?:api_key|oauth_token|password|secret_access_key)\s*[:=]\s*[\"\']?[A-Za-z0-9/+_-]{20,}'),
}


def approved_synthetic_database(path,name):
    import hashlib
    import sqlite3
    allowed={'evidence/v0.2/workspace/warehouse.sqlite3','evidence/v0.2/workspace/lifecycle/lifecycle.sqlite3'}
    if name not in allowed:raise ValueError('Database is not an approved synthetic release artifact')
    workspace=ROOT/'evidence/v0.2/workspace'
    manifest=json.loads((workspace/'workspace.json').read_text(encoding='utf-8-sig'))
    relative=path.relative_to(workspace).as_posix()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['binary_sha256'].get(relative):raise ValueError('Synthetic database hash mismatch')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if name.endswith('/warehouse.sqlite3'):
            metadata=json.loads(db.execute("SELECT value FROM warehouse_manifest WHERE key='metadata'").fetchone()[0])
            if metadata.get('synthetic') is not True:raise ValueError('Database is not synthetic')
        elif db.execute('SELECT COUNT(*) FROM lifecycle_events WHERE synthetic<>1').fetchone()[0]:raise ValueError('Lifecycle contains nonsynthetic events')
        return '\n'.join(db.iterdump())
    finally:db.close()


def audit():
    result=subprocess.run(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT,capture_output=True,check=True)
    names=sorted(set(n for n in result.stdout.decode('utf-8').split('\0') if n))
    findings=[];checked=0
    for name in names:
        path=ROOT/name
        if any(p in {'.local','.local-archive','.venv','build','__pycache__'} for p in Path(name).parts):
            findings.append(dict(file=name,issue='excluded_directory_tracked'));continue
        if not path.is_file():continue
        if path.suffix.lower() in {'.png','.pdf','.gif','.zip'}:continue
        try:
            content=approved_synthetic_database(path,name) if path.suffix.lower()=='.sqlite3' else path.read_text(encoding='utf-8-sig')
        except ValueError:
            findings.append(dict(file=name,issue='invalid_synthetic_database_or_text'));continue
        except UnicodeDecodeError:
            findings.append(dict(file=name,issue='unexpected_binary'));continue
        checked+=1
        for rule,pattern in PATTERNS.items():
            for match in pattern.finditer(content):findings.append(dict(file=name,line=content.count('\n',0,match.start())+1,issue=rule))
    license_present=(ROOT/'LICENSE').is_file()
    out=dict(schema_version='1.0',text_files_checked=checked,license_present=license_present,findings=findings,passed=not findings and license_present,limits='Pattern audit of Git publishable scope; not proof that arbitrary user text is free of PII. All shipped business records are generated synthetic fixtures.')
    print(json.dumps(out,indent=2))
    return 0 if out['passed'] else 1

if __name__=='__main__':raise SystemExit(audit())
