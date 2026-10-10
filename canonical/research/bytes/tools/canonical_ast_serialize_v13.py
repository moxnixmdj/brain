from pathlib import Path
import ast, hashlib, json
BASE_MANIFEST='e034fc543027ca55a3a5f01b4bc3fec4869952ef7e3e7a06dd8cc08cdc92edce'
TARGET_MANIFEST='89b2b2d8cfed14ef37442a87ff95a861362f50bf3a2e8210d2c4a6abb0891a14'
class StripDocs(ast.NodeTransformer):
    def _body(self,node):
        b=node.body
        if b and isinstance(b[0],ast.Expr) and isinstance(getattr(b[0],'value',None),ast.Constant) and isinstance(b[0].value.value,str):
            node.body=b[1:] or [ast.Pass()]
        return node
    def visit_Module(self,node): self.generic_visit(node); return self._body(node)
    def visit_FunctionDef(self,node): self.generic_visit(node); return self._body(node)
    def visit_AsyncFunctionDef(self,node): self.generic_visit(node); return self._body(node)
    def visit_ClassDef(self,node): self.generic_visit(node); return self._body(node)
def manifest(root):
    items=[]
    for p in sorted(Path(root).rglob('*.py')):
        b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items
def apply(root):
    root=Path(root); before,_=manifest(root)
    if before!=BASE_MANIFEST: raise RuntimeError(f'base manifest drift: {before}')
    for p in sorted(root.rglob('*.py')):
        tree=ast.parse(p.read_text(),type_comments=True); tree=StripDocs().visit(tree); ast.fix_missing_locations(tree)
        out=(ast.unparse(tree)+'\n'); compile(out,str(p),'exec'); p.write_text(out)
    after,_=manifest(root)
    if after!=TARGET_MANIFEST: raise RuntimeError(f'target manifest mismatch: {after}')
    return after
