from pathlib import Path
import ast,hashlib,json
BASE="84a4947df1815c9dd5e9a82ba25670ee051f6a7bb3e05f904e17445fe8abd6e4"
TARGET="0566f7127b810bfb1e379ccbbd2901255d13fb372063de8df72b7a2a70635223"
SELECT=set(tuple(x) for x in [
('sympy/simplify/radsimp.py','radsimp'),
('sympy/functions/elementary/trigonometric.py','tan.eval'),
('sympy/functions/elementary/exponential.py','log._eval_nseries'),
('sympy/functions/elementary/trigonometric.py','cot.eval'),
('sympy/simplify/simplify.py','nsimplify'),
('sympy/functions/elementary/miscellaneous.py','MinMaxBase._collapse_arguments'),
('sympy/functions/special/gamma_functions.py','uppergamma.eval'),
('sympy/polys/polytools.py','groebner'),
('sympy/polys/polytools.py','poly'),
('sympy/functions/elementary/complexes.py','principal_branch.eval'),
('sympy/functions/elementary/trigonometric.py','asin._eval_nseries'),
('sympy/functions/elementary/trigonometric.py','acos._eval_nseries'),
('sympy/simplify/radsimp.py','collect_const'),
('sympy/functions/elementary/hyperbolic.py','acosh.eval'),
('sympy/simplify/simplify.py','_separatevars'),
('sympy/functions/elementary/trigonometric.py','acsc._eval_nseries'),
('sympy/functions/elementary/trigonometric.py','asec._eval_nseries'),
('sympy/polys/polytools.py','lcm_list'),
('sympy/matrices/matrixbase.py','MatrixBase.diag'),
('sympy/functions/elementary/hyperbolic.py','coth.eval'),
])
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest()
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 by={}
 for r,q in SELECT:by.setdefault(r,set()).add(q)
 for rel,qs in by.items():
  p=root/rel;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);stack=[];reps=[]
  class V(ast.NodeVisitor):
   def visit_ClassDef(self,n):stack.append(n.name);self.generic_visit(n);stack.pop()
   def visit_FunctionDef(self,n):
    q='.'.join(stack+[n.name])
    if q in qs:
     a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
     reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q));return
    stack.append(n.name);self.generic_visit(n);stack.pop()
   visit_AsyncFunctionDef=visit_FunctionDef
  V().visit(tree);found={x[3] for x in reps}
  if found!=qs:raise RuntimeError((rel,qs,found))
  for a,b,new,q in sorted(reps,reverse=True):lines[a:b]=[new]
  out=''.join(lines);compile(out,str(p),'exec');p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 items=[]
 for q in sorted(root.rglob('*.py')):
  b=q.read_bytes();items.append({'path':q.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return after
