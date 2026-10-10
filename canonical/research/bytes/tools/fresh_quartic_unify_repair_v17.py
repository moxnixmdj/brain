from pathlib import Path
import ast,hashlib,json
BASE="b1729c4e2e5e4d3729d8b829ab5c9115821b00bfbed5322c1e8536b9bb86cfee"
TARGET="9dc4ad75c82f466c197b070d99935828bb6c62bf278fa864d57e3c420e2c14ed"
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob("*.py")):
  b=p.read_bytes();items.append({"path":p.relative_to(root).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
 return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(",",":")).encode()).hexdigest()
class DomainFix(ast.NodeTransformer):
 def __init__(self): self.stack=[];super().__init__()
 def visit_ClassDef(self,n):
  self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 def visit_FunctionDef(self,n):
  q=".".join(self.stack+[n.name])
  if q=="Domain.unify_with_symbols":
   n.body=ast.parse("if K0.is_Composite and set(K0.symbols) & set(symbols) or K1.is_Composite and set(K1.symbols) & set(symbols):\n    raise UnificationFailed('Cannot unify %s with %s, given %s generators' % (K0, K1, tuple(symbols)))\nreturn K0.unify(K1)").body
  return self.generic_visit(n)
class PolyFix(ast.NodeTransformer):
 def __init__(self): self.stack=[];super().__init__()
 def visit_ClassDef(self,n):
  self.stack.append(n.name);n=self.generic_visit(n);self.stack.pop();return n
 def visit_FunctionDef(self,n):
  q=".".join(self.stack+[n.name])
  if q=="DMP.sub": n.body=ast.parse("F, G = f.unify_DMP(g)\nreturn F._sub(G)").body
  elif q=="DMP_Python._sub": n.body=ast.parse("return f.per(dmp_sub(f._rep, g._rep, f.lev, f.dom))").body
  return self.generic_visit(n)
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f"base manifest drift: {before}")
 jobs=[(root/'sympy/polys/domains/domain.py',DomainFix()),(root/'sympy/polys/polyclasses.py',PolyFix())]
 for p,t in jobs:
  tree=t.visit(ast.parse(p.read_text()));ast.fix_missing_locations(tree);out=ast.unparse(tree)+"\n";compile(out,str(p),"exec");p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f"target manifest mismatch: {after}")
 return after