from pathlib import Path
import ast, hashlib, json
BASE='c93cd3aabe9fc5d1a66cf3e6090ab1f937c63e1eaa83beb68040a1a8faa99dee'
TARGET='f6c950d49791f05fbfc1e8985fde4c1b623b8087b62f89fc7d4a30f78e39e97a'
SELECT=set(tuple(x) for x in [
('sympy/functions/elementary/complexes.py', 'Abs._eval_derivative'),
('sympy/functions/elementary/complexes.py', 'Abs._eval_nseries'),
('sympy/functions/elementary/complexes.py', 'Abs._eval_power'),
('sympy/functions/elementary/complexes.py', 'adjoint.eval'),
('sympy/functions/elementary/complexes.py', 'arg._eval_as_leading_term'),
('sympy/functions/elementary/complexes.py', 'periodic_argument._eval_evalf'),
('sympy/functions/elementary/complexes.py', 'polarify'),
('sympy/functions/elementary/complexes.py', 'sign._eval_derivative'),
('sympy/functions/elementary/complexes.py', 'sign._eval_nseries'),
('sympy/functions/elementary/complexes.py', 'unpolarify'),
('sympy/functions/elementary/exponential.py', 'ExpBase._eval_is_rational'),
('sympy/functions/elementary/exponential.py', 'LambertW._eval_as_leading_term'),
('sympy/functions/elementary/exponential.py', 'LambertW._eval_is_algebraic'),
('sympy/functions/elementary/exponential.py', 'LambertW._eval_is_extended_real'),
('sympy/functions/elementary/exponential.py', 'LambertW.fdiff'),
('sympy/functions/elementary/exponential.py', 'exp._eval_is_algebraic'),
('sympy/functions/elementary/exponential.py', 'exp._eval_is_extended_positive'),
('sympy/functions/elementary/exponential.py', 'exp._eval_refine'),
('sympy/functions/elementary/exponential.py', 'exp._eval_rewrite_as_Pow'),
('sympy/functions/elementary/exponential.py', 'exp._eval_rewrite_as_sqrt'),
('sympy/functions/elementary/exponential.py', 'exp.taylor_term'),
('sympy/functions/elementary/exponential.py', 'log.taylor_term'),
('sympy/functions/elementary/trigonometric.py', 'InverseTrigonometricFunction._acsc_table'),
('sympy/functions/elementary/trigonometric.py', 'InverseTrigonometricFunction._asin_table'),
('sympy/functions/elementary/trigonometric.py', 'TrigonometricFunction._as_real_imag'),
('sympy/functions/elementary/trigonometric.py', 'TrigonometricFunction._eval_is_algebraic'),
('sympy/functions/elementary/trigonometric.py', 'TrigonometricFunction._eval_is_rational'),
('sympy/functions/elementary/trigonometric.py', 'TrigonometricFunction._period'),
('sympy/functions/elementary/trigonometric.py', 'acos._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'asec._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'asin._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'atan._eval_nseries'),
('sympy/functions/elementary/trigonometric.py', 'cot._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'cot._eval_rewrite_as_exp'),
('sympy/functions/elementary/trigonometric.py', 'cot.as_real_imag'),
('sympy/functions/elementary/trigonometric.py', 'csc._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'sec._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'tan._eval_as_leading_term'),
('sympy/functions/elementary/trigonometric.py', 'tan._eval_rewrite_as_exp'),
('sympy/functions/elementary/trigonometric.py', 'tan.as_real_imag'),
('sympy/functions/special/tensor_functions.py', 'KroneckerDelta.is_above_fermi'),
('sympy/functions/special/tensor_functions.py', 'KroneckerDelta.is_below_fermi'),
('sympy/sets/sets.py', 'Complement.is_finite_set'),
('sympy/sets/sets.py', 'Complement.reduce'),
('sympy/sets/sets.py', 'Interval.is_empty'),
('sympy/sets/sets.py', 'SymmetricDifference.reduce'),
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
