from pathlib import Path
import ast,hashlib,json,sys
BASE='9f36c6de3186c6d72f0c24284426d4c5441e6e64e9c89404421359cc0ef8bfed'
TARGET='0145aceb14e86c89ab4a2b52bfc581d92650ed7bed4905ef98918434bc7c4f1d'
PATH='mpmath/libmp/libmpf.py'
NEW="""def _normalize1(sign, man, exp, bc, prec, rnd):
    if not man:return fzero
    if bc<=prec:return sign,man,exp,bc
    return _normalize(sign,man,exp,bc,prec,rnd)
"""
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_normalize1']
 if len(hits)!=1:raise RuntimeError('function identity drift')
 n=hits[0];old=''.join(lines[n.lineno-1:n.end_lineno]);lines[n.lineno-1:n.end_lineno]=[NEW]
 out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':len(old.encode())-len(NEW.encode())}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
