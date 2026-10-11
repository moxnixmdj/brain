from pathlib import Path
import ast, hashlib, json

BASE="c0299bf134c92e6d850b64d3b135df59d766ae91954ab7bf15bcfe48c4989ca8"
TARGET="e0c2e96ab217bbcf5b14031f8c1b615d39259331382eaa17920a8766b207ce29"
SELECT=set(tuple(x) for x in [
("sympy/functions/special/elliptic_integrals.py","elliptic_e.eval"),
("sympy/functions/combinatorial/numbers.py","bell.eval"),
("sympy/functions/combinatorial/numbers.py","andre.eval"),
("sympy/functions/combinatorial/numbers.py","_AOP_product"),
("sympy/functions/combinatorial/numbers.py","motzkin.is_motzkin"),
("sympy/functions/special/bessel.py","airybi.taylor_term"),
("sympy/functions/special/delta_functions.py","DiracDelta.eval"),
("sympy/functions/special/gamma_functions.py","loggamma.eval"),
("sympy/sets/fancysets.py","Range._sup"),
("sympy/sets/fancysets.py","Range._inf"),
("sympy/assumptions/assume.py","AppliedPredicate.binary_symbols"),
("sympy/matrices/expressions/matexpr.py","MatrixExpr.from_index_summation"),
("sympy/functions/elementary/complexes.py","periodic_argument._getunbranched"),
("sympy/series/residues.py","residue"),
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
