"""Remove local Office author metadata without changing formulas or cached values."""
from pathlib import Path
import argparse
import io
import zipfile
from xml.etree import ElementTree as ET


def normalize(path):
    path=Path(path)
    if path.suffix.lower()!='.xlsx':raise ValueError('Only .xlsx files are supported.')
    core='http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
    dc='http://purl.org/dc/elements/1.1/'
    with zipfile.ZipFile(path) as original:
        root=ET.fromstring(original.read('docProps/core.xml'))
        properties={f'{{{dc}}}creator':'Alma de Lujo',f'{{{core}}}lastModifiedBy':'Alma de Lujo'}
        for tag,value in properties.items():
            child=root.find(tag)
            if child is None:child=ET.SubElement(root,tag)
            child.text=value
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as updated:
            for info in original.infolist():
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True) if info.filename=='docProps/core.xml' else original.read(info.filename)
                updated.writestr(info,data)
    path.write_bytes(out.getvalue())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('path',type=Path);normalize(parser.parse_args().path)
