import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from alma import process_engine as engine
from alma.native_agents import digest, make_request, validate_response
from alma.storage import canonical


def response(request,role=None):
    # Disposable fixture, not a native execution claim.
    refs=['/counts/orders','/metadata/synthetic']
    return dict(version='2.0',request_id=request['request_id'],role=role or request['role'],evidence_hash=request['evidence_hash'],summary='Synthetic test fixture only',
      facts=[dict(id='f1',statement='Synthetic order count',kind='observation',evidence_refs=[refs[0]],value=12),dict(id='f2',statement='Synthetic origin',kind='observation',evidence_refs=[refs[1]],value=True)],
      unknowns=['Real sales unknown'],hypotheses=[],recommendations=[dict(id='r1',action='Review evidence',evidence_refs=[refs[0]],primary_metric='net contribution',guardrail='no spend',window='14 days',population='eligible customers',closure_rule='review at day 14',approval_required=True,execution='PROHIBITED')],challenges=['Synthetic data does not prove business impact'],verdict='READY_FOR_OWNER')


def receipt(req,res,agent='/root/disposable_test_analyst'):
    return dict(request_id=req['request_id'],role=req['role'],provider='native-codex',model='gpt-5.6-sol',agent_id=agent,response_sha256=digest(res),recorded_by='parent-runtime',mode='live',effort='medium',started_at_utc='2026-09-22T00:00:00Z',completed_at_utc='2026-09-22T00:01:00Z',retry_history=[],parent_review='schema-and-evidence-validated')


class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.request=make_request('finance_analyst','finance-close',{'counts':{'orders':12},'metadata':{'synthetic':True}},'fixture')

    def test_exact_values_stale_hash_and_authority(self):
        original=response(self.request)
        self.assertTrue(validate_response(self.request,original)['valid'])
        for mutate in (lambda r:r['facts'][0].update(value=13),lambda r:r.update(evidence_hash='stale'),lambda r:r['recommendations'][0].update(execution='EXECUTE'),lambda r:r['facts'][0].update(evidence_refs=['/../secret'])):
            bad=copy.deepcopy(original);mutate(bad)
            with self.assertRaises(ValueError):validate_response(self.request,bad)
        changed=copy.deepcopy(self.request);changed['evidence']['counts']['orders']=13
        with self.assertRaises(ValueError):validate_response(changed,original)


class ProcessFixture:
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        defs=engine.definitions();coverage={t:True for d in defs.values() for t in d['required_tables']}
        self.meta={'synthetic':True,'coverage':coverage};self.files={}
        for name,value in [('quality.json',[]),('research.json',{'sources':[]}),('lineage.json',{})]:engine.atomic(self.root/name,value)
        for name in {m for d in defs.values() for m in d['marts']}:engine.atomic(self.root/'marts'/(name+'.json'),[{'value':12}])
        for p in self.root.rglob('*.json'):self.files[p.relative_to(self.root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifest={'metadata':self.meta,'counts':{'orders':12},'sha256':self.files}
        engine.atomic(self.root/'workspace.json',self.manifest)

    def tearDown(self):self.temp.cleanup()

    def deliver(self,role,agent):
        folder=self.root/'processes/finance-close'
        req=engine.read(folder/'tasks'/(role+'.request.json'));res=response(req)
        engine.atomic(self.root/'response.json',res);engine.atomic(self.root/'receipt.json',receipt(req,res,agent))
        return engine.submit(self.root,'finance-close',self.root/'response.json',self.root/'receipt.json')

class ProcessTests(ProcessFixture,unittest.TestCase):
    def test_run_resume_review_and_no_external_action(self):
        state=engine.start(self.root,'finance-close');self.assertEqual(state['status'],'WAITING_AGENT')
        before=engine.verify_events(self.root/'processes/finance-close')
        self.assertEqual(engine.start(self.root,'finance-close'),state)
        self.assertEqual(before,engine.verify_events(self.root/'processes/finance-close'))
        self.assertEqual(self.deliver('finance_analyst','/root/disposable_test_analyst')['status'],'WAITING_REVIEW')
        final=self.deliver('evidence_reviewer','/root/disposable_test_reviewer')
        self.assertEqual(final['status'],'READY_FOR_OWNER')
        packet=engine.read(self.root/'processes/finance-close/decision-packet.json')
        self.assertEqual(packet['external_execution'],'PROHIBITED')
        self.assertEqual(len(packet['agent_receipts']),2)

    def test_unknown_required_coverage_blocks(self):
        self.manifest['metadata']['coverage']['payments']=False;engine.atomic(self.root/'workspace.json',self.manifest)
        self.assertEqual(engine.start(self.root,'finance-close')['status'],'BLOCKED')

    def test_changed_evidence_and_event_chain_fail(self):
        engine.start(self.root,'finance-close')
        engine.atomic(self.root/'quality.json',[{'status':'FAIL'}])
        with self.assertRaisesRegex(ValueError,'modified'):engine.resume(self.root,'finance-close')
        engine.atomic(self.root/'quality.json',[])
        folder=self.root/'processes/finance-close';events=engine.read(folder/'events.json');events[0]['to_status']='READY_FOR_OWNER';engine.atomic(folder/'events.json',events)
        with self.assertRaisesRegex(ValueError,'chain'):engine.resume(self.root,'finance-close')

    def test_independent_reviewer_required(self):
        engine.start(self.root,'finance-close');self.deliver('finance_analyst','/root/disposable_test_same')
        with self.assertRaisesRegex(ValueError,'different'):self.deliver('evidence_reviewer','/root/disposable_test_same')

    def test_accepted_analyst_cannot_change_while_waiting(self):
        engine.start(self.root,'finance-close');self.deliver('finance_analyst','/root/disposable_test_analyst')
        p=self.root/'processes/finance-close/tasks/finance_analyst.response.json';res=engine.read(p);res['summary']='Changed prose';engine.atomic(p,res)
        with self.assertRaises(ValueError):self.deliver('evidence_reviewer','/root/disposable_test_reviewer')

class BridgeTamperTests(ProcessFixture,unittest.TestCase):
    def test_coherently_replaced_request_is_rejected(self):
        engine.start(self.root,'finance-close')
        path=self.root/'processes/finance-close/tasks/finance_analyst.request.json'
        original=engine.read(path);changed=copy.deepcopy(original['evidence']);changed['counts']['orders']=999999
        replacement=make_request('finance_analyst','finance-close',changed,original['run_id'])
        engine.atomic(path,replacement)
        with self.assertRaisesRegex(ValueError,'immutable'):engine.resume(self.root,'finance-close')

    def test_state_identity_and_response_hash_rewrite_rejected(self):
        engine.start(self.root,'finance-close');self.deliver('finance_analyst','/root/disposable_test_analyst')
        path=self.root/'processes/finance-close/state.json';state=engine.read(path)
        state['run_id']='replacement';state['input_hash']='arbitrary';engine.atomic(path,state)
        with self.assertRaisesRegex(ValueError,'checkpoint'):engine.resume(self.root,'finance-close')

    def test_interrupted_checkpoint_write_recovers_from_committed_journal(self):
        state=engine.start(self.root,'finance-close')
        (self.root/'processes/finance-close/state.json').unlink()
        recovered=engine.resume(self.root,'finance-close')
        self.assertEqual(state,recovered)

    def test_terminal_packet_and_dispatch_are_revalidated(self):
        engine.start(self.root,'finance-close');self.deliver('finance_analyst','/root/disposable_test_analyst');self.deliver('evidence_reviewer','/root/disposable_test_reviewer')
        path=self.root/'processes/finance-close/decision-packet.json';packet=engine.read(path);packet['external_execution']='EXECUTE';engine.atomic(path,packet)
        with self.assertRaisesRegex(ValueError,'packet'):engine.resume(self.root,'finance-close')
        with self.assertRaisesRegex(ValueError,'packet'):engine.status(self.root)

if __name__=='__main__':unittest.main()
