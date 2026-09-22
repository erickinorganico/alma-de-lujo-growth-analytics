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
        try:content=path.read_text(encoding='utf-8-sig')
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
