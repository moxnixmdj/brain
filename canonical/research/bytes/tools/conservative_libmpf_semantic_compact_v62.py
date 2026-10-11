from pathlib import Path
import ast,hashlib,json,sys
BASE='fd5c28fdb77149e30887c68e498580f6f630aba8857ae98e1f53975489d9b6f5'
TARGET='97731686624e02e2c7de4286bf0c9c41a43f58ae54d23a4df05bd1a5e2379831'
PATH='mpmath/libmp/libmpf.py'
REPL={
'from_pickable':['return (x[0], MPZ(x[1], 16), x[2], x[3])'],
'from_int':['return int_cache[n] if not prec and n in int_cache else from_man_exp(n, 0, prec, rnd)'],
'mpf_neg':['sign, man, exp, bc = s','if not man:','    if s == finf: return fninf','    if s == fninf: return finf','    return s','return (1 - sign, man, exp, bc) if not prec else normalize1(1 - sign, man, exp, bc, prec, rnd)'],
'mpf_sign':['if s == finf: return 1','if s == fninf: return -1','return 0 if not s[1] else (-1) ** s[0]'],
'mpf_lt':['return False if s == fnan or t == fnan else mpf_cmp(s, t) < 0'],
'mpf_gt':['return False if s == fnan or t == fnan else mpf_cmp(s, t) > 0'],
}
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def replace(p,name,body):
 text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
 if len(hits)!=1: raise RuntimeError((name,len(hits)))
 n=hits[0];a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new=''.join(ind+x+'\n' for x in body);lines[a:b]=[new];out=''.join(lines);compile(out,str(p),'exec');p.write_text(out);return len(old.encode()),len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;d=[]
 for name,body in REPL.items():
  old,new=replace(p,name,body);d.append([name,old,new,new-old])
 after,items,mb=manifest(root)
 if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in d),'deltas':d}
if __name__=='__main__': print(json.dumps(apply(sys.argv[1]),indent=2))
