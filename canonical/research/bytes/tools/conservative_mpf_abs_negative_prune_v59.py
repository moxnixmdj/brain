from pathlib import Path
import ast, hashlib, json
BASE='409dd682c47e2a25acc2915af689650757f02cf828826a9854d06c0e386bb1c1'
TARGET='694f9c52e40530f4c41fe46e4ba01001f8d0a672c8e1cf2024d2cee15bda757c'
PATH='mpmath/libmp/libmpf.py'
QUAL='mpf_abs'
NEW='''def mpf_abs(s, prec=None, rnd=round_fast):\n    sign, man, exp, bc = s\n    if prec or not sign or not man:\n        raise NotImplementedError\n    return (0, man, exp, bc)\n'''
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode(); return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    p=root/PATH; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text)
    hits=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==QUAL]
    if len(hits)!=1: raise RuntimeError(f'{QUAL} identity count: {len(hits)}')
    n=hits[0]; old=''.join(lines[n.lineno-1:n.end_lineno]); lines[n.lineno-1:n.end_lineno]=[NEW]
    out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':len(old.encode())-len(NEW.encode()),'raw_python_source_bytes':sum(x['bytes'] for x in items)}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
