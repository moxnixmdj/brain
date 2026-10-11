from pathlib import Path
import ast, hashlib, json
BASE='11b996be90057f3a9e1c8adcad7d47688515a7a3fb1b15713b9e04be76ae1676'
TARGET='def0459b04d0bcf848c3c06fb6f954fec7de8c7085fc69fe736936f20fe5b588'
SELECT=[('sympy/core/evalf.py','evalf_trig'),('sympy/core/function.py','Subs.__new__')]

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    cuts=[]
    for rel,q in SELECT:
        p=root/rel; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; hits=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n): stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_FunctionDef(self,n):
                qq='.'.join(stack+[n.name])
                if qq==q: hits.append(n); return
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree)
        if len(hits)!=1: raise RuntimeError((rel,q,len(hits)))
        n=hits[0]; a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=' '*n.body[0].col_offset
        old=''.join(lines[a:b]); new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
        lines[a:b]=[new]; out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
        cuts.append((rel,q,len(old.encode())-len(new.encode())))
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':sum(x[2] for x in cuts),'raw_python_source_bytes':sum(x['bytes'] for x in items),'cuts':cuts}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
