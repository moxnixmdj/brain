from pathlib import Path
import ast,hashlib,json,sys
BASE='b3c2160a49a29fc7012ae38c0113debf6f4b735e7d6023e89e53d0ea97c76e79'
TARGET='9da7d492a933a472ed4e2c88a30f836fad0c0f4481a9a8ecbd67b594427c5bda'
PATH='mpmath/libmp/libmpf.py'
REPL={
'_normalize':"""def _normalize(sign, man, exp, bc, prec, rnd):
    s,m,e,b,p,r=sign,man,exp,bc,prec,rnd
    if not m:return fzero
    n=b-p
    if n>0:
        if r==round_nearest:
            t=m>>n-1;m=(t>>1)+1 if t&1 and(t&2 or m&h_mask[n<300][n]) else t>>1
        elif shifts_down[r][s]:m>>=n
        else:m=-(-m>>n)
        e+=n;b=p
    if not m&1:
        t=trailtable[int(m&255)]
        if not t:
            while not m&255:m>>=8;e+=8;b-=8
            t=trailtable[int(m&255)]
        m>>=t;e+=t;b-=t
    if m==1:b=1
    return s,m,e,b
""",
'_normalize1':"""def _normalize1(sign, man, exp, bc, prec, rnd):
    s,m,e,b,p,r=sign,man,exp,bc,prec,rnd
    if not m:return fzero
    if b<=p:return s,m,e,b
    n=b-p
    if r==round_nearest:
        t=m>>n-1;m=(t>>1)+1 if t&1 and(t&2 or m&h_mask[n<300][n]) else t>>1
    elif shifts_down[r][s]:m>>=n
    else:m=-(-m>>n)
    e+=n;b=p
    if not m&1:
        t=trailtable[int(m&255)]
        if not t:
            while not m&255:m>>=8;e+=8;b-=8
            t=trailtable[int(m&255)]
        m>>=t;e+=t;b-=t
    if m==1:b=1
    return s,m,e,b
""",
'from_man_exp':"""def from_man_exp(man, exp, prec=None, rnd=round_fast):
    m=MPZ(man);e=exp;p=prec;r=rnd;s=0
    if m<0:s=1;m=-m
    b=bctable[int(m)] if m<1024 else bitcount(m)
    if not p:
        if not m:return fzero
        if not m&1:
            if m&2:return s,m>>1,e+1,b-1
            t=trailtable[int(m&255)]
            if not t:
                while not m&255:m>>=8;e+=8;b-=8
                t=trailtable[int(m&255)]
            m>>=t;e+=t;b-=t
        return s,m,e,b
    return normalize(s,m,e,b,p,r)
""",
'mpf_rdiv_int':"""def mpf_rdiv_int(n, t, prec, rnd=round_fast):
    s,m,e,b=t;p=prec;r=rnd
    if not n or not m:return mpf_div(from_int(n),t,p,r)
    if n<0:s^=1;n=-n
    x=p+b+5;q,z=divmod(n<<x,m)
    if z:q=(q<<1)+1;x+=1
    return (normalize1 if z else normalize)(s,q,-e-x,bitcount(q),p,r)
""",
'mpf_pow_int':"""def mpf_pow_int(s, n, prec, rnd=round_fast):
    n=int(n)
    if n!=2:raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    a,m,e,b=s
    if not m:return finf if s in(finf,fninf) else fzero if s==fzero else fnan
    m*=m
    if m==1:return 0,MPZ_ONE,e*2,1
    b=b*2-2;b+=bctable[int(m>>b)]
    return normalize1(0,m,e*2,b,prec,rnd)
""",
'mpf_perturb':"""def mpf_perturb(x, eps_sign, prec, rnd):
    e=eps_sign;p=prec;r=rnd
    if r!=round_down or e not in(0,1) or x[0] or not x[1]:raise NotImplementedError("outside Brain bounded exact-symbolic contract")
    return mpf_add(x,(1,MPZ_ONE,x[2]+x[3]-p-1,1),p,r) if e else mpf_pos(x,p,r)
""",
'mpf_neg':"""def mpf_neg(s, prec=None, rnd=round_fast):
    a,m,e,b=s
    if not m:
        if s==finf:return fninf
        if s==fninf:return finf
        return s
    return (1-a,m,e,b) if not prec else normalize1(1-a,m,e,b,prec,rnd)
""",
'mpf_hypot':"""def mpf_hypot(x, y, prec, rnd=round_fast):
    if y==fzero:return mpf_abs(x,prec,rnd)
    if x==fzero:return mpf_abs(y,prec,rnd)
    return mpf_sqrt(mpf_add(mpf_mul(x,x),mpf_mul(y,y),prec+4),prec,rnd)
"""
}
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in REPL}
 if set(hits)!=set(REPL):raise RuntimeError('function set drift')
 d=[]
 for name,n in sorted(hits.items(),key=lambda kv:kv[1].lineno,reverse=True):
  a=n.lineno-1;b=n.end_lineno;old=''.join(lines[a:b]);new=REPL[name];lines[a:b]=[new];d.append([name,len(old.encode()),len(new.encode()),len(new.encode())-len(old.encode())])
 out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in d),'deltas':list(reversed(d))}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
