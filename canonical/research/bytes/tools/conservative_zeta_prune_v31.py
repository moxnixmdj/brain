from pathlib import Path
import ast, hashlib, json
BASE="9e8322e1034dd8ced3100b1c66503d0d7fd51f52ab43553672f1d36d19fe78b8"
TARGET="7378181385754faac46bef85dd647314ed2773e87e2b80b3888eb53ea9f2725a"
REL="sympy/functions/special/zeta_functions.py"
SELECT=set(["zeta.eval","dirichlet_eta.eval","riemann_xi.eval","stieltjes.eval","_dilogtable"])
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob("*.py")):
        b=p.read_bytes(); items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
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
                reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q)); return
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
