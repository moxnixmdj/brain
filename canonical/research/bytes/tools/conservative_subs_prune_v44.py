from pathlib import Path
import ast, hashlib, json
BASE='11b996be90057f3a9e1c8adcad7d47688515a7a3fb1b15713b9e04be76ae1676'
TARGET='0a7f6fdc38cd3db7a265ac74181e4367b3b88c98c66950c2c0ed2ae3d355a5d5'
REL='sympy/core/function.py'; Q='Subs.__new__'

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    p=root/REL; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; hits=[]
    class V(ast.NodeVisitor):
        def visit_ClassDef(self,n): stack.append(n.name); self.generic_visit(n); stack.pop()
        def visit_FunctionDef(self,n):
            qq='.'.join(stack+[n.name])
            if qq==Q: hits.append(n); return
            stack.append(n.name); self.generic_visit(n); stack.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
    V().visit(tree)
    if len(hits)!=1: raise RuntimeError((REL,Q,len(hits)))
    n=hits[0]; a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=' '*n.body[0].col_offset
    old=''.join(lines[a:b]); new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
    lines[a:b]=[new]; out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':len(old.encode())-len(new.encode()),'raw_python_source_bytes':sum(x['bytes'] for x in items)}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
