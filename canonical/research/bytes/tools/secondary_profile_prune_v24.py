from pathlib import Path
import ast,hashlib,json
BASE="0566f7127b810bfb1e379ccbbd2901255d13fb372063de8df72b7a2a70635223"
TARGET="eb71ab231a6281de6133082c59eb9732864e68af42daf4cfb6c6f258c3dea1f9"
SELECT=set(tuple(x) for x in [
('sympy/functions/elementary/complexes.py','Abs.eval'),
('sympy/series/gruntz.py','mrv'),
('sympy/sets/sets.py','Intersection._handle_finite_sets'),
('mpmath/libmp/libmpf.py','to_str'),
('sympy/functions/elementary/exponential.py','exp._eval_nseries'),
('sympy/external/ntheory.py','_lucas_sequence'),
('sympy/functions/elementary/trigonometric.py','acos.eval'),
('sympy/functions/combinatorial/factorials.py','RisingFactorial.eval'),
('sympy/functions/elementary/trigonometric.py','asin.eval'),
('sympy/functions/elementary/trigonometric.py','acot.eval'),
('sympy/functions/elementary/hyperbolic.py','tanh.eval'),
('sympy/series/gruntz.py','rewrite'),
('sympy/functions/elementary/hyperbolic.py','atanh.eval'),
('sympy/simplify/simplify.py','_real_to_rational'),
('sympy/polys/rootoftools.py','RootSum._rational_case'),
('sympy/functions/special/gamma_functions.py','lowergamma.eval'),
('sympy/tensor/array/ndim_array.py','NDimArray._handle_ndarray_creation_inputs'),
('sympy/simplify/simplify.py','sum_add'),
('sympy/functions/elementary/trigonometric.py','asec.eval'),
('sympy/functions/elementary/hyperbolic.py','sinh.eval'),
('sympy/functions/elementary/hyperbolic.py','cosh.eval'),
('sympy/functions/elementary/trigonometric.py','cos._eval_rewrite_as_sqrt'),
('sympy/polys/polytools.py','terms_gcd'),
('sympy/functions/combinatorial/numbers.py','euler.eval'),
('sympy/functions/combinatorial/numbers.py','harmonic.eval'),
('sympy/utilities/iterables.py','multiset_permutations'),
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
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();(root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return after
