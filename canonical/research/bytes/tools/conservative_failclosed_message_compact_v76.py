from pathlib import Path
import hashlib,json
BASE='42c3255fe51bc6e7c30afd912d3fd3aabc422742b4671eed1e7b7fc50ce290f9'
TARGET='407e9c792852d45212362356c7ccbb9faffc491426dc4d7b166a84fa0be8e5b9'
OLD=b'raise NotImplementedError("outside Brain bounded exact-symbolic contract")'
NEW=b'raise NotImplementedError()'
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 count=files=saved=0;details=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();n=b.count(OLD)
  if not n:continue
  nb=b.replace(OLD,NEW);compile(nb.decode('utf-8'),str(p),'exec');p.write_bytes(nb)
  count+=n;files+=1;d=len(b)-len(nb);saved+=d;details.append((p.relative_to(root).as_posix(),n,d))
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'replacement_count':count,'changed_python_files':files,'saved_bytes':saved,'raw_python_source_bytes':sum(x['bytes'] for x in items),'details':details}
if __name__=='__main__':
 import sys;print(json.dumps(apply(sys.argv[1]),indent=2))
