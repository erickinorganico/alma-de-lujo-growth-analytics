"""Validate a client workbook and prepare a private report without model calls."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from alma.client_review import review_file

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',required=True)
parser.add_argument('--output',required=True,help='New folder under .local/client-runs')
args=parser.parse_args()
try:
    result=review_file(args.input,args.output)
    print('Estado: '+result['status']+' | Informe privado: '+str(Path(args.output)/'informe.html'))
    raise SystemExit(2 if result['status']=='CORREGIR_CAPTURA' else 0)
except (ValueError,FileNotFoundError) as exc:
    print('No se generó el informe: '+str(exc),file=sys.stderr)
    raise SystemExit(1)
except ImportError:
    print('Instala las herramientas opcionales: python -m pip install -r requirements-client.txt', file=sys.stderr)
    raise SystemExit(1)
