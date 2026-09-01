from __future__ import annotations
import json
from importlib.metadata import distributions
from pathlib import Path

items=[]
for d in distributions():
    name=d.metadata.get('Name') or 'unknown'
    version=d.version
    license_value=d.metadata.get('License') or ''
    items.append({'name':name,'version':version,'license_metadata':license_value})
items.sort(key=lambda x:x['name'].lower())
out=Path('runtime/sbom-python.json')
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'components':items},ensure_ascii=False,indent=2),encoding='utf-8')
print(out)
