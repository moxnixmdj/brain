from pathlib import Path
import ast,hashlib,json,sys
BASE='57a12fdb5e4b82d65a1160df8754732b98b94a3e2e8d55f55845639db7acb029'
TARGET='b3c2160a49a29fc7012ae38c0113debf6f4b735e7d6023e89e53d0ea97c76e79'
PATH='mpmath/libmp/libmpf.py'
REPL={
'mpf_cmp':"""def mpf_cmp(s,t):
    a,b,c,d=s;e,f,g,h=t
    if not b or not f:
        if s==fzero:return -mpf_sign(t)
        if t==fzero:return mpf_sign(s)
        if s==t:return 0
        if t==fnan or s==finf or t==fninf:return 1
        return -1
    if a!=e:return -1 if a else 1
    if c==g:
        if b==f:return 0
        return (-1 if b>f else 1) if a else (1 if b>f else -1)
    d+=c;h+=g
    if d!=h:return (1 if d<h else -1) if a else (-1 if d<h else 1)
    return -1 if mpf_sub(s,t,5,round_floor)[0] else 1
""",
'to_float':"""def to_float(s,strict=False,rnd=round_fast):
    a,b,c,d=s
    if not b:
        if s==fzero:return 0.0
        if s==finf:return math_float_inf
        if s==fninf:return -math_float_inf
        return math_float_inf/math_float_inf
    if d>53:a,b,c,d=normalize1(a,b,c,d,53,rnd)
    if a:b=-b
    try:return math.ldexp(b,c)
    except OverflowError:
        if strict:raise
        if c+d>0:return -math_float_inf if a else math_float_inf
        return 0.0
""",
'python_mpf_mul':"""def python_mpf_mul(s,t,prec=0,rnd=round_fast):
    a,b,c,d=s;e,f,g,h=t;q=a^e;m=b*f
    if m:
        z=d+h-1;z+=int(m>>z)
        return normalize1(q,m,c+g,z,prec,rnd) if prec else (q,m,c+g,z)
    x=not b and c;y=not f and g
    if not x and not y:return fzero
    if fnan in (s,t):return fnan
    if not f and g:s,t=t,s
    if t==fzero:return fnan
    return {1:finf,-1:fninf}[mpf_sign(s)*mpf_sign(t)]
""",
'mpf_div':"""def mpf_div(s,t,prec,rnd=round_fast):
    a,b,c,d=s;e,f,g,h=t
    if not b or not f:
        if s==fzero:
            if t==fzero:raise ZeroDivisionError
            return fnan if t==fnan else fzero
        if t==fzero:raise ZeroDivisionError
        x=not b and c;y=not f and g
        if x and y or s==fnan or t==fnan:return fnan
        if not y:return {1:finf,-1:fninf}[mpf_sign(s)*mpf_sign(t)]
        return fzero
    a^=e
    if f==1:return normalize1(a,b,c-g,d,prec,rnd)
    x=max(5,prec-d+h+5);q,r=divmod(b<<x,f)
    if r:q=(q<<1)+1;x+=1;return normalize1(a,q,c-g-x,bitcount(q),prec,rnd)
    return normalize(a,q,c-g-x,bitcount(q),prec,rnd)
""",
'mpf_sqrt':"""def mpf_sqrt(s,prec,rnd=round_fast):
    a,b,c,d=s
    if a:raise ComplexResult('square root of a negative number')
    if not b:return s
    if c&1:c-=1;b<<=1;d+=1
    elif b==1:return normalize1(a,b,c//2,d,prec,rnd)
    x=max(4,2*prec-d+4);x+=x&1
    if rnd in 'fd':b=isqrt(b<<x)
    else:
        b,r=sqrtrem(b<<x)
        if r:b=(b<<1)+1;x+=2
    return from_man_exp(b,(c-x)//2,prec,rnd)
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
 p=root/PATH;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in REPL]
 if {n.name for n in hits}!=set(REPL):raise RuntimeError('function set drift')
 d=[]
 for n in sorted(hits,key=lambda n:n.lineno,reverse=True):
  a=n.lineno-1;b=n.end_lineno;old=''.join(lines[a:b]);new=REPL[n.name];lines[a:b]=[new];d.append([n.name,len(old.encode()),len(new.encode()),len(new.encode())-len(old.encode())])
 out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':-sum(x[3] for x in d),'deltas':list(reversed(d))}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
