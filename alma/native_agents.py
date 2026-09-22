"""Evidence-bound task exchange for actual native Codex analytical agents.

This module never pretends a rule template is an LLM call. It prepares portable
requests, validates submitted responses, and records native dispatch receipts.
Execution remains in the Codex task runtime; no separately billed API client.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .storage import canonical

ROOT = Path(__file__).resolve().parent.parent
ROLE_IDS = ('merchandiser', 'commerce_analyst', 'returns_analyst', 'finance_analyst', 'growth_analyst', 'market_researcher', 'evidence_reviewer')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def resolve_ref(evidence, ref):
    """Resolve a local JSON pointer only; never follow paths or remote URLs."""
    if not isinstance(ref, str) or not ref.startswith('/') or len(ref) > 500:
        raise ValueError('Evidence reference must be a JSON pointer')
    node = evidence
    for part in ref[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(node, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part): raise ValueError('Invalid array reference')
            try: node = node[int(part)]
            except IndexError: raise ValueError('Evidence reference is absent') from None
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else: raise ValueError('Evidence reference is absent: ' + ref)
    return node


def make_request(role, process_id, evidence, run_id):
    if role not in ROLE_IDS: raise ValueError('Unknown native agent role')
    contract = json.loads((ROOT/'agents'/(role+'.json')).read_text(encoding='utf-8-sig'))
    body = dict(version='2.0', run_id=run_id, process_id=process_id, role=role,
                evidence_hash=digest(evidence), contract=contract, evidence=evidence,
                response_contract='contracts/native-agent-response.schema.json',
                execution_mode='native-codex-task-bridge', synthetic_business_data=True)
    body['request_id'] = digest(body)
    return body


def verify_request(request):
    body = {k:v for k,v in request.items() if k!='request_id'}
    if digest(body) != request.get('request_id') or digest(request['evidence']) != request['evidence_hash']:
        raise ValueError('Request or evidence was modified')


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value)>12000:
        raise ValueError(label + ': nonempty bounded text required')


def validate_response(request, response):
    verify_request(request)
    keys = {'version','request_id','role','evidence_hash','summary','facts','unknowns','hypotheses','recommendations','challenges','verdict'}
    if not isinstance(response, dict) or set(response)!=keys: raise ValueError('Response fields differ from contract')
    if response['version']!='2.0' or any(response[k]!=request[k] for k in ('request_id','role','evidence_hash')):
        raise ValueError('Stale response or wrong role')
    if response['verdict'] not in ('REVIEW','BLOCKED','READY_FOR_OWNER'): raise ValueError('Invalid advisory verdict')
    _text(response['summary'],'summary')
    if not isinstance(response['facts'],list) or not 2<=len(response['facts'])<=30: raise ValueError('Two to thirty evidenced facts required')
    seen=set()
    for fact in response['facts']:
        if not isinstance(fact,dict) or set(fact)!={'id','statement','kind','evidence_refs','value'}: raise ValueError('Fact fields invalid')
        _text(fact['id'],'fact id'); _text(fact['statement'],'fact statement')
        if fact['id'] in seen: raise ValueError('Duplicate fact id')
        seen.add(fact['id'])
        if fact['kind'] not in ('observation','inference'): raise ValueError('Fact kind invalid')
        refs=fact['evidence_refs']
        if not isinstance(refs,list) or not 1<=len(refs)<=20: raise ValueError('Evidence references required')
        values=[resolve_ref(request['evidence'],r) for r in refs]
        if fact['kind']=='observation' and not any(type(v)==type(fact['value']) and v==fact['value'] for v in values):
            raise ValueError('Observation value does not equal its source')
        if fact['kind']=='inference' and fact['value'] is not None:
            raise ValueError('Inferences must not masquerade as measured values')
    for field in ('unknowns','hypotheses','challenges'):
        if not isinstance(response[field],list) or len(response[field])>30: raise ValueError('Invalid '+field)
        for item in response[field]: _text(item,field)
    if not response['unknowns']: raise ValueError('Synthetic limitations must be acknowledged')
    if not isinstance(response['recommendations'],list) or len(response['recommendations'])>(5 if request['process_id']=='weekly-growth-review' else 12): raise ValueError('Invalid recommendations')
    for rec in response['recommendations']:
        expected={'id','action','evidence_refs','primary_metric','guardrail','window','population','closure_rule','approval_required','execution'}
        if not isinstance(rec,dict) or set(rec)!=expected: raise ValueError('Recommendation fields invalid')
        for field in expected-{'evidence_refs','approval_required','execution'}: _text(rec[field],field)
        if rec['approval_required'] is not True or rec['execution']!='PROHIBITED': raise ValueError('No external execution authority')
        if not isinstance(rec['evidence_refs'],list) or not rec['evidence_refs']:raise ValueError('Recommendation evidence required')
        for ref in rec['evidence_refs']: resolve_ref(request['evidence'],ref)
    if request['role']=='evidence_reviewer' and not response['challenges']:
        raise ValueError('Independent reviewer must document at least one limitation or challenge')
    return {'valid':True,'request_id':request['request_id'],'facts_checked':len(response['facts']),
            'scope':'schema, immutable evidence, exact observation values and authority; prose meaning requires reviewer'}


def validate_dispatch(receipt, request):
    required={'request_id','role','provider','model','agent_id','response_sha256','recorded_by','mode','effort','started_at_utc','completed_at_utc','retry_history','parent_review'}
    if not isinstance(receipt,dict) or set(receipt)!=required: raise ValueError('Dispatch receipt fields invalid')
    if receipt['request_id']!=request['request_id'] or receipt['role']!=request['role']:raise ValueError('Dispatch/request mismatch')
    if receipt['provider']!='native-codex' or receipt['mode']!='live' or receipt['recorded_by']!='parent-runtime':
        raise ValueError('Only explicitly recorded native runtime dispatch accepted')
    if not re.fullmatch(r'gpt-(5\.6-(sol|luna|terra)|6-astra|5\.5)',receipt['model']):raise ValueError('Native model required')
    if not receipt['agent_id'].startswith('/root/'):raise ValueError('Actual native agent task id required')
    if not re.fullmatch('[0-9a-f]{64}',receipt['response_sha256']):raise ValueError('Response hash required')
    from datetime import datetime
    try:
        begin=datetime.fromisoformat(receipt['started_at_utc'].replace('Z','+00:00'))
        end=datetime.fromisoformat(receipt['completed_at_utc'].replace('Z','+00:00'))
        if begin.tzinfo is None or end.tzinfo is None or end<begin:raise ValueError('Invalid dispatch times')
    except (TypeError,ValueError):raise ValueError('UTC dispatch timestamps required') from None
    if receipt['effort'] not in ('low','medium','high','xhigh','max','ultra'):raise ValueError('Effort required')
    if not isinstance(receipt['retry_history'],list) or receipt['parent_review']!='schema-and-evidence-validated':raise ValueError('Parent validation receipt required')
    return True
