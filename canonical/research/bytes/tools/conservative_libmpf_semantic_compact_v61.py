from pathlib import Path
import ast,hashlib,json,sys
BASE='6ab3ad3366fe10d0d081784d61838d097eac1c242cee729453d78d48ede5033e'
TARGET='fd5c28fdb77149e30887c68e498580f6f630aba8857ae98e1f53975489d9b6f5'
PATH='mpmath/libmp/libmpf.py'
REPL={
'mpf_shift':['return s if not s[1] else (s[0], s[1], s[2] + n, s[3])'],
'mpf_pos':['if not prec: return s','sign, man, exp, bc = s','return s if not man and exp else normalize1(sign, man, exp, bc, prec, rnd)'],
'to_fixed':['sign, man, exp, bc = s','offset = exp + prec','man = -man if sign else man','return man << offset if offset >= 0 else man >> -offset'],
'mpf_le':['return False if s == fnan or t == fnan else mpf_cmp(s, t) <= 0'],
'mpf_ge':['return False if s == fnan or t == fnan else mpf_cmp(s, t) >= 0'],
'repr_dps':['dps = prec_to_dps(n)','return 17 if dps == 15 else dps + 3'],
}
def manifest(root):
 root=Path(root); items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def replace(p,name,body):
 text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
 if len(hits)!=1: raise RuntimeError((name,len(hits)))
 n=hits[0];a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new=''.join(ind+x+'\n' for x in body);lines[a:b]=[new];out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 return len(old.encode()),len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;deltas=[]
 for name,body in REPL.items():
  old,new=replace(p,name,body);deltas.append([name,old,new,new-old])
 after,items,mb=manifest(root)
 if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in deltas),'deltas':deltas}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
