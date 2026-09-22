"""Explicit v2 JSON/CSV import contract; no inferred column mapping or credentials."""
import csv
import json
from pathlib import Path
from .warehouse import TABLE_COLUMNS, NULLABLE, INTEGER_COLUMNS


def import_dataset(path):
    path=Path(path)
    if path.is_file():
        if path.stat().st_size>50_000_000:raise ValueError('Dataset exceeds 50 MB local limit')
        data=json.loads(path.read_text(encoding='utf-8-sig'))
    elif path.is_dir():
        metadata=json.loads((path/'metadata.json').read_text(encoding='utf-8-sig'));tables={}
        for table,columns in TABLE_COLUMNS.items():
            file=path/(table+'.csv')
            if file.stat().st_size>20_000_000:raise ValueError('CSV table exceeds 20 MB local limit')
            with file.open(encoding='utf-8-sig',newline='') as stream:
                reader=csv.DictReader(stream)
                if reader.fieldnames!=list(columns):raise ValueError('CSV columns differ: '+table)
                rows=[]
                for row in reader:
                    if None in row or any(v is None for v in row.values()):raise ValueError('Ragged CSV row: '+table)
                    for key,value in row.items():
                        if value=='' and (table,key) in NULLABLE:row[key]=None
                        elif key in INTEGER_COLUMNS:
                            try:row[key]=int(value)
                            except ValueError:raise ValueError('Integer required: '+table+'.'+key) from None
                    rows.append(row)
                tables[table]=rows
        data={'metadata':metadata,'tables':tables}
    else:raise ValueError('Dataset path does not exist')
    if not isinstance(data,dict) or set(data)!={'metadata','tables'} or data['metadata'].get('synthetic') is not True:
        raise ValueError('Only explicitly synthetic v2 input is authorized')
    return data
