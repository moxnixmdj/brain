from pathlib import Path
import ast,hashlib,json,sys
BASE='0c8543d23c29030dd6b533d4402bae7dcac8466de0754a1b9eaafb07ca636ed4'
TARGET='7234515852b97d3c9c16b0a9747486cda3b95aa6c0e9f9a67c39ba860d0b1a19'
PATH='mpmath/libmp/libmpf.py'
BODY=[
'ssign, sman, sexp, sbc = s',
'tsign, tman, texp, tbc = t',
'if not sman or not tman:',
'    if s == fzero: return -mpf_sign(t)',
'    if t == fzero: return mpf_sign(s)',
'    if s == t: return 0',
'    if t == fnan or s == finf or t == fninf: return 1',
'    return -1',
'if ssign != tsign: return -1 if ssign else 1',
'if sexp == texp:',
'    if sman == tman: return 0',
'    return (-1 if sman > tman else 1) if ssign else (1 if sman > tman else -1)',
'a = sbc + sexp; b = tbc + texp',
'if a != b: return (1 if a < b else -1) if ssign else (-1 if a < b else 1)',
'return -1 if mpf_sub(s, t, 5, round_floor)[0] else 1',
]
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='mpf_cmp']
 if len(hits)!=1: raise RuntimeError(('mpf_cmp',len(hits)))
 n=hits[0];a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new=''.join(ind+x+'\n' for x in BODY);lines[a:b]=[new];out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 after,items,mb=manifest(root)
 if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':len(old.encode())-len(new.encode()),'delta':['mpf_cmp',len(old.encode()),len(new.encode()),len(new.encode())-len(old.encode())]}
if __name__=='__main__': print(json.dumps(apply(sys.argv[1]),indent=2))
