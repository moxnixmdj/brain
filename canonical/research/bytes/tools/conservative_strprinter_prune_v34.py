from pathlib import Path
import ast, hashlib, json
BASE="8bd85a2a0d7fb314a37115aa625b9d56965e1abf3dd8dffa4b46b549781eb91f"
TARGET="fb7bc2ff8650b69a2a3e20a2d9c227c516ef34448903aa11a5f55a6a23e8a555"
REL="sympy/printing/str.py"
SELECT=set(["StrPrinter._print_AccumulationBounds","StrPrinter._print_AlgebraicNumber","StrPrinter._print_And","StrPrinter._print_AppliedBinaryRelation","StrPrinter._print_AppliedPredicate","StrPrinter._print_ArrayElement","StrPrinter._print_Basic","StrPrinter._print_BlockMatrix","StrPrinter._print_ComplexRootOf","StrPrinter._print_ConditionSet","StrPrinter._print_DMF","StrPrinter._print_DMP","StrPrinter._print_Derivative","StrPrinter._print_Differential","StrPrinter._print_FiniteSet","StrPrinter._print_Float","StrPrinter._print_FracElement","StrPrinter._print_FracField","StrPrinter._print_Fraction","StrPrinter._print_GroebnerBasis","StrPrinter._print_Integral","StrPrinter._print_Interval","StrPrinter._print_Lambda","StrPrinter._print_LatticeOp","StrPrinter._print_Limit","StrPrinter._print_MatMul","StrPrinter._print_MatPow","StrPrinter._print_MatrixElement","StrPrinter._print_MatrixSlice","StrPrinter._print_NamedMorphism","StrPrinter._print_Order","StrPrinter._print_Partition","StrPrinter._print_Permutation","StrPrinter._print_PermutationGroup","StrPrinter._print_Poly","StrPrinter._print_PolyRing","StrPrinter._print_PythonRational","StrPrinter._print_Quantity","StrPrinter._print_Quaternion","StrPrinter._print_RandomDomain","StrPrinter._print_Rational","StrPrinter._print_Relational","StrPrinter._print_RootSum","StrPrinter._print_Subs","StrPrinter._print_Sum","StrPrinter._print_TensMul","StrPrinter._print_Zero","StrPrinter._print_dict","StrPrinter._print_frozenset","StrPrinter._print_mpq","StrPrinter._print_set","StrPrinter._print_tuple","StrPrinter.emptyPrinter"])
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
