"""Durable, replayable analytical process state machines; no business side effects."""
from __future__ import annotations
from contextlib import contextmanager
import json
from pathlib import Path
from .storage import canonical
from .native_agents import digest, make_request, validate_response, validate_dispatch, verify_request

ROOT=Path(__file__).resolve().parent.parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic(path,value):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents): raise ValueError('Symlink output is prohibited')
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    if temp.is_symlink(): raise ValueError('Symlink temporary file is prohibited')
    temp.write_bytes(canonical(value));temp.replace(path)


def definitions():
    return {p.stem:read(p) for p in sorted((ROOT/'processes').glob('*.json'))}


@contextmanager
def locked(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    lock=folder/'.run-lock'
    try: handle=lock.open('x',encoding='utf-8')
    except FileExistsError: raise ValueError('Process is locked; inspect interrupted owner before removing .run-lock') from None
    try:
        handle.write('exclusive process mutation');handle.close();yield
    finally: lock.unlink(missing_ok=True)


def verify_events(folder):
    path=Path(folder)/'events.json'
    events=read(path) if path.exists() else []
    previous='GENESIS'
    for index,event in enumerate(events):
        if event['sequence']!=index+1 or event['previous_hash']!=previous or digest({k:v for k,v in event.items() if k!='hash'})!=event['hash']:
            raise ValueError('Process event chain was modified')
        previous=event['hash']
    return events


def transition(folder,state,status,step,details):
    events=verify_events(folder)
    event=dict(sequence=len(events)+1,previous_hash=events[-1]['hash'] if events else 'GENESIS',
               from_status=state.get('status','NEW'),to_status=status,step=step,details=details)
    event['hash']=digest(event);events.append(event)
    atomic(Path(folder)/'events.json',events)
    state.update(status=status,step=step,event_hash=event['hash'])
    atomic(Path(folder)/'state.json',state)
    return state


def _manifest(workspace):
    manifest=read(workspace/'workspace.json')
    for name,expected in manifest['sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Invalid manifest artifact path')
        p=workspace/name
        if p.is_symlink() or not p.is_file():raise ValueError('Workspace artifact missing: '+name)
        import hashlib
        if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError('Workspace artifact modified: '+name)
    return manifest


def _evidence(workspace,definition,manifest):
    return dict(metadata=manifest['metadata'],counts=manifest['counts'],
                quality=read(workspace/'quality.json'),
                marts={name:read(workspace/'marts'/(name+'.json')) for name in definition['marts']},
                sources=read(workspace/'research.json'),
                lineage=read(workspace/'lineage.json'),
                experiment_analysis=read(workspace/'experiment-analysis.json') if (workspace/'experiment-analysis.json').exists() else {})


def _write_request(folder,request):
    dest=Path(folder)/'tasks'/(request['role']+'.request.json')
    if dest.exists() and read(dest)!=request:raise ValueError('Existing request differs; start a new workspace for changed inputs')
    atomic(dest,request)
    return dest.name


def start(workspace,process_id):
    workspace=Path(workspace).resolve()
    all_defs=definitions()
    if process_id not in all_defs:raise ValueError('Unknown process')
    manifest=_manifest(workspace);definition=all_defs[process_id]
    folder=workspace/'processes'/process_id
    with locked(folder):
        if (folder/'state.json').exists():return _resume(workspace,folder,manifest)
        evidence=_evidence(workspace,definition,manifest)
        state=dict(version='2.0',run_id=digest({'input':manifest['sha256'],'definition':definition})[:24],
                   process_id=process_id,definition_hash=digest(definition),workspace_hash=digest(manifest),
                   owner=definition['owner'],input_hash=digest(evidence),responses={},status='NEW')
        transition(folder,state,'VALIDATING','source_contract',{'required_tables':definition['required_tables']})
        gates=[q for q in evidence['quality'] if q['status']=='FAIL']
        unknown=[t for t in definition['required_tables'] if manifest['metadata']['coverage'].get(t) is not True]
        if gates or unknown:
            return transition(folder,state,'BLOCKED','source_contract',{'failed_checks':[g['id'] for g in gates],'unknown_coverage':unknown})
        transition(folder,state,'ANALYZING','sql_marts',{'marts':definition['marts'],'evidence_hash':digest(evidence)})
        request=make_request(definition['agent'],process_id,evidence,state['run_id'])
        _write_request(folder,request)
        return transition(folder,state,'WAITING_AGENT','native_analysis',{'request_id':request['request_id'],'role':definition['agent']})


def _resume(workspace,folder,manifest):
    state=read(folder/'state.json');events=verify_events(folder)
    if not events or state['event_hash']!=events[-1]['hash'] or state['status']!=events[-1]['to_status']:
        raise ValueError('Process checkpoint differs from event chain')
    definition=definitions()[state['process_id']]
    if digest(definition)!=state['definition_hash'] or digest(manifest)!=state['workspace_hash']:
        raise ValueError('Inputs or process changed; create a new workspace')
    if state['status'] not in ('WAITING_AGENT','WAITING_REVIEW'):return state
    role=definition['agent'] if state['status']=='WAITING_AGENT' else 'evidence_reviewer'
    request=read(folder/'tasks'/(role+'.request.json'));verify_request(request)
    response_path=folder/'tasks'/(role+'.response.json')
    receipt_path=folder/'tasks'/(role+'.dispatch.json')
    if not response_path.exists() or not receipt_path.exists():return state
    response=read(response_path);receipt=read(receipt_path)
    validate_response(request,response);validate_dispatch(receipt,request)
    if digest(response)!=receipt['response_sha256']:raise ValueError('Response differs from native dispatch receipt')
    state['responses'][role]={'sha256':digest(response),'request_id':request['request_id'],'agent_id':receipt['agent_id'],'model':receipt['model']}
    if response['verdict']=='BLOCKED':return transition(folder,state,'BLOCKED','agent_review',{'role':role,'summary':response['summary']})
    if role!='evidence_reviewer':
        evidence=dict(request['evidence']);evidence['analysis']=response
        reviewer=make_request('evidence_reviewer',state['process_id'],evidence,state['run_id'])
        _write_request(folder,reviewer)
        return transition(folder,state,'WAITING_REVIEW','independent_review',{'request_id':reviewer['request_id'],'analyst':role})
    analyst=read(folder/'tasks'/(definition['agent']+'.response.json'))
    analyst_receipt=read(folder/'tasks'/(definition['agent']+'.dispatch.json'))
    if receipt['agent_id']==analyst_receipt['agent_id']:raise ValueError('Reviewer must be a different native agent')
    # Revalidate accepted analyst after waiting; a changed response cannot silently enter a packet.
    analyst_request=read(folder/'tasks'/(definition['agent']+'.request.json'))
    validate_response(analyst_request,analyst)
    if digest(analyst)!=state['responses'][definition['agent']]['sha256']:raise ValueError('Accepted analyst response changed')
    packet=dict(version='2.0',run_id=state['run_id'],process_id=state['process_id'],synthetic=True,
                status='READY_FOR_OWNER' if response['verdict']=='READY_FOR_OWNER' else 'REVIEW',
                input_hash=state['input_hash'],facts=analyst['facts'],unknowns=analyst['unknowns'],
                hypotheses=analyst['hypotheses'],recommendations=analyst['recommendations'],
                review=response,agent_receipts=state['responses'],external_execution='PROHIBITED')
    atomic(folder/'decision-packet.json',packet)
    return transition(folder,state,packet['status'],'decision_packet',{'sha256':digest(packet),'external_execution':'PROHIBITED'})


def resume(workspace,process_id):
    workspace=Path(workspace).resolve();manifest=_manifest(workspace)
    if process_id not in definitions():raise ValueError('Unknown process')
    folder=workspace/'processes'/process_id
    with locked(folder):return _resume(workspace,folder,manifest)


def submit(workspace,process_id,response_path,receipt_path):
    workspace=Path(workspace).resolve();manifest=_manifest(workspace)
    if process_id not in definitions():raise ValueError('Unknown process')
    folder=workspace/'processes'/process_id
    with locked(folder):
        state=read(folder/'state.json');role=read(response_path).get('role')
        expected=definitions()[process_id]['agent'] if state['status']=='WAITING_AGENT' else 'evidence_reviewer' if state['status']=='WAITING_REVIEW' else None
        if role!=expected:raise ValueError('No task currently waiting for this role')
        request=read(folder/'tasks'/(role+'.request.json'));response=read(response_path);receipt=read(receipt_path)
        validate_response(request,response);validate_dispatch(receipt,request)
        if digest(response)!=receipt['response_sha256']:raise ValueError('Response hash mismatch')
        atomic(folder/'tasks'/(role+'.response.json'),response)
        atomic(folder/'tasks'/(role+'.dispatch.json'),receipt)
        return _resume(workspace,folder,manifest)


def status(workspace):
    workspace=Path(workspace).resolve();_manifest(workspace)
    result=[]
    for p in sorted((workspace/'processes').glob('*/state.json')):
        state=read(p);events=verify_events(p.parent)
        if state['event_hash']!=events[-1]['hash']:raise ValueError('Checkpoint hash mismatch')
        result.append({k:state[k] for k in ('process_id','status','step','run_id')})
    return result
