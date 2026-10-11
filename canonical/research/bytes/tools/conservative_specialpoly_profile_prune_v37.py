from pathlib import Path
import ast, hashlib, json

BASE="e0c2e96ab217bbcf5b14031f8c1b615d39259331382eaa17920a8766b207ce29"
TARGET="d4523c1ea91070db972ad04143ddd48954224cfd964ad2be40a6d7c116533d47"
SELECT=set(tuple(x) for x in [
("sympy/functions/special/polynomials.py","chebyshevu.eval"),
("sympy/functions/special/polynomials.py","legendre.eval"),
("sympy/functions/special/polynomials.py","laguerre.eval"),
("sympy/functions/special/polynomials.py","assoc_legendre.eval"),
("sympy/functions/special/polynomials.py","assoc_laguerre.eval"),
("sympy/functions/special/polynomials.py","hermite_prob.eval"),
("sympy/functions/special/polynomials.py","hermite.eval"),
("sympy/polys/orthopolys.py","dup_jacobi"),
("sympy/polys/orthopolys.py","dup_gegenbauer"),
("sympy/polys/orthopolys.py","_dup_chebyshevt_prod"),
("sympy/polys/orthopolys.py","dup_legendre"),
("sympy/polys/orthopolys.py","dup_hermite"),
("sympy/polys/orthopolys.py","dup_laguerre"),
("sympy/polys/orthopolys.py","dup_spherical_bessel_fn"),
("sympy/polys/orthopolys.py","dup_hermite_prob"),
("sympy/polys/orthopolys.py","dup_chebyshevu"),
("sympy/functions/special/hyper.py","hyper.convergence_statement"),
("sympy/functions/special/hyper.py","appellf1.eval"),
("sympy/functions/special/hyper.py","HyperRep_sqrts2._expr_big"),
("sympy/functions/special/hyper.py","HyperRep_sqrts1._expr_big"),
("sympy/functions/special/hyper.py","HyperRep_sqrts1._expr_big_minus"),
("sympy/functions/special/hyper.py","HyperRep_log2._expr_big"),
("sympy/functions/special/hyper.py","HyperRep_power2._expr_big"),
])

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes()
        items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(mb).hexdigest()

def apply(root):
    root=Path(root); before=manifest(root)
    if before!=BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    by={}
    for rel,q in SELECT:
        by.setdefault(rel,set()).add(q)
    for rel,qs in by.items():
        p=root/rel; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; reps=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n):
                stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_FunctionDef(self,n):
                q=".".join(stack+[n.name])
                if q in qs:
                    a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=" "*n.body[0].col_offset
                    reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q))
                    return
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree)
        found={x[3] for x in reps}
        if found!=qs:
            raise RuntimeError((rel,qs,found))
        for a,b,new,_ in sorted(reps,reverse=True):
            lines[a:b]=[new]
        out="".join(lines); compile(out,str(p),"exec"); p.write_text(out)
    after=manifest(root)
    if after!=TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    items=[]
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes()
        items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    (root/"BRAIN_SLICE_MANIFEST.json").write_bytes(mb+b"\n")
    return after

if __name__=="__main__":
    import sys
    print(apply(sys.argv[1]))
