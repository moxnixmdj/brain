from pathlib import Path
import ast,hashlib,json
BASE='89b2b2d8cfed14ef37442a87ff95a861362f50bf3a2e8210d2c4a6abb0891a14';TARGET='a08322767e870d97082745e22b2757a5efcafdeefb84b4911bf5de382111178a'
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class T(ast.NodeTransformer):
 def visit_FunctionDef(self,n):
  self.generic_visit(n)
  for a in list(n.args.posonlyargs)+list(n.args.args)+list(n.args.kwonlyargs):a.annotation=None
  if n.args.vararg:n.args.vararg.annotation=None
  if n.args.kwarg:n.args.kwarg.annotation=None
  n.returns=None;n.type_comment=None;return n
 visit_AsyncFunctionDef=visit_FunctionDef
 def visit_AnnAssign(self,n):
  self.generic_visit(n)
  return None if n.value is None else ast.copy_location(ast.Assign(targets=[n.target],value=n.value),n)
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 for p in sorted(root.rglob('*.py')):
  tree=ast.parse(p.read_text(),type_comments=True);tree=T().visit(tree);ast.fix_missing_locations(tree);out=ast.unparse(tree)+'\n';compile(out,str(p),'exec');p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 return after