"""Parent-runtime receipt writer; supply IDs/times from actual Codex dispatches."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from alma.native_agents import digest, validate_response, validate_dispatch
from alma.process_engine import atomic, read

parser=argparse.ArgumentParser()
parser.add_argument('--request',required=True);parser.add_argument('--response',required=True)
parser.add_argument('--receipt',required=True);parser.add_argument('--agent-id',required=True)
parser.add_argument('--model',required=True);parser.add_argument('--effort',required=True)
parser.add_argument('--started-at',required=True);parser.add_argument('--completed-at',required=True)
args=parser.parse_args()
request=read(args.request);response=read(args.response)
validate_response(request,response)
receipt=dict(request_id=request['request_id'],role=request['role'],provider='native-codex',model=args.model,agent_id=args.agent_id,
 response_sha256=digest(response),recorded_by='parent-runtime',mode='live',effort=args.effort,
 started_at_utc=args.started_at,completed_at_utc=args.completed_at,retry_history=[],parent_review='schema-and-evidence-validated')
validate_dispatch(receipt,request);atomic(args.receipt,receipt)
print('Validated native response and recorded parent attestation: '+args.receipt)
