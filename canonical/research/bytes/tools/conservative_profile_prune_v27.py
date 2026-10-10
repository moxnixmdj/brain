from pathlib import Path
import ast, hashlib, json

BASE="e5d91392e4ef3c962561d3c7f9bdf9bd8dc1a4474ba6ab5f48db71a7c8dcc507"
TARGET="44e43221928b763c60eacd0a39c50e067ded82c66151886829d7cc58d037b3b9"
SELECT=set(tuple(x) for x in [
("sympy/functions/special/error_functions.py","TrigonometricIntegral.eval"),
("sympy/simplify/hyperexpand.py","try_shifted_sum"),
("sympy/simplify/simplify.py","product_simplify"),
("sympy/simplify/simplify.py","product_mul"),
("sympy/core/function.py","UndefinedFunction.__new__"),
("sympy/printing/printer.py","Printer._compare_pretty"),
("sympy/functions/special/hyper.py","hyper.radius_of_convergence"),
("sympy/ntheory/generate.py","Sieve.totientrange"),
("sympy/ntheory/generate.py","nextprime"),
("sympy/functions/special/tensor_functions.py","KroneckerDelta.eval"),
("sympy/simplify/gammasimp.py","_rf.eval"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__sub__"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__add__"),
("sympy/functions/elementary/trigonometric.py","cot._eval_expand_trig"),
("sympy/functions/elementary/trigonometric.py","tan._eval_expand_trig"),
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
