from pathlib import Path
import ast,hashlib,json,sys
BASE='0c8543d23c29030dd6b533d4402bae7dcac8466de0754a1b9eaafb07ca636ed4'
TARGET='89524bdb390a99d08727930c101ecb598a46246e05c82910fdd6708782e3c4c9'
PATH='mpmath/libmp/libmpf.py'
REPL={
'from_float':['if x != x: return fnan','try: m, e = math.frexp(x)','except: return finf if x == math_float_inf else fninf if x == -math_float_inf else fnan','if x == math_float_inf: return finf','if x == -math_float_inf: return fninf','return from_man_exp(int(m * (1 << 53)), e - 53, prec, rnd)'],
'to_float':['sign, man, exp, bc = s','if not man:','    if s == fzero: return 0.0','    if s == finf: return math_float_inf','    if s == fninf: return -math_float_inf','    return math_float_inf / math_float_inf','if bc > 53: sign, man, exp, bc = normalize1(sign, man, exp, bc, 53, rnd)','if sign: man = -man','try: return math.ldexp(man, exp)','except OverflowError:','    if strict: raise','    if exp + bc > 0: return -math_float_inf if sign else math_float_inf','    return 0.0'],
'from_rational':['return mpf_div(from_int(p),from_int(q),prec,rnd)'],
'mpf_frac':['return mpf_sub(s,mpf_floor(s),prec,rnd)'],
'mpf_cmp':['ssign, sman, sexp, sbc = s; tsign, tman, texp, tbc = t','if not sman or not tman:','    if s == fzero: return -mpf_sign(t)','    if t == fzero: return mpf_sign(s)','    if s == t: return 0','    if t == fnan or s == finf or t == fninf: return 1','    return -1','if ssign != tsign: return -1 if ssign else 1','if sexp == texp:','    if sman == tman: return 0','    return (-1 if sman > tman else 1) if ssign else (1 if sman > tman else -1)','a = sbc + sexp; b = tbc + texp','if a != b: return (1 if a < b else -1) if ssign else (-1 if a < b else 1)','return -1 if mpf_sub(s,t,5,round_floor)[0] else 1'],
'mpf_abs':['sign, man, exp, bc = s','if not man or (not prec and not sign): raise NotImplementedError("outside Brain bounded exact-symbolic contract")','return normalize1(0,man,exp,bc,prec,rnd) if prec else (0,man,exp,bc)'],
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
