from pathlib import Path
import ast, hashlib, json

BASE="7d633d565a52b8a84e3836aadf496e2d1d9af667f94b1876d5dd6b28cc106a9b"
TARGET="e5d91392e4ef3c962561d3c7f9bdf9bd8dc1a4474ba6ab5f48db71a7c8dcc507"
SELECT=set(tuple(x) for x in [
("sympy/assumptions/ask_generated.py","get_known_facts_dict"),
("sympy/assumptions/ask_generated.py","get_all_known_facts"),
("sympy/assumptions/ask_generated.py","get_all_known_number_facts"),
("sympy/assumptions/ask_generated.py","get_all_known_matrix_facts"),
("sympy/logic/boolalg.py","_simplify_patterns_and"),
("sympy/logic/boolalg.py","_simplify_patterns_and3"),
("sympy/logic/boolalg.py","_simplify_patterns_or"),
("sympy/logic/boolalg.py","_simplify_patterns_xor"),
("sympy/assumptions/assume.py","PredicateMeta.__doc__"),
("sympy/functions/special/polynomials.py","jacobi.eval"),
("sympy/functions/special/polynomials.py","gegenbauer.eval"),
("sympy/functions/elementary/trigonometric.py","acsc.eval"),
("sympy/functions/elementary/trigonometric.py","ReciprocalTrigonometricFunction.eval"),
("sympy/functions/elementary/complexes.py","_polarify"),
("sympy/functions/elementary/complexes.py","_unpolarify"),
("sympy/functions/elementary/complexes.py","polar_lift.eval"),
("sympy/functions/elementary/complexes.py","periodic_argument.eval"),
("sympy/functions/combinatorial/numbers.py","_nP"),
("sympy/functions/combinatorial/numbers.py","bernoulli.eval"),
("sympy/functions/special/gamma_functions.py","gamma.eval"),
("sympy/functions/special/gamma_functions.py","polygamma.eval"),
("sympy/functions/elementary/exponential.py","LambertW.eval"),
("sympy/functions/elementary/hyperbolic.py","asinh.eval"),
("sympy/simplify/hyperexpand.py","FormulaCollection.lookup_origin"),
("sympy/simplify/simplify.py","kroneckersimp"),
("mpmath/libmp/gammazeta.py","glaisher_fixed"),
])

def manifest(root):
    items=[]
    root=Path(root)
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes()
        items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(mb).hexdigest()

def apply(root):
    root=Path(root)
    before=manifest(root)
    if before != BASE:
        raise RuntimeError(f"base manifest drift: {before}")
    by={}
    for rel,q in SELECT:
        by.setdefault(rel,set()).add(q)
    for rel,qs in by.items():
        p=root/rel
        text=p.read_text()
        lines=text.splitlines(True)
        tree=ast.parse(text)
        stack=[]
        reps=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n):
                stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_FunctionDef(self,n):
                q=".".join(stack+[n.name])
                if q in qs:
                    a=n.body[0].lineno-1
                    b=n.body[-1].end_lineno
                    ind=" "*n.body[0].col_offset
                    reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q))
                    return
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree)
        found={x[3] for x in reps}
        if found != qs:
            raise RuntimeError((rel,qs,found))
        for a,b,new,q in sorted(reps,reverse=True):
            lines[a:b]=[new]
        out="".join(lines)
        compile(out,str(p),"exec")
        p.write_text(out)
    after=manifest(root)
    if after != TARGET:
        raise RuntimeError(f"target manifest mismatch: {after}")
    items=[]
    for q in sorted(root.rglob("*.py")):
        b=q.read_bytes()
        items.append({"path":q.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    (root/"BRAIN_SLICE_MANIFEST.json").write_bytes(mb+b"\n")
    return after

if __name__=="__main__":
    import sys
    print(apply(sys.argv[1]))
