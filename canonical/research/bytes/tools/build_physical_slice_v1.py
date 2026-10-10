from pathlib import Path
import shutil, json, hashlib, sys
src=Path(sys.argv[1]).resolve()
loaded_path=Path(sys.argv[2]).resolve()
out=Path(sys.argv[3]).resolve()
if out.exists(): shutil.rmtree(out)
out.mkdir(parents=True)
rels=set()
for line in loaded_path.read_text().splitlines():
    if not line.strip(): continue
    p=Path(line).resolve()
    try: rel=p.relative_to(src)
    except ValueError: continue
    if p.suffix=='.py': rels.add(rel)
for rel in list(rels):
    par=rel.parent
    while str(par)!='.':
        init=par/'__init__.py'
        if (src/init).exists(): rels.add(init)
        par=par.parent
for rel in sorted(rels):
    sp=src/rel; dp=out/rel
    dp.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(sp,dp)
items=[]
for p in sorted(out.rglob('*.py')):
    b=p.read_bytes()
    items.append({'path':p.relative_to(out).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest_bytes=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
(out/'BRAIN_SLICE_MANIFEST.json').write_bytes(manifest_bytes+b'\n')
print(json.dumps({'python_files':len(items),'raw_python_source_bytes':sum(x['bytes'] for x in items),'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest()}))
