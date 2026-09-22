"""Durable, replayable analytical process state machines; no business side effects."""
from __future__ import annotations
from contextlib import contextmanager
import json
from pathlib import Path
from .storage import canonical
from .native_agents import digest, make_request, validate_response, validate_dispatch, verify_request

ROOT=Path(__file__).resolve().parent.parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def read_json_clone(value):return json.loads(canonical(value))


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
    checkpoint={**state,'status':status,'step':step};checkpoint.pop('event_hash',None)
    checkpoint=read_json_clone(checkpoint)
    event=dict(checkpoint=checkpoint,sequence=len(events)+1,previous_hash=events[-1]['hash'] if events else 'GENESIS',
               from_status=state.get('status','NEW'),to_status=status,step=step,details=details)
    event['hash']=digest(event);events.append(event)
    atomic(Path(folder)/'events.json',events)
    state.update(status=status,step=step,event_hash=event['hash'])
    atomic(Path(folder)/'state.json',state)
    return state


def _manifest(workspace):
    manifest=read(workspace/'workspace.json')
    for name,expected in {**manifest['sha256'],**manifest.get('binary_sha256',{})}.items():
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
                experiment_analysis=read(workspace/'experiment-analysis.json') if (workspace/'experiment-analysis.json').exists() else {},
                lifecycle=read(workspace/'lifecycle/summary.json') if (workspace/'lifecycle/summary.json').exists() else {})


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


def _bound_context(workspace,folder,manifest):
    events=verify_events(folder)
    state_path=folder/'state.json'
    expected_state={**events[-1]['checkpoint'],'event_hash':events[-1]['hash']} if events else None
    if not state_path.exists() and expected_state is not None:
        atomic(state_path,expected_state)
    state=read(state_path)
    # Events are the atomic commit record. Recover the only legitimate interrupted
    # write window: the prior exact checkpoint remains after a committed event.
    if len(events)>1 and state=={**events[-2]['checkpoint'],'event_hash':events[-2]['hash']}:
        atomic(state_path,expected_state);state=expected_state
    if not events or state.get('event_hash')!=events[-1]['hash']:
        raise ValueError('Process checkpoint differs from event chain')
    projected={k:v for k,v in state.items() if k!='event_hash'}
    if projected!=events[-1].get('checkpoint'):
        raise ValueError('Full process checkpoint differs from journal anchor')
    definition=definitions()[state['process_id']]
    if digest(definition)!=state['definition_hash'] or digest(manifest)!=state['workspace_hash']:
        raise ValueError('Inputs or process changed; create a new workspace')
    evidence=_evidence(workspace,definition,manifest)
    run_id=digest({'input':manifest['sha256'],'definition':definition})[:24]
    if state['input_hash']!=digest(evidence) or state['run_id']!=run_id or state['owner']!=definition['owner']:
        raise ValueError('Process identity or input evidence binding changed')
    return state,events,definition,evidence


def _request_bound(folder,expected):
    path=folder/'tasks'/(expected['role']+'.request.json')
    request=read(path);verify_request(request)
    if request!=expected:raise ValueError('Task request differs from immutable process evidence')
    return request


def _accepted(folder,request,anchored=None):
    role=request['role'];response=read(folder/'tasks'/(role+'.response.json'))
    receipt=read(folder/'tasks'/(role+'.dispatch.json'))
    validate_response(request,response);validate_dispatch(receipt,request)
    if digest(response)!=receipt['response_sha256']:raise ValueError('Response differs from native dispatch receipt')
    entry={'sha256':digest(response),'request_id':request['request_id'],'agent_id':receipt['agent_id'],'model':receipt['model'],'dispatch_hash':digest(receipt)}
    if anchored is not None and entry!=anchored:raise ValueError('Accepted response or dispatch changed')
    return response,receipt,entry


def _packet(state,definition,analyst,reviewer):
    return dict(version='2.0',run_id=state['run_id'],process_id=state['process_id'],synthetic=True,
        status='READY_FOR_OWNER' if reviewer['verdict']=='READY_FOR_OWNER' else 'REVIEW',
        input_hash=state['input_hash'],facts=analyst['facts'],unknowns=analyst['unknowns'],
        hypotheses=analyst['hypotheses'],recommendations=analyst['recommendations'],
        review=reviewer,agent_receipts=state['responses'],external_execution='PROHIBITED')


def _validate_completed(workspace,folder,manifest):
    state,events,definition,evidence=_bound_context(workspace,folder,manifest)
    if state['status'] not in ('READY_FOR_OWNER','REVIEW','WAITING_AGENT','WAITING_REVIEW'):return state
    analyst_request=_request_bound(folder,make_request(definition['agent'],state['process_id'],evidence,state['run_id']))
    if state['status']=='WAITING_AGENT':return state
    analyst,ar,_=_accepted(folder,analyst_request,state['responses'].get(definition['agent']))
    review_evidence={**evidence,'analysis':analyst}
    reviewer_request=_request_bound(folder,make_request('evidence_reviewer',state['process_id'],review_evidence,state['run_id']))
    if state['status']=='WAITING_REVIEW':return state
    reviewer,rr,_=_accepted(folder,reviewer_request,state['responses'].get('evidence_reviewer'))
    if ar['agent_id']==rr['agent_id']:raise ValueError('Reviewer must be a different native agent')
    packet=read(folder/'decision-packet.json');expected=_packet(state,definition,analyst,reviewer)
    if packet!=expected or digest(packet)!=events[-1]['details']['sha256']:
        raise ValueError('Terminal decision packet was modified')
    return state


def _resume(workspace,folder,manifest):
    state,events,definition,evidence=_bound_context(workspace,folder,manifest)
    if state['status'] in ('READY_FOR_OWNER','REVIEW'):return _validate_completed(workspace,folder,manifest)
    if state['status'] not in ('WAITING_AGENT','WAITING_REVIEW'):return state
    analyst_request=make_request(definition['agent'],state['process_id'],evidence,state['run_id'])
    _request_bound(folder,analyst_request)
    if state['status']=='WAITING_AGENT':
        role=definition['agent'];request=analyst_request
    else:
        analyst,analyst_receipt,_=_accepted(folder,analyst_request,state['responses'][definition['agent']])
        role='evidence_reviewer'
        request=_request_bound(folder,make_request(role,state['process_id'],{**evidence,'analysis':analyst},state['run_id']))
    if events[-1]['details'].get('request_id')!=request['request_id']:
        raise ValueError('Task request differs from emitted event identity')
    if not (folder/'tasks'/(role+'.response.json')).exists() or not (folder/'tasks'/(role+'.dispatch.json')).exists():return state
    response,receipt,entry=_accepted(folder,request)
    state['responses'][role]=entry
    if response['verdict']=='BLOCKED':return transition(folder,state,'BLOCKED','agent_review',{'role':role,'summary':response['summary']})
    if role!='evidence_reviewer':
        reviewer=make_request('evidence_reviewer',state['process_id'],{**evidence,'analysis':response},state['run_id'])
        _write_request(folder,reviewer)
        return transition(folder,state,'WAITING_REVIEW','independent_review',{'request_id':reviewer['request_id'],'analyst':role})
    if receipt['agent_id']==analyst_receipt['agent_id']:raise ValueError('Reviewer must be a different native agent')
    packet=_packet(state,definition,analyst,response)
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
        state,events,definition,evidence=_bound_context(workspace,folder,manifest);role=read(response_path).get('role')
        expected=definitions()[process_id]['agent'] if state['status']=='WAITING_AGENT' else 'evidence_reviewer' if state['status']=='WAITING_REVIEW' else None
        if role!=expected:raise ValueError('No task currently waiting for this role')
        expected_request=make_request(definition['agent'],process_id,evidence,state['run_id'])
        _request_bound(folder,expected_request)
        if role=='evidence_reviewer':
            analyst,ar,_=_accepted(folder,expected_request,state['responses'][definition['agent']])
            expected_request=make_request(role,process_id,{**evidence,'analysis':analyst},state['run_id'])
        request=_request_bound(folder,expected_request);response=read(response_path);receipt=read(receipt_path)
        validate_response(request,response);validate_dispatch(receipt,request)
        if digest(response)!=receipt['response_sha256']:raise ValueError('Response hash mismatch')
        atomic(folder/'tasks'/(role+'.response.json'),response)
        atomic(folder/'tasks'/(role+'.dispatch.json'),receipt)
        return _resume(workspace,folder,manifest)


def status(workspace):
    workspace=Path(workspace).resolve();manifest=_manifest(workspace)
    result=[]
    for p in sorted((workspace/'processes').glob('*/state.json')):
        state=_validate_completed(workspace,p.parent,manifest)
        result.append({k:state[k] for k in ('process_id','status','step','run_id')})
    return result
