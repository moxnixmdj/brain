from pathlib import Path
import ast, hashlib, json
BASE='74a2c8eb3caf941c1efc80beb39018e4577565ae40e5b9c952cc52491a453e6d'
TARGET='0327ae08f5ac9e0bbbe92d74fc1e4aa114c1bae9c0f94a0e5dedc96a1032137f'
SELECT={
('sympy/core/add.py','Add.extract_leading_order'),
('sympy/core/basic.py','Basic.matches'),('sympy/core/basic.py','Basic.rewrite'),
('sympy/core/evalf.py','get_abs'),('sympy/core/evalf.py','evalf_trig'),('sympy/core/evalf.py','evalf_log'),('sympy/core/evalf.py','do_integral'),('sympy/core/evalf.py','evalf_sum'),
('sympy/core/expr.py','Expr.is_constant'),('sympy/core/expr.py','Expr._eval_interval'),('sympy/core/expr.py','Expr.as_coefficients_dict'),('sympy/core/expr.py','Expr.series.yield_lseries'),('sympy/core/expr.py','Expr.aseries'),
('sympy/core/function.py','Function._eval_evalf'),('sympy/core/function.py','Function._eval_nseries'),('sympy/core/function.py','Derivative._eval_subs'),('sympy/core/function.py','Subs._eval_subs'),
('sympy/core/mul.py','Mul.matches'),('sympy/core/mul.py','Mul._matches_noncomm'),('sympy/core/mul.py','Mul._matches_new_states'),('sympy/core/mul.py','Mul._combine_inverse'),
('sympy/core/numbers.py','NegativeInfinity._eval_power'),('sympy/core/numbers.py','Exp1._eval_power_exp_is_pow'),
('sympy/core/operations.py','AssocOp._matches_commutative'),
('sympy/core/power.py','Pow._eval_Mod'),('sympy/core/power.py','Pow._eval_subs._check'),('sympy/core/power.py','Pow.matches')}
FILES=sorted({r for r,_ in SELECT})
def manifest(root):
    items=[]
    for p in sorted(Path(root).rglob('*.py')):
        b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest()
class T(ast.NodeTransformer):
    def __init__(self,rel):self.rel=rel;self.stack=[];super().__init__()
    def visit_ClassDef(self,n):
        self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
    def visit_FunctionDef(self,n):
        q='.'.join(self.stack+[n.name])
        if (self.rel,q) in SELECT:
            n.body=[ast.Raise(exc=ast.Call(func=ast.Name(id='NotImplementedError',ctx=ast.Load()),args=[],keywords=[]),cause=None)]
            return n
        self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
    visit_AsyncFunctionDef=visit_FunctionDef
def apply(root):
    root=Path(root);before=manifest(root)
    if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
    for rel in FILES:
        p=root/rel;tree=T(rel).visit(ast.parse(p.read_text()));ast.fix_missing_locations(tree);out=ast.unparse(tree)+'\n';compile(out,str(p),'exec');p.write_text(out)
    after=manifest(root)
    if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
    return after
