from pathlib import Path
import ast, hashlib, json
BASE="44e43221928b763c60eacd0a39c50e067ded82c66151886829d7cc58d037b3b9"
TARGET="6b7eee6f8a15670189e06ffda61d9149ea5e5a58ec158ce23f396ac50edf34eb"
SELECT=set(tuple(x) for x in [
("sympy/functions/elementary/trigonometric.py","acot._eval_nseries"),
("sympy/functions/elementary/trigonometric.py","acot._eval_as_leading_term"),
("sympy/functions/elementary/hyperbolic.py","acoth.eval"),
("sympy/functions/elementary/hyperbolic.py","asech.eval"),
("sympy/utilities/iterables.py","binary_partitions"),
("sympy/functions/elementary/trigonometric.py","atan._eval_as_leading_term"),
("sympy/functions/elementary/trigonometric.py","acsc._eval_as_leading_term"),
("sympy/functions/special/zeta_functions.py","polylog.eval"),
("sympy/functions/elementary/hyperbolic.py","acsch.eval"),
])
def manifest(root):
 items=[];root=Path(root)
 for p in sorted(root.rglob("*.py")):
  b=p.read_bytes();items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode();return hashlib.sha256(mb).hexdigest()
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f"base manifest drift: {before}")
 by={}
 for rel,q in SELECT:by.setdefault(rel,set()).add(q)
 for rel,qs in by.items():
  p=root/rel;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);stack=[];reps=[]
  class V(ast.NodeVisitor):
   def visit_ClassDef(self,n):stack.append(n.name);self.generic_visit(n);stack.pop()
   def visit_FunctionDef(self,n):
    q=".".join(stack+[n.name])
    if q in qs:
     a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=" "*n.body[0].col_offset
     reps.append((a,b,ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n',q));return
    stack.append(n.name);self.generic_visit(n);stack.pop()
   visit_AsyncFunctionDef=visit_FunctionDef
  V().visit(tree);found={x[3] for x in reps}
  if found!=qs:raise RuntimeError((rel,qs,found))
  for a,b,new,q in sorted(reps,reverse=True):lines[a:b]=[new]
  out="".join(lines);compile(out,str(p),"exec");p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f"target manifest mismatch: {after}")
 items=[]
 for q in sorted(root.rglob("*.py")):
  b=q.read_bytes();items.append({"path":q.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(",",":")).encode();(root/"BRAIN_SLICE_MANIFEST.json").write_bytes(mb+b"\n")
 return after
if __name__=="__main__":
 import sys;print(apply(sys.argv[1]))
