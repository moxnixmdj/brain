from pathlib import Path
import ast,hashlib,json,sys
BASE='b3c2160a49a29fc7012ae38c0113debf6f4b735e7d6023e89e53d0ea97c76e79'
TARGET='7e9e0f0d8147057268ae0992ac16e8e3fa86388c5e08cf5580df60b85cd18ab3'
PATH='mpmath/libmp/libmpf.py'
REPL={'_normalize':'def _normalize(sign,man,exp,bc,prec,rnd):\n    s=sign;m=man;e=exp;b=bc;p=prec;r=rnd\n    if not m:return fzero\n    n=b-p\n    if n>0:\n        if r==round_nearest:\n            t=m>>n-1\n            m=(t>>1)+1 if t&1 and (t&2 or m&h_mask[n<300][n]) else t>>1\n        elif shifts_down[r][s]:m>>=n\n        else:m=-(-m>>n)\n        e+=n;b=p\n    if not m&1:\n        t=trailtable[int(m&255)]\n        if not t:\n            while not m&255:m>>=8;e+=8;b-=8\n            t=trailtable[int(m&255)]\n        m>>=t;e+=t;b-=t\n    if m==1:b=1\n    return (s,m,e,b)\n','_normalize1':'def _normalize1(sign,man,exp,bc,prec,rnd):\n    s=sign;m=man;e=exp;b=bc;p=prec;r=rnd\n    if not m:return fzero\n    if b<=p:return (s,m,e,b)\n    n=b-p\n    if r==round_nearest:\n        t=m>>n-1\n        m=(t>>1)+1 if t&1 and (t&2 or m&h_mask[n<300][n]) else t>>1\n    elif shifts_down[r][s]:m>>=n\n    else:m=-(-m>>n)\n    e+=n;b=p\n    if not m&1:\n        t=trailtable[int(m&255)]\n        if not t:\n            while not m&255:m>>=8;e+=8;b-=8\n            t=trailtable[int(m&255)]\n        m>>=t;e+=t;b-=t\n    if m==1:b=1\n    return (s,m,e,b)\n','from_man_exp':'def from_man_exp(man,exp,prec=None,rnd=round_fast):\n    m=MPZ(man);e=exp;p=prec;r=rnd;s=0\n    if m<0:s=1;m=-m\n    b=bctable[int(m)] if m<1024 else bitcount(m)\n    if not p:\n        if not m:return fzero\n        if not m&1:\n            if m&2:return (s,m>>1,e+1,b-1)\n            t=trailtable[int(m&255)]\n            if not t:\n                while not m&255:m>>=8;e+=8;b-=8\n                t=trailtable[int(m&255)]\n            m>>=t;e+=t;b-=t\n        return (s,m,e,b)\n    return normalize(s,m,e,b,p,r)\n','mpf_pow_int':'def mpf_pow_int(s,n,prec,rnd=round_fast):\n    n=int(n);p=prec;r=rnd\n    if n!=2:raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    a,m,e,b=s\n    if not m:return finf if s in (finf,fninf) else fzero if s==fzero else fnan\n    m*=m\n    if m==1:return (0,MPZ_ONE,e*2,1)\n    b=b*2-2;b+=bctable[int(m>>b)]\n    return normalize1(0,m,e*2,b,p,r)\n','mpf_rdiv_int':'def mpf_rdiv_int(n,t,prec,rnd=round_fast):\n    s,m,e,b=t;p=prec;r=rnd\n    if not n or not m:return mpf_div(from_int(n),t,p,r)\n    if n<0:s^=1;n=-n\n    x=p+b+5;q,z=divmod(n<<x,m)\n    if z:q=(q<<1)+1;x+=1\n    return (normalize1 if z else normalize)(s,q,-e-x,bitcount(q),p,r)\n'}
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def replace(p,name,new):
 text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
 if len(hits)!=1:raise RuntimeError((name,len(hits)))
 n=hits[0];old=''.join(lines[n.lineno-1:n.end_lineno]);lines[n.lineno-1:n.end_lineno]=[new]
 out=''.join(lines);compile(out,str(p),'exec');p.write_text(out);return len(old.encode()),len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;d=[]
 for name,new in REPL.items():
  old,n=replace(p,name,new);d.append([name,old,n,n-old])
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in d),'deltas':d}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
