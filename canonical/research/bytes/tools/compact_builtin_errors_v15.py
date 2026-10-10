from pathlib import Path
import ast,hashlib,json
BASE='a08322767e870d97082745e22b2757a5efcafdeefb84b4911bf5de382111178a';TARGET='8fa8d5f6e4a957d35bbf8c1edb82ff0cb068ecbba77bc1550f082363f7abc635'
SAFE={'ValueError','TypeError','NotImplementedError','ZeroDivisionError','RuntimeError','AssertionError','IndexError','KeyError','AttributeError','StopIteration','OverflowError','ArithmeticError'}
def manifest(root):
 items=[]
 for p in sorted(Path(root).rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class T(ast.NodeTransformer):
 def visit_Raise(self,n):
  self.generic_visit(n);e=n.exc
  if isinstance(e,ast.Call) and isinstance(e.func,ast.Name) and e.func.id in SAFE and (e.args or e.keywords):e.args=[];e.keywords=[]
  return n
 def visit_Assert(self,n):
  self.generic_visit(n);n.msg=None;return n
def apply(root):
 root=Path(root);before=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 for p in sorted(root.rglob('*.py')):
  tree=ast.parse(p.read_text());tree=T().visit(tree);ast.fix_missing_locations(tree);out=ast.unparse(tree)+'\n';compile(out,str(p),'exec');p.write_text(out)
 after=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 return after