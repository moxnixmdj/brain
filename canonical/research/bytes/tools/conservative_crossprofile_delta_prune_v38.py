from pathlib import Path
import ast, hashlib, json
BASE='d4523c1ea91070db972ad04143ddd48954224cfd964ad2be40a6d7c116533d47'
TARGET='9014f0769d42ca95bc68910e07282789a7075222c4747c6115b85048247a54e6'
SELECT=set(tuple(x) for x in [
('sympy/functions/special/elliptic_integrals.py','elliptic_k.eval'),
('sympy/functions/special/elliptic_integrals.py','elliptic_f.eval'),
('sympy/functions/special/bessel.py','besselk.eval'),
('sympy/functions/special/bessel.py','airybi.eval'),
('sympy/functions/special/bessel.py','airyai.eval'),
('sympy/functions/special/bessel.py','airybiprime.eval'),
('sympy/functions/special/bessel.py','airyaiprime.eval'),
('sympy/functions/special/bessel.py','jn.eval'),
('sympy/functions/special/gamma_functions.py','multigamma.eval'),
('sympy/functions/elementary/hyperbolic.py','acsch.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','asech.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','acosh.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','asinh.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','_acsch_table'),
('sympy/functions/special/delta_functions.py','Heaviside.eval'),
('sympy/matrices/expressions/diagonal.py','DiagonalOf.shape'),
('sympy/matrices/expressions/diagonal.py','DiagonalMatrix.diagonal_length'),
('sympy/matrices/expressions/blockmatrix.py','BlockMatrix.is_Identity'),
('sympy/matrices/expressions/blockmatrix.py','BlockDiagMatrix.blocks'),
('sympy/matrices/expressions/slice.py','MatrixSlice.shape'),
])
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode(); return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    by={}
    for rel,q in SELECT: by.setdefault(rel,set()).add(q)
    saved=0; cut=[]
    for rel,qs in by.items():
        p=root/rel; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; reps=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n): stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_FunctionDef(self,n):
                q='.'.join(stack+[n.name])
                if q in qs:
                    a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=' '*n.body[0].col_offset
                    old=''.join(lines[a:b]); new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
                    reps.append((a,b,new,q,len(old.encode())-len(new.encode())))
                    return
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree); found={x[3] for x in reps}
        if found!=qs: raise RuntimeError((rel,qs,found))
        for a,b,new,q,s in sorted(reps,reverse=True): lines[a:b]=[new]; saved+=s; cut.append((rel,q,s))
        out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return after,saved,sorted(cut)
if __name__=='__main__':
 import sys; print(json.dumps(dict(zip(['manifest','saved','cut'],apply(sys.argv[1]))),indent=2))
