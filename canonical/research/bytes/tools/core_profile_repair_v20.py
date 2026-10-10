from pathlib import Path
import ast,hashlib,json,zlib,base64,copy
BASE="0327ae08f5ac9e0bbbe92d74fc1e4aa114c1bae9c0f94a0e5dedc96a1032137f"
TARGET="45adf82ebe04814cdb5827821ee9d079f48dbc5f58d35f8b7a4a6d4e512deacb"
SELECT=set(tuple(x) for x in [('sympy/core/mod.py', 'Mod.eval'), ('sympy/core/relational.py', 'Relational.canonical'), ('sympy/core/kind.py', 'KindDispatcher.dispatch_kinds'), ('sympy/core/logic.py', 'Logic.fromstring'), ('sympy/core/numbers.py', 'Infinity._eval_power'), ('sympy/core/function.py', 'Subs._eval_derivative'), ('sympy/core/add.py', 'Add._combine_inverse'), ('sympy/core/expr.py', 'Expr._eval_lseries'), ('sympy/core/basic.py', 'Basic._rewrite'), ('sympy/core/expr.py', 'Expr.__int__'), ('sympy/core/power.py', 'Pow._eval_rewrite_as_exp'), ('sympy/core/evalf.py', 'evalf_integral'), ('sympy/core/power.py', 'Pow.is_constant'), ('sympy/core/evalf.py', 'chop_parts'), ('sympy/core/basic.py', 'Basic.dummy_eq'), ('sympy/core/evalf.py', 'check_convergence'), ('sympy/core/power.py', 'Pow._eval_transpose'), ('sympy/core/evalf.py', 'evalf_symbol'), ('sympy/core/power.py', 'Pow.taylor_term'), ('sympy/core/function.py', 'Lambda._match_signature'), ('sympy/core/evalf.py', 'evalf_piecewise'), ('sympy/core/power.py', 'Pow._eval_rewrite_as_sqrt'), ('sympy/core/numbers.py', 'Integer.__rdivmod__')])
PAYLOAD=json.loads(zlib.decompress(base64.b64decode('eNqlVm1v2zYQ/iucv1hqFTkpsC9BXcDoEixA4xaNWwxwA4GRKYeYSAqk7Fjd9t97R4o2JdkJuvKDxJd7eXh8eMd/RqYRVTPJlWaTYiPzmiuZVs2/176fsS0t7acYXY5WrCDBTGRYWSSk0iyPL7/Jb5JAszJrVmeiErR+zNBsVEgqGMqQtvGCcMOlqanMWWtnVlUlZ6svEkyEstg0qzdakrmSrGNEqpo8UkPrWkfOYUIGzrDZSTIlt59uZ4s/s8Xn2fzuw2xx83F+lwJahzCxDuKuJnhxytzY5Z7hk+jaSTB+BJ0Tc7F0K4DNi7pwjMPVcQcaL7qqQ2QYdbA4OAg0nWIvzTIEkmXBbqleG1CyMth3K6w0fcuJFw1RRAdw1vsQFBfVkV3CbDYeRB4JAuLHY3403rVujotdl4rWEViLXi156phrOUsKpQknXB62fB+3fD5YYrucVTWJFk3FrrRWOiFfablx/Rd52kXVhm0J/zSrlY8ceiSvye8OESwiJgvH3yp/sx7oKhIDbmsliKeCqJSuYQSxFVU+oHJw6wRKDG4aNgEYRQroiuwk2cXy4p78NiUXhMoVjM5gOIVhV4GVR3zmR30mRHq3+c+7tcNI+tXYj/163MdlnrnI1xSWO1yksokiDD5tz8ifUDxgAOWGBQxpL5Ej0WH6sp8o3PiJwxm6o0yflP4bmRH5BOsVthAne5tfWQRuoYV+tat0miEjPLm2LaNHSZjt7TXAVG87Wa35uk3whwmvmhBVYTUwHoQlnDWW+qphUlYywWRNdZOispJKMOjknpK5MgkBJiQEqLBPFQE3wBvIxMMshjyEFZ+OBlowOKEFKye1oHNCa4+vxxJ3tHNV34jKbZatgjPGezslW5tHluf3bnJn7/aUtFf8zbk/rQTiksA/o3mOffyDnEtPYCJxqofYH0ImuoV0bDYPZoyEbEV7jNxaVCgUtQJLp3IfD6qVc78N676jX58JezRYgTU7WdqHhxp4iwrIky71e/u9MvDyaYfm5oG5w/d5cz0a/KS5QRZ5gSM7w7/jM6Sgpi7VOtJBSXdrb8nFIDdAoPC6632UtFzFJ+O2N/UO8t55YKzHRSsUuvqflHx65CXroG58guoiDgR6YWiCtTXFV8JZ00UHUDaa5mjZbeOs3eQZKnRztRd9a31fDmpgC9+++8Zbph+UYeNjNanSXILI3c188v7j3WQxm8NDxZuHt8sTxeMd+z2OAQkM4BufsgU138DbB5QvzuPhQ9Nt7V0XoaB2Giz/cXU9+/Jhkd3O/vr0+ep9fLqCoQdHjwPcI29b5+/1tBvDX2KDb7mSNZcb9vxt6aMNyAz1ylWwSckfRIVfKDFAK6xabXJvS1Y7inYB26ZabeQqQ4b5OPknhCsnA42EvHnZKSgGTmH0y04v4tF/PwC/gw7L')))
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob("*.py")):
  b=p.read_bytes();items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode();return hashlib.sha256(mb).hexdigest()
class Stub(ast.NodeTransformer):
 def __init__(self,rel):self.rel=rel;self.stack=[]
 def visit_ClassDef(self,n):self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 def visit_FunctionDef(self,n):
  q=".".join(self.stack+[n.name])
  if (self.rel,q) in SELECT:
   n.body=[ast.Raise(exc=ast.Call(func=ast.Name(id="NotImplementedError",ctx=ast.Load()),args=[],keywords=[]),cause=None)];return n
  self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 visit_AsyncFunctionDef=visit_FunctionDef
class Restore(ast.NodeTransformer):
 def __init__(self,rel):self.rel=rel;self.stack=[]
 def visit_ClassDef(self,n):self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 def visit_FunctionDef(self,n):
  q=".".join(self.stack+[n.name]);key=self.rel+"|"+q
  if key in PAYLOAD:return ast.parse(PAYLOAD[key]).body[0]
  self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 visit_AsyncFunctionDef=visit_FunctionDef
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f"base manifest drift: {before}")
 rels=sorted(set([r for r,_ in SELECT]+[k.split("|",1)[0] for k in PAYLOAD]))
 for rel in rels:
  p=root/rel;t=ast.parse(p.read_text());t=Stub(rel).visit(t);ast.fix_missing_locations(t);t=Restore(rel).visit(t);ast.fix_missing_locations(t);out=ast.unparse(t)+"\n";compile(out,str(p),"exec");p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f"target manifest mismatch: {after}")
 return after
