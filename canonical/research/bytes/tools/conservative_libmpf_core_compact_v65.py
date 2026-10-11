from pathlib import Path
import ast,hashlib,json,sys
BASE='89524bdb390a99d08727930c101ecb598a46246e05c82910fdd6708782e3c4c9'
TARGET='4882aba98c4a135453b4e3d5399ef092689c314c075617cf63f1915a54fe3241'
PATH='mpmath/libmp/libmpf.py'
REPL={
'_normalize':['if not man:return fzero','n=bc-prec','if n>0:','    if rnd==round_nearest:','        t=man>>n-1','        man=(t>>1)+1 if t&1 and (t&2 or man&h_mask[n<300][n]) else t>>1','    elif shifts_down[rnd][sign]:man>>=n','    else:man=-(-man>>n)','    exp+=n;bc=prec','if not man&1:','    t=trailtable[int(man&255)]','    if not t:','        while not man&255:man>>=8;exp+=8;bc-=8','        t=trailtable[int(man&255)]','    man>>=t;exp+=t;bc-=t','if man==1:bc=1','return (sign,man,exp,bc)'],
'_normalize1':['if not man:return fzero','if bc<=prec:return (sign,man,exp,bc)','n=bc-prec','if rnd==round_nearest:','    t=man>>n-1','    man=(t>>1)+1 if t&1 and (t&2 or man&h_mask[n<300][n]) else t>>1','elif shifts_down[rnd][sign]:man>>=n','else:man=-(-man>>n)','exp+=n;bc=prec','if not man&1:','    t=trailtable[int(man&255)]','    if not t:','        while not man&255:man>>=8;exp+=8;bc-=8','        t=trailtable[int(man&255)]','    man>>=t;exp+=t;bc-=t','if man==1:bc=1','return (sign,man,exp,bc)'],
'from_man_exp':['man=MPZ(man);sign=0','if man<0:sign=1;man=-man','bc=bctable[int(man)] if man<1024 else bitcount(man)','if not prec:','    if not man:return fzero','    if not man&1:','        if man&2:return (sign,man>>1,exp+1,bc-1)','        t=trailtable[int(man&255)]','        if not t:','            while not man&255:man>>=8;exp+=8;bc-=8','            t=trailtable[int(man&255)]','        man>>=t;exp+=t;bc-=t','    return (sign,man,exp,bc)','return normalize(sign,man,exp,bc,prec,rnd)'],
'python_mpf_mul':['ssign,sman,sexp,sbc=s;tsign,tman,texp,tbc=t','sign=ssign^tsign;man=sman*tman','if man:','    bc=sbc+tbc-1;bc+=int(man>>bc)','    return normalize1(sign,man,sexp+texp,bc,prec,rnd) if prec else (sign,man,sexp+texp,bc)','s_special=not sman and sexp;t_special=not tman and texp','if not s_special and not t_special:return fzero','if fnan in (s,t):return fnan','if not tman and texp:s,t=t,s','if t==fzero:return fnan','return {1:finf,-1:fninf}[mpf_sign(s)*mpf_sign(t)]'],
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
