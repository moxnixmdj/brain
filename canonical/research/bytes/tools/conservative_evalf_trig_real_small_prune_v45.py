from pathlib import Path
import ast, hashlib, json
BASE='0a7f6fdc38cd3db7a265ac74181e4367b3b88c98c66950c2c0ed2ae3d355a5d5'
TARGET='3d7c21fdebe1db363cc3e4c5fdf57a2ddb76c5219cd832c34eab9a99d60f9576'
PATH='sympy/core/evalf.py'
QUAL='evalf_trig'
NEW='''def evalf_trig(v, prec, options):\n    from sympy.functions.elementary.trigonometric import cos, sin\n    if isinstance(v, cos):\n        func = mpf_cos\n    elif isinstance(v, sin):\n        func = mpf_sin\n    else:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    arg = v.args[0]\n    xprec = prec + 20\n    re, im, re_acc, im_acc = evalf(arg, xprec, options)\n    if im or not re:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    if fastlog(re) >= 1:\n        raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n    return (func(re, prec, rnd), None, prec, None)\n'''
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode(); return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    p=root/PATH; text=p.read_text(); tree=ast.parse(text); hits=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==QUAL]
    if len(hits)!=1: raise RuntimeError(f'{QUAL} identity count: {len(hits)}')
    n=hits[0]; lines=text.splitlines(True); old=''.join(lines[n.lineno-1:n.end_lineno]); lines[n.lineno-1:n.end_lineno]=[NEW]
    out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':len(old.encode())-len(NEW.encode()),'raw_python_source_bytes':sum(x['bytes'] for x in items),'changed':[[PATH,QUAL]]}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
