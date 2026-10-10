from pathlib import Path
import ast, hashlib, json

BASE="eb71ab231a6281de6133082c59eb9732864e68af42daf4cfb6c6f258c3dea1f9"
TARGET="7d633d565a52b8a84e3836aadf496e2d1d9af667f94b1876d5dd6b28cc106a9b"
SELECT=set(tuple(x) for x in [
("sympy/simplify/trigsimp.py","__trigsimp"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__pow__"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__truediv__"),
("sympy/simplify/simplify.py","logcombine.f"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__mul__"),
("sympy/calculus/accumulationbounds.py","AccumulationBounds.__rtruediv__"),
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
                stack.append(n.name)
                self.generic_visit(n)
                stack.pop()
            def visit_FunctionDef(self,n):
                q=".".join(stack+[n.name])
                if q in qs:
                    a=n.body[0].lineno-1
                    b=n.body[-1].end_lineno
                    ind=" "*n.body[0].col_offset
                    reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q))
                    return
                stack.append(n.name)
                self.generic_visit(n)
                stack.pop()
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
