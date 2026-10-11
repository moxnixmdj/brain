from pathlib import Path
import ast, hashlib, json

BASE="fb7bc2ff8650b69a2a3e20a2d9c227c516ef34448903aa11a5f55a6a23e8a555"
TARGET="c0299bf134c92e6d850b64d3b135df59d766ae91954ab7bf15bcfe48c4989ca8"
SELECT=set(tuple(x) for x in [
("sympy/functions/special/singularity_functions.py","SingularityFunction.eval"),
("sympy/functions/special/bessel.py","marcumq.eval"),
("sympy/functions/special/bessel.py","bessely.eval"),
("sympy/functions/special/bessel.py","airyai.taylor_term"),
("sympy/functions/elementary/exponential.py","LambertW._eval_nseries"),
("sympy/functions/combinatorial/numbers.py","divisor_sigma.eval"),
("sympy/functions/combinatorial/numbers.py","reduced_totient.eval"),
("sympy/functions/elementary/hyperbolic.py","_asech_table"),
("sympy/functions/elementary/hyperbolic.py","_acosh_table"),
("sympy/logic/boolalg.py","ITE.eval"),
("sympy/logic/boolalg.py","Implies.eval"),
("sympy/sets/sets.py","Union._measure"),
("sympy/series/sequences.py","SeqMul.reduce"),
("sympy/series/sequences.py","SeqAdd.reduce"),
("sympy/tensor/indexed.py","Indexed.shape"),
("sympy/functions/elementary/miscellaneous.py","MinMaxBase._is_connected"),
("sympy/functions/elementary/miscellaneous.py","MinMaxBase._find_localzeros"),
])

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes()
        items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(mb).hexdigest()

def apply(root):
    root=Path(root)
    before=manifest(root)
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
