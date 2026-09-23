"""Package ONLY generated blank/synthetic customer deliverables, never filled books."""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import zipfile
import tempfile
import csv
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from alma.client_review import CONTRACT, clean_json, read_inputs, evaluate
from alma.client_report import render


def workbook_content(path):
    """Check whole workbook content, including hidden cells/comments/links."""
    wb=load_workbook(path,data_only=False)
    result={'sheets':wb.sheetnames,'cells':{},'metadata':{},'names':{k:str(v) for k,v in wb.defined_names.items()}}
    try:
        for ws in wb:
            cells=[]
            for row in ws:
                for c in row:
                    if c.value is not None or c.comment or c.hyperlink:
                        value=c.value.isoformat() if isinstance(c.value,(builder_date_types())) else c.value
                        cells.append((c.coordinate,value,c.data_type,c.comment.text if c.comment else None,str(c.hyperlink) if c.hyperlink else None))
            result['cells'][ws.title]=cells
        for name in ('creator','title','description','subject','identifier','language','category','contentStatus','version','revision','keywords'):
            result['metadata'][name]=getattr(wb.properties,name,None)
        if wb.properties.lastModifiedBy not in (None,'Alma de Lujo'):
            raise ValueError('Personal Office metadata must be normalized before publication.')
        if getattr(wb,'custom_doc_props',None) and len(wb.custom_doc_props):
            raise ValueError('Custom document properties are not part of the generated kit.')
    finally:wb.close()
    return result


def builder_date_types():
    from datetime import date,datetime
    return (date,datetime)


def assert_generated_content(path, expected_path):
    if workbook_content(path)!=workbook_content(expected_path):
        raise ValueError('Workbook contains ungenerated cells, formulas, metadata, comments, links or sheets. Publication refused.')
    with zipfile.ZipFile(path) as actual,zipfile.ZipFile(expected_path) as expected:
        unexpected=set(actual.namelist())-set(expected.namelist())-{'xl/calcChain.xml'}
        if unexpected:raise ValueError('Workbook has ungenerated archive parts. Publication refused.')
        # Chart/drawing text can hide content outside cells. Excel rewrites chart
        # caches, so compare text nodes that are labels rather than cached values.
        from xml.etree import ElementTree as ET
        for name in expected.namelist():
            if name.startswith(('xl/charts/','xl/drawings/')) and name.endswith('.xml'):
                def labels(z):
                    return [e.text for e in ET.fromstring(z.read(name)).iter() if e.tag.endswith('}t')]
                if labels(actual)!=labels(expected):raise ValueError('Unexpected chart/drawing labels.')


def run(output):
    verification_path=ROOT/'evidence/v0.3/workbook-checks.json'
    if not verification_path.is_file():raise ValueError('Recalculate and verify the client workbooks before packaging.')
    verified=json.loads(verification_path.read_text(encoding='utf-8'))
    if verified.get('passed') is not True:raise ValueError('Workbook acceptance must pass before packaging.')
    accepted={r['file']:r for r in verified['workbooks']}
    spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_client_workbook.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    manifest={'version':'0.3.0','scope':'Generated synthetic/blank client kit plus the offline analytical atlas and its exact hashed evidence; no filled client records.','workbook_sha256':{},'input_sha256':{},'builder_sha256':sha256((ROOT/'scripts/build_client_workbook.py').read_bytes()).hexdigest()}
    for kind,payload in [('EJEMPLO',builder.example_payload(CONTRACT)),('PLANTILLA',builder.template_payload(CONTRACT))]:
        path=ROOT/f'client/Alma_de_Lujo_{kind}.xlsx'
        receipt=accepted.get(path.name,{})
        if receipt.get('passed') is not True or receipt.get('sha256')!=sha256(path.read_bytes()).hexdigest():
            raise ValueError('Workbook bytes differ from passed Excel/Decimal acceptance.')
        with tempfile.TemporaryDirectory(prefix='alma-generated-public-') as temp:
            expected_path=Path(temp)/path.name
            builder.build_workbook(expected_path,payload,CONTRACT)
            assert_generated_content(path,expected_path)
        data,issues=read_inputs(path)
        if issues:raise ValueError('Unexpected source input issues: '+kind)
        actual={'parameters':clean_json(data['config'])}
        expected={'parameters':builder.json_ready(payload)['parameters']}
        for sheet,key in [('CATALOGO','catalog'),('VENTAS','sales'),('STOCK','stock'),('CAJA','cash')]:
            actual[sheet]=clean_json([{k:v for k,v in row.items() if k!='_row'} for row in data[key]])
            expected[sheet]=builder.json_ready(payload)[sheet]
        if actual!=expected or data['metadata']['workbook_marker']!=payload['workbook_type']:
            raise ValueError('Workbook input differs from generated '+kind+' fixture. Publication refused.')
        name=path.relative_to(ROOT).as_posix()
        manifest['workbook_sha256'][name]=sha256(path.read_bytes()).hexdigest()
        manifest['input_sha256'][name]=sha256(json.dumps(actual,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if kind=='EJEMPLO':
            report=evaluate(data)
            if report['status']=='CORREGIR_CAPTURA':raise ValueError('Synthetic example has invalid capture.')
            report['metadata']['synthetic']=True
            content=json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8')
            evidence=ROOT/'evidence/v0.3';evidence.mkdir(parents=True,exist_ok=True)
            (evidence/'client-example.json').write_bytes(content)
            (ROOT/'client/EJEMPLO_RESUELTO.html').write_text(render(report,sha256(content).hexdigest()),encoding='utf-8',newline='\n')
    files=['Alma_de_Lujo_EJEMPLO.xlsx','Alma_de_Lujo_PLANTILLA.xlsx','EMPIEZA_AQUI.md','GUIA_SEMANAL.html','REGISTRO_DECISIONES.csv','EJEMPLO_RESUELTO.html','DECISIONES_DEL_EJEMPLO.md','FUENTES_METRICAS_AGENTES.md']
    for name in files:
        if not (ROOT/'client'/name).is_file():raise FileNotFoundError(name)
    with (ROOT/'client/REGISTRO_DECISIONES.csv').open(encoding='utf-8-sig',newline='') as f:
        register=list(csv.reader(f))
    expected_header='decision_id,fecha_corte,area,sku_o_referencia,decision,accion_propuesta,motivo,evidencia,metrica,guardrail,poblacion,ventana,responsable,fecha_revision,estado,cierre,notas'.split(',')
    if register!=[expected_header]:raise ValueError('The public decision register must contain only its exact blank header.')
    manifest['delivery_file_sha256']={n:sha256((ROOT/'client'/n).read_bytes()).hexdigest() for n in files}
    system_manifest_path=ROOT/'client/system-manifest.json'
    system_manifest=json.loads(system_manifest_path.read_text(encoding='utf-8'))
    system_files={str(path):expected for path,expected in system_manifest.get('source_sha256',{}).items()}
    system_files['client/SISTEMA_ANALITICO.html']=sha256((ROOT/'client/SISTEMA_ANALITICO.html').read_bytes()).hexdigest()
    system_files['client/system-manifest.json']=sha256(system_manifest_path.read_bytes()).hexdigest()
    system_files['client/FUENTES_METRICAS_AGENTES.md']=sha256((ROOT/'client/FUENTES_METRICAS_AGENTES.md').read_bytes()).hexdigest()
    system_files['README.md']=sha256((ROOT/'README.md').read_bytes()).hexdigest()
    system_files['docs/CLIENT-SYSTEM-ACCEPTANCE.md']=sha256((ROOT/'docs/CLIENT-SYSTEM-ACCEPTANCE.md').read_bytes()).hexdigest()
    for relative,expected_hash in system_files.items():
        path=ROOT/relative
        if not path.is_file():raise FileNotFoundError('Offline system evidence missing: '+relative)
        actual_hash=sha256(path.read_bytes()).hexdigest()
        if actual_hash!=expected_hash:raise ValueError('Offline system evidence hash drift: '+relative)
    manifest['offline_system']={'entrypoint':'sistema/client/SISTEMA_ANALITICO.html','files':len(system_files),'sha256':dict(sorted(system_files.items()))}
    (ROOT/'client/release-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'.local/releases').resolve()):
        raise ValueError('Release ZIP output must stay under .local/releases.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in files:archive.write(ROOT/'client'/name,name)
        for relative in sorted(system_files):archive.write(ROOT/relative,'sistema/'+relative)
        archive.write(ROOT/'evidence/v0.3/workbook-checks.json','sistema/evidence/v0.3/workbook-checks.json')
        archive.write(ROOT/'evidence/v0.3/excel/excel-recalculation.json','sistema/evidence/v0.3/excel/excel-recalculation.json')
        archive.write(ROOT/'client/release-manifest.json','release-manifest.json')
        archive.writestr('LEEME.txt','ALMA DE LUJO - SISTEMA ANALITICO v0.3.0\n\n1. Extrae esta carpeta completa.\n2. Abre sistema/client/SISTEMA_ANALITICO.html para recorrer fuentes, metricas, procesos, agentes, evidencia y brechas.\n3. Abre GUIA_SEMANAL.html para la operacion semanal.\n4. Practica con Alma_de_Lujo_EJEMPLO.xlsx en Excel de escritorio.\n5. Guarda una copia PRIVADA de Alma_de_Lujo_PLANTILLA.xlsx y captura tus datos.\n\nLos datos del ejemplo son sinteticos. No los copies como ventas reales.\nEl sistema propone escenarios y paquetes de decision; no ejecuta ni autoriza compras o pagos.\n')
    result={'zip':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),'files':files,'offline_system_files':len(system_files),'source_checks':'Exact workbook inputs and every offline atlas evidence file match their recorded hashes.'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'.local/releases/Alma_de_Lujo_Kit_v0.3.0.zip');args=parser.parse_args();run(args.output)
