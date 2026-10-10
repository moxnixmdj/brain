from pathlib import Path
import ast, hashlib, json
BASE="fefb4f023644b1d63fd5a693289226b64080c161adbd3f782a3c361232c4462a"
TARGET="9e8322e1034dd8ced3100b1c66503d0d7fd51f52ab43553672f1d36d19fe78b8"
REL="sympy/simplify/hyperexpand.py"
SELECT=set(["make_simp","Hyper_Function.__new__","Hyper_Function.build_invariants","Hyper_Function.difficulty","Hyper_Function._is_suitable_origin","G_Function.__new__","G_Function.compute_buckets","Formula._compute_basis","Formula.__init__","FormulaCollection.__init__","MeijerFormula.__init__","MeijerFormula.try_instantiate","MeijerFormulaCollection.__init__","MeijerFormulaCollection.lookup_origin","Operator.apply","ShiftA.__init__","ShiftB.__init__","UnShiftA.__init__","UnShiftB.__init__","MeijerUnShiftA.__init__","MeijerUnShiftA.__str__","MeijerUnShiftB.__init__","MeijerUnShiftB.__str__","MeijerUnShiftC.__init__","MeijerUnShiftC.__str__","MeijerUnShiftD.__init__","MeijerUnShiftD.__str__","ReduceOrder.__new__","ReduceOrder._meijer","_reduce_order","reduce_order","reduce_order_meijer","make_derivative_operator","try_polynomial","hyperexpand_special","hyperexpand.do_replace","hyperexpand.do_meijer"])
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
