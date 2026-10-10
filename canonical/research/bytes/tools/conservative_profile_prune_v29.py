from pathlib import Path
import ast, hashlib, json
BASE="6b7eee6f8a15670189e06ffda61d9149ea5e5a58ec158ce23f396ac50edf34eb"
TARGET="fefb4f023644b1d63fd5a693289226b64080c161adbd3f782a3c361232c4462a"
SELECT=set([
"erf.eval","erf.taylor_term","erfc.eval","erfc.taylor_term","erfi.eval","erfi.taylor_term",
"erf2.eval","erfinv.eval","erfcinv.eval","erf2inv.eval","Ei.eval","expint.eval","li.eval",
"Li.eval","FresnelIntegral.eval","fresnels.taylor_term","fresnelc.taylor_term"
])
REL="sympy/functions/special/error_functions.py"
def manifest(root):
    items=[];root=Path(root)
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes();items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(mb).hexdigest()
def apply(root):
    root=Path(root); before=manifest(root)
    if before!=BASE: raise RuntimeError(f"base manifest drift: {before}")
    p=root/REL; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; reps=[]
    class V(ast.NodeVisitor):
        def visit_ClassDef(self,n):
            stack.append(n.name); self.generic_visit(n); stack.pop()
        def visit_FunctionDef(self,n):
            q=".".join(stack+[n.name])
            if q in SELECT:
                a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=" "*n.body[0].col_offset
                reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q))
                return
            stack.append(n.name); self.generic_visit(n); stack.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
    V().visit(tree)
    found={x[3] for x in reps}
    if found!=SELECT: raise RuntimeError((SELECT,found))
    for a,b,new,q in sorted(reps,reverse=True): lines[a:b]=[new]
    out="".join(lines); compile(out,str(p),"exec"); p.write_text(out)
    after=manifest(root)
    if after!=TARGET: raise RuntimeError(f"target manifest mismatch: {after}")
    items=[]
    for q in sorted(root.rglob("*.py")):
        b=q.read_bytes();items.append({"path":q.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode()
    (root/"BRAIN_SLICE_MANIFEST.json").write_bytes(mb+b"\n")
    return after
if __name__=="__main__":
    import sys; print(apply(sys.argv[1]))
