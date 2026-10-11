from pathlib import Path
import ast,hashlib,json,sys
BASE='97731686624e02e2c7de4286bf0c9c41a43f58ae54d23a4df05bd1a5e2379831'
TARGET='0c8543d23c29030dd6b533d4402bae7dcac8466de0754a1b9eaafb07ca636ed4'
PATH='mpmath/libmp/libmpf.py'
FAIL='raise NotImplementedError("outside Brain bounded exact-symbolic contract")'
REPL={
'mpf_rdiv_int':[
'sign, man, exp, bc = t',
'if not n or not man: return mpf_div(from_int(n), t, prec, rnd)',
'if n < 0: sign ^= 1; n = -n',
'extra = prec + bc + 5',
'quot, rem = divmod(n << extra, man)',
'if rem: quot = (quot << 1) + 1; extra += 1',
'return (normalize1 if rem else normalize)(sign, quot, -exp-extra, bitcount(quot), prec, rnd)',
],
'mpf_pow_int':[
'n = int(n)',
'if n != 2: '+FAIL,
'sign, man, exp, bc = s',
'if not man: return finf if s in (finf, fninf) else fzero if s == fzero else fnan',
'man *= man',
'if man == 1: return (0, MPZ_ONE, exp*2, 1)',
'bc = bc*2 - 2',
'bc += bctable[int(man >> bc)]',
'return normalize1(0, man, exp*2, bc, prec, rnd)',
],
'mpf_hypot':[
'if y == fzero: return mpf_abs(x, prec, rnd)',
'if x == fzero: return mpf_abs(y, prec, rnd)',
'return mpf_sqrt(mpf_add(mpf_mul(x, x), mpf_mul(y, y), prec + 4), prec, rnd)',
],
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
