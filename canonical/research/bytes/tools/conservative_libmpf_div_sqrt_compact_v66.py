from pathlib import Path
import ast,hashlib,json,sys
BASE='4882aba98c4a135453b4e3d5399ef092689c314c075617cf63f1915a54fe3241'
TARGET='d1952da89ebbc7a8a925979cbf2ff2f9c4401144b4e657fc84c27c42f6c7994b'
PATH='mpmath/libmp/libmpf.py'
REPL={
'mpf_div':[
'ssign,sman,sexp,sbc=s;tsign,tman,texp,tbc=t',
'if not sman or not tman:',
'    if s==fzero:',
'        if t==fzero:raise ZeroDivisionError',
'        return fnan if t==fnan else fzero',
'    if t==fzero:raise ZeroDivisionError',
'    ss=not sman and sexp;ts=not tman and texp',
'    if ss and ts or s==fnan or t==fnan:return fnan',
'    if not ts:return {1:finf,-1:fninf}[mpf_sign(s)*mpf_sign(t)]',
'    return fzero',
'sign=ssign^tsign',
'if tman==1:return normalize1(sign,sman,sexp-texp,sbc,prec,rnd)',
'extra=max(5,prec-sbc+tbc+5);quot,rem=divmod(sman<<extra,tman)',
'if rem:quot=(quot<<1)+1;extra+=1;return normalize1(sign,quot,sexp-texp-extra,bitcount(quot),prec,rnd)',
'return normalize(sign,quot,sexp-texp-extra,bitcount(quot),prec,rnd)',
],
'mpf_sqrt':[
'sign,man,exp,bc=s',
"if sign:raise ComplexResult('square root of a negative number')",
'if not man:return s',
'if exp&1:exp-=1;man<<=1;bc+=1',
'elif man==1:return normalize1(sign,man,exp//2,bc,prec,rnd)',
'shift=max(4,2*prec-bc+4);shift+=shift&1',
"if rnd in 'fd':man=isqrt(man<<shift)",
'else:',
'    man,rem=sqrtrem(man<<shift)',
'    if rem:man=(man<<1)+1;shift+=2',
'return from_man_exp(man,(exp-shift)//2,prec,rnd)',
],
}
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def replace(p,name,body):
 text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
 if len(hits)!=1:raise RuntimeError((name,len(hits)))
 n=hits[0];a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new=''.join(ind+x+'\n' for x in body);lines[a:b]=[new];out=''.join(lines);compile(out,str(p),'exec');p.write_text(out);return len(old.encode()),len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;d=[]
 for name,body in REPL.items():
  old,new=replace(p,name,body);d.append([name,old,new,new-old])
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in d),'deltas':d}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
