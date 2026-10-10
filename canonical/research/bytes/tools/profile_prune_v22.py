from pathlib import Path
import ast,hashlib,json
BASE="0fa7fd19f6a674e493954d48f7438285dbab4fd9eefe559a3d537ca9834c6022"
TARGET="84a4947df1815c9dd5e9a82ba25670ee051f6a7bb3e05f904e17445fe8abd6e4"
SELECT=set(tuple(x) for x in [
('sympy/matrices/sparse.py','SparseRepMatrix._handle_creation_inputs'),
('sympy/simplify/simplify.py','besselsimp'),
('sympy/simplify/hyperexpand.py','devise_plan'),
('sympy/simplify/hyperexpand.py','Formula.find_instantiations'),
('sympy/simplify/hyperexpand.py','devise_plan_meijer'),
('sympy/simplify/hyperexpand.py','build_hypergeometric_formula'),
('sympy/functions/special/elliptic_integrals.py','elliptic_pi.eval'),
('sympy/functions/special/bessel.py','besseli.eval'),
('sympy/functions/special/bessel.py','besselj.eval'),
('sympy/utilities/iterables.py','multiset_partitions'),
('sympy/utilities/iterables.py','random_derangement'),
('sympy/utilities/iterables.py','partitions'),
('sympy/utilities/iterables.py','ordered_partitions'),
('sympy/utilities/iterables.py','multiset_combinations'),
('sympy/utilities/iterables.py','generate_bell'),
('sympy/utilities/iterables.py','kbins'),
('sympy/printing/str.py','StrPrinter._print_Poly'),
('sympy/printing/str.py','StrPrinter._print_Permutation'),
('sympy/functions/combinatorial/numbers.py','mobius.eval'),
('sympy/ntheory/factor_.py','smoothness_p'),
('sympy/ntheory/factor_.py','multiplicity'),
('sympy/ntheory/generate.py','composite'),
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
