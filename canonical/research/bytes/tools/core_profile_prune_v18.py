from pathlib import Path
import ast, hashlib, json
BASE='9dc4ad75c82f466c197b070d99935828bb6c62bf278fa864d57e3c420e2c14ed'
TARGET='74a2c8eb3caf941c1efc80beb39018e4577565ae40e5b9c952cc52491a453e6d'
SELECT={
('sympy/core/expr.py','Expr._random'),('sympy/core/expr.py','Expr.equals'),('sympy/core/expr.py','Expr.dir'),('sympy/core/expr.py','Expr.extract_additively'),('sympy/core/expr.py','Expr.extract_branch_factor'),('sympy/core/expr.py','Expr.round'),
('sympy/core/basic.py','_atomic'),
('sympy/core/operations.py','AssocOpDispatcher.dispatch'),('sympy/core/operations.py','AssocOpDispatcher.__doc__'),
('sympy/core/evalf.py','get_integer_part'),('sympy/core/evalf.py','get_integer_part.calc_part'),('sympy/core/evalf.py','hypsum'),
('sympy/core/function.py','Function.fdiff'),('sympy/core/function.py','Derivative._sort_variable_count._block'),('sympy/core/function.py','Lambda._check_signature'),('sympy/core/function.py','Subs.doit'),('sympy/core/function.py','nfloat'),
('sympy/core/numbers.py','comp'),('sympy/core/numbers.py','_literal_float'),('sympy/core/numbers.py','Number.__divmod__'),('sympy/core/numbers.py','Float.__mod__'),('sympy/core/numbers.py','all_close'),('sympy/core/numbers.py','all_close._all_close_ac')}
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
