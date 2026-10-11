from pathlib import Path
import tokenize,io,ast,hashlib,json,sys
BASE='e4e5e57c5c41f738ced105271d4e4bb907eaa1afe33e01788204009d49315f60'
V79='0a646be1990d7ed4cfe0b8cc918d2fae3856be6bdca0cec9e65a7002b434dea5'
V80='11d1de653b4168c3d8bbba669ffb7d363d636f18accccb8531a84a8a3e9fd761'
TARGET='c06813a7a46bb8dcbd172d4de02a3ba432408efa355971a6373f765b1d99a021'

def manifest(root):
    root=Path(root);items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def compact(path):
    src=path.read_bytes(); pairs=[]; depth=0
    for t in tokenize.tokenize(io.BytesIO(src).readline):
        s=t.string
        if t.type==tokenize.INDENT:
            depth+=1; s=' '*depth
        elif t.type==tokenize.DEDENT:
            depth=max(0,depth-1)
        elif t.type==tokenize.COMMENT:
            continue
        pairs.append((t.type,s))
    out=tokenize.untokenize(pairs)
    if isinstance(out,str): out=out.encode()
    a=ast.parse(src.decode(),type_comments=True); b=ast.parse(out.decode(),type_comments=True)
    if ast.dump(a,include_attributes=False)!=ast.dump(b,include_attributes=False): raise RuntimeError('AST drift '+str(path))
    compile(out.decode(),str(path),'exec'); path.write_bytes(out)
    return len(src)-len(out)

def apply(root):
    root=Path(root)
    h,_,_=manifest(root)
    if h!=BASE: raise RuntimeError('base drift '+h)
    s1=compact(root/'sympy/core/mul.py')
    h,_,_=manifest(root)
    if h!=V79: raise RuntimeError('V79 drift '+h)
    s2=compact(root/'sympy/core/power.py')
    h,_,_=manifest(root)
    if h!=V80: raise RuntimeError('V80 drift '+h)
    p=root/'mpmath/ctx_mp_python.py'; b=p.read_bytes()
    old=b'    def convert(ctx,x,strings=True):\n        raise NotImplementedError()\n'
    new=b'    def convert(ctx,x,strings=True):\n        if type(x) in ctx.types:return x\n        if isinstance(x,int_types):return ctx.make_mpf(from_int(x))\n        raise NotImplementedError()\n'
    if b.count(old)!=1: raise RuntimeError('convert stub drift')
    nb=b.replace(old,new); compile(nb.decode(),str(p),'exec'); p.write_bytes(nb)
    h,items,mb=manifest(root)
    if h!=TARGET: raise RuntimeError('target drift '+h)
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':h,'raw_python_source_bytes':sum(x['bytes'] for x in items),'mul_saved':s1,'power_saved':s2,'convert_repair_cost':len(new)-len(old)}
if __name__=='__main__': print(json.dumps(apply(sys.argv[1]),sort_keys=True))
