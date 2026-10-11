from pathlib import Path
import ast, hashlib, json
BASE='9014f0769d42ca95bc68910e07282789a7075222c4747c6115b85048247a54e6'
TARGET='c93cd3aabe9fc5d1a66cf3e6090ab1f937c63e1eaa83beb68040a1a8faa99dee'
SELECT=set(tuple(x) for x in [
('sympy/functions/elementary/integers.py','floor._eval_const_number'),
('sympy/functions/elementary/integers.py','ceiling._eval_const_number'),
('sympy/functions/elementary/integers.py','frac.eval'),
('sympy/functions/elementary/trigonometric.py','acsc.taylor_term'),
('sympy/functions/elementary/trigonometric.py','asec.taylor_term'),
('sympy/functions/elementary/trigonometric.py','acos.taylor_term'),
('sympy/functions/elementary/trigonometric.py','asin.taylor_term'),
('sympy/functions/elementary/trigonometric.py','csc.taylor_term'),
('sympy/functions/elementary/trigonometric.py','cot.taylor_term'),
('sympy/functions/elementary/trigonometric.py','tan.taylor_term'),
('sympy/functions/elementary/trigonometric.py','sec.taylor_term'),
('sympy/functions/elementary/trigonometric.py','acot.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','sinh.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','cosh.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','csch.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','coth.taylor_term'),
('sympy/functions/elementary/hyperbolic.py','tanh.taylor_term'),
('sympy/functions/special/tensor_functions.py','KroneckerDelta.indices_contain_equal_information'),
('sympy/sets/fancysets.py','ImageSet._check_sig'),
('sympy/sets/fancysets.py','Range.reversed'),
('sympy/sets/fancysets.py','Range.size'),
('sympy/sets/fancysets.py','Range.is_iterable'),
('sympy/sets/sets.py','DisjointUnion.is_iterable'),
('sympy/functions/elementary/complexes.py','adjoint._pretty'),
('sympy/functions/elementary/complexes.py','principal_branch._eval_evalf'),
('sympy/matrices/expressions/blockmatrix.py','BlockMatrix.shape'),
('sympy/matrices/expressions/matexpr.py','MatrixExpr.is_square'),
])

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def apply(root):
    root=Path(root);before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    by={}
    for rel,q in SELECT:by.setdefault(rel,set()).add(q)
    saved=0;cut=[]
    for rel,qs in by.items():
        p=root/rel;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);stack=[];reps=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n):stack.append(n.name);self.generic_visit(n);stack.pop()
            def visit_FunctionDef(self,n):
                q='.'.join(stack+[n.name])
                if q in qs:
                    a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
                    old=''.join(lines[a:b]);new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
                    reps.append((a,b,new,q,len(old.encode())-len(new.encode())));return
                stack.append(n.name);self.generic_visit(n);stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree)
        found={r[3] for r in reps}
        if found!=qs:raise RuntimeError((rel,qs,found))
        for a,b,new,q,s in sorted(reps,reverse=True):lines[a:b]=[new];saved+=s;cut.append((rel,q,s))
        out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return after,saved,sorted(cut)

if __name__=='__main__':
    import sys
    print(json.dumps(dict(zip(['manifest','saved','cut'],apply(sys.argv[1]))),indent=2))
